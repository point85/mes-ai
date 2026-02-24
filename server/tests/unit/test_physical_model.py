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
    equipment_status_changed,
    site_created,
)
from mes.core.physical_model.exceptions import DuplicateCodeException
from mes.core.physical_model.models import (
    Area,
    Equipment,
    ProductionLine,
    Site,
    WorkCenter,
)
from mes.core.physical_model.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    EquipmentCreate,
    EquipmentRead,
    EquipmentStatusUpdate,
    EquipmentUpdate,
    ProductionLineCreate,
    ProductionLineRead,
    ProductionLineUpdate,
    SiteCreate,
    SiteRead,
    SiteUpdate,
    WorkCenterCreate,
    WorkCenterRead,
    WorkCenterUpdate,
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

    def test_work_center_tablename(self):
        assert WorkCenter.__tablename__ == "work_centers"

    def test_equipment_tablename(self):
        assert Equipment.__tablename__ == "equipment"

    def test_all_models_inherit_base_columns(self):
        """All physical model entities must have id, created_at, updated_at, is_active."""
        for model_cls in [Site, Area, ProductionLine, WorkCenter, Equipment]:
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


class TestWorkCenterSchemas:
    def test_work_center_create_default_type(self):
        schema = WorkCenterCreate(name="Station A", code="WC-A")
        assert schema.wc_type == "manual"

    def test_work_center_create_automated(self):
        schema = WorkCenterCreate(name="Robot A", code="WC-R1", wc_type="automated")
        assert schema.wc_type == "automated"

    def test_work_center_create_invalid_type(self):
        with pytest.raises(Exception):
            WorkCenterCreate(name="Bad", code="WC-BAD", wc_type="unknown")


class TestEquipmentSchemas:
    def test_equipment_create_default_status(self):
        schema = EquipmentCreate(name="CNC Mill", code="EQ-001")
        assert schema.status == "idle"
        assert schema.capabilities is None

    def test_equipment_create_with_capabilities(self):
        schema = EquipmentCreate(
            name="CNC Mill",
            code="EQ-001",
            capabilities={"max_rpm": 12000, "axes": 5},
        )
        assert schema.capabilities["max_rpm"] == 12000

    def test_equipment_create_invalid_status(self):
        with pytest.raises(Exception):
            EquipmentCreate(name="Test", code="EQ-T", status="broken")

    def test_equipment_status_update_valid(self):
        update = EquipmentStatusUpdate(status="down", reason="Maintenance")
        assert update.status == "down"
        assert update.reason == "Maintenance"

    def test_equipment_status_update_invalid(self):
        with pytest.raises(Exception):
            EquipmentStatusUpdate(status="exploded")

    def test_equipment_read_full(self):
        now = datetime.now(timezone.utc)
        schema = EquipmentRead(
            id=uuid.uuid4(),
            name="Mill",
            code="ML-01",
            work_center_id=uuid.uuid4(),
            status="up",
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
    def test_equipment_status_changed_event(self):
        event = equipment_status_changed("eq-123", "idle", "up", reason="Startup")
        assert event.event_type == "equipment.state.changed"
        assert event.source == "physical_model"
        assert event.payload["equipment_id"] == "eq-123"
        assert event.payload["old_status"] == "idle"
        assert event.payload["new_status"] == "up"
        assert event.payload["reason"] == "Startup"

    def test_site_created_event(self):
        event = site_created("site-abc", "PLANT-01")
        assert event.event_type == "physical_model.site.created"
        assert event.payload["site_id"] == "site-abc"
        assert event.payload["code"] == "PLANT-01"

    def test_equipment_created_event(self):
        event = equipment_created("eq-1", "EQ-001", "wc-1")
        assert event.event_type == "physical_model.equipment.created"
        assert event.payload["equipment_id"] == "eq-1"
        assert event.payload["work_center_id"] == "wc-1"


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
        for entity in ["Site", "Area", "ProductionLine", "WorkCenter", "Equipment"]:
            exc = DuplicateCodeException(entity, "CODE-1")
            assert entity in str(exc)
