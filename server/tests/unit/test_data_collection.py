"""
Unit tests for DATA-COLLECT (Data Collection) module.

Covers:
- Model table names, columns, relationships, and repr
- Schema validation (create / read / update) for DataDefinition and DataPoint
- Event factory functions
- Exception hierarchy and error codes
- Service-level validation logic (_validate_value)
- Router path verification
"""

from __future__ import annotations

import types
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mes.core.data_collection.events import (
    data_collected,
    data_definition_created,
)
from mes.core.data_collection.exceptions import (
    DuplicateDefinitionCodeException,
    InvalidDataValueException,
    InvalidEnumValueException,
    MissingRequiredDataException,
    ValueOutOfLimitsException,
)
from mes.core.data_collection.models import DataDefinition, DataPoint
from mes.core.data_collection.schemas import (
    CollectBatchRequest,
    CollectRequest,
    DataDefinitionCreate,
    DataDefinitionRead,
    DataDefinitionUpdate,
    DataPointRead,
    DATA_SOURCES,
    DATA_TYPES,
)
from mes.core.data_collection.service import DataPointService


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_definition(**overrides) -> types.SimpleNamespace:
    """Create a lightweight DataDefinition-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Oven Temperature",
        "code": "TEMP-OVEN-1",
        "description": "Temperature reading from oven zone 1",
        "data_type": "numeric",
        "uom_id": uuid.uuid4(),
        "step_id": uuid.uuid4(),
        "source": "equipment",
        "is_required": True,
        "enum_values": None,
        "lower_limit": 180.0,
        "upper_limit": 220.0,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _make_data_point(**overrides) -> types.SimpleNamespace:
    """Create a lightweight DataPoint-like object."""
    defaults = {
        "id": uuid.uuid4(),
        "definition_id": uuid.uuid4(),
        "unit_id": uuid.uuid4(),
        "lot_id": None,
        "value_numeric": 195.5,
        "value_string": None,
        "value_boolean": None,
        "collected_at": datetime.now(timezone.utc),
        "source_equipment_id": uuid.uuid4(),
        "operator_id": None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


# ═════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataDefinitionModel:
    """Tests for the DataDefinition SQLAlchemy model."""

    def test_tablename(self):
        assert DataDefinition.__tablename__ == "data_definitions"

    def test_has_mapper(self):
        assert hasattr(DataDefinition, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in DataDefinition.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names, f"Missing '{col}'"

    def test_domain_columns_present(self):
        col_names = {c.key for c in DataDefinition.__mapper__.columns}
        for col in (
            "name", "code", "description", "data_type", "uom_id",
            "step_id", "source", "is_required", "enum_values",
            "lower_limit", "upper_limit",
        ):
            assert col in col_names, f"Missing '{col}'"

    def test_code_column_is_unique(self):
        col = DataDefinition.__table__.c.code
        assert col.unique is True

    def test_data_points_relationship(self):
        rels = {r.key for r in DataDefinition.__mapper__.relationships}
        assert "data_points" in rels

    def test_repr(self):
        obj = _make_definition()
        r = repr(obj)
        assert "TEMP-OVEN-1" in r


class TestDataPointModel:
    """Tests for the DataPoint SQLAlchemy model."""

    def test_tablename(self):
        assert DataPoint.__tablename__ == "data_points"

    def test_has_mapper(self):
        assert hasattr(DataPoint, "__mapper__")

    def test_base_columns_present(self):
        col_names = {c.key for c in DataPoint.__mapper__.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names

    def test_domain_columns_present(self):
        col_names = {c.key for c in DataPoint.__mapper__.columns}
        for col in (
            "definition_id", "unit_id", "lot_id",
            "value_numeric", "value_string", "value_boolean",
            "collected_at", "source_equipment_id", "operator_id",
        ):
            assert col in col_names, f"Missing '{col}'"

    def test_definition_relationship(self):
        rels = {r.key for r in DataPoint.__mapper__.relationships}
        assert "definition" in rels

    def test_repr(self):
        obj = _make_data_point()
        r = repr(obj)
        assert "195.5" in r


class TestAllModelsInheritBase:
    @pytest.mark.parametrize("model_cls", [DataDefinition, DataPoint])
    def test_base_columns(self, model_cls):
        col_names = {c.key for c in model_cls.__mapper__.columns}
        assert "id" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "is_active" in col_names


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — DataDefinition
# ═════════════════════════════════════════════════════════════════════


class TestDataDefinitionCreateSchema:
    def test_full_creation(self):
        s = DataDefinitionCreate(
            name="Oven Temperature",
            code="TEMP-OVEN-1",
            description="Zone 1 temperature",
            data_type="numeric",
            uom_id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            source="equipment",
            is_required=True,
            lower_limit=180.0,
            upper_limit=220.0,
        )
        assert s.name == "Oven Temperature"
        assert s.code == "TEMP-OVEN-1"
        assert s.data_type == "numeric"
        assert s.source == "equipment"
        assert s.is_required is True

    def test_defaults(self):
        s = DataDefinitionCreate(name="Test", code="TST-1")
        assert s.data_type == "numeric"
        assert s.source == "manual"
        assert s.is_required is False
        assert s.uom_id is None
        assert s.step_id is None
        assert s.enum_values is None
        assert s.lower_limit is None
        assert s.upper_limit is None

    def test_all_data_types_accepted(self):
        for dt in DATA_TYPES:
            s = DataDefinitionCreate(name="X", code=f"X-{dt}", data_type=dt)
            assert s.data_type == dt

    def test_invalid_data_type_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="X", code="X-1", data_type="complex")

    def test_all_sources_accepted(self):
        for src in DATA_SOURCES:
            s = DataDefinitionCreate(name="X", code=f"X-{src}", source=src)
            assert s.source == src

    def test_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="X", code="X-1", source="magic")

    def test_code_with_spaces_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="X", code="bad code")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="", code="X-1")

    def test_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="X", code="")

    def test_enum_type_with_values(self):
        s = DataDefinitionCreate(
            name="Color", code="COLOR-1",
            data_type="enum", enum_values="red,green,blue",
        )
        assert s.enum_values == "red,green,blue"


class TestDataDefinitionReadSchema:
    def test_from_attributes(self):
        obj = _make_definition()
        s = DataDefinitionRead.model_validate(obj, from_attributes=True)
        assert s.code == "TEMP-OVEN-1"
        assert s.data_type == "numeric"
        assert s.source == "equipment"
        assert s.is_required is True

    def test_optional_fields(self):
        obj = _make_definition(
            description=None, uom_id=None, step_id=None,
            enum_values=None, lower_limit=None, upper_limit=None,
        )
        s = DataDefinitionRead.model_validate(obj, from_attributes=True)
        assert s.description is None
        assert s.uom_id is None
        assert s.step_id is None


class TestDataDefinitionUpdateSchema:
    def test_partial_update(self):
        s = DataDefinitionUpdate(description="Updated")
        assert s.description == "Updated"
        assert s.name is None
        assert s.code is None

    def test_code_with_spaces_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionUpdate(code="bad code")

    def test_invalid_data_type_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionUpdate(data_type="complex")

    def test_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionUpdate(source="magic")

    def test_valid_data_type_accepted(self):
        s = DataDefinitionUpdate(data_type="boolean")
        assert s.data_type == "boolean"

    def test_valid_source_accepted(self):
        s = DataDefinitionUpdate(source="sensor")
        assert s.source == "sensor"


# ═════════════════════════════════════════════════════════════════════
# SCHEMA TESTS — DataPoint / Collection
# ═════════════════════════════════════════════════════════════════════


class TestCollectRequestSchema:
    def test_numeric_collect(self):
        s = CollectRequest(
            definition_id=uuid.uuid4(),
            unit_id=uuid.uuid4(),
            value_numeric=42.5,
        )
        assert s.value_numeric == 42.5
        assert s.value_string is None
        assert s.value_boolean is None

    def test_string_collect(self):
        s = CollectRequest(
            definition_id=uuid.uuid4(),
            value_string="OK",
        )
        assert s.value_string == "OK"

    def test_boolean_collect(self):
        s = CollectRequest(
            definition_id=uuid.uuid4(),
            value_boolean=True,
        )
        assert s.value_boolean is True

    def test_lot_based_collect(self):
        lid = uuid.uuid4()
        s = CollectRequest(
            definition_id=uuid.uuid4(),
            lot_id=lid,
            value_numeric=10.0,
        )
        assert s.lot_id == lid
        assert s.unit_id is None

    def test_with_source_info(self):
        s = CollectRequest(
            definition_id=uuid.uuid4(),
            value_numeric=1.0,
            source_equipment_id=uuid.uuid4(),
            operator_id=uuid.uuid4(),
        )
        assert s.source_equipment_id is not None
        assert s.operator_id is not None


class TestCollectBatchRequestSchema:
    def test_single_item_batch(self):
        item = CollectRequest(definition_id=uuid.uuid4(), value_numeric=1.0)
        s = CollectBatchRequest(items=[item])
        assert len(s.items) == 1

    def test_multi_item_batch(self):
        items = [
            CollectRequest(definition_id=uuid.uuid4(), value_numeric=float(i))
            for i in range(5)
        ]
        s = CollectBatchRequest(items=items)
        assert len(s.items) == 5

    def test_empty_batch_rejected(self):
        with pytest.raises(ValidationError):
            CollectBatchRequest(items=[])


class TestDataPointReadSchema:
    def test_from_attributes(self):
        obj = _make_data_point()
        s = DataPointRead.model_validate(obj, from_attributes=True)
        assert s.value_numeric == 195.5
        assert s.unit_id is not None

    def test_nullable_fields(self):
        obj = _make_data_point(
            unit_id=None, lot_id=None, value_numeric=None,
            value_string="test", source_equipment_id=None, operator_id=None,
        )
        s = DataPointRead.model_validate(obj, from_attributes=True)
        assert s.unit_id is None
        assert s.value_string == "test"
        assert s.source_equipment_id is None


# ═════════════════════════════════════════════════════════════════════
# EVENT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataCollectionEvents:
    def test_data_collected_numeric(self):
        def_id = str(uuid.uuid4())
        unit_id = str(uuid.uuid4())
        event = data_collected(def_id, unit_id, 42.5)
        assert event.event_type == "data.collected"
        assert event.source == "data_collection"
        assert event.payload["definition_id"] == def_id
        assert event.payload["unit_id"] == unit_id
        assert event.payload["value"] == 42.5

    def test_data_collected_string(self):
        event = data_collected(str(uuid.uuid4()), None, "OK")
        assert event.payload["value"] == "OK"
        assert event.payload["unit_id"] is None

    def test_data_collected_boolean(self):
        event = data_collected(str(uuid.uuid4()), str(uuid.uuid4()), True)
        assert event.payload["value"] is True

    def test_data_collected_none_value(self):
        event = data_collected(str(uuid.uuid4()), None, None)
        assert event.payload["value"] is None

    def test_data_definition_created_event(self):
        def_id = str(uuid.uuid4())
        event = data_definition_created(def_id, "TEMP-1", "numeric")
        assert event.event_type == "data.definition.created"
        assert event.source == "data_collection"
        assert event.payload["definition_id"] == def_id
        assert event.payload["code"] == "TEMP-1"
        assert event.payload["data_type"] == "numeric"


# ═════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataCollectionExceptions:
    def test_duplicate_definition_code(self):
        exc = DuplicateDefinitionCodeException("TEMP-1")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_DEFINITION_CODE"
        assert "TEMP-1" in str(exc.message)
        assert exc.details["definition_code"] == "TEMP-1"

    def test_invalid_data_value(self):
        exc = InvalidDataValueException("TEMP-1", "numeric", "value_numeric is required")
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_DATA_VALUE"
        assert "numeric" in str(exc.message)
        assert exc.details["expected_type"] == "numeric"

    def test_value_out_of_limits_both(self):
        exc = ValueOutOfLimitsException("TEMP-1", 250.0, 180.0, 220.0)
        assert exc.status_code == 422
        assert exc.error_code == "VALUE_OUT_OF_LIMITS"
        assert "250" in str(exc.message)
        assert exc.details["value"] == 250.0
        assert exc.details["lower_limit"] == 180.0
        assert exc.details["upper_limit"] == 220.0

    def test_value_out_of_limits_lower_only(self):
        exc = ValueOutOfLimitsException("X", 5.0, 10.0, None)
        assert ">=" in str(exc.message)

    def test_value_out_of_limits_upper_only(self):
        exc = ValueOutOfLimitsException("X", 50.0, None, 40.0)
        assert "<=" in str(exc.message)

    def test_missing_required_data(self):
        exc = MissingRequiredDataException(["TEMP-1", "TORQUE-A"])
        assert exc.status_code == 422
        assert exc.error_code == "MISSING_REQUIRED_DATA"
        assert "TEMP-1" in str(exc.message)
        assert "TORQUE-A" in str(exc.message)
        assert exc.details["missing_codes"] == ["TEMP-1", "TORQUE-A"]

    def test_invalid_enum_value(self):
        exc = InvalidEnumValueException("COLOR", "purple", ["red", "green", "blue"])
        assert exc.status_code == 422
        assert exc.error_code == "INVALID_ENUM_VALUE"
        assert "purple" in str(exc.message)
        assert exc.details["value"] == "purple"
        assert exc.details["allowed_values"] == ["red", "green", "blue"]

    def test_all_exceptions_have_message(self):
        exceptions = [
            DuplicateDefinitionCodeException("X"),
            InvalidDataValueException("X", "numeric", "reason"),
            ValueOutOfLimitsException("X", 1.0, 0.0, 0.5),
            MissingRequiredDataException(["X"]),
            InvalidEnumValueException("X", "y", ["a", "b"]),
        ]
        for exc in exceptions:
            assert len(exc.message) > 10


# ═════════════════════════════════════════════════════════════════════
# SERVICE VALIDATION LOGIC TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataPointValidation:
    """Test DataPointService._validate_value without a database."""

    def test_numeric_valid(self):
        defn = _make_definition(data_type="numeric", lower_limit=0.0, upper_limit=100.0)
        # Should not raise
        DataPointService._validate_value(
            defn, value_numeric=50.0, value_string=None, value_boolean=None,
        )

    def test_numeric_missing_raises(self):
        defn = _make_definition(data_type="numeric")
        with pytest.raises(InvalidDataValueException):
            DataPointService._validate_value(
                defn, value_numeric=None, value_string=None, value_boolean=None,
            )

    def test_numeric_below_lower_limit(self):
        defn = _make_definition(data_type="numeric", lower_limit=10.0, upper_limit=100.0)
        with pytest.raises(ValueOutOfLimitsException):
            DataPointService._validate_value(
                defn, value_numeric=5.0, value_string=None, value_boolean=None,
            )

    def test_numeric_above_upper_limit(self):
        defn = _make_definition(data_type="numeric", lower_limit=10.0, upper_limit=100.0)
        with pytest.raises(ValueOutOfLimitsException):
            DataPointService._validate_value(
                defn, value_numeric=150.0, value_string=None, value_boolean=None,
            )

    def test_numeric_at_exact_limits(self):
        defn = _make_definition(data_type="numeric", lower_limit=10.0, upper_limit=100.0)
        # At exact boundaries should pass
        DataPointService._validate_value(
            defn, value_numeric=10.0, value_string=None, value_boolean=None,
        )
        DataPointService._validate_value(
            defn, value_numeric=100.0, value_string=None, value_boolean=None,
        )

    def test_numeric_no_limits(self):
        defn = _make_definition(data_type="numeric", lower_limit=None, upper_limit=None)
        DataPointService._validate_value(
            defn, value_numeric=99999.0, value_string=None, value_boolean=None,
        )

    def test_string_valid(self):
        defn = _make_definition(data_type="string")
        DataPointService._validate_value(
            defn, value_numeric=None, value_string="hello", value_boolean=None,
        )

    def test_string_missing_raises(self):
        defn = _make_definition(data_type="string")
        with pytest.raises(InvalidDataValueException):
            DataPointService._validate_value(
                defn, value_numeric=None, value_string=None, value_boolean=None,
            )

    def test_boolean_valid(self):
        defn = _make_definition(data_type="boolean")
        DataPointService._validate_value(
            defn, value_numeric=None, value_string=None, value_boolean=True,
        )
        DataPointService._validate_value(
            defn, value_numeric=None, value_string=None, value_boolean=False,
        )

    def test_boolean_missing_raises(self):
        defn = _make_definition(data_type="boolean")
        with pytest.raises(InvalidDataValueException):
            DataPointService._validate_value(
                defn, value_numeric=None, value_string=None, value_boolean=None,
            )

    def test_enum_valid(self):
        defn = _make_definition(
            data_type="enum", enum_values="red,green,blue",
        )
        DataPointService._validate_value(
            defn, value_numeric=None, value_string="red", value_boolean=None,
        )

    def test_enum_invalid_value(self):
        defn = _make_definition(
            data_type="enum", enum_values="red,green,blue",
        )
        with pytest.raises(InvalidEnumValueException):
            DataPointService._validate_value(
                defn, value_numeric=None, value_string="purple", value_boolean=None,
            )

    def test_enum_missing_value_raises(self):
        defn = _make_definition(data_type="enum", enum_values="a,b")
        with pytest.raises(InvalidDataValueException):
            DataPointService._validate_value(
                defn, value_numeric=None, value_string=None, value_boolean=None,
            )

    def test_enum_no_allowed_values_accepts_anything(self):
        """If enum_values is empty/null, any string should be accepted."""
        defn = _make_definition(data_type="enum", enum_values=None)
        DataPointService._validate_value(
            defn, value_numeric=None, value_string="anything", value_boolean=None,
        )

    def test_enum_whitespace_trimming(self):
        defn = _make_definition(
            data_type="enum", enum_values=" red , green , blue ",
        )
        DataPointService._validate_value(
            defn, value_numeric=None, value_string="green", value_boolean=None,
        )


# ═════════════════════════════════════════════════════════════════════
# SERVICE / ROUTER IMPORT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataCollectionServiceImports:
    def test_definition_service_importable(self):
        from mes.core.data_collection.service import DataDefinitionService
        assert DataDefinitionService is not None

    def test_definition_service_has_crud_methods(self):
        from mes.core.data_collection.service import DataDefinitionService
        for method in (
            "list_definitions", "get_definition",
            "create_definition", "update_definition", "delete_definition",
        ):
            assert hasattr(DataDefinitionService, method), f"Missing {method}"

    def test_point_service_importable(self):
        from mes.core.data_collection.service import DataPointService
        assert DataPointService is not None

    def test_point_service_has_methods(self):
        from mes.core.data_collection.service import DataPointService
        for method in (
            "collect", "collect_batch",
            "list_points", "get_point",
            "get_points_for_unit", "get_definitions_for_step",
        ):
            assert hasattr(DataPointService, method), f"Missing {method}"


class TestDataCollectionRouterImports:
    def test_router_importable(self):
        from mes.core.data_collection.routes import router
        assert router is not None

    def test_router_has_definition_routes(self):
        from mes.core.data_collection.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/data/definitions" in paths
        assert "/api/v1/data/definitions/{definition_id}" in paths

    def test_router_has_collect_routes(self):
        from mes.core.data_collection.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/data/collect" in paths
        assert "/api/v1/data/collect-batch" in paths

    def test_router_has_points_routes(self):
        from mes.core.data_collection.routes import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/data/points" in paths
        assert "/api/v1/data/points/{point_id}" in paths


# ═════════════════════════════════════════════════════════════════════
# CONSTANTS TESTS
# ═════════════════════════════════════════════════════════════════════


class TestDataCollectionConstants:
    def test_data_types(self):
        assert "numeric" in DATA_TYPES
        assert "string" in DATA_TYPES
        assert "boolean" in DATA_TYPES
        assert "enum" in DATA_TYPES
        assert len(DATA_TYPES) == 4

    def test_data_sources(self):
        assert "manual" in DATA_SOURCES
        assert "equipment" in DATA_SOURCES
        assert "sensor" in DATA_SOURCES
        assert len(DATA_SOURCES) == 3


# ═════════════════════════════════════════════════════════════════════
# MODULE INIT TESTS
# ═════════════════════════════════════════════════════════════════════


class TestModuleInit:
    def test_module_importable(self):
        import mes.core.data_collection
        assert mes.core.data_collection is not None

    def test_models_importable(self):
        from mes.core.data_collection.models import DataDefinition, DataPoint
        assert DataDefinition is not None
        assert DataPoint is not None

    def test_events_importable(self):
        from mes.core.data_collection.events import data_collected, data_definition_created
        assert data_collected is not None
        assert data_definition_created is not None

    def test_exceptions_importable(self):
        from mes.core.data_collection.exceptions import (
            DuplicateDefinitionCodeException,
            InvalidDataValueException,
            InvalidEnumValueException,
            MissingRequiredDataException,
            ValueOutOfLimitsException,
        )
        assert DuplicateDefinitionCodeException is not None
        assert InvalidDataValueException is not None
        assert ValueOutOfLimitsException is not None
        assert MissingRequiredDataException is not None
        assert InvalidEnumValueException is not None
