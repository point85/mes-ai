"""
PHYS-MODEL: Business logic service for the physical asset hierarchy.

Provides CRUD operations for Site, Area, ProductionLine, WorkCell, Equipment.
All write operations emit domain events via the global event bus.
"""

from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import ConflictException, NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import equipment_created, site_created
from .exceptions import DuplicateCodeException
from .models import (
    Area,
    Equipment,
    EquipmentCapability,
    EquipmentCapabilityProperty,
    EquipmentClass,
    EquipmentClassProperty,
    EquipmentMaterial,
    ProductionLine,
    Site,
    WorkCell,
)

logger = logging.getLogger("mes.physical_model")


class PhysicalModelService:
    """Service class for physical model CRUD operations."""

    # ─── Site operations ─────────────────────────────────────────────

    @staticmethod
    async def list_sites(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[Site], str | None, bool]:
        """List active sites with pagination."""
        stmt = select(Site).where(Site.is_active.is_(True))
        return await paginate_query(session, stmt, Site, params)

    @staticmethod
    async def get_site(session: AsyncSession, site_id: UUID) -> Site:
        """Get a site by ID. Raises NotFoundException if not found."""
        stmt = select(Site).where(Site.id == site_id, Site.is_active.is_(True))
        result = await session.execute(stmt)
        site = result.scalar_one_or_none()
        if site is None:
            raise NotFoundException(resource="Site", resource_id=str(site_id))
        return site

    @staticmethod
    async def create_site(session: AsyncSession, **kwargs: Any) -> Site:
        """Create a new site. Raises DuplicateCodeException if code exists."""
        # Check uniqueness
        existing = await session.execute(
            select(Site).where(Site.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("Site", kwargs["code"])

        site = Site(**kwargs)
        session.add(site)
        await session.flush()

        await event_bus.publish(site_created(str(site.id), site.code))
        logger.info("Created site %s (code=%s)", site.id, site.code)
        return site

    @staticmethod
    async def update_site(
        session: AsyncSession, site_id: UUID, **kwargs: Any
    ) -> Site:
        """Update a site's fields. Only non-None values are applied."""
        site = await PhysicalModelService.get_site(session, site_id)

        # Check code uniqueness if code is being changed
        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != site.code:
            existing = await session.execute(
                select(Site).where(Site.code == kwargs["code"], Site.id != site_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateCodeException("Site", kwargs["code"])

        for key, value in kwargs.items():
            if value is not None:
                setattr(site, key, value)
        await session.flush()
        return site

    @staticmethod
    async def delete_site(session: AsyncSession, site_id: UUID) -> None:
        """Soft-delete a site by setting is_active=False."""
        site = await PhysicalModelService.get_site(session, site_id)
        site.is_active = False
        await session.flush()
        logger.info("Soft-deleted site %s", site_id)

    # ─── Area operations ─────────────────────────────────────────────

    @staticmethod
    async def list_areas_in_site(
        session: AsyncSession,
        site_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[Area], str | None, bool]:
        """List active areas belonging to a site."""
        # Validate parent exists
        await PhysicalModelService.get_site(session, site_id)
        stmt = select(Area).where(Area.site_id == site_id, Area.is_active.is_(True))
        return await paginate_query(session, stmt, Area, params)

    @staticmethod
    async def get_area(session: AsyncSession, area_id: UUID) -> Area:
        """Get an area by ID."""
        stmt = select(Area).where(Area.id == area_id, Area.is_active.is_(True))
        result = await session.execute(stmt)
        area = result.scalar_one_or_none()
        if area is None:
            raise NotFoundException(resource="Area", resource_id=str(area_id))
        return area

    @staticmethod
    async def create_area(
        session: AsyncSession, site_id: UUID, **kwargs: Any
    ) -> Area:
        """Create a new area within a site."""
        await PhysicalModelService.get_site(session, site_id)

        existing = await session.execute(
            select(Area).where(Area.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("Area", kwargs["code"])

        area = Area(site_id=site_id, **kwargs)
        session.add(area)
        await session.flush()
        logger.info("Created area %s (code=%s) in site %s", area.id, area.code, site_id)
        return area

    @staticmethod
    async def update_area(
        session: AsyncSession, area_id: UUID, **kwargs: Any
    ) -> Area:
        """Update an area's fields."""
        area = await PhysicalModelService.get_area(session, area_id)

        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != area.code:
            existing = await session.execute(
                select(Area).where(Area.code == kwargs["code"], Area.id != area_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateCodeException("Area", kwargs["code"])

        for key, value in kwargs.items():
            if value is not None:
                setattr(area, key, value)
        await session.flush()
        return area

    @staticmethod
    async def delete_area(session: AsyncSession, area_id: UUID) -> None:
        """Soft-delete an area by setting is_active=False."""
        area = await PhysicalModelService.get_area(session, area_id)
        area.is_active = False
        await session.flush()
        logger.info("Soft-deleted area %s", area_id)

    # ─── ProductionLine operations ───────────────────────────────────

    @staticmethod
    async def list_lines_in_area(
        session: AsyncSession,
        area_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[ProductionLine], str | None, bool]:
        """List active production lines belonging to an area."""
        await PhysicalModelService.get_area(session, area_id)
        stmt = select(ProductionLine).where(
            ProductionLine.area_id == area_id, ProductionLine.is_active.is_(True)
        )
        return await paginate_query(session, stmt, ProductionLine, params)

    @staticmethod
    async def get_line(session: AsyncSession, line_id: UUID) -> ProductionLine:
        """Get a production line by ID."""
        stmt = select(ProductionLine).where(
            ProductionLine.id == line_id, ProductionLine.is_active.is_(True)
        )
        result = await session.execute(stmt)
        line = result.scalar_one_or_none()
        if line is None:
            raise NotFoundException(resource="ProductionLine", resource_id=str(line_id))
        return line

    @staticmethod
    async def create_line(
        session: AsyncSession, area_id: UUID, **kwargs: Any
    ) -> ProductionLine:
        """Create a new production line within an area."""
        await PhysicalModelService.get_area(session, area_id)

        existing = await session.execute(
            select(ProductionLine).where(ProductionLine.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("ProductionLine", kwargs["code"])

        line = ProductionLine(area_id=area_id, **kwargs)
        session.add(line)
        await session.flush()
        logger.info("Created line %s (code=%s) in area %s", line.id, line.code, area_id)
        return line

    @staticmethod
    async def update_line(
        session: AsyncSession, line_id: UUID, **kwargs: Any
    ) -> ProductionLine:
        """Update a production line's fields."""
        line = await PhysicalModelService.get_line(session, line_id)

        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != line.code:
            existing = await session.execute(
                select(ProductionLine).where(ProductionLine.code == kwargs["code"], ProductionLine.id != line_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateCodeException("ProductionLine", kwargs["code"])

        for key, value in kwargs.items():
            if value is not None:
                setattr(line, key, value)
        await session.flush()
        return line

    @staticmethod
    async def delete_line(session: AsyncSession, line_id: UUID) -> None:
        """Soft-delete a production line."""
        line = await PhysicalModelService.get_line(session, line_id)
        line.is_active = False
        await session.flush()
        logger.info("Soft-deleted production line %s", line_id)

    @staticmethod
    async def get_line_with_work_cells(
        session: AsyncSession, line_id: UUID
    ) -> ProductionLine:
        """Get a production line with its work cells eagerly loaded."""
        stmt = (
            select(ProductionLine)
            .where(ProductionLine.id == line_id, ProductionLine.is_active.is_(True))
            .options(selectinload(ProductionLine.work_cells))
        )
        result = await session.execute(stmt)
        line = result.scalar_one_or_none()
        if line is None:
            raise NotFoundException(resource="ProductionLine", resource_id=str(line_id))
        return line

    # ─── WorkCell operations ───────────────────────────────────────

    @staticmethod
    async def list_work_cells_in_line(
        session: AsyncSession,
        line_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[WorkCell], str | None, bool]:
        """List active work cells belonging to a production line."""
        await PhysicalModelService.get_line(session, line_id)
        stmt = select(WorkCell).where(
            WorkCell.line_id == line_id, WorkCell.is_active.is_(True)
        )
        return await paginate_query(session, stmt, WorkCell, params)

    @staticmethod
    async def list_all_work_cells(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[WorkCell], str | None, bool]:
        """List all active work cells across all lines."""
        stmt = select(WorkCell).where(WorkCell.is_active.is_(True))
        return await paginate_query(session, stmt, WorkCell, params)

    @staticmethod
    async def list_all_lines(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[ProductionLine], str | None, bool]:
        """List all active production lines across all areas."""
        stmt = select(ProductionLine).where(ProductionLine.is_active.is_(True))
        return await paginate_query(session, stmt, ProductionLine, params)

    @staticmethod
    async def get_work_cell(session: AsyncSession, wc_id: UUID) -> WorkCell:
        """Get a work cell by ID."""
        stmt = select(WorkCell).where(
            WorkCell.id == wc_id, WorkCell.is_active.is_(True)
        )
        result = await session.execute(stmt)
        wc = result.scalar_one_or_none()
        if wc is None:
            raise NotFoundException(resource="WorkCell", resource_id=str(wc_id))
        return wc

    @staticmethod
    async def create_work_cell(
        session: AsyncSession, line_id: UUID, **kwargs: Any
    ) -> WorkCell:
        """Create a new work cell within a production line."""
        await PhysicalModelService.get_line(session, line_id)

        existing = await session.execute(
            select(WorkCell).where(WorkCell.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("WorkCell", kwargs["code"])

        wc = WorkCell(line_id=line_id, **kwargs)
        session.add(wc)
        await session.flush()
        logger.info("Created work cell %s (code=%s) in line %s", wc.id, wc.code, line_id)
        return wc

    @staticmethod
    async def update_work_cell(
        session: AsyncSession, wc_id: UUID, **kwargs: Any
    ) -> WorkCell:
        """Update a work cell's fields."""
        wc = await PhysicalModelService.get_work_cell(session, wc_id)

        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != wc.code:
            existing = await session.execute(
                select(WorkCell).where(WorkCell.code == kwargs["code"], WorkCell.id != wc_id)
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateCodeException("WorkCell", kwargs["code"])

        for key, value in kwargs.items():
            if value is not None:
                setattr(wc, key, value)
        await session.flush()
        return wc

    @staticmethod
    async def delete_work_cell(session: AsyncSession, wc_id: UUID) -> None:
        """Soft-delete a work cell."""
        wc = await PhysicalModelService.get_work_cell(session, wc_id)
        wc.is_active = False
        await session.flush()
        logger.info("Soft-deleted work cell %s", wc_id)

    # ─── Equipment operations ────────────────────────────────────────

    @staticmethod
    async def list_all_equipment(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[Equipment], str | None, bool]:
        """List all active equipment across all work cells."""
        stmt = select(Equipment).where(Equipment.is_active.is_(True))
        return await paginate_query(session, stmt, Equipment, params)

    @staticmethod
    async def list_equipment_in_work_cell(
        session: AsyncSession,
        wc_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[Equipment], str | None, bool]:
        """List active equipment belonging to a work cell."""
        await PhysicalModelService.get_work_cell(session, wc_id)
        stmt = select(Equipment).where(
            Equipment.work_cell_id == wc_id, Equipment.is_active.is_(True)
        )
        return await paginate_query(session, stmt, Equipment, params)

    @staticmethod
    async def get_equipment(session: AsyncSession, equip_id: UUID) -> Equipment:
        """Get equipment by ID."""
        stmt = select(Equipment).where(
            Equipment.id == equip_id, Equipment.is_active.is_(True)
        )
        result = await session.execute(stmt)
        equip = result.scalar_one_or_none()
        if equip is None:
            raise NotFoundException(resource="Equipment", resource_id=str(equip_id))
        return equip

    @staticmethod
    async def create_equipment(
        session: AsyncSession, wc_id: UUID, **kwargs: Any
    ) -> Equipment:
        """Create new equipment within a work cell."""
        await PhysicalModelService.get_work_cell(session, wc_id)

        existing = await session.execute(
            select(Equipment).where(Equipment.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("Equipment", kwargs["code"])

        equip = Equipment(work_cell_id=wc_id, **kwargs)
        session.add(equip)
        await session.flush()

        await event_bus.publish(
            equipment_created(str(equip.id), equip.code, str(wc_id))
        )
        logger.info("Created equipment %s (code=%s) in work cell %s", equip.id, equip.code, wc_id)
        return equip

    @staticmethod
    async def update_equipment(
        session: AsyncSession, equip_id: UUID, **kwargs: Any
    ) -> Equipment:
        """Update equipment fields (not status — use update_equipment_status)."""
        equip = await PhysicalModelService.get_equipment(session, equip_id)

        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != equip.code:
            existing = await session.execute(
                select(Equipment).where(
                    Equipment.code == kwargs["code"], Equipment.id != equip_id
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateCodeException("Equipment", kwargs["code"])

        for key, value in kwargs.items():
            if value is not None:
                setattr(equip, key, value)
        await session.flush()
        return equip

    @staticmethod
    async def delete_equipment(session: AsyncSession, equip_id: UUID) -> None:
        """Soft-delete equipment."""
        equip = await PhysicalModelService.get_equipment(session, equip_id)
        equip.is_active = False
        await session.flush()
        logger.info("Soft-deleted equipment %s", equip_id)

    # ─── Equipment–Material Setup operations ─────────────────────────

    @staticmethod
    async def list_equipment_materials(
        session: AsyncSession,
        equip_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[EquipmentMaterial], str | None, bool]:
        """List active equipment-material setups for a given equipment."""
        await PhysicalModelService.get_equipment(session, equip_id)
        stmt = (
            select(EquipmentMaterial)
            .options(selectinload(EquipmentMaterial.material))
            .where(
                EquipmentMaterial.equipment_id == equip_id,
                EquipmentMaterial.is_active.is_(True),
            )
        )
        return await paginate_query(session, stmt, EquipmentMaterial, params)

    @staticmethod
    async def get_equipment_material(
        session: AsyncSession, em_id: UUID,
    ) -> EquipmentMaterial:
        """Get an equipment-material setup by ID."""
        stmt = (
            select(EquipmentMaterial)
            .options(selectinload(EquipmentMaterial.material))
            .where(
                EquipmentMaterial.id == em_id, EquipmentMaterial.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        em = result.scalar_one_or_none()
        if em is None:
            raise NotFoundException(
                resource="EquipmentMaterial", resource_id=str(em_id),
            )
        return em

    @staticmethod
    async def create_equipment_material(
        session: AsyncSession, equip_id: UUID, **kwargs: Any,
    ) -> EquipmentMaterial:
        """Create a new equipment-material setup."""
        await PhysicalModelService.get_equipment(session, equip_id)

        # Enforce unique (equipment_id, material_id) among active records
        existing = await session.execute(
            select(EquipmentMaterial).where(
                EquipmentMaterial.equipment_id == equip_id,
                EquipmentMaterial.material_id == kwargs["material_id"],
                EquipmentMaterial.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException(
                "EquipmentMaterial",
                f"equipment={equip_id}, material={kwargs['material_id']}",
            )

        em = EquipmentMaterial(equipment_id=equip_id, **kwargs)
        session.add(em)
        await session.flush()
        logger.info(
            "Created equipment-material setup %s (equip=%s, mat=%s)",
            em.id, equip_id, kwargs["material_id"],
        )
        return em

    @staticmethod
    async def update_equipment_material(
        session: AsyncSession, em_id: UUID, **kwargs: Any,
    ) -> EquipmentMaterial:
        """Update an equipment-material setup's fields."""
        em = await PhysicalModelService.get_equipment_material(session, em_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(em, key, value)
        await session.flush()
        return em

    @staticmethod
    async def delete_equipment_material(
        session: AsyncSession, em_id: UUID,
    ) -> None:
        """Soft-delete an equipment-material setup."""
        em = await PhysicalModelService.get_equipment_material(session, em_id)
        em.is_active = False
        await session.flush()
        logger.info("Soft-deleted equipment-material setup %s", em_id)

    # ─── Material Setup (current running material) ───────────────────

    @staticmethod
    async def get_material_setup(
        session: AsyncSession, equip_id: UUID,
    ) -> Equipment:
        """Get equipment with its current material setup eagerly loaded."""
        stmt = (
            select(Equipment)
            .options(
                selectinload(Equipment.active_material_setup).selectinload(
                    EquipmentMaterial.material
                ),
            )
            .where(Equipment.id == equip_id, Equipment.is_active.is_(True))
        )
        result = await session.execute(stmt)
        equip = result.scalar_one_or_none()
        if equip is None:
            raise NotFoundException(resource="Equipment", resource_id=str(equip_id))
        return equip

    @staticmethod
    async def set_material_setup(
        session: AsyncSession,
        equip_id: UUID,
        equipment_material_id: UUID,
        job_number: str | None = None,
    ) -> tuple[Equipment, EquipmentMaterial]:
        """Switch the current material setup on equipment.

        Returns the (equipment, equipment_material) tuple so that callers
        can build the response without a lazy-load round-trip.
        """
        equip = await PhysicalModelService.get_equipment(session, equip_id)
        # Validate the equipment_material_id belongs to this equipment
        em = await PhysicalModelService.get_equipment_material(session, equipment_material_id)
        if em.equipment_id != equip_id:
            raise NotFoundException(
                resource="EquipmentMaterial",
                resource_id=f"{equipment_material_id} (not configured for equipment {equip_id})",
            )
        equip.current_material_id = equipment_material_id
        equip.current_job_number = job_number
        now = _dt.datetime.now(_dt.timezone.utc)
        equip.material_setup_at = now
        equip.material_setup_at_utc = now.replace(tzinfo=None)
        await session.flush()
        logger.info(
            "Material setup on equipment %s: material_setup=%s job=%s",
            equip_id, equipment_material_id, job_number,
        )
        return equip, em

    @staticmethod
    async def clear_material_setup(
        session: AsyncSession, equip_id: UUID,
    ) -> Equipment:
        """Clear the current material setup on equipment."""
        equip = await PhysicalModelService.get_equipment(session, equip_id)
        equip.current_material_id = None
        equip.current_job_number = None
        equip.material_setup_at = None
        equip.material_setup_at_utc = None
        await session.flush()
        logger.info("Cleared material setup on equipment %s", equip_id)
        return equip

    @staticmethod
    async def find_equipment_material_by_code(
        session: AsyncSession, equip_id: UUID, material_code: str,
    ) -> EquipmentMaterial:
        """Find an active equipment-material by material code for a given equipment."""
        from mes.core.material.models import MaterialDefinition

        stmt = (
            select(EquipmentMaterial)
            .join(MaterialDefinition, EquipmentMaterial.material_id == MaterialDefinition.id)
            .options(selectinload(EquipmentMaterial.material))
            .where(
                EquipmentMaterial.equipment_id == equip_id,
                MaterialDefinition.code == material_code,
                EquipmentMaterial.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        em = result.scalar_one_or_none()
        if em is None:
            raise NotFoundException(
                resource="EquipmentMaterial",
                resource_id=f"material_code={material_code} for equipment {equip_id}",
            )
        return em

    # ─── Equipment Class operations (ISA-95 Part 2) ──────────────────

    @staticmethod
    async def list_equipment_classes(
        session: AsyncSession,
        params: PaginationParams,
    ) -> tuple[Sequence[EquipmentClass], str | None, bool]:
        stmt = select(EquipmentClass).where(EquipmentClass.is_active.is_(True))
        return await paginate_query(session, stmt, EquipmentClass, params)

    @staticmethod
    async def get_equipment_class(
        session: AsyncSession, class_id: UUID
    ) -> EquipmentClass:
        stmt = (
            select(EquipmentClass)
            .options(
                selectinload(EquipmentClass.properties),
                selectinload(EquipmentClass.equipment_members),
            )
            .where(EquipmentClass.id == class_id, EquipmentClass.is_active.is_(True))
        )
        result = await session.execute(stmt)
        ec = result.scalar_one_or_none()
        if ec is None:
            raise NotFoundException(resource="EquipmentClass", resource_id=str(class_id))
        return ec

    @staticmethod
    async def create_equipment_class(
        session: AsyncSession, **kwargs: Any
    ) -> EquipmentClass:
        existing = await session.execute(
            select(EquipmentClass).where(EquipmentClass.code == kwargs["code"])
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateCodeException("EquipmentClass", kwargs["code"])
        ec = EquipmentClass(**kwargs)
        session.add(ec)
        await session.flush()
        logger.info("Created equipment class %s (code=%s)", ec.id, ec.code)
        return ec

    @staticmethod
    async def update_equipment_class(
        session: AsyncSession, class_id: UUID, **kwargs: Any
    ) -> EquipmentClass:
        ec = await PhysicalModelService.get_equipment_class(session, class_id)
        if "code" in kwargs and kwargs["code"] is not None and kwargs["code"] != ec.code:
            dup = await session.execute(
                select(EquipmentClass).where(EquipmentClass.code == kwargs["code"])
            )
            if dup.scalar_one_or_none() is not None:
                raise DuplicateCodeException("EquipmentClass", kwargs["code"])
        for k, v in kwargs.items():
            if v is not None:
                setattr(ec, k, v)
        await session.flush()
        return ec

    @staticmethod
    async def delete_equipment_class(
        session: AsyncSession, class_id: UUID
    ) -> None:
        ec = await PhysicalModelService.get_equipment_class(session, class_id)
        ec.is_active = False
        await session.flush()

    # ─── Equipment Class Property operations ─────────────────────────

    @staticmethod
    async def list_class_properties(
        session: AsyncSession, class_id: UUID,
    ) -> Sequence[EquipmentClassProperty]:
        stmt = (
            select(EquipmentClassProperty)
            .where(
                EquipmentClassProperty.equipment_class_id == class_id,
                EquipmentClassProperty.is_active.is_(True),
            )
            .order_by(EquipmentClassProperty.name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_class_property(
        session: AsyncSession, prop_id: UUID,
    ) -> EquipmentClassProperty:
        stmt = select(EquipmentClassProperty).where(
            EquipmentClassProperty.id == prop_id,
            EquipmentClassProperty.is_active.is_(True),
        )
        result = await session.execute(stmt)
        prop = result.scalar_one_or_none()
        if prop is None:
            raise NotFoundException(resource="EquipmentClassProperty", resource_id=str(prop_id))
        return prop

    @staticmethod
    async def create_class_property(
        session: AsyncSession, class_id: UUID, **kwargs: Any
    ) -> EquipmentClassProperty:
        # Ensure class exists
        await PhysicalModelService.get_equipment_class(session, class_id)
        prop = EquipmentClassProperty(equipment_class_id=class_id, **kwargs)
        session.add(prop)
        await session.flush()
        logger.info("Created class property %s on class %s", prop.name, class_id)
        return prop

    @staticmethod
    async def update_class_property(
        session: AsyncSession, prop_id: UUID, **kwargs: Any
    ) -> EquipmentClassProperty:
        prop = await PhysicalModelService.get_class_property(session, prop_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(prop, k, v)
        await session.flush()
        return prop

    @staticmethod
    async def delete_class_property(
        session: AsyncSession, prop_id: UUID,
    ) -> None:
        prop = await PhysicalModelService.get_class_property(session, prop_id)
        prop.is_active = False
        await session.flush()

    # ─── Equipment Capability operations ─────────────────────────────

    @staticmethod
    async def list_equipment_capabilities(
        session: AsyncSession, equip_id: UUID,
    ) -> Sequence[EquipmentCapability]:
        stmt = (
            select(EquipmentCapability)
            .options(selectinload(EquipmentCapability.properties))
            .where(
                EquipmentCapability.equipment_id == equip_id,
                EquipmentCapability.is_active.is_(True),
            )
            .order_by(EquipmentCapability.created_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_capability(
        session: AsyncSession, cap_id: UUID,
    ) -> EquipmentCapability:
        stmt = (
            select(EquipmentCapability)
            .options(selectinload(EquipmentCapability.properties))
            .where(EquipmentCapability.id == cap_id, EquipmentCapability.is_active.is_(True))
        )
        result = await session.execute(stmt)
        cap = result.scalar_one_or_none()
        if cap is None:
            raise NotFoundException(resource="EquipmentCapability", resource_id=str(cap_id))
        return cap

    @staticmethod
    async def _assert_no_capability_overlap(
        session: AsyncSession,
        *,
        equipment_id: UUID,
        equipment_class_id: UUID | None,
        capability_type: str,
        start_time: _dt.datetime | None,
        end_time: _dt.datetime | None,
        exclude_id: UUID | None = None,
    ) -> None:
        """Raise ConflictException if an active capability with the same
        (equipment, class, type) has a time window that overlaps with the
        proposed [start_time, end_time). Null start = -infinity, null end
        = +infinity. Intervals overlap iff s1 < e2 and s2 < e1.
        """
        # s1 < e2: (new.start is null) OR (existing.end is null) OR (new.start < existing.end)
        cond_start = or_(
            EquipmentCapability.end_time.is_(None),
            *([] if start_time is None else [start_time < EquipmentCapability.end_time]),
        )
        # s2 < e1: (existing.start is null) OR (new.end is null) OR (existing.start < new.end)
        cond_end = or_(
            EquipmentCapability.start_time.is_(None),
            *([] if end_time is None else [EquipmentCapability.start_time < end_time]),
        )
        stmt = (
            select(EquipmentCapability.id)
            .where(
                EquipmentCapability.equipment_id == equipment_id,
                EquipmentCapability.capability_type == capability_type,
                EquipmentCapability.is_active.is_(True),
                (
                    EquipmentCapability.equipment_class_id.is_(None)
                    if equipment_class_id is None
                    else EquipmentCapability.equipment_class_id == equipment_class_id
                ),
                and_(cond_start, cond_end),
            )
            .limit(1)
        )
        if exclude_id is not None:
            stmt = stmt.where(EquipmentCapability.id != exclude_id)
        existing_id = (await session.execute(stmt)).scalar_one_or_none()
        if existing_id is not None:
            raise ConflictException(
                message=(
                    f"An active '{capability_type}' capability already exists for this "
                    f"equipment/class with an overlapping time window (conflicts with "
                    f"capability {existing_id})."
                ),
                details={"conflicting_capability_id": str(existing_id)},
            )

    @staticmethod
    async def create_capability(
        session: AsyncSession,
        equip_id: UUID,
        *,
        equipment_class_id: UUID | None = None,
        capability_type: str = "available",
        reason: str | None = None,
        start_time: _dt.datetime | None = None,
        end_time: _dt.datetime | None = None,
        properties: list[dict[str, Any]] | None = None,
    ) -> EquipmentCapability:
        # Ensure equipment exists
        await PhysicalModelService.get_equipment(session, equip_id)
        await PhysicalModelService._assert_no_capability_overlap(
            session,
            equipment_id=equip_id,
            equipment_class_id=equipment_class_id,
            capability_type=capability_type,
            start_time=start_time,
            end_time=end_time,
        )
        cap = EquipmentCapability(
            equipment_id=equip_id,
            equipment_class_id=equipment_class_id,
            capability_type=capability_type,
            reason=reason,
            start_time=start_time,
            end_time=end_time,
        )
        session.add(cap)
        await session.flush()

        if properties:
            for p in properties:
                prop = EquipmentCapabilityProperty(
                    capability_id=cap.id,
                    class_property_id=p["class_property_id"],
                    value=p["value"],
                )
                session.add(prop)
            await session.flush()

        # Always reload so the `properties` relationship is eagerly loaded
        # (Pydantic would otherwise trigger a lazy-load on the async session).
        cap = await PhysicalModelService.get_capability(session, cap.id)

        logger.info("Created capability %s for equipment %s", cap.id, equip_id)
        return cap

    @staticmethod
    async def update_capability(
        session: AsyncSession, cap_id: UUID, **kwargs: Any
    ) -> EquipmentCapability:
        cap = await PhysicalModelService.get_capability(session, cap_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(cap, k, v)
        # Re-check overlap after applying edits (excluding self).
        await PhysicalModelService._assert_no_capability_overlap(
            session,
            equipment_id=cap.equipment_id,
            equipment_class_id=cap.equipment_class_id,
            capability_type=cap.capability_type,
            start_time=cap.start_time,
            end_time=cap.end_time,
            exclude_id=cap.id,
        )
        await session.flush()
        # Reload with properties eagerly loaded for serialization.
        return await PhysicalModelService.get_capability(session, cap.id)

    @staticmethod
    async def delete_capability(
        session: AsyncSession, cap_id: UUID,
    ) -> None:
        cap = await PhysicalModelService.get_capability(session, cap_id)
        cap.is_active = False
        await session.flush()
