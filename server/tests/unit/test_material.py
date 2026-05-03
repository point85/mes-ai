"""
Unit tests for MAT-MGMT (Material Management) module.

Covers:
- Model table names, columns, relationships, and repr
- Schema validation (create / read / update) for MaterialDefinition, MaterialLot,
  MaterialConsumption, and ConsumeRequest
- Event factory functions
- Exception hierarchy and error codes
- Service-level invariants (duplicate checks, consume logic)
"""

from __future__ import annotations

import types
import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.material.events import (
    material_consumed,
    material_lot_created,
    material_lot_expired,
)
from mes.core.material.exceptions import (
    DuplicateLotNumberException,
    DuplicateMaterialCodeException,
    InsufficientQuantityException,
    MaterialLotNotAvailableException,
)
from mes.core.material.models import (
    MaterialConsumption,
    MaterialDefinition,
    MaterialLot,
)
from mes.core.material.schemas import (
    ConsumeRequest,
    ConsumptionRead,
    MaterialCreate,
    MaterialLotCreate,
    MaterialLotRead,
    MaterialLotUpdate,
    MaterialRead,
    MaterialUpdate,
    MATERIAL_TYPES,
    MATERIAL_LOT_STATUSES,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_material(**overrides) -> types.SimpleNamespace:
    """Create a lightweight MaterialDefinition-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Steel Bar",
        "code": "STL-BAR-001",
        "description": "Cold-rolled steel bar",
        "material_type": "raw",
        "uom_id": uuid.uuid4(),
        "shelf_life_days": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_lot(**overrides) -> types.SimpleNamespace:
    """Create a lightweight MaterialLot-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "material_id": uuid.uuid4(),
        "lot_number": "LOT-2025-001",
        "quantity_on_hand": 100.0,
        "quantity_reserved": 0.0,
        "status": "available",
        "received_date": date(2025, 1, 15),
        "expiry_date": date(2026, 1, 15),
        "supplier": "Acme Steel Inc.",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_consumption(**overrides) -> types.SimpleNamespace:
    """Create a lightweight MaterialConsumption-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "material_lot_id": uuid.uuid4(),
        "unit_id": uuid.uuid4(),
        "lot_id": None,
        "step_id": uuid.uuid4(),
        "quantity_consumed": 2.5,
        "consumed_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestMaterialDefinitionModel:
    """Tests for the MaterialDefinition SQLAlchemy model."""

    def test_tablename(self):
        assert MaterialDefinition.__tablename__ == "material_definitions"

    def test_has_mapper(self):
        assert hasattr(MaterialDefinition, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in MaterialDefinition.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names, f"Missing '{col}'"

    def test_domain_columns_present(self):
        col_names = {c.key for c in MaterialDefinition.__mapper__.columns}
        for col in ("name", "code", "description", "material_type", "uom_id", "shelf_life_days"):
            assert col in col_names, f"Missing '{col}'"

    def test_code_column_is_unique(self):
        col = MaterialDefinition.__table__.c.code
        assert col.unique is True

    def test_lots_relationship(self):
        rels = {r.key for r in MaterialDefinition.__mapper__.relationships}
        assert "lots" in rels

    def test_repr(self):
        obj = _make_material()
        r = repr(obj)
        assert "STL-BAR-001" in r


class TestMaterialLotModel:
    """Tests for the MaterialLot SQLAlchemy model."""

    def test_tablename(self):
        assert MaterialLot.__tablename__ == "material_lots"

    def test_has_mapper(self):
        assert hasattr(MaterialLot, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in MaterialLot.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names

    def test_domain_columns_present(self):
        col_names = {c.key for c in MaterialLot.__mapper__.columns}
        for col in (
            "material_id", "lot_number", "quantity_on_hand",
            "quantity_reserved", "status", "received_date",
            "expiry_date", "supplier",
        ):
            assert col in col_names, f"Missing '{col}'"

    def test_lot_number_column_is_unique(self):
        col = MaterialLot.__table__.c.lot_number
        assert col.unique is True

    def test_material_relationship(self):
        rels = {r.key for r in MaterialLot.__mapper__.relationships}
        assert "material" in rels

    def test_consumptions_relationship(self):
        rels = {r.key for r in MaterialLot.__mapper__.relationships}
        assert "consumptions" in rels

    def test_repr(self):
        obj = _make_lot()
        r = repr(obj)
        assert "LOT-2025-001" in r


class TestMaterialConsumptionModel:
    """Tests for the MaterialConsumption SQLAlchemy model."""

    def test_tablename(self):
        assert MaterialConsumption.__tablename__ == "material_consumptions"

    def test_has_mapper(self):
        assert hasattr(MaterialConsumption, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in MaterialConsumption.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names

    def test_domain_columns_present(self):
        col_names = {c.key for c in MaterialConsumption.__mapper__.columns}
        for col in (
            "material_lot_id", "unit_id", "lot_id",
            "step_id", "quantity_consumed", "consumed_at",
        ):
            assert col in col_names, f"Missing '{col}'"

    def test_material_lot_relationship(self):
        rels = {r.key for r in MaterialConsumption.__mapper__.relationships}
        assert "material_lot" in rels

    def test_repr(self):
        obj = _make_consumption(quantity_consumed=5.0)
        r = repr(obj)
        assert "5.0" in r


class TestAllModelsInheritBase:
    """Cross-cutting check that all material models inherit BaseModel columns."""

    @pytest.mark.parametrize("model_cls", [
        MaterialDefinition, MaterialLot, MaterialConsumption,
    ])
    def test_base_columns(self, model_cls):
        col_names = {c.key for c in model_cls.__mapper__.columns}
        assert "id" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "is_active" in col_names


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — MaterialDefinition
# ═════════════════════════════════════════════════════════════════════


class TestMaterialCreateSchema:
    def test_full_creation(self):
        uom_uid = uuid.uuid4()
        s = MaterialCreate(
            name="Steel Bar",
            code="STL-BAR-001",
            description="Cold-rolled steel bar",
            material_type="raw",
            uom_id=uom_uid,
            shelf_life_days=365,
        )
        assert s.name == "Steel Bar"
        assert s.code == "STL-BAR-001"
        assert s.material_type == "raw"
        assert s.uom_id == uom_uid
        assert s.shelf_life_days == 365

    def test_defaults(self):
        s = MaterialCreate(name="Widget", code="WDG-001", uom_id=uuid.uuid4())
        assert s.material_type == "raw"
        assert s.revision is None
        assert s.shelf_life_days is None
        assert s.description is None

    def test_all_material_types_accepted(self):
        for mtype in MATERIAL_TYPES:
            s = MaterialCreate(name="X", code=f"X-{mtype}", material_type=mtype, uom_id=uuid.uuid4())
            assert s.material_type == mtype

    def test_invalid_material_type_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="X", code="X-1", material_type="exotic")

    def test_code_with_spaces_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="X", code="bad code")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="", code="X-1")

    def test_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="Widget", code="")

    def test_negative_shelf_life_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="X", code="X-1", shelf_life_days=-1)

    def test_zero_shelf_life_rejected(self):
        with pytest.raises(ValidationError):
            MaterialCreate(name="X", code="X-1", shelf_life_days=0)


class TestMaterialReadSchema:
    def test_from_attributes(self):
        obj = _make_material()
        s = MaterialRead.model_validate(obj, from_attributes=True)
        assert s.code == "STL-BAR-001"
        assert s.material_type == "raw"
        assert s.is_active is True

    def test_shelf_life_days_optional(self):
        obj = _make_material(shelf_life_days=None)
        s = MaterialRead.model_validate(obj, from_attributes=True)
        assert s.shelf_life_days is None


class TestMaterialUpdateSchema:
    def test_partial_update(self):
        s = MaterialUpdate(description="Updated desc")
        assert s.description == "Updated desc"
        assert s.name is None
        assert s.code is None

    def test_code_with_spaces_rejected(self):
        with pytest.raises(ValidationError):
            MaterialUpdate(code="bad code")

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            MaterialUpdate(material_type="exotic")

    def test_valid_type_accepted(self):
        s = MaterialUpdate(material_type="intermediate")
        assert s.material_type == "intermediate"


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — MaterialLot
# ═════════════════════════════════════════════════════════════════════


class TestMaterialLotCreateSchema:
    def test_full_creation(self):
        mid = uuid.uuid4()
        s = MaterialLotCreate(
            material_id=mid,
            lot_number="LOT-001",
            quantity_on_hand=50.0,
            received_date=date(2025, 6, 1),
            expiry_date=date(2026, 6, 1),
            supplier="Acme Inc.",
        )
        assert s.material_id == mid
        assert s.lot_number == "LOT-001"
        assert s.quantity_on_hand == 50.0
        assert s.supplier == "Acme Inc."

    def test_defaults(self):
        s = MaterialLotCreate(
            material_id=uuid.uuid4(),
            lot_number="LOT-002",
            quantity_on_hand=10.0,
        )
        assert s.received_date is None
        assert s.expiry_date is None
        assert s.supplier is None

    def test_empty_lot_number_rejected(self):
        with pytest.raises(ValidationError):
            MaterialLotCreate(
                material_id=uuid.uuid4(),
                lot_number="",
                quantity_on_hand=10.0,
            )

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            MaterialLotCreate(
                material_id=uuid.uuid4(),
                lot_number="LOT-003",
                quantity_on_hand=-5.0,
            )


class TestMaterialLotReadSchema:
    def test_from_attributes(self):
        obj = _make_lot()
        s = MaterialLotRead.model_validate(obj, from_attributes=True)
        assert s.lot_number == "LOT-2025-001"
        assert s.status == "available"
        assert s.quantity_on_hand == 100.0

    def test_optional_fields(self):
        obj = _make_lot(received_date=None, expiry_date=None, supplier=None)
        s = MaterialLotRead.model_validate(obj, from_attributes=True)
        assert s.received_date is None
        assert s.expiry_date is None
        assert s.supplier is None


class TestMaterialLotUpdateSchema:
    def test_partial_update(self):
        s = MaterialLotUpdate(supplier="New Supplier")
        assert s.supplier == "New Supplier"
        assert s.lot_number is None
        assert s.quantity_on_hand is None

    def test_valid_status(self):
        for st in MATERIAL_LOT_STATUSES:
            s = MaterialLotUpdate(status=st)
            assert s.status == st

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            MaterialLotUpdate(status="deleted")

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            MaterialLotUpdate(quantity_on_hand=-1.0)


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — Consumption
# ═════════════════════════════════════════════════════════════════════


class TestConsumeRequestSchema:
    def test_valid_consume_request(self):
        uid = uuid.uuid4()
        s = ConsumeRequest(
            unit_id=uid,
            quantity_consumed=5.0,
            step_id=uuid.uuid4(),
        )
        assert s.unit_id == uid
        assert s.quantity_consumed == 5.0

    def test_lot_based_consume(self):
        lid = uuid.uuid4()
        s = ConsumeRequest(lot_id=lid, quantity_consumed=10.0)
        assert s.lot_id == lid
        assert s.unit_id is None

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            ConsumeRequest(unit_id=uuid.uuid4(), quantity_consumed=0)

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            ConsumeRequest(unit_id=uuid.uuid4(), quantity_consumed=-1.0)


class TestConsumptionReadSchema:
    def test_from_attributes(self):
        obj = _make_consumption()
        s = ConsumptionRead.model_validate(obj, from_attributes=True)
        assert s.quantity_consumed == 2.5
        assert s.unit_id is not None

    def test_nullable_fields(self):
        obj = _make_consumption(unit_id=None, lot_id=None, step_id=None)
        s = ConsumptionRead.model_validate(obj, from_attributes=True)
        assert s.unit_id is None
        assert s.lot_id is None
        assert s.step_id is None


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestMaterialEvents:
    """Test event factory functions."""

    def test_material_consumed_event(self):
        lot_id = str(uuid.uuid4())
        unit_id = str(uuid.uuid4())
        event = material_consumed(lot_id, unit_id, 5.5)
        assert event.event_type == "material.consumed"
        assert event.source == "material"
        assert event.payload["material_lot_id"] == lot_id
        assert event.payload["unit_id"] == unit_id
        assert event.payload["quantity"] == 5.5

    def test_material_consumed_event_no_unit(self):
        lot_id = str(uuid.uuid4())
        event = material_consumed(lot_id, None, 3.0)
        assert event.payload["unit_id"] is None
        assert event.payload["quantity"] == 3.0

    def test_material_lot_created_event(self):
        lot_id = str(uuid.uuid4())
        mat_id = str(uuid.uuid4())
        event = material_lot_created(lot_id, mat_id, "LOT-100", 50.0)
        assert event.event_type == "material.lot.created"
        assert event.source == "material"
        assert event.payload["material_lot_id"] == lot_id
        assert event.payload["material_id"] == mat_id
        assert event.payload["lot_number"] == "LOT-100"
        assert event.payload["quantity"] == 50.0

    def test_material_lot_expired_event(self):
        lot_id = str(uuid.uuid4())
        event = material_lot_expired(lot_id, "LOT-EXP-001")
        assert event.event_type == "material.lot.expired"
        assert event.source == "material"
        assert event.payload["material_lot_id"] == lot_id
        assert event.payload["lot_number"] == "LOT-EXP-001"


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestMaterialExceptions:
    """Test domain exception hierarchy and error codes."""

    def test_duplicate_material_code(self):
        exc = DuplicateMaterialCodeException("STL-001")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_MATERIAL_CODE"
        assert "STL-001" in str(exc.message)
        assert exc.details["material_code"] == "STL-001"

    def test_duplicate_lot_number(self):
        exc = DuplicateLotNumberException("LOT-DUP")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_LOT_NUMBER"
        assert "LOT-DUP" in str(exc.message)
        assert exc.details["lot_number"] == "LOT-DUP"

    def test_insufficient_quantity(self):
        exc = InsufficientQuantityException("LOT-001", 20.0, 5.0)
        assert exc.status_code == 422
        assert exc.error_code == "INSUFFICIENT_QUANTITY"
        assert "20" in str(exc.message)
        assert "5" in str(exc.message)
        assert exc.details["requested"] == 20.0
        assert exc.details["available"] == 5.0

    def test_lot_not_available(self):
        exc = MaterialLotNotAvailableException("LOT-002", "consumed")
        assert exc.status_code == 422
        assert exc.error_code == "LOT_NOT_AVAILABLE"
        assert "consumed" in str(exc.message)
        assert exc.details["current_status"] == "consumed"

    def test_all_exceptions_have_message(self):
        """All material exceptions should have a descriptive message."""
        exceptions = [
            DuplicateMaterialCodeException("X"),
            DuplicateLotNumberException("Y"),
            InsufficientQuantityException("Z", 10.0, 5.0),
            MaterialLotNotAvailableException("W", "expired"),
        ]
        for exc in exceptions:
            assert len(exc.message) > 10  # Non-trivial message


# ═════════════════════════════════════════════════════════════════════
# SERVICE INVARIANT TESTS (no DB, logic-only)
# ═════════════════════════════════════════════════════════════════════


class TestMaterialServiceImports:
    """Verify that service classes can be imported and have expected methods."""

    def test_material_service_importable(self):
        from mes.core.material.service import MaterialService
        assert MaterialService is not None

    def test_material_service_has_crud_methods(self):
        from mes.core.material.service import MaterialService
        for method in (
            "list_materials", "get_material",
            "create_material", "update_material", "delete_material",
        ):
            assert hasattr(MaterialService, method), f"Missing {method}"

    def test_lot_service_importable(self):
        from mes.core.material.service import MaterialLotService
        assert MaterialLotService is not None

    def test_lot_service_has_crud_methods(self):
        from mes.core.material.service import MaterialLotService
        for method in (
            "list_lots", "get_lot",
            "create_lot", "update_lot",
            "consume",
            "get_consumptions_for_unit",
            "get_consumptions_for_lot",
        ):
            assert hasattr(MaterialLotService, method), f"Missing {method}"


class TestMaterialRouterImports:
    """Verify that the router can be imported and has expected routes."""

    def test_router_importable(self):
        from mes.core.material.routes import router
        assert router is not None

    def test_router_has_material_routes(self):
        from mes.core.material.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/materials" in paths
        assert "/api/v1/materials/{material_id}" in paths

    def test_router_has_lot_routes(self):
        from mes.core.material.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/material-lots" in paths
        assert "/api/v1/material-lots/{lot_id}" in paths

    def test_router_has_consume_route(self):
        from mes.core.material.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/material-lots/{lot_id}/consume" in paths

    def test_router_has_consumed_materials_route(self):
        from mes.core.material.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/units/{unit_id}/consumed-materials" in paths


# ═════════════════════════════════════════════════════════════════════
# CONSTANTS TESTS
# ═════════════════════════════════════════════════════════════════════


class TestMaterialConstants:
    """Test that domain constants are defined correctly."""

    def test_material_types(self):
        assert "raw" in MATERIAL_TYPES
        assert "intermediate" in MATERIAL_TYPES
        assert "finished" in MATERIAL_TYPES
        assert "semi" in MATERIAL_TYPES
        assert "consumable" in MATERIAL_TYPES
        assert "packaging" in MATERIAL_TYPES
        assert "spare" in MATERIAL_TYPES
        assert len(MATERIAL_TYPES) == 7

    def test_lot_statuses(self):
        assert "available" in MATERIAL_LOT_STATUSES
        assert "reserved" in MATERIAL_LOT_STATUSES
        assert "consumed" in MATERIAL_LOT_STATUSES
        assert "expired" in MATERIAL_LOT_STATUSES
        assert len(MATERIAL_LOT_STATUSES) == 4


# ═════════════════════════════════════════════════════════════════════
# CONSUME LOGIC TESTS (service-level invariant checks via schema)
# ═════════════════════════════════════════════════════════════════════


class TestConsumeInvariants:
    """Tests for consumption-related business rules enforced at schema/exception level."""

    def test_insufficient_quantity_values(self):
        """InsufficientQuantityException should preserve exact requested/available values."""
        exc = InsufficientQuantityException("L1", 100.0, 25.0)
        assert exc.details["requested"] == 100.0
        assert exc.details["available"] == 25.0

    def test_lot_not_available_preserves_status(self):
        for status in ("consumed", "expired"):
            exc = MaterialLotNotAvailableException("L2", status)
            assert exc.details["current_status"] == status

    def test_consume_request_requires_positive_quantity(self):
        """ConsumeRequest must reject zero and negative quantities."""
        with pytest.raises(ValidationError):
            ConsumeRequest(unit_id=uuid.uuid4(), quantity_consumed=0.0)
        with pytest.raises(ValidationError):
            ConsumeRequest(unit_id=uuid.uuid4(), quantity_consumed=-5.0)

    def test_consume_request_allows_no_unit_and_no_lot(self):
        """ConsumeRequest with neither unit nor lot should be valid (ad hoc consumption)."""
        s = ConsumeRequest(quantity_consumed=1.0)
        assert s.unit_id is None
        assert s.lot_id is None

    def test_consume_request_fractional_quantity(self):
        s = ConsumeRequest(unit_id=uuid.uuid4(), quantity_consumed=0.001)
        assert s.quantity_consumed == 0.001


# ═════════════════════════════════════════════════════════════════════
# INTEGRATION-READY: Module init
# ═════════════════════════════════════════════════════════════════════


class TestModuleInit:
    """Test that the module __init__.py is importable."""

    def test_module_importable(self):
        import mes.core.material
        assert mes.core.material is not None

    def test_models_importable(self):
        from mes.core.material.models import (
            MaterialConsumption,
            MaterialDefinition,
            MaterialLot,
        )
        assert MaterialDefinition is not None
        assert MaterialLot is not None
        assert MaterialConsumption is not None

    def test_events_importable(self):
        from mes.core.material.events import (
            material_consumed,
            material_lot_created,
            material_lot_expired,
        )
        assert material_consumed is not None
        assert material_lot_created is not None
        assert material_lot_expired is not None

    def test_exceptions_importable(self):
        from mes.core.material.exceptions import (
            DuplicateLotNumberException,
            DuplicateMaterialCodeException,
            InsufficientQuantityException,
            MaterialLotNotAvailableException,
        )
        assert DuplicateMaterialCodeException is not None
        assert DuplicateLotNumberException is not None
        assert InsufficientQuantityException is not None
        assert MaterialLotNotAvailableException is not None
