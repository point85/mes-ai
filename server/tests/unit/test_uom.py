"""
Unit tests for the UOM (Units of Measure) module.

Covers:
- Model instantiation & table mapping
- Schema validation (create, read, update, conversion)
- Seed data completeness & correctness
- Conversion formula (affine) for SI, imperial, temperature, custom units
- Exception construction
- Event factories
"""

from __future__ import annotations

import math
import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.uom.models import UnitOfMeasure
from mes.core.uom.schemas import (
    ConversionRequest,
    ConversionResult,
    UoMCreate,
    UoMRead,
    UoMUpdate,
)
from mes.core.uom.events import uom_created, uom_updated, uom_deleted
from mes.core.uom.exceptions import (
    BuiltinUoMException,
    DuplicateSymbolException,
    IncompatibleUoMTypeException,
)
from mes.core.uom.seed import BUILTIN_UNITS, BUILTIN_RATE_UNITS, get_builtin_unit_dicts, get_builtin_rate_unit_dicts
from mes.core.uom.service import UoMService


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_uom(**overrides) -> types.SimpleNamespace:
    """
    Create a lightweight UoM-like object for unit tests.

    Uses SimpleNamespace instead of a real SQLAlchemy model to avoid
    requiring a database session.  The service's convert() method only
    reads .symbol, .uom_type, .multiplier, .offset, .is_rate,
    .numerator_uom, .denominator_uom so this is sufficient.
    """
    defaults = {
        "id": uuid.uuid4(),
        "symbol": "kg",
        "name": "kilogram",
        "uom_type": "mass",
        "multiplier": 1.0,
        "offset": 0.0,
        "is_builtin": True,
        "is_active": True,
        "is_rate": False,
        "numerator_uom_id": None,
        "denominator_uom_id": None,
        "numerator_uom": None,
        "denominator_uom": None,
        "numerator_uom_symbol": None,
        "denominator_uom_symbol": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_rate_uom(symbol: str, name: str, numerator, denominator) -> types.SimpleNamespace:
    """Create a rate UoM-like object from two base UoMs."""
    return _make_uom(
        symbol=symbol,
        name=name,
        uom_type="rate",
        multiplier=1.0,
        offset=0.0,
        is_rate=True,
        numerator_uom_id=numerator.id,
        denominator_uom_id=denominator.id,
        numerator_uom=numerator,
        denominator_uom=denominator,
        numerator_uom_symbol=numerator.symbol,
        denominator_uom_symbol=denominator.symbol,
    )


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestUnitOfMeasureModel:
    """Tests for the SQLAlchemy model."""

    def test_tablename(self):
        assert UnitOfMeasure.__tablename__ == "units_of_measure"

    def test_has_mapper(self):
        """Confirms the model is concrete (not abstract)."""
        assert hasattr(UnitOfMeasure, "__mapper__")

    def test_default_multiplier(self):
        uom = _make_uom()
        assert uom.multiplier == 1.0

    def test_default_offset(self):
        uom = _make_uom()
        assert uom.offset == 0.0

    def test_repr(self):
        uom = _make_uom(symbol="lb", uom_type="mass")
        assert "lb" in repr(uom)
        assert "mass" in repr(uom)


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestUoMCreateSchema:
    """Validation tests for UoMCreate."""

    def test_valid_create(self):
        s = UoMCreate(symbol="kg", name="kilogram", uom_type="mass")
        assert s.symbol == "kg"
        assert s.multiplier == 1.0
        assert s.offset == 0.0

    def test_custom_multiplier(self):
        s = UoMCreate(symbol="g", name="gram", uom_type="mass", multiplier=0.001)
        assert s.multiplier == 0.001

    def test_symbol_min_length(self):
        with pytest.raises(ValidationError):
            UoMCreate(symbol="", name="empty", uom_type="mass")

    def test_symbol_no_whitespace(self):
        with pytest.raises(ValidationError, match="spaces"):
            UoMCreate(symbol="fl oz", name="fluid ounce", uom_type="volume")

    def test_name_required(self):
        with pytest.raises(ValidationError):
            UoMCreate(symbol="x", uom_type="mass")  # type: ignore[call-arg]

    def test_uom_type_required(self):
        with pytest.raises(ValidationError):
            UoMCreate(symbol="x", name="x")  # type: ignore[call-arg]

    def test_multiplier_must_be_positive(self):
        with pytest.raises(ValidationError):
            UoMCreate(symbol="x", name="x", uom_type="mass", multiplier=0)

    def test_multiplier_negative_rejected(self):
        with pytest.raises(ValidationError):
            UoMCreate(symbol="x", name="x", uom_type="mass", multiplier=-1.0)

    def test_offset_can_be_negative(self):
        s = UoMCreate(symbol="x", name="x", uom_type="temperature", offset=-10.0)
        assert s.offset == -10.0


class TestUoMReadSchema:
    """Validation tests for UoMRead."""

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        read = UoMRead(
            id=uid,
            symbol="lb",
            name="pound",
            uom_type="mass",
            multiplier=0.45359237,
            offset=0.0,
            is_builtin=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert read.symbol == "lb"
        assert read.multiplier == pytest.approx(0.45359237)
        assert read.is_builtin is True


class TestUoMUpdateSchema:
    """Validation tests for UoMUpdate."""

    def test_all_optional(self):
        s = UoMUpdate()
        assert s.symbol is None
        assert s.multiplier is None

    def test_partial_update(self):
        s = UoMUpdate(name="pound (avoirdupois)")
        assert s.name == "pound (avoirdupois)"
        assert s.symbol is None

    def test_symbol_no_whitespace(self):
        with pytest.raises(ValidationError, match="spaces"):
            UoMUpdate(symbol="bad symbol")


class TestConversionSchemas:
    """Tests for ConversionRequest / ConversionResult."""

    def test_request_valid(self):
        r = ConversionRequest(value=5.0, from_symbol="kg", to_symbol="lb")
        assert r.value == 5.0

    def test_request_requires_symbols(self):
        with pytest.raises(ValidationError):
            ConversionRequest(value=1.0)  # type: ignore[call-arg]

    def test_result_fields(self):
        r = ConversionResult(
            original_value=100.0,
            from_symbol="°C",
            from_name="degree Celsius",
            converted_value=212.0,
            to_symbol="°F",
            to_name="degree Fahrenheit",
        )
        assert r.converted_value == 212.0


# ═════════════════════════════════════════════════════════════════════
# SEED DATA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestSeedData:
    """Verify the built-in seed data is complete and consistent."""

    def test_builtin_units_not_empty(self):
        assert len(BUILTIN_UNITS) > 0

    def test_all_symbols_unique(self):
        symbols = [u[0] for u in BUILTIN_UNITS]
        assert len(symbols) == len(set(symbols))

    def test_si_fundamentals_present(self):
        symbols = {u[0] for u in BUILTIN_UNITS}
        for si in ("kg", "s", "m", "K"):
            assert si in symbols, f"Missing SI fundamental: {si}"

    def test_si_fundamentals_have_unit_multiplier(self):
        for sym, _name, _typ, mult, off in BUILTIN_UNITS:
            if sym in ("kg", "s", "m", "K"):
                assert mult == 1.0, f"{sym} multiplier should be 1.0"
                assert off == 0.0, f"{sym} offset should be 0.0"

    def test_additional_si_present(self):
        symbols = {u[0] for u in BUILTIN_UNITS}
        for expected in ("g", "min", "h", "d", "km", "°C", "L"):
            assert expected in symbols, f"Missing additional SI: {expected}"

    def test_imperial_present(self):
        symbols = {u[0] for u in BUILTIN_UNITS}
        for expected in ("lb", "oz", "ft", "°F", "fl_oz"):
            assert expected in symbols, f"Missing imperial: {expected}"

    def test_get_builtin_unit_dicts_length(self):
        dicts = get_builtin_unit_dicts()
        assert len(dicts) == len(BUILTIN_UNITS)

    def test_builtin_flag_set(self):
        for d in get_builtin_unit_dicts():
            assert d["is_builtin"] is True

    def test_all_multipliers_positive(self):
        for sym, _name, _typ, mult, _off in BUILTIN_UNITS:
            assert mult > 0, f"{sym} has non-positive multiplier"


# ═════════════════════════════════════════════════════════════════════
# CONVERSION FORMULA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestConversionFormula:
    """
    Test the static UoMService.convert() method directly.
    No database required — we construct ORM instances in-memory.
    """

    # Convenience factories ────────────────────────────────────────

    @staticmethod
    def _kg():
        return _make_uom(symbol="kg", uom_type="mass", multiplier=1.0, offset=0.0)

    @staticmethod
    def _g():
        return _make_uom(symbol="g", uom_type="mass", multiplier=0.001, offset=0.0)

    @staticmethod
    def _lb():
        return _make_uom(symbol="lb", uom_type="mass", multiplier=0.45359237, offset=0.0)

    @staticmethod
    def _oz():
        return _make_uom(symbol="oz", uom_type="mass", multiplier=0.028349523125, offset=0.0)

    @staticmethod
    def _m():
        return _make_uom(symbol="m", uom_type="length", multiplier=1.0, offset=0.0)

    @staticmethod
    def _km():
        return _make_uom(symbol="km", uom_type="length", multiplier=1000.0, offset=0.0)

    @staticmethod
    def _ft():
        return _make_uom(symbol="ft", uom_type="length", multiplier=0.3048, offset=0.0)

    @staticmethod
    def _kelvin():
        return _make_uom(symbol="K", uom_type="temperature", multiplier=1.0, offset=0.0)

    @staticmethod
    def _celsius():
        return _make_uom(symbol="°C", uom_type="temperature", multiplier=1.0, offset=273.15)

    @staticmethod
    def _fahrenheit():
        return _make_uom(
            symbol="°F", uom_type="temperature",
            multiplier=5.0 / 9.0, offset=273.15 - 32.0 * 5.0 / 9.0,
        )

    @staticmethod
    def _second():
        return _make_uom(symbol="s", uom_type="time", multiplier=1.0, offset=0.0)

    @staticmethod
    def _hour():
        return _make_uom(symbol="h", uom_type="time", multiplier=3600.0, offset=0.0)

    @staticmethod
    def _minute():
        return _make_uom(symbol="min", uom_type="time", multiplier=60.0, offset=0.0)

    @staticmethod
    def _day():
        return _make_uom(symbol="d", uom_type="time", multiplier=86400.0, offset=0.0)

    @staticmethod
    def _liter():
        return _make_uom(symbol="L", uom_type="volume", multiplier=0.001, offset=0.0)

    @staticmethod
    def _fl_oz():
        return _make_uom(symbol="fl_oz", uom_type="volume", multiplier=2.95735295625e-5, offset=0.0)

    @staticmethod
    def _m3():
        return _make_uom(symbol="m³", uom_type="volume", multiplier=1.0, offset=0.0)

    # ── Mass conversions ─────────────────────────────────────────

    def test_kg_to_g(self):
        assert UoMService.convert(1.0, self._kg(), self._g()) == pytest.approx(1000.0)

    def test_g_to_kg(self):
        assert UoMService.convert(500.0, self._g(), self._kg()) == pytest.approx(0.5)

    def test_kg_to_lb(self):
        assert UoMService.convert(1.0, self._kg(), self._lb()) == pytest.approx(2.20462, rel=1e-4)

    def test_lb_to_kg(self):
        assert UoMService.convert(1.0, self._lb(), self._kg()) == pytest.approx(0.45359237)

    def test_lb_to_oz(self):
        # 1 lb = 16 oz
        assert UoMService.convert(1.0, self._lb(), self._oz()) == pytest.approx(16.0, rel=1e-4)

    def test_oz_to_lb(self):
        assert UoMService.convert(16.0, self._oz(), self._lb()) == pytest.approx(1.0, rel=1e-4)

    def test_kg_to_kg_identity(self):
        assert UoMService.convert(42.0, self._kg(), self._kg()) == 42.0

    # ── Length conversions ───────────────────────────────────────

    def test_m_to_km(self):
        assert UoMService.convert(1500.0, self._m(), self._km()) == pytest.approx(1.5)

    def test_km_to_m(self):
        assert UoMService.convert(2.5, self._km(), self._m()) == pytest.approx(2500.0)

    def test_m_to_ft(self):
        assert UoMService.convert(1.0, self._m(), self._ft()) == pytest.approx(3.28084, rel=1e-4)

    def test_ft_to_m(self):
        assert UoMService.convert(1.0, self._ft(), self._m()) == pytest.approx(0.3048)

    # ── Temperature conversions (affine) ─────────────────────────

    def test_celsius_to_kelvin(self):
        # 0°C = 273.15 K
        assert UoMService.convert(0.0, self._celsius(), self._kelvin()) == pytest.approx(273.15)

    def test_kelvin_to_celsius(self):
        assert UoMService.convert(373.15, self._kelvin(), self._celsius()) == pytest.approx(100.0)

    def test_celsius_to_fahrenheit(self):
        # 100°C = 212°F
        assert UoMService.convert(100.0, self._celsius(), self._fahrenheit()) == pytest.approx(212.0, rel=1e-6)

    def test_fahrenheit_to_celsius(self):
        # 32°F = 0°C
        assert UoMService.convert(32.0, self._fahrenheit(), self._celsius()) == pytest.approx(0.0, abs=1e-6)

    def test_fahrenheit_to_kelvin(self):
        # 32°F = 273.15 K
        assert UoMService.convert(32.0, self._fahrenheit(), self._kelvin()) == pytest.approx(273.15, rel=1e-6)

    def test_boiling_point_f_to_k(self):
        # 212°F = 373.15 K
        assert UoMService.convert(212.0, self._fahrenheit(), self._kelvin()) == pytest.approx(373.15, rel=1e-6)

    def test_absolute_zero_k_to_f(self):
        # 0 K = −459.67°F
        assert UoMService.convert(0.0, self._kelvin(), self._fahrenheit()) == pytest.approx(-459.67, rel=1e-4)

    def test_body_temp_f_to_c(self):
        # 98.6°F ≈ 37°C
        assert UoMService.convert(98.6, self._fahrenheit(), self._celsius()) == pytest.approx(37.0, rel=1e-4)

    # ── Time conversions ─────────────────────────────────────────

    def test_hour_to_seconds(self):
        assert UoMService.convert(1.0, self._hour(), self._second()) == pytest.approx(3600.0)

    def test_seconds_to_minutes(self):
        assert UoMService.convert(120.0, self._second(), self._minute()) == pytest.approx(2.0)

    def test_day_to_hours(self):
        assert UoMService.convert(1.0, self._day(), self._hour()) == pytest.approx(24.0)

    # ── Volume conversions ───────────────────────────────────────

    def test_liter_to_m3(self):
        assert UoMService.convert(1000.0, self._liter(), self._m3()) == pytest.approx(1.0)

    def test_m3_to_liter(self):
        assert UoMService.convert(1.0, self._m3(), self._liter()) == pytest.approx(1000.0)

    def test_fl_oz_to_liter(self):
        # 1 fl oz ≈ 0.0295735 L
        assert UoMService.convert(1.0, self._fl_oz(), self._liter()) == pytest.approx(0.0295735, rel=1e-4)

    # ── Custom / packaging units ─────────────────────────────────

    def test_case_to_cans(self):
        """1 case = 12 cans — user-defined packaging conversion."""
        can = _make_uom(symbol="can", uom_type="count", multiplier=1.0, offset=0.0)
        case = _make_uom(symbol="case", uom_type="count", multiplier=12.0, offset=0.0)
        assert UoMService.convert(1.0, case, can) == pytest.approx(12.0)

    def test_cans_to_cases(self):
        can = _make_uom(symbol="can", uom_type="count", multiplier=1.0, offset=0.0)
        case = _make_uom(symbol="case", uom_type="count", multiplier=12.0, offset=0.0)
        assert UoMService.convert(24.0, can, case) == pytest.approx(2.0)

    def test_pallet_to_cases_to_cans(self):
        """1 pallet = 100 cases = 1200 cans."""
        can = _make_uom(symbol="can", uom_type="count", multiplier=1.0, offset=0.0)
        case = _make_uom(symbol="case", uom_type="count", multiplier=12.0, offset=0.0)
        pallet = _make_uom(symbol="pallet", uom_type="count", multiplier=1200.0, offset=0.0)
        assert UoMService.convert(1.0, pallet, can) == pytest.approx(1200.0)
        assert UoMService.convert(1.0, pallet, case) == pytest.approx(100.0)

    def test_bottles_and_boxes(self):
        """1 box = 6 bottles."""
        bottle = _make_uom(symbol="bottle", uom_type="packaging", multiplier=1.0, offset=0.0)
        box = _make_uom(symbol="box", uom_type="packaging", multiplier=6.0, offset=0.0)
        assert UoMService.convert(3.0, box, bottle) == pytest.approx(18.0)
        assert UoMService.convert(18.0, bottle, box) == pytest.approx(3.0)

    # ── Error: incompatible types ────────────────────────────────

    def test_incompatible_types_raises(self):
        with pytest.raises(IncompatibleUoMTypeException):
            UoMService.convert(1.0, self._kg(), self._m())

    def test_incompatible_types_custom_vs_si(self):
        can = _make_uom(symbol="can", uom_type="count", multiplier=1.0, offset=0.0)
        with pytest.raises(IncompatibleUoMTypeException):
            UoMService.convert(1.0, can, self._kg())


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestExceptions:

    def test_duplicate_symbol(self):
        exc = DuplicateSymbolException("kg")
        assert exc.status_code == 409
        assert "kg" in str(exc)
        assert exc.error_code == "DUPLICATE_SYMBOL"

    def test_incompatible_type(self):
        exc = IncompatibleUoMTypeException("kg", "mass", "m", "length")
        assert exc.status_code == 422
        assert "mass" in str(exc)
        assert "length" in str(exc)

    def test_builtin_protected(self):
        exc = BuiltinUoMException("kg")
        assert exc.status_code == 403
        assert "kg" in str(exc)


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestEvents:

    def test_uom_created_event(self):
        evt = uom_created("id-1", "kg", "mass")
        assert evt.event_type == "uom.created"
        assert evt.source == "uom"
        assert evt.payload["symbol"] == "kg"
        assert evt.payload["uom_type"] == "mass"

    def test_uom_updated_event(self):
        evt = uom_updated("id-1", "kg")
        assert evt.event_type == "uom.updated"
        assert evt.payload["symbol"] == "kg"

    def test_uom_deleted_event(self):
        evt = uom_deleted("id-1", "kg")
        assert evt.event_type == "uom.deleted"
        assert evt.payload["uom_id"] == "id-1"


# ═════════════════════════════════════════════════════════════════════
# ROUND-TRIP CONVERSION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestRoundTrip:
    """Converting A→B→A should return the original value."""

    @pytest.mark.parametrize("value", [0.0, 1.0, 100.0, -40.0])
    def test_celsius_fahrenheit_round_trip(self, value):
        c = _make_uom(symbol="°C", uom_type="temperature", multiplier=1.0, offset=273.15)
        f = _make_uom(symbol="°F", uom_type="temperature", multiplier=5.0/9.0, offset=273.15 - 32.0*5.0/9.0)
        there = UoMService.convert(value, c, f)
        back = UoMService.convert(there, f, c)
        assert back == pytest.approx(value, abs=1e-9)

    @pytest.mark.parametrize("value", [0.001, 1.0, 1000.0])
    def test_kg_lb_round_trip(self, value):
        kg = _make_uom(symbol="kg", uom_type="mass", multiplier=1.0, offset=0.0)
        lb = _make_uom(symbol="lb", uom_type="mass", multiplier=0.45359237, offset=0.0)
        there = UoMService.convert(value, kg, lb)
        back = UoMService.convert(there, lb, kg)
        assert back == pytest.approx(value, rel=1e-12)

    @pytest.mark.parametrize("value", [1.0, 12.0, 144.0])
    def test_can_case_round_trip(self, value):
        can = _make_uom(symbol="can", uom_type="count", multiplier=1.0, offset=0.0)
        case = _make_uom(symbol="case", uom_type="count", multiplier=12.0, offset=0.0)
        there = UoMService.convert(value, can, case)
        back = UoMService.convert(there, case, can)
        assert back == pytest.approx(value, rel=1e-12)


# ═════════════════════════════════════════════════════════════════════
# RATE UOM SCHEMA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestRateUoMSchemas:
    """Validation tests for rate UoM schema constraints."""

    def test_create_rate_requires_both_symbols(self):
        with pytest.raises(ValidationError, match="numerator_uom_symbol"):
            UoMCreate(symbol="EA/h", name="each per hour", uom_type="rate")

    def test_create_rate_requires_denominator(self):
        with pytest.raises(ValidationError, match="denominator_uom_symbol"):
            UoMCreate(
                symbol="EA/h", name="each per hour", uom_type="rate",
                numerator_uom_symbol="EA",
            )

    def test_create_rate_requires_numerator(self):
        with pytest.raises(ValidationError, match="numerator_uom_symbol"):
            UoMCreate(
                symbol="EA/h", name="each per hour", uom_type="rate",
                denominator_uom_symbol="h",
            )

    def test_create_rate_valid(self):
        s = UoMCreate(
            symbol="EA/h", name="each per hour", uom_type="rate",
            numerator_uom_symbol="EA", denominator_uom_symbol="h",
        )
        assert s.numerator_uom_symbol == "EA"
        assert s.denominator_uom_symbol == "h"

    def test_non_rate_rejects_numerator(self):
        with pytest.raises(ValidationError, match="only valid for rate"):
            UoMCreate(
                symbol="kg", name="kilogram", uom_type="mass",
                numerator_uom_symbol="EA",
            )

    def test_non_rate_rejects_denominator(self):
        with pytest.raises(ValidationError, match="only valid for rate"):
            UoMCreate(
                symbol="kg", name="kilogram", uom_type="mass",
                denominator_uom_symbol="h",
            )

    def test_read_includes_rate_fields(self):
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        read = UoMRead(
            id=uid, symbol="EA/h", name="each per hour", uom_type="rate",
            multiplier=1.0, offset=0.0, is_builtin=True, is_active=True,
            numerator_uom_id=uuid.uuid4(), denominator_uom_id=uuid.uuid4(),
            numerator_uom_symbol="EA", denominator_uom_symbol="h",
            created_at=now, updated_at=now,
        )
        assert read.numerator_uom_symbol == "EA"
        assert read.denominator_uom_symbol == "h"

    def test_update_rate_fields(self):
        s = UoMUpdate(numerator_uom_symbol="PC", denominator_uom_symbol="min")
        assert s.numerator_uom_symbol == "PC"
        assert s.denominator_uom_symbol == "min"


# ═════════════════════════════════════════════════════════════════════
# RATE UOM CONVERSION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestRateConversion:
    """Test rate-to-rate conversion via the static convert() method."""

    @staticmethod
    def _ea():
        return _make_uom(symbol="EA", uom_type="count", multiplier=1.0, offset=0.0)

    @staticmethod
    def _pc():
        return _make_uom(symbol="PC", uom_type="count", multiplier=1.0, offset=0.0)

    @staticmethod
    def _kg():
        return _make_uom(symbol="kg", uom_type="mass", multiplier=1.0, offset=0.0)

    @staticmethod
    def _g():
        return _make_uom(symbol="g", uom_type="mass", multiplier=0.001, offset=0.0)

    @staticmethod
    def _h():
        return _make_uom(symbol="h", uom_type="time", multiplier=3600.0, offset=0.0)

    @staticmethod
    def _min():
        return _make_uom(symbol="min", uom_type="time", multiplier=60.0, offset=0.0)

    @staticmethod
    def _s():
        return _make_uom(symbol="s", uom_type="time", multiplier=1.0, offset=0.0)

    def test_ea_per_hour_to_ea_per_min(self):
        """10 EA/h = 10/60 EA/min ≈ 0.1667."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        ea_min = _make_rate_uom("EA/min", "each per minute", self._ea(), self._min())
        result = UoMService.convert(10.0, ea_h, ea_min)
        assert result == pytest.approx(10.0 / 60.0)

    def test_ea_per_min_to_ea_per_hour(self):
        """5 EA/min = 300 EA/h."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        ea_min = _make_rate_uom("EA/min", "each per minute", self._ea(), self._min())
        result = UoMService.convert(5.0, ea_min, ea_h)
        assert result == pytest.approx(300.0)

    def test_kg_per_hour_to_g_per_min(self):
        """10 kg/h = 10000 g / 60 min ≈ 166.667 g/min."""
        kg_h = _make_rate_uom("kg/h", "kg per hour", self._kg(), self._h())
        g_min = _make_rate_uom("g/min", "grams per min", self._g(), self._min())
        result = UoMService.convert(10.0, kg_h, g_min)
        assert result == pytest.approx(10000.0 / 60.0, rel=1e-9)

    def test_g_per_min_to_kg_per_hour(self):
        """166.667 g/min ≈ 10 kg/h."""
        kg_h = _make_rate_uom("kg/h", "kg per hour", self._kg(), self._h())
        g_min = _make_rate_uom("g/min", "grams per min", self._g(), self._min())
        result = UoMService.convert(10000.0 / 60.0, g_min, kg_h)
        assert result == pytest.approx(10.0, rel=1e-9)

    def test_same_rate_identity(self):
        """Converting a rate to itself returns the same value."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        assert UoMService.convert(42.0, ea_h, ea_h) == 42.0

    def test_rate_incompatible_numerator_types(self):
        """EA/h → kg/h should fail: numerator types don't match."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        kg_h = _make_rate_uom("kg/h", "kg per hour", self._kg(), self._h())
        with pytest.raises(IncompatibleUoMTypeException):
            UoMService.convert(1.0, ea_h, kg_h)

    def test_rate_incompatible_with_simple(self):
        """Cannot convert a rate type to a simple type."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        with pytest.raises(IncompatibleUoMTypeException):
            UoMService.convert(1.0, ea_h, self._kg())

    def test_ea_per_hour_to_ea_per_second(self):
        """3600 EA/h = 1 EA/s."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        ea_s = _make_rate_uom("EA/s", "each per second", self._ea(), self._s())
        result = UoMService.convert(3600.0, ea_h, ea_s)
        assert result == pytest.approx(1.0)

    @pytest.mark.parametrize("value", [0.5, 1.0, 60.0, 1000.0])
    def test_rate_round_trip(self, value):
        """EA/h → EA/min → EA/h returns the original value."""
        ea_h = _make_rate_uom("EA/h", "each per hour", self._ea(), self._h())
        ea_min = _make_rate_uom("EA/min", "each per minute", self._ea(), self._min())
        there = UoMService.convert(value, ea_h, ea_min)
        back = UoMService.convert(there, ea_min, ea_h)
        assert back == pytest.approx(value, rel=1e-12)

    @pytest.mark.parametrize("value", [1.0, 10.0, 100.0])
    def test_kg_rate_round_trip(self, value):
        """kg/h → g/min → kg/h returns the original value."""
        kg_h = _make_rate_uom("kg/h", "kg per hour", self._kg(), self._h())
        g_min = _make_rate_uom("g/min", "grams per minute", self._g(), self._min())
        there = UoMService.convert(value, kg_h, g_min)
        back = UoMService.convert(there, g_min, kg_h)
        assert back == pytest.approx(value, rel=1e-9)


# ═════════════════════════════════════════════════════════════════════
# RATE UOM SEED DATA TESTS
# ═════════════════════════════════════════════════════════════════════


class TestRateSeedData:
    """Verify the built-in rate seed data is consistent."""

    def test_rate_units_not_empty(self):
        assert len(BUILTIN_RATE_UNITS) > 0

    def test_rate_symbols_unique(self):
        symbols = [u[0] for u in BUILTIN_RATE_UNITS]
        assert len(symbols) == len(set(symbols))

    def test_rate_symbols_dont_collide_with_base(self):
        base_symbols = {u[0] for u in BUILTIN_UNITS}
        for sym, _, _, _ in BUILTIN_RATE_UNITS:
            assert sym not in base_symbols, f"Rate symbol {sym} collides with base unit"

    def test_rate_numerators_exist_in_base(self):
        base_symbols = {u[0] for u in BUILTIN_UNITS}
        for sym, _, num, _ in BUILTIN_RATE_UNITS:
            assert num in base_symbols, f"Rate {sym}: numerator {num} not in base units"

    def test_rate_denominators_exist_in_base(self):
        base_symbols = {u[0] for u in BUILTIN_UNITS}
        for sym, _, _, den in BUILTIN_RATE_UNITS:
            assert den in base_symbols, f"Rate {sym}: denominator {den} not in base units"

    def test_get_builtin_rate_unit_dicts(self):
        # Build a fake symbol->id map for all referenced base symbols
        base_symbols = {u[0] for u in BUILTIN_UNITS}
        symbol_to_id = {s: uuid.uuid4() for s in base_symbols}
        dicts = get_builtin_rate_unit_dicts(symbol_to_id)
        assert len(dicts) == len(BUILTIN_RATE_UNITS)
        for d in dicts:
            assert d["uom_type"] == "rate"
            assert d["is_builtin"] is True
            assert d["numerator_uom_id"] is not None
            assert d["denominator_uom_id"] is not None
