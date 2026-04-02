"""
Unit tests for PROD-DEF module.

Tests cover:
- Model creation and field defaults
- Schema validation (create/read/update)
- Event factory functions
- Exception hierarchy
- Business logic validation (code+version uniqueness, type constraints)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from mes.core.product_def.events import bom_created, product_created, route_created
from mes.core.product_def.exceptions import DuplicateProductException
from mes.core.product_def.models import (
    BillOfMaterial,
    BOMItem,
    ProcessRoute,
    ProductDefinition,
    RouteStep,
    StepParameter,
    StepTransition,
)
from mes.core.product_def.schemas import (
    BOMCreate,
    BOMItemCreate,
    BOMItemRead,
    BOMRead,
    BOMUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    RouteCreate,
    RouteRead,
    RouteStepCreate,
    RouteStepRead,
    RouteStepUpdate,
    RouteUpdate,
    StepParameterCreate,
    StepParameterRead,
    StepTransitionCreate,
    StepTransitionRead,
    StepTransitionUpdate,
)


# ─── Model tests ─────────────────────────────────────────────────────


class TestProductDefModels:
    """Test SQLAlchemy model definitions."""

    def test_product_definition_tablename(self):
        assert ProductDefinition.__tablename__ == "product_definitions"

    def test_bill_of_material_tablename(self):
        assert BillOfMaterial.__tablename__ == "bills_of_material"

    def test_bom_item_tablename(self):
        assert BOMItem.__tablename__ == "bom_items"

    def test_process_route_tablename(self):
        assert ProcessRoute.__tablename__ == "process_routes"

    def test_route_step_tablename(self):
        assert RouteStep.__tablename__ == "route_steps"

    def test_step_parameter_tablename(self):
        assert StepParameter.__tablename__ == "step_parameters"

    def test_step_transition_tablename(self):
        assert StepTransition.__tablename__ == "step_transitions"

    def test_all_models_inherit_base_columns(self):
        """All product def entities must have id, created_at, updated_at, is_active."""
        for model_cls in [
            ProductDefinition, BillOfMaterial, BOMItem,
            ProcessRoute, RouteStep, StepParameter, StepTransition,
        ]:
            mapper = model_cls.__mapper__
            col_names = {c.key for c in mapper.columns}
            assert "id" in col_names, f"{model_cls.__name__} missing 'id'"
            assert "created_at" in col_names, f"{model_cls.__name__} missing 'created_at'"
            assert "updated_at" in col_names, f"{model_cls.__name__} missing 'updated_at'"
            assert "is_active" in col_names, f"{model_cls.__name__} missing 'is_active'"

    def test_product_has_boms_relationship(self):
        """ProductDefinition should declare a 'boms' relationship."""
        rels = {r.key for r in ProductDefinition.__mapper__.relationships}
        assert "boms" in rels

    def test_product_has_routes_relationship(self):
        """ProductDefinition should declare a 'routes' relationship."""
        rels = {r.key for r in ProductDefinition.__mapper__.relationships}
        assert "routes" in rels

    def test_bom_has_items_relationship(self):
        rels = {r.key for r in BillOfMaterial.__mapper__.relationships}
        assert "items" in rels

    def test_route_has_steps_relationship(self):
        rels = {r.key for r in ProcessRoute.__mapper__.relationships}
        assert "steps" in rels

    def test_step_has_parameters_relationship(self):
        rels = {r.key for r in RouteStep.__mapper__.relationships}
        assert "parameters" in rels

    def test_step_has_outgoing_transitions_relationship(self):
        rels = {r.key for r in RouteStep.__mapper__.relationships}
        assert "outgoing_transitions" in rels

    def test_step_has_incoming_transitions_relationship(self):
        rels = {r.key for r in RouteStep.__mapper__.relationships}
        assert "incoming_transitions" in rels

    def test_step_transition_has_from_and_to_step_relationships(self):
        rels = {r.key for r in StepTransition.__mapper__.relationships}
        assert "from_step" in rels
        assert "to_step" in rels


# ─── ProductDefinition schema tests ──────────────────────────────────


class TestProductSchemas:
    def test_product_create_full(self):
        schema = ProductCreate(
            name="Widget A",
            code="WDG-A",
            version="2.0",
            description="Premium widget",
            uom="EA",
            product_type="discrete",
        )
        assert schema.name == "Widget A"
        assert schema.code == "WDG-A"
        assert schema.version == "2.0"
        assert schema.product_type == "discrete"

    def test_product_create_defaults(self):
        schema = ProductCreate(name="Basic Widget", code="WDG-B")
        assert schema.version == "1.0"
        assert schema.uom == "EA"
        assert schema.product_type == "discrete"

    def test_product_create_process_type(self):
        schema = ProductCreate(name="Chemical X", code="CHM-X", product_type="process")
        assert schema.product_type == "process"

    def test_product_create_invalid_type(self):
        with pytest.raises(Exception):
            ProductCreate(name="Bad", code="BAD", product_type="hybrid")

    def test_product_create_empty_name_rejected(self):
        with pytest.raises(Exception):
            ProductCreate(name="", code="TST")

    def test_product_read(self):
        now = datetime.now(timezone.utc)
        schema = ProductRead(
            id=uuid.uuid4(),
            name="Widget",
            code="WDG",
            version="1.0",
            uom="EA",
            product_type="discrete",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.code == "WDG"

    def test_product_update_partial(self):
        schema = ProductUpdate(description="New description")
        assert schema.description == "New description"
        assert schema.name is None
        assert schema.code is None


# ─── BOM schema tests ────────────────────────────────────────────────


class TestBOMSchemas:
    def test_bom_create_defaults(self):
        schema = BOMCreate()
        assert schema.version == "1.0"
        assert schema.effective_date is None
        assert schema.expiry_date is None

    def test_bom_create_with_dates(self):
        schema = BOMCreate(
            version="2.0",
            effective_date=date(2026, 3, 1),
            expiry_date=date(2027, 3, 1),
        )
        assert schema.version == "2.0"
        assert schema.effective_date == date(2026, 3, 1)

    def test_bom_read(self):
        now = datetime.now(timezone.utc)
        schema = BOMRead(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            version="1.0",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.version == "1.0"


class TestBOMItemSchemas:
    def test_bom_item_create_valid(self):
        schema = BOMItemCreate(
            material_code="MAT-001",
            quantity=5.0,
            uom="KG",
            position=10,
        )
        assert schema.material_code == "MAT-001"
        assert schema.quantity == 5.0
        assert schema.position == 10

    def test_bom_item_create_defaults(self):
        schema = BOMItemCreate(material_code="MAT-001", quantity=1.0)
        assert schema.uom == "EA"
        assert schema.position == 0

    def test_bom_item_create_zero_quantity_rejected(self):
        with pytest.raises(Exception):
            BOMItemCreate(material_code="MAT-001", quantity=0)

    def test_bom_item_create_negative_quantity_rejected(self):
        with pytest.raises(Exception):
            BOMItemCreate(material_code="MAT-001", quantity=-1.0)


# ─── Route schema tests ──────────────────────────────────────────────


class TestRouteSchemas:
    def test_route_create_full(self):
        schema = RouteCreate(
            name="Standard Route",
            version="1.0",
            description="Main manufacturing route",
            is_default=True,
        )
        assert schema.name == "Standard Route"
        assert schema.is_default is True

    def test_route_create_defaults(self):
        schema = RouteCreate(name="Route A")
        assert schema.version == "1.0"
        assert schema.is_default is False

    def test_route_read(self):
        now = datetime.now(timezone.utc)
        schema = RouteRead(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            version="1.0",
            name="Standard",
            is_default=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.is_default is True


# ─── RouteStep schema tests ──────────────────────────────────────────


class TestRouteStepSchemas:
    def test_step_create_production(self):
        schema = RouteStepCreate(
            sequence=10,
            name="Machining",
            step_type="production",
            expected_cycle_time_sec=120.0,
        )
        assert schema.sequence == 10
        assert schema.step_type == "production"

    def test_step_create_inspection(self):
        schema = RouteStepCreate(
            sequence=20,
            name="Visual Inspection",
            step_type="inspection",
        )
        assert schema.step_type == "inspection"

    def test_step_create_rework(self):
        schema = RouteStepCreate(
            sequence=30,
            name="Rework Loop",
            step_type="rework",
        )
        assert schema.step_type == "rework"

    def test_step_create_defaults(self):
        schema = RouteStepCreate(sequence=10, name="Step 1")
        assert schema.step_type == "production"
        assert schema.work_cell_id is None
        assert schema.expected_cycle_time_sec is None
        assert schema.erp_operation_number is None

    def test_step_create_invalid_type(self):
        with pytest.raises(Exception):
            RouteStepCreate(sequence=10, name="Bad", step_type="unknown")

    def test_step_create_with_work_cell(self):
        wc_id = uuid.uuid4()
        schema = RouteStepCreate(
            sequence=10,
            name="Step",
            work_cell_id=wc_id,
        )
        assert schema.work_cell_id == wc_id

    def test_step_create_zero_sequence_rejected(self):
        with pytest.raises(Exception):
            RouteStepCreate(sequence=0, name="Bad")

    def test_step_create_mrb_type(self):
        schema = RouteStepCreate(sequence=30, name="MRB Review", step_type="mrb")
        assert schema.step_type == "mrb"


# ─── StepParameter schema tests ──────────────────────────────────────


class TestStepParameterSchemas:
    def test_param_create_numeric(self):
        schema = StepParameterCreate(
            name="Torque",
            data_type="numeric",
            uom="Nm",
            target_value="50",
            lower_limit="45",
            upper_limit="55",
            is_required=True,
        )
        assert schema.name == "Torque"
        assert schema.data_type == "numeric"
        assert schema.is_required is True
        assert schema.target_value == "50"

    def test_param_create_defaults(self):
        schema = StepParameterCreate(name="Note")
        assert schema.data_type == "numeric"
        assert schema.is_required is False
        assert schema.uom is None

    def test_param_create_boolean_type(self):
        schema = StepParameterCreate(name="Pass/Fail", data_type="boolean")
        assert schema.data_type == "boolean"


# ─── ERP Operation Number tests ──────────────────────────────────────


class TestRouteStepERPFields:
    def test_step_create_with_erp_operation_number(self):
        schema = RouteStepCreate(
            sequence=10,
            name="Machining",
            erp_operation_number="0010",
        )
        assert schema.erp_operation_number == "0010"

    def test_step_read_with_erp_operation_number(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        schema = RouteStepRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            sequence=20,
            name="Assembly",
            step_type="production",
            erp_operation_number="0020",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.erp_operation_number == "0020"

    def test_step_read_erp_operation_number_default_none(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        schema = RouteStepRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            sequence=10,
            name="Step",
            step_type="production",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.erp_operation_number is None

    def test_step_update_erp_operation_number(self):
        schema = RouteStepUpdate(erp_operation_number="0030")
        assert schema.erp_operation_number == "0030"

    def test_route_step_model_has_erp_operation_number(self):
        col_names = {c.key for c in RouteStep.__mapper__.columns}
        assert "erp_operation_number" in col_names

    def test_service_has_sync_method(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "sync_routes_from_erp")

    def test_param_create_enum_type(self):
        schema = StepParameterCreate(name="Color", data_type="enum")
        assert schema.data_type == "enum"

    def test_param_create_string_type(self):
        schema = StepParameterCreate(name="Comment", data_type="string")
        assert schema.data_type == "string"

    def test_param_create_invalid_type(self):
        with pytest.raises(Exception):
            StepParameterCreate(name="Bad", data_type="float")

    def test_param_read(self):
        now = datetime.now(timezone.utc)
        schema = StepParameterRead(
            id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            name="Temperature",
            data_type="numeric",
            uom="°C",
            target_value="22",
            lower_limit="20",
            upper_limit="25",
            is_required=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.name == "Temperature"
        assert schema.uom == "°C"


# ─── Event tests ─────────────────────────────────────────────────────


class TestProductDefEvents:
    def test_product_created_event(self):
        event = product_created("prod-123", "WDG-A", "1.0")
        assert event.event_type == "product_def.product.created"
        assert event.source == "product_def"
        assert event.payload["product_id"] == "prod-123"
        assert event.payload["code"] == "WDG-A"
        assert event.payload["version"] == "1.0"

    def test_route_created_event(self):
        event = route_created("route-456", "prod-123", "Standard Route")
        assert event.event_type == "product_def.route.created"
        assert event.payload["route_id"] == "route-456"
        assert event.payload["product_id"] == "prod-123"
        assert event.payload["name"] == "Standard Route"

    def test_bom_created_event(self):
        event = bom_created("bom-789", "prod-123", "2.0")
        assert event.event_type == "product_def.bom.created"
        assert event.payload["bom_id"] == "bom-789"
        assert event.payload["version"] == "2.0"


# ─── Exception tests ─────────────────────────────────────────────────


class TestProductDefExceptions:
    def test_duplicate_product_exception(self):
        exc = DuplicateProductException("WDG-A", "2.0")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_PRODUCT"
        assert "WDG-A" in str(exc)
        assert "2.0" in str(exc)
        assert exc.details["code"] == "WDG-A"
        assert exc.details["version"] == "2.0"
