"""
PHYS-MODEL: Business logic service for the physical asset hierarchy.

Provides CRUD operations for Site, Area, ProductionLine, WorkCell, Equipment.
All write operations emit domain events via the global event bus.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.exceptions import NotFoundException
from mes.framework.api.pagination import PaginationParams, paginate_query
from mes.framework.events import event_bus

from .events import equipment_created, site_created
from .exceptions import DuplicateCodeException
from .models import Area, Equipment, EquipmentMaterial, ProductionLine, Site, WorkCell

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

    # ─── Equipment operations ────────────────────────────────────────

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

    # ─── Equipment–Material Setup operations ─────────────────────────

    @staticmethod
    async def list_equipment_materials(
        session: AsyncSession,
        equip_id: UUID,
        params: PaginationParams,
    ) -> tuple[Sequence[EquipmentMaterial], str | None, bool]:
        """List active equipment-material setups for a given equipment."""
        await PhysicalModelService.get_equipment(session, equip_id)
        stmt = select(EquipmentMaterial).where(
            EquipmentMaterial.equipment_id == equip_id,
            EquipmentMaterial.is_active.is_(True),
        )
        return await paginate_query(session, stmt, EquipmentMaterial, params)

    @staticmethod
    async def get_equipment_material(
        session: AsyncSession, em_id: UUID,
    ) -> EquipmentMaterial:
        """Get an equipment-material setup by ID."""
        stmt = select(EquipmentMaterial).where(
            EquipmentMaterial.id == em_id, EquipmentMaterial.is_active.is_(True),
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
