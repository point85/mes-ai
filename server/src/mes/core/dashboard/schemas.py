from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


AlertMetric = Literal[
    "oee_below", "scrap_rate_above", "downtime_minutes_above", "current_downtime_above",
]


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    metric: AlertMetric
    threshold: float = Field(ge=0)
    window_minutes: int = Field(default=60, ge=1, le=10080)
    equipment_id: UUID | None = None

    @model_validator(mode="after")
    def validate_metric_scope(self) -> AlertRuleCreate:
        if self.metric == "oee_below" and self.equipment_id is None:
            raise ValueError("OEE alert rules require an equipment_id")
        if self.metric == "oee_below" and self.threshold > 1:
            raise ValueError("OEE threshold must be between 0 and 1")
        if self.metric == "scrap_rate_above" and self.threshold > 1:
            raise ValueError("Scrap-rate threshold must be between 0 and 1")
        return self


class AlertRuleRead(AlertRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_enabled: bool
    created_at: datetime


class AlertRead(BaseModel):
    rule_id: UUID
    rule_name: str
    metric: AlertMetric
    equipment_id: UUID | None
    observed_value: float
    threshold: float
    window_start: datetime
    window_end: datetime
    message: str


class AlertRuleUpdate(BaseModel):
    is_enabled: bool


class AlertTestRequest(BaseModel):
    """Hypothetical sample data for a dry-run of an alert rule (nothing is persisted)."""

    downtime_minutes: float | None = Field(default=None, ge=0)
    run_minutes: float | None = Field(default=None, ge=0)
    ideal_cycle_time_sec: float | None = Field(default=None, gt=0)
    good_count: int | None = Field(default=None, ge=0)
    reject_count: int | None = Field(default=None, ge=0)
    rework_count: int | None = Field(default=None, ge=0)


class AlertTestResult(BaseModel):
    would_trigger: bool
    observed_value: float
    threshold: float
    message: str
