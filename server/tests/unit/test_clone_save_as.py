"""
Unit tests for the clone / save-as feature across all DT entities.

Covers:
- Partial unique index (WHERE is_active = TRUE) present on every soft-delete
  entity so that soft-deleted codes don't block re-creation.
- Duplicate exception hierarchy: correct HTTP status, error_code, and message
  for every entity type.
- Create-schema validation: code constraints enforced before the server is
  even reached (empty code, too-long code, whitespace in code).
- Service-level duplicate guard (async, mocked session): the service raises the
  right exception when an *active* record with the same code exists, and
  proceeds normally when the only matching record is soft-deleted (filtered out
  by is_active = TRUE).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# ── Models ───────────────────────────────────────────────────────────
# Importing all models here resolves any SQLAlchemy relationship strings.
import mes.core.material.models  # noqa: F401
import mes.core.uom.models  # noqa: F401
from mes.core.data_collection.models import DataDefinition
from mes.core.inventory.models import StorageLocation
from mes.core.physical_model.models import (
    Area,
    Equipment,
    EquipmentClass,
    ProductionLine,
    Site,
    WorkCell,
)
from mes.core.product_def.models import Disposition

# ── Exceptions ───────────────────────────────────────────────────────
from mes.core.data_collection.exceptions import DuplicateDefinitionCodeException
from mes.core.inventory.exceptions import DuplicateLocationCodeException
from mes.core.physical_model.exceptions import DuplicateCodeException
from mes.core.product_def.exceptions import (
    DuplicateDispositionCodeException,
    DuplicateProductException,
)

# ── Schemas ───────────────────────────────────────────────────────────
from mes.core.data_collection.schemas import DataDefinitionCreate
from mes.core.inventory.schemas import StorageLocationCreate
from mes.core.physical_model.schemas import (
    AreaCreate,
    EquipmentCreate,
    ProductionLineCreate,
    SiteCreate,
    WorkCellCreate,
)
from mes.core.product_def.schemas import DispositionCreate, ProductCreate

# ── Services ─────────────────────────────────────────────────────────
from mes.core.data_collection.service import DataDefinitionService
from mes.core.inventory.service import StorageLocationService
from mes.core.physical_model.service import PhysicalModelService
from mes.core.product_def.service import ProductDefService


# ═══════════════════════════════════════════════════════════════════
# 1. Partial unique-index verification
#
#    Every entity that participates in soft-delete must enforce code
#    uniqueness via a partial index (WHERE is_active = TRUE) rather
#    than a plain column-level UNIQUE constraint.  This allows a code
#    that was used by a soft-deleted record to be reused by a clone.
# ═══════════════════════════════════════════════════════════════════

class TestPartialUniqueIndexes:
    """The code column on each soft-delete entity uses a partial unique index."""

    _CASES = [
        (DataDefinition,   "ix_data_definitions_code"),
        (StorageLocation,  "ix_storage_locations_code"),
        (Site,             "ix_sites_code"),
        (Area,             "ix_areas_code"),
        (ProductionLine,   "ix_production_lines_code"),
        (WorkCell,         "ix_work_cells_code"),
        (Equipment,        "ix_equipment_code"),
        (EquipmentClass,   "ix_equipment_classes_code"),
        (Disposition,      "ix_dispositions_code"),
    ]

    @pytest.mark.parametrize("model_cls,idx_name", _CASES)
    def test_partial_unique_index_exists(self, model_cls, idx_name):
        """Index must exist on __table__ and have unique=True."""
        idx = next(
            (i for i in model_cls.__table__.indexes if i.name == idx_name),
            None,
        )
        assert idx is not None, (
            f"{model_cls.__name__}: partial index '{idx_name}' not found in __table__.indexes"
        )
        assert idx.unique is True, f"{idx_name} must be a unique index"

    @pytest.mark.parametrize("model_cls,idx_name", _CASES)
    def test_code_column_has_no_column_level_unique(self, model_cls, idx_name):
        """col.unique must be None/False — uniqueness lives in __table_args__ only."""
        col = model_cls.__table__.c.code
        assert not col.unique, (
            f"{model_cls.__name__}.code should not carry col.unique=True; "
            "uniqueness is enforced by the partial index."
        )


# ═══════════════════════════════════════════════════════════════════
# 2. Duplicate exception hierarchy
# ═══════════════════════════════════════════════════════════════════

class TestDuplicateExceptions:
    """Each duplicate exception has the right HTTP status, error_code, and message."""

    def test_duplicate_definition_code_exception(self):
        exc = DuplicateDefinitionCodeException("FLOW001")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_DEFINITION_CODE"
        assert "FLOW001" in exc.message
        assert exc.details["definition_code"] == "FLOW001"

    def test_duplicate_location_code_exception(self):
        exc = DuplicateLocationCodeException("RECV-01")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_LOCATION_CODE"
        assert "RECV-01" in exc.message
        assert exc.details["location_code"] == "RECV-01"

    def test_duplicate_code_exception_site(self):
        exc = DuplicateCodeException("Site", "PLANT-01")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_CODE"
        assert "PLANT-01" in exc.message
        assert exc.details["entity"] == "Site"
        assert exc.details["code"] == "PLANT-01"

    @pytest.mark.parametrize("entity", ["Site", "Area", "ProductionLine", "WorkCell", "Equipment", "EquipmentClass"])
    def test_duplicate_code_exception_all_entities(self, entity):
        exc = DuplicateCodeException(entity, "X-99")
        assert exc.status_code == 409
        assert entity in str(exc)

    def test_duplicate_product_exception(self):
        exc = DuplicateProductException("PROD-A", "2.0")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_PRODUCT"
        assert "PROD-A" in exc.message
        assert "2.0" in exc.message
        assert exc.details["code"] == "PROD-A"
        assert exc.details["version"] == "2.0"

    def test_duplicate_disposition_code_exception(self):
        exc = DuplicateDispositionCodeException("PASS")
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE_DISPOSITION_CODE"
        assert "PASS" in exc.message
        assert exc.details["code"] == "PASS"


# ═══════════════════════════════════════════════════════════════════
# 3. Create-schema validation
#
#    The clone dialog sends a DataDefinitionCreate (or equivalent) with a
#    new code.  Pydantic must reject invalid codes before the service runs.
# ═══════════════════════════════════════════════════════════════════

class TestCloneSchemaValidation:
    """Clone uses the Create schema; invalid codes are rejected by Pydantic."""

    # ── DataDefinition ────────────────────────────────────────────

    def test_data_definition_create_valid_clone_code(self):
        s = DataDefinitionCreate(
            name="Flow rate", code="FLOW002", data_type="numeric", source="manual",
        )
        assert s.code == "FLOW002"

    def test_data_definition_create_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(name="Flow rate", code="", data_type="numeric", source="manual")

    def test_data_definition_create_code_too_long_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(
                name="Flow rate", code="X" * 51, data_type="numeric", source="manual",
            )

    def test_data_definition_create_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            DataDefinitionCreate(
                name="Flow rate", code="FLOW002", data_type="numeric", source="robot",
            )

    # ── StorageLocation ───────────────────────────────────────────

    def test_storage_location_create_valid_clone_code(self):
        s = StorageLocationCreate(name="Rack B", code="RACK-B")
        assert s.code == "RACK-B"

    def test_storage_location_code_with_spaces_rejected(self):
        with pytest.raises(ValidationError, match="spaces"):
            StorageLocationCreate(name="Rack B", code="RACK B")

    def test_storage_location_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            StorageLocationCreate(name="Rack B", code="")

    def test_storage_location_code_too_long_rejected(self):
        with pytest.raises(ValidationError):
            StorageLocationCreate(name="Rack B", code="X" * 51)

    # ── Physical model ─────────────────────────────────────────────

    def test_site_create_valid_clone_code(self):
        s = SiteCreate(name="Plant B", code="PLANT-B")
        assert s.code == "PLANT-B"

    def test_site_create_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            SiteCreate(name="Plant B", code="")

    def test_area_create_valid_clone_code(self):
        s = AreaCreate(name="Assembly 2", code="ASSY-02")
        assert s.code == "ASSY-02"

    def test_production_line_create_valid_clone_code(self):
        s = ProductionLineCreate(name="Line 2", code="LINE-02")
        assert s.code == "LINE-02"

    def test_work_cell_create_valid_clone_code(self):
        s = WorkCellCreate(name="Station B", code="WC-B")
        assert s.code == "WC-B"

    def test_equipment_create_valid_clone_code(self):
        s = EquipmentCreate(name="CNC 2", code="CNC-002")
        assert s.code == "CNC-002"

    # ── Disposition ───────────────────────────────────────────────

    def test_disposition_create_valid_clone_code(self):
        s = DispositionCreate(name="Pass 2", code="PASS2", category="route")
        assert s.code == "PASS2"

    def test_disposition_create_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            DispositionCreate(name="Pass", code="", category="route")

    def test_disposition_create_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            DispositionCreate(name="Pass", code="PASS", category="unknown")

    # ── Product ───────────────────────────────────────────────────

    def test_product_create_valid_clone_code(self):
        s = ProductCreate(name="Widget B", code="WIDGE-B", uom_id=uuid.uuid4())
        assert s.code == "WIDGE-B"
        assert s.version == "1.0"  # default

    def test_product_create_custom_version(self):
        s = ProductCreate(name="Widget B", code="WIDGE-B", version="2.0", uom_id=uuid.uuid4())
        assert s.version == "2.0"


# ═══════════════════════════════════════════════════════════════════
# 4. Service-level duplicate guard (mocked async session)
#
#    The service must raise the entity-specific duplicate exception when
#    an *active* record with the same code already exists, but must
#    proceed when the duplicate check returns None (i.e. any matching
#    record is soft-deleted and filtered out by is_active = TRUE).
# ═══════════════════════════════════════════════════════════════════

def _mock_session(scalar_result=None):
    """Build a minimal AsyncSession mock.

    scalar_result: the value returned by result.scalar_one_or_none().
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_result

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


