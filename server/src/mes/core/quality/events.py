"""
QUAL-MGMT: Event definitions for the Quality Management domain.
"""

from mes.framework.events import MESEvent


def quality_test_passed(test_id: str, unit_id: str | None, result_id: str) -> MESEvent:
    return MESEvent(
        event_type="quality.test.passed",
        source="quality",
        payload={
            "test_id": test_id,
            "unit_id": unit_id,
            "result_id": result_id,
        },
    )


def quality_test_failed(test_id: str, unit_id: str | None, result_id: str) -> MESEvent:
    return MESEvent(
        event_type="quality.test.failed",
        source="quality",
        payload={
            "test_id": test_id,
            "unit_id": unit_id,
            "result_id": result_id,
        },
    )


def quality_nc_created(nc_id: str, unit_id: str | None, nc_type: str) -> MESEvent:
    return MESEvent(
        event_type="quality.nc.created",
        source="quality",
        payload={
            "nc_id": nc_id,
            "unit_id": unit_id,
            "nc_type": nc_type,
        },
    )


def quality_nc_resolved(nc_id: str, disposition: str) -> MESEvent:
    return MESEvent(
        event_type="quality.nc.resolved",
        source="quality",
        payload={
            "nc_id": nc_id,
            "disposition": disposition,
        },
    )
