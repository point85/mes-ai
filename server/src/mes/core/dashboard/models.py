from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db import BaseModel


class DashboardAlertRule(BaseModel):
    """Persisted threshold rule evaluated when the dashboard requests alerts."""

    __tablename__ = "dashboard_alert_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    equipment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("equipment.id"), nullable=True, index=True,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