class TestDataDefinitionServiceDuplicateGuard:
    """DataDefinitionService.create_definition raises on active duplicate, allows re-creation after soft-delete."""

    _COMMON_KWARGS = dict(
        name="Flow rate",
        code="FLOW002",
        description=None,
        data_type="numeric",
        uom_id=None,
        step_id=None,
        source="manual",
        is_required=False,
        enum_values=None,
        lower_limit=None,
        upper_limit=None,
    )

    @pytest.mark.asyncio
    async def test_raises_when_active_duplicate_exists(self):
        """Should raise DuplicateDefinitionCodeException when an active record exists."""
        existing = MagicMock(spec=DataDefinition)
        session = _mock_session(scalar_result=existing)

        with pytest.raises(DuplicateDefinitionCodeException) as exc_info:
            await DataDefinitionService.create_definition(session, **self._COMMON_KWARGS)

        assert exc_info.value.details["definition_code"] == "FLOW002"
        # session.add must NOT have been called — INSERT was aborted
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_no_active_duplicate(self):
        """Should not raise when the duplicate check returns None (soft-deleted record filtered out)."""
        session = _mock_session(scalar_result=None)  # no active match

        with patch("mes.core.data_collection.service.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            result = await DataDefinitionService.create_definition(session, **self._COMMON_KWARGS)

        session.add.assert_called_once()
        session.flush.assert_awaited()
        session.refresh.assert_awaited()
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_check_uses_is_active_filter(self):
        """The WHERE clause passed to session.execute must include is_active = TRUE."""
        session = _mock_session(scalar_result=None)

        with patch("mes.core.data_collection.service.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            await DataDefinitionService.create_definition(session, **self._COMMON_KWARGS)

        call_args = session.execute.call_args_list
        # First call is the duplicate check SELECT
        stmt = call_args[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "is_active" in compiled.lower(), (
            "Duplicate check SELECT must filter by is_active"
        )


class TestInventoryServiceDuplicateGuard:
    """InventoryService.create_location raises on active duplicate, allows re-creation after soft-delete."""

    _COMMON_KWARGS = dict(
        name="Rack B",
        code="RACK-B",
        description=None,
        location_type="storage",
        aisle=None,
        bay=None,
        tier=None,
        site_id=None,
        capacity=None,
        capacity_uom_id=None,
    )

    @pytest.mark.asyncio
    async def test_raises_when_active_duplicate_exists(self):
        existing = MagicMock(spec=StorageLocation)
        session = _mock_session(scalar_result=existing)

        with pytest.raises(DuplicateLocationCodeException) as exc_info:
            await StorageLocationService.create_location(session, **self._COMMON_KWARGS)

        assert exc_info.value.details["location_code"] == "RACK-B"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_no_active_duplicate(self):
        session = _mock_session(scalar_result=None)

        result = await StorageLocationService.create_location(session, **self._COMMON_KWARGS)

        session.add.assert_called_once()
        session.flush.assert_awaited()
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_check_uses_is_active_filter(self):
        session = _mock_session(scalar_result=None)

        await StorageLocationService.create_location(session, **self._COMMON_KWARGS)

        stmt = session.execute.call_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "is_active" in compiled.lower()


class TestPhysicalModelServiceDuplicateGuard:
    """PhysicalModelService.create_site (representative) raises on active duplicate."""

    @pytest.mark.asyncio
    async def test_site_raises_when_active_duplicate_exists(self):
        existing = MagicMock(spec=Site)
        session = _mock_session(scalar_result=existing)

        with pytest.raises(DuplicateCodeException) as exc_info:
            await PhysicalModelService.create_site(session, name="Plant B", code="PLANT-B")

        assert exc_info.value.details["code"] == "PLANT-B"
        assert exc_info.value.details["entity"] == "Site"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_site_proceeds_when_no_active_duplicate(self):
        session = _mock_session(scalar_result=None)

        with patch("mes.core.physical_model.service.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            result = await PhysicalModelService.create_site(
                session, name="Plant B", code="PLANT-B"
            )

        session.add.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_site_duplicate_check_uses_is_active_filter(self):
        session = _mock_session(scalar_result=None)

        with patch("mes.core.physical_model.service.event_bus") as mock_bus:
            mock_bus.publish = AsyncMock()
            await PhysicalModelService.create_site(session, name="Plant B", code="PLANT-B")

        stmt = session.execute.call_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "is_active" in compiled.lower()


class TestDispositionServiceDuplicateGuard:
    """ProductDefService.create_disposition raises on active duplicate."""

    _COMMON_KWARGS = dict(
        name="Pass 2",
        code="PASS2",
        description=None,
        category="route",
    )

    @pytest.mark.asyncio
    async def test_raises_when_active_duplicate_exists(self):
        existing = MagicMock(spec=Disposition)
        session = _mock_session(scalar_result=existing)

        with pytest.raises(DuplicateDispositionCodeException) as exc_info:
            await ProductDefService.create_disposition(session, **self._COMMON_KWARGS)

        assert exc_info.value.details["code"] == "PASS2"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_no_active_duplicate(self):
        session = _mock_session(scalar_result=None)

        result = await ProductDefService.create_disposition(session, **self._COMMON_KWARGS)

        session.add.assert_called_once()
        session.flush.assert_awaited()
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_check_uses_is_active_filter(self):
        session = _mock_session(scalar_result=None)

        await ProductDefService.create_disposition(session, **self._COMMON_KWARGS)

        stmt = session.execute.call_args_list[0].args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "is_active" in compiled.lower()


# ═══════════════════════════════════════════════════════════════════
# 5. Update-path duplicate guard (rename to an existing active code)
#
#    Renaming an entity to a code that an *active* sibling already uses
#    must also be blocked.  The update service checks uniqueness
#    excluding the entity's own ID.
# ═══════════════════════════════════════════════════════════════════

class TestUpdateDuplicateGuard:
    """Rename-to-existing-code is blocked; rename-to-soft-deleted-code is allowed."""

    @pytest.mark.asyncio
    async def test_data_definition_update_raises_on_active_code_conflict(self):
        """update_definition must raise when the new code belongs to another active record."""
        own_id = uuid.uuid4()
        own_defn = MagicMock(spec=DataDefinition)
        own_defn.id = own_id
        own_defn.code = "FLOW001"

        conflict = MagicMock(spec=DataDefinition)

        # First execute → get_definition (returns own record)
        # Second execute → uniqueness check (returns conflicting record)
        result_own = MagicMock(); result_own.scalar_one_or_none.return_value = own_defn
        result_conflict = MagicMock(); result_conflict.scalar_one_or_none.return_value = conflict

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[result_own, result_conflict])
        session.add = MagicMock()
        session.flush = AsyncMock()

        with pytest.raises(DuplicateDefinitionCodeException):
            await DataDefinitionService.update_definition(
                session, own_id, code="FLOW002"
            )

    @pytest.mark.asyncio
    async def test_data_definition_update_allows_soft_deleted_code(self):
        """Renaming to a code that only soft-deleted records carry must succeed."""
        own_id = uuid.uuid4()
        own_defn = MagicMock(spec=DataDefinition)
        own_defn.id = own_id
        own_defn.code = "FLOW001"
        own_defn.step_id = None

        # Uniqueness check returns None (soft-deleted record filtered out)
        result_own = MagicMock(); result_own.scalar_one_or_none.return_value = own_defn
        result_no_conflict = MagicMock(); result_no_conflict.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[result_own, result_no_conflict])
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # Should not raise
        await DataDefinitionService.update_definition(session, own_id, code="FLOW002")
        session.flush.assert_awaited()
