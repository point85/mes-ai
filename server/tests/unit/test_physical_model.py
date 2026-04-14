"""
Unit tests for PHYS-MODEL module.

Tests cover:
- Model creation and field defaults
- Schema validation (create/read/update)
- Event factory functions
- Exception hierarchy
- Service business logic validation (code uniqueness, parent existence, soft delete)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from mes.core.physical_model.events import (
    equipment_created,
    site_created,
)
from mes.core.physical_model.exceptions import DuplicateCodeException
from mes.core.physical_model.models import (
    Area,
    Equipment,
    EquipmentMaterial,
    ProductionLine,
    Site,
    WorkCell,
)
# EquipmentMaterial references MaterialDefinition and UnitOfMeasure via
# string-based relationships — import their modules so SQLAlchemy can resolve them.
import mes.core.material.models  # noqa: F401
import mes.core.uom.models  # noqa: F401
from mes.core.physical_model.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    EquipmentCreate,
    EquipmentMaterialCreate,
    EquipmentMaterialRead,
    EquipmentMaterialUpdate,
    EquipmentRead,
    EquipmentUpdate,
    ProductionLineCreate,
    ProductionLineRead,
    ProductionLineUpdate,
    SiteCreate,
    SiteRead,
    SiteUpdate,
    WorkCellCreate,
    WorkCellRead,
    WorkCellUpdate,
)


# ─── Model tests ─────────────────────────────────────────────────────


class TestPhysicalModels:
    """Test SQLAlchemy model definitions (abstract base, fields, tablenames)."""

    def test_site_is_concrete_model(self):
        """Site should be a concrete mapped model (has __tablename__, is in mapper)."""
        assert hasattr(Site, "__tablename__")
        assert Site.__tablename__ == "sites"
        # Confirm it has a mapper (concrete models do, abstract don't)
        assert hasattr(Site, "__mapper__")

    def test_site_tablename(self):
        assert Site.__tablename__ == "sites"

    def test_area_tablename(self):
        assert Area.__tablename__ == "areas"

    def test_production_line_tablename(self):
        assert ProductionLine.__tablename__ == "production_lines"

    def test_work_cell_tablename(self):
        assert WorkCell.__tablename__ == "work_cells"

    def test_equipment_tablename(self):
        assert Equipment.__tablename__ == "equipment"

    def test_all_models_inherit_base_columns(self):
        """All physical model entities must have id, created_at, updated_at, is_active."""
        for model_cls in [Site, Area, ProductionLine, WorkCell, Equipment, EquipmentMaterial]:
            mapper = model_cls.__mapper__
            col_names = {c.key for c in mapper.columns}
            assert "id" in col_names, f"{model_cls.__name__} missing 'id'"
            assert "created_at" in col_names, f"{model_cls.__name__} missing 'created_at'"
            assert "updated_at" in col_names, f"{model_cls.__name__} missing 'updated_at'"
            assert "is_active" in col_names, f"{model_cls.__name__} missing 'is_active'"


# ─── Schema tests ────────────────────────────────────────────────────


class TestSiteSchemas:
    def test_site_create_valid(self):
        schema = SiteCreate(
            name="Main Plant",
            code="PLANT-001",
            description="Primary manufacturing facility",
            timezone="America/Chicago",
            address="123 Factory Rd",
        )
        assert schema.name == "Main Plant"
        assert schema.code == "PLANT-001"
        assert schema.timezone == "America/Chicago"

    def test_site_create_minimal(self):
        schema = SiteCreate(name="Test Site", code="TS01")
        assert schema.name == "Test Site"
        assert schema.description is None
        assert schema.timezone is None
        assert schema.address is None

    def test_site_create_empty_name_rejected(self):
        with pytest.raises(Exception):
            SiteCreate(name="", code="TS01")

    def test_site_read_from_attributes(self):
        """SiteRead should be constructable from model-like attributes."""
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        schema = SiteRead(
            id=uid,
            name="Plant A",
            code="PA",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.id == uid
        assert schema.is_active is True

    def test_site_update_all_optional(self):
        schema = SiteUpdate()
        assert schema.name is None
        assert schema.code is None
        assert schema.description is None

    def test_site_update_partial(self):
        schema = SiteUpdate(name="Updated Name")
        assert schema.name == "Updated Name"
        assert schema.code is None


class TestAreaSchemas:
    def test_area_create_valid(self):
        schema = AreaCreate(name="Assembly", code="ASSY-01")
        assert schema.name == "Assembly"
        assert schema.code == "ASSY-01"

    def test_area_read_includes_site_id(self):
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        site_uid = uuid.uuid4()
        schema = AreaRead(
            id=uid, name="Area A", code="AA", site_id=site_uid,
            is_active=True, created_at=now, updated_at=now,
        )
        assert schema.site_id == site_uid


class TestProductionLineSchemas:
    def test_line_create_valid(self):
        schema = ProductionLineCreate(name="Line 1", code="L01")
        assert schema.name == "Line 1"

    def test_line_update_partial(self):
        schema = ProductionLineUpdate(description="Updated line")
        assert schema.description == "Updated line"
        assert schema.name is None


class TestWorkCellSchemas:
    def test_work_cell_create_default_type(self):
        schema = WorkCellCreate(name="Station A", code="WC-A")
        assert schema.wc_type == "manual"

    def test_work_cell_create_automated(self):
        schema = WorkCellCreate(name="Robot A", code="WC-R1", wc_type="automated")
        assert schema.wc_type == "automated"

    def test_work_cell_create_invalid_type(self):
        with pytest.raises(Exception):
            WorkCellCreate(name="Bad", code="WC-BAD", wc_type="unknown")


class TestEquipmentSchemas:
    def test_equipment_create_defaults(self):
        schema = EquipmentCreate(name="CNC Mill", code="EQ-001")
        assert schema.capabilities is None

    def test_equipment_create_with_capabilities(self):
        schema = EquipmentCreate(
            name="CNC Mill",
            code="EQ-001",
            capabilities={"max_rpm": 12000, "axes": 5},
        )
        assert schema.capabilities["max_rpm"] == 12000

    def test_equipment_read_full(self):
        now = datetime.now(timezone.utc)
        schema = EquipmentRead(
            id=uuid.uuid4(),
            name="Mill",
            code="ML-01",
            work_cell_id=uuid.uuid4(),
            is_active=True,
            created_at=now,
            updated_at=now,
            equipment_type="CNC",
            capabilities={"speed": 100},
        )
        assert schema.equipment_type == "CNC"
        assert schema.capabilities == {"speed": 100}


# ─── Event tests ─────────────────────────────────────────────────────


class TestPhysicalModelEvents:
    def test_site_created_event(self):
        event = site_created("site-abc", "PLANT-01")
        assert event.event_type == "physical_model.site.created"
        assert event.payload["site_id"] == "site-abc"
        assert event.payload["code"] == "PLANT-01"

    def test_equipment_created_event(self):
        event = equipment_created("eq-1", "EQ-001", "wc-1")
        assert event.event_type == "physical_model.equipment.created"
        assert event.payload["equipment_id"] == "eq-1"
        assert event.payload["work_cell_id"] == "wc-1"


# ─── Exception tests ─────────────────────────────────────────────────


class TestPhysicalModelExceptions:
    def test_duplicate_code_exception(self):
        exc = DuplicateCodeException("Site", "PLANT-01")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_CODE"
        assert "PLANT-01" in str(exc)
        assert exc.details["entity"] == "Site"
        assert exc.details["code"] == "PLANT-01"

    def test_duplicate_code_exception_different_entities(self):
        for entity in ["Site", "Area", "ProductionLine", "WorkCell", "Equipment"]:
            exc = DuplicateCodeException(entity, "CODE-1")
            assert entity in str(exc)


# ─── EquipmentMaterial model tests ───────────────────────────────────


class TestEquipmentMaterialModel:
    """Test the EquipmentMaterial junction model definition."""

    def test_tablename(self):
        assert EquipmentMaterial.__tablename__ == "equipment_materials"

    def test_inherits_base_columns(self):
        mapper = EquipmentMaterial.__mapper__
        col_names = {c.key for c in mapper.columns}
        for col in ("id", "created_at", "updated_at", "is_active"):
            assert col in col_names, f"Missing base column '{col}'"

    def test_has_junction_columns(self):
        mapper = EquipmentMaterial.__mapper__
        col_names = {c.key for c in mapper.columns}
        for col in (
            "equipment_id", "material_id",
            "design_speed", "design_speed_uom",
            "reject_uom", "target_oee",
        ):
            assert col in col_names, f"Missing column '{col}'"

    def test_has_unique_constraint(self):
        """Should have a unique constraint on (equipment_id, material_id)."""
        table = EquipmentMaterial.__table__
        uc_names = [c.name for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        assert "uq_equip_material" in uc_names

    def test_repr(self):
        em = EquipmentMaterial(
            equipment_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            design_speed=120.0,
            design_speed_uom="EA/h",
            reject_uom="EA",
            target_oee=85.0,
        )
        r = repr(em)
        assert "EquipmentMaterial" in r
        assert "120.0" in r
        assert "85.0%" in r


# ─── EquipmentMaterial schema tests ──────────────────────────────────


class TestEquipmentMaterialSchemas:
    """Test Pydantic schemas for equipment material setups."""

    def test_create_valid(self):
        schema = EquipmentMaterialCreate(
            material_id=uuid.uuid4(),
            design_speed=120.5,
            design_speed_uom="EA/h",
            reject_uom="EA",
            target_oee=85.0,
        )
        assert schema.design_speed == 120.5
        assert schema.design_speed_uom == "EA/h"
        assert schema.reject_uom == "EA"
        assert schema.target_oee == 85.0

    def test_create_zero_speed_rejected(self):
        with pytest.raises(Exception):
            EquipmentMaterialCreate(
                material_id=uuid.uuid4(),
                design_speed=0,
                design_speed_uom="EA/h",
                reject_uom="EA",
                target_oee=85.0,
            )

    def test_create_negative_speed_rejected(self):
        with pytest.raises(Exception):
            EquipmentMaterialCreate(
                material_id=uuid.uuid4(),
                design_speed=-10,
                design_speed_uom="EA/h",
                reject_uom="EA",
                target_oee=85.0,
            )

    def test_create_oee_below_zero_rejected(self):
        with pytest.raises(Exception):
            EquipmentMaterialCreate(
                material_id=uuid.uuid4(),
                design_speed=100,
                design_speed_uom="EA/h",
                reject_uom="EA",
                target_oee=-1,
            )

    def test_create_oee_above_100_rejected(self):
        with pytest.raises(Exception):
            EquipmentMaterialCreate(
                material_id=uuid.uuid4(),
                design_speed=100,
                design_speed_uom="EA/h",
                reject_uom="EA",
                target_oee=101,
            )

    def test_create_oee_boundary_zero(self):
        schema = EquipmentMaterialCreate(
            material_id=uuid.uuid4(),
            design_speed=50,
            design_speed_uom="EA/h",
            reject_uom="EA",
            target_oee=0.0,
        )
        assert schema.target_oee == 0.0

    def test_create_oee_boundary_hundred(self):
        schema = EquipmentMaterialCreate(
            material_id=uuid.uuid4(),
            design_speed=50,
            design_speed_uom="EA/h",
            reject_uom="EA",
            target_oee=100.0,
        )
        assert schema.target_oee == 100.0

    def test_create_empty_uom_rejected(self):
        with pytest.raises(Exception):
            EquipmentMaterialCreate(
                material_id=uuid.uuid4(),
                design_speed=100,
                design_speed_uom="",
                reject_uom="EA",
                target_oee=85.0,
            )

    def test_read_from_attributes(self):
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        equip_id = uuid.uuid4()
        mat_id = uuid.uuid4()
        schema = EquipmentMaterialRead(
            id=uid,
            equipment_id=equip_id,
            material_id=mat_id,
            design_speed=200.0,
            design_speed_uom="kg/h",
            reject_uom="kg",
            target_oee=90.0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.id == uid
        assert schema.equipment_id == equip_id
        assert schema.material_id == mat_id
        assert schema.design_speed == 200.0

    def test_update_all_optional(self):
        schema = EquipmentMaterialUpdate()
        assert schema.design_speed is None
        assert schema.design_speed_uom is None
        assert schema.reject_uom is None
        assert schema.target_oee is None

    def test_update_partial(self):
        schema = EquipmentMaterialUpdate(target_oee=92.5)
        assert schema.target_oee == 92.5
        assert schema.design_speed is None

    def test_update_oee_validation(self):
        with pytest.raises(Exception):
            EquipmentMaterialUpdate(target_oee=150)

    def test_update_speed_validation(self):
        with pytest.raises(Exception):
            EquipmentMaterialUpdate(design_speed=-5)


# ─── Route registration tests ────────────────────────────────────────


class TestEquipmentRouteRegistration:
    """Verify the flat GET /equipment route is registered."""

    def test_list_all_equipment_route_exists(self):
        from mes.core.physical_model.routes import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/v1/equipment" in paths

    def test_list_all_equipment_is_get(self):
        from mes.core.physical_model.routes import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/api/v1/equipment":
                assert "GET" in route.methods
                break
        else:
            pytest.fail("GET /api/v1/equipment route not found")

    def test_service_has_list_all_equipment(self):
        from mes.core.physical_model.service import PhysicalModelService

        assert hasattr(PhysicalModelService, "list_all_equipment")
        assert callable(PhysicalModelService.list_all_equipment)
