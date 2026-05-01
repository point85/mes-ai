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
    OperationsDefinition,
    ProductDefinition,
    OperationsDefinitionMaterialAssignment,
    OperationsDefinitionProductAssignment,
    ProcessSegment,
    SegmentEquipmentRequirement,
    SegmentMaterialRequirement,
    SegmentParameter,
    ProcessSegmentInputDisposition,
    ProcessSegmentOutputDisposition,
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
    RouteProductAssignmentCreate,
    RouteProductAssignmentRead,
    RouteMaterialAssignmentCreate,
    RouteMaterialAssignmentRead,
    StepEquipmentRequirementCreate,
    StepEquipmentRequirementRead,
    StepEquipmentRequirementUpdate,
    StepMaterialRequirementCreate,
    StepMaterialRequirementRead,
    StepMaterialRequirementUpdate,
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
        assert OperationsDefinition.__tablename__ == "operations_definitions"

    def test_route_step_tablename(self):
        assert ProcessSegment.__tablename__ == "process_segments"

    def test_step_parameter_tablename(self):
        assert SegmentParameter.__tablename__ == "segment_parameters"

    def test_step_input_disposition_tablename(self):
        assert ProcessSegmentInputDisposition.__tablename__ == "process_segment_input_dispositions"

    def test_step_output_disposition_tablename(self):
        assert ProcessSegmentOutputDisposition.__tablename__ == "process_segment_output_dispositions"

    def test_all_models_inherit_base_columns(self):
        """All product def entities must have id, created_at, updated_at, is_active."""
        for model_cls in [
            ProductDefinition, BillOfMaterial, BOMItem,
            OperationsDefinition, ProcessSegment, SegmentParameter,
            ProcessSegmentInputDisposition, ProcessSegmentOutputDisposition,
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

    def test_product_has_route_assignments_relationship(self):
        """ProductDefinition links to routes via the product_assignments M2M."""
        rels = {r.key for r in ProductDefinition.__mapper__.relationships}
        assert "route_assignments" in rels

    def test_bom_has_items_relationship(self):
        rels = {r.key for r in BillOfMaterial.__mapper__.relationships}
        assert "items" in rels

    def test_route_has_steps_relationship(self):
        rels = {r.key for r in OperationsDefinition.__mapper__.relationships}
        assert "steps" in rels

    def test_step_has_parameters_relationship(self):
        rels = {r.key for r in ProcessSegment.__mapper__.relationships}
        assert "parameters" in rels

    def test_step_has_input_dispositions_relationship(self):
        rels = {r.key for r in ProcessSegment.__mapper__.relationships}
        assert "input_dispositions" in rels

    def test_step_has_output_dispositions_relationship(self):
        rels = {r.key for r in ProcessSegment.__mapper__.relationships}
        assert "output_dispositions" in rels

    def test_input_disposition_has_step_and_disposition_relationships(self):
        rels = {r.key for r in ProcessSegmentInputDisposition.__mapper__.relationships}
        assert "step" in rels
        assert "disposition" in rels

    def test_output_disposition_has_step_and_disposition_relationships(self):
        rels = {r.key for r in ProcessSegmentOutputDisposition.__mapper__.relationships}
        assert "step" in rels
        assert "disposition" in rels


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


# ─── ProcessSegment schema tests ──────────────────────────────────────────


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
        assert schema.expected_cycle_time_sec is None
        assert schema.erp_operation_number is None

    def test_step_create_invalid_type(self):
        with pytest.raises(Exception):
            RouteStepCreate(sequence=10, name="Bad", step_type="unknown")

    def test_step_create_zero_sequence_rejected(self):
        with pytest.raises(Exception):
            RouteStepCreate(sequence=0, name="Bad")

    def test_step_create_mrb_type(self):
        schema = RouteStepCreate(sequence=30, name="MRB Review", step_type="mrb")
        assert schema.step_type == "mrb"


# ─── SegmentParameter schema tests ──────────────────────────────────────


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
        col_names = {c.key for c in ProcessSegment.__mapper__.columns}
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


# ─── Route–Product Assignment tests ──────────────────────────────────


class TestRouteProductAssignment:
    """Tests for the route–product many-to-many support."""

    def test_route_product_assignment_tablename(self):
        assert OperationsDefinitionProductAssignment.__tablename__ == "operations_definition_product_assignments"

    def test_route_product_assignment_has_base_columns(self):
        col_names = {c.key for c in OperationsDefinitionProductAssignment.__mapper__.columns}
        assert "id" in col_names
        assert "route_id" in col_names
        assert "product_id" in col_names
        assert "is_active" in col_names

    def test_route_product_assignment_relationships(self):
        rels = {r.key for r in OperationsDefinitionProductAssignment.__mapper__.relationships}
        assert "route" in rels
        assert "product" in rels

    def test_process_route_has_product_assignments_relationship(self):
        rels = {r.key for r in OperationsDefinition.__mapper__.relationships}
        assert "product_assignments" in rels

    def test_route_product_assignment_create_schema(self):
        schema = RouteProductAssignmentCreate(product_id=uuid.uuid4())
        assert schema.product_id is not None

    def test_route_product_assignment_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = RouteProductAssignmentRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.is_active is True

    def test_route_read_standalone(self):
        """RouteRead is independent of ProductDefinition (M2M via assignment)."""
        now = datetime.now(timezone.utc)
        schema = RouteRead(
            id=uuid.uuid4(),
            version="1.0",
            name="Standalone Route",
            description=None,
            is_default=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.name == "Standalone Route"

    def test_service_has_standalone_route_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_all_routes")
        assert hasattr(ProductDefService, "create_standalone_route")
        assert hasattr(ProductDefService, "assign_product_to_route")
        assert hasattr(ProductDefService, "unassign_product_from_route")
        assert hasattr(ProductDefService, "list_route_products")


# ─── Route–Material Assignment tests ─────────────────────────────────


class TestRouteMaterialAssignment:
    """Tests for the route–material many-to-many support."""

    def test_route_material_assignment_tablename(self):
        assert OperationsDefinitionMaterialAssignment.__tablename__ == "operations_definition_material_assignments"

    def test_route_material_assignment_has_base_columns(self):
        col_names = {c.key for c in OperationsDefinitionMaterialAssignment.__mapper__.columns}
        assert "id" in col_names
        assert "route_id" in col_names
        assert "material_id" in col_names
        assert "is_active" in col_names

    def test_route_material_assignment_relationships(self):
        rels = {r.key for r in OperationsDefinitionMaterialAssignment.__mapper__.relationships}
        assert "route" in rels
        assert "material" in rels

    def test_process_route_has_material_assignments_relationship(self):
        rels = {r.key for r in OperationsDefinition.__mapper__.relationships}
        assert "material_assignments" in rels

    def test_route_material_assignment_create_schema(self):
        schema = RouteMaterialAssignmentCreate(material_id=uuid.uuid4())
        assert schema.material_id is not None

    def test_route_material_assignment_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = RouteMaterialAssignmentRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.is_active is True

    def test_service_has_material_assignment_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_route_materials")
        assert hasattr(ProductDefService, "assign_material_to_route")
        assert hasattr(ProductDefService, "unassign_material_from_route")

    def test_service_has_delete_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "delete_standalone_route")
        assert hasattr(ProductDefService, "delete_step")


# ─── ISA-95 Process Segment — Route Step Equipment Class ─────────────


class TestRouteStepEquipmentClass:
    """Tests for equipment_class_id on ProcessSegment."""

    def test_route_step_create_with_equipment_class_id(self):
        schema = RouteStepCreate(
            sequence=10,
            name="Fill",
            equipment_class_id=str(uuid.uuid4()),
        )
        assert schema.equipment_class_id is not None

    def test_route_step_create_without_equipment_class_id(self):
        schema = RouteStepCreate(sequence=10, name="Mix")
        assert schema.equipment_class_id is None

    def test_route_step_read_includes_equipment_class_id(self):
        now = datetime.now(timezone.utc)
        ec_id = uuid.uuid4()
        schema = RouteStepRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            sequence=10,
            name="Fill",
            step_type="production",
            equipment_class_id=ec_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.equipment_class_id == ec_id

    def test_route_step_update_equipment_class_id(self):
        ec_id = uuid.uuid4()
        schema = RouteStepUpdate(equipment_class_id=ec_id)
        assert schema.equipment_class_id == ec_id

    def test_model_has_equipment_class_id_column(self):
        assert hasattr(ProcessSegment, "equipment_class_id")

    def test_model_has_equipment_class_relationship(self):
        assert hasattr(ProcessSegment, "equipment_class")

    def test_model_has_equipment_requirements_relationship(self):
        assert hasattr(ProcessSegment, "equipment_requirements")

    def test_model_has_material_requirements_relationship(self):
        assert hasattr(ProcessSegment, "material_requirements")


# ─── ISA-95 Process Segment — Step Equipment Requirement ─────────────


class TestStepEquipmentRequirement:
    """Tests for SegmentEquipmentRequirement model and schemas."""

    def test_model_tablename(self):
        assert SegmentEquipmentRequirement.__tablename__ == "segment_equipment_requirements"

    def test_model_has_expected_columns(self):
        assert hasattr(SegmentEquipmentRequirement, "step_id")
        assert hasattr(SegmentEquipmentRequirement, "equipment_id")
        assert hasattr(SegmentEquipmentRequirement, "use_type")
        assert hasattr(SegmentEquipmentRequirement, "description")

    def test_create_schema_defaults(self):
        schema = StepEquipmentRequirementCreate(equipment_id=uuid.uuid4())
        assert schema.use_type == "preferred"
        assert schema.description is None

    def test_create_schema_required_use_type(self):
        schema = StepEquipmentRequirementCreate(
            equipment_id=uuid.uuid4(), use_type="required",
        )
        assert schema.use_type == "required"

    def test_create_schema_alternate_use_type(self):
        schema = StepEquipmentRequirementCreate(
            equipment_id=uuid.uuid4(), use_type="alternate",
        )
        assert schema.use_type == "alternate"

    def test_create_schema_invalid_use_type(self):
        with pytest.raises(Exception):
            StepEquipmentRequirementCreate(
                equipment_id=uuid.uuid4(), use_type="invalid",
            )

    def test_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = StepEquipmentRequirementRead(
            id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            equipment_id=uuid.uuid4(),
            use_type="preferred",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.use_type == "preferred"

    def test_update_schema(self):
        schema = StepEquipmentRequirementUpdate(use_type="required")
        assert schema.use_type == "required"

    def test_service_has_equipment_requirement_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_segment_equipment_requirements")
        assert hasattr(ProductDefService, "create_step_equipment_requirement")
        assert hasattr(ProductDefService, "update_step_equipment_requirement")
        assert hasattr(ProductDefService, "delete_step_equipment_requirement")


# ─── ISA-95 Process Segment — Step Material Requirement ──────────────


class TestStepMaterialRequirement:
    """Tests for SegmentMaterialRequirement model and schemas."""

    def test_model_tablename(self):
        assert SegmentMaterialRequirement.__tablename__ == "segment_material_requirements"

    def test_model_has_expected_columns(self):
        assert hasattr(SegmentMaterialRequirement, "step_id")
        assert hasattr(SegmentMaterialRequirement, "material_id")
        assert hasattr(SegmentMaterialRequirement, "quantity")
        assert hasattr(SegmentMaterialRequirement, "uom")
        assert hasattr(SegmentMaterialRequirement, "material_use")
        assert hasattr(SegmentMaterialRequirement, "position")
        assert hasattr(SegmentMaterialRequirement, "description")

    def test_create_schema_defaults(self):
        schema = StepMaterialRequirementCreate(
            material_id=uuid.uuid4(), quantity=5.0,
        )
        assert schema.uom == "EA"
        assert schema.material_use == "consumed"
        assert schema.position == 0
        assert schema.description is None

    def test_create_schema_produced(self):
        schema = StepMaterialRequirementCreate(
            material_id=uuid.uuid4(), quantity=1.0, material_use="produced",
        )
        assert schema.material_use == "produced"

    def test_create_schema_invalid_material_use(self):
        with pytest.raises(Exception):
            StepMaterialRequirementCreate(
                material_id=uuid.uuid4(), quantity=1.0, material_use="invalid",
            )

    def test_create_schema_quantity_must_be_positive(self):
        with pytest.raises(Exception):
            StepMaterialRequirementCreate(
                material_id=uuid.uuid4(), quantity=0,
            )

    def test_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = StepMaterialRequirementRead(
            id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            quantity=5.0,
            uom="kg",
            material_use="consumed",
            position=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.quantity == 5.0
        assert schema.material_use == "consumed"

    def test_update_schema(self):
        schema = StepMaterialRequirementUpdate(quantity=10.0, material_use="produced")
        assert schema.quantity == 10.0
        assert schema.material_use == "produced"

    def test_service_has_material_requirement_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_segment_material_requirements")
        assert hasattr(ProductDefService, "create_step_material_requirement")
        assert hasattr(ProductDefService, "update_step_material_requirement")
        assert hasattr(ProductDefService, "delete_step_material_requirement")


# ─── ISA-95 Process Segment — Route Step Equipment Class ─────────────


class TestRouteStepEquipmentClass:
    """Tests for equipment_class_id on ProcessSegment."""

    def test_route_step_create_with_equipment_class_id(self):
        schema = RouteStepCreate(
            sequence=10,
            name="Fill",
            equipment_class_id=str(uuid.uuid4()),
        )
        assert schema.equipment_class_id is not None

    def test_route_step_create_without_equipment_class_id(self):
        schema = RouteStepCreate(sequence=10, name="Mix")
        assert schema.equipment_class_id is None

    def test_route_step_read_includes_equipment_class_id(self):
        now = datetime.now(timezone.utc)
        ec_id = uuid.uuid4()
        schema = RouteStepRead(
            id=uuid.uuid4(),
            route_id=uuid.uuid4(),
            sequence=10,
            name="Fill",
            step_type="production",
            equipment_class_id=ec_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.equipment_class_id == ec_id

    def test_route_step_update_equipment_class_id(self):
        ec_id = uuid.uuid4()
        schema = RouteStepUpdate(equipment_class_id=ec_id)
        assert schema.equipment_class_id == ec_id

    def test_model_has_equipment_class_id_column(self):
        assert hasattr(ProcessSegment, "equipment_class_id")

    def test_model_has_equipment_class_relationship(self):
        assert hasattr(ProcessSegment, "equipment_class")

    def test_model_has_equipment_requirements_relationship(self):
        assert hasattr(ProcessSegment, "equipment_requirements")

    def test_model_has_material_requirements_relationship(self):
        assert hasattr(ProcessSegment, "material_requirements")


# ─── ISA-95 Process Segment — Step Equipment Requirement ─────────────


class TestStepEquipmentRequirement:
    """Tests for SegmentEquipmentRequirement model and schemas."""

    def test_model_tablename(self):
        assert SegmentEquipmentRequirement.__tablename__ == "segment_equipment_requirements"

    def test_model_has_expected_columns(self):
        assert hasattr(SegmentEquipmentRequirement, "step_id")
        assert hasattr(SegmentEquipmentRequirement, "equipment_id")
        assert hasattr(SegmentEquipmentRequirement, "use_type")
        assert hasattr(SegmentEquipmentRequirement, "description")

    def test_create_schema_defaults(self):
        schema = StepEquipmentRequirementCreate(equipment_id=uuid.uuid4())
        assert schema.use_type == "preferred"
        assert schema.description is None

    def test_create_schema_required_use_type(self):
        schema = StepEquipmentRequirementCreate(
            equipment_id=uuid.uuid4(), use_type="required",
        )
        assert schema.use_type == "required"

    def test_create_schema_alternate_use_type(self):
        schema = StepEquipmentRequirementCreate(
            equipment_id=uuid.uuid4(), use_type="alternate",
        )
        assert schema.use_type == "alternate"

    def test_create_schema_invalid_use_type(self):
        with pytest.raises(Exception):
            StepEquipmentRequirementCreate(
                equipment_id=uuid.uuid4(), use_type="invalid",
            )

    def test_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = StepEquipmentRequirementRead(
            id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            equipment_id=uuid.uuid4(),
            use_type="preferred",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.use_type == "preferred"

    def test_update_schema(self):
        schema = StepEquipmentRequirementUpdate(use_type="required")
        assert schema.use_type == "required"

    def test_service_has_equipment_requirement_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_segment_equipment_requirements")
        assert hasattr(ProductDefService, "create_step_equipment_requirement")
        assert hasattr(ProductDefService, "update_step_equipment_requirement")
        assert hasattr(ProductDefService, "delete_step_equipment_requirement")


# ─── ISA-95 Process Segment — Step Material Requirement ──────────────


class TestStepMaterialRequirement:
    """Tests for SegmentMaterialRequirement model and schemas."""

    def test_model_tablename(self):
        assert SegmentMaterialRequirement.__tablename__ == "segment_material_requirements"

    def test_model_has_expected_columns(self):
        assert hasattr(SegmentMaterialRequirement, "step_id")
        assert hasattr(SegmentMaterialRequirement, "material_id")
        assert hasattr(SegmentMaterialRequirement, "quantity")
        assert hasattr(SegmentMaterialRequirement, "uom")
        assert hasattr(SegmentMaterialRequirement, "material_use")
        assert hasattr(SegmentMaterialRequirement, "position")
        assert hasattr(SegmentMaterialRequirement, "description")

    def test_create_schema_defaults(self):
        schema = StepMaterialRequirementCreate(
            material_id=uuid.uuid4(), quantity=5.0,
        )
        assert schema.uom == "EA"
        assert schema.material_use == "consumed"
        assert schema.position == 0
        assert schema.description is None

    def test_create_schema_produced(self):
        schema = StepMaterialRequirementCreate(
            material_id=uuid.uuid4(), quantity=1.0, material_use="produced",
        )
        assert schema.material_use == "produced"

    def test_create_schema_invalid_material_use(self):
        with pytest.raises(Exception):
            StepMaterialRequirementCreate(
                material_id=uuid.uuid4(), quantity=1.0, material_use="invalid",
            )

    def test_create_schema_quantity_must_be_positive(self):
        with pytest.raises(Exception):
            StepMaterialRequirementCreate(
                material_id=uuid.uuid4(), quantity=0,
            )

    def test_read_schema(self):
        now = datetime.now(timezone.utc)
        schema = StepMaterialRequirementRead(
            id=uuid.uuid4(),
            step_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            quantity=5.0,
            uom="kg",
            material_use="consumed",
            position=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.quantity == 5.0
        assert schema.material_use == "consumed"

    def test_update_schema(self):
        schema = StepMaterialRequirementUpdate(quantity=10.0, material_use="produced")
        assert schema.quantity == 10.0
        assert schema.material_use == "produced"

    def test_service_has_material_requirement_methods(self):
        from mes.core.product_def.service import ProductDefService
        assert hasattr(ProductDefService, "list_segment_material_requirements")
        assert hasattr(ProductDefService, "create_step_material_requirement")
        assert hasattr(ProductDefService, "update_step_material_requirement")
        assert hasattr(ProductDefService, "delete_step_material_requirement")
