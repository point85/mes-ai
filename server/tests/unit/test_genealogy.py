"""
Unit tests for GENEALOGY (Product Genealogy/Traceability) module.

Covers:
- Schema construction and validation
- Service/route import checks
- Schema field completeness
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from mes.core.genealogy.schemas import (
    GenealogyDataRecord,
    GenealogyMaterialRecord,
    GenealogyRecord,
    GenealogyStepRecord,
    GenealogyTestRecord,
)


# ═══════════════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════════════


class TestGenealogyStepRecord:
    def test_minimal(self):
        rec = GenealogyStepRecord()
        assert rec.step_id is None
        assert rec.result is None

    def test_full(self):
        sid = uuid.uuid4()
        eid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        rec = GenealogyStepRecord(
            step_id=sid, step_name="Assembly",
            entered_at=now, exited_at=now,
            result="pass", equipment_id=eid,
            data_snapshot={"temp": 25.0},
        )
        assert rec.step_name == "Assembly"
        assert rec.data_snapshot == {"temp": 25.0}


class TestGenealogyMaterialRecord:
    def test_full(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyMaterialRecord(
            material_lot_id=uuid.uuid4(),
            material_code="STL-001",
            material_name="Steel Bar",
            lot_number="LOT-001",
            quantity_consumed=5.0,
            consumed_at=now,
            step_id=uuid.uuid4(),
        )
        assert rec.material_code == "STL-001"
        assert rec.quantity_consumed == 5.0


class TestGenealogyTestRecord:
    def test_full(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyTestRecord(
            result_id=uuid.uuid4(),
            test_code="DIM-001",
            test_name="Dimension Check",
            result="pass",
            measured_values={"dim_a": 10.5},
            tested_at=now,
            equipment_id=uuid.uuid4(),
        )
        assert rec.result == "pass"
        assert rec.measured_values["dim_a"] == 10.5


class TestGenealogyDataRecord:
    def test_numeric(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyDataRecord(
            data_point_id=uuid.uuid4(),
            definition_code="TEMP-001",
            definition_name="Temperature",
            value_numeric=25.5,
            collected_at=now,
        )
        assert rec.value_numeric == 25.5
        assert rec.value_string is None

    def test_string(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyDataRecord(
            data_point_id=uuid.uuid4(),
            definition_code="COLOR-001",
            value_string="red",
            collected_at=now,
        )
        assert rec.value_string == "red"

    def test_boolean(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyDataRecord(
            data_point_id=uuid.uuid4(),
            value_boolean=True,
            collected_at=now,
        )
        assert rec.value_boolean is True


class TestGenealogyRecord:
    def test_empty_unit_record(self):
        uid = uuid.uuid4()
        rec = GenealogyRecord(
            unit_id=uid, serial_number="SN-001",
            order_id=uuid.uuid4(), status="completed",
        )
        assert rec.unit_id == uid
        assert rec.steps == []
        assert rec.materials == []
        assert rec.test_results == []
        assert rec.data_points == []
        assert rec.lot_id is None

    def test_empty_lot_record(self):
        lid = uuid.uuid4()
        rec = GenealogyRecord(
            lot_id=lid, lot_number="LOT-001",
            status="completed",
        )
        assert rec.lot_id == lid
        assert rec.unit_id is None

    def test_fully_populated_record(self):
        now = datetime.now(timezone.utc)
        rec = GenealogyRecord(
            unit_id=uuid.uuid4(),
            serial_number="SN-123",
            order_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            status="completed",
            steps=[
                GenealogyStepRecord(
                    step_id=uuid.uuid4(),
                    step_name="Step 1",
                    entered_at=now,
                    exited_at=now,
                    result="pass",
                ),
            ],
            materials=[
                GenealogyMaterialRecord(
                    material_lot_id=uuid.uuid4(),
                    material_code="MAT-001",
                    quantity_consumed=2.0,
                    consumed_at=now,
                ),
            ],
            test_results=[
                GenealogyTestRecord(
                    result_id=uuid.uuid4(),
                    test_code="TST-001",
                    result="pass",
                    tested_at=now,
                ),
            ],
            data_points=[
                GenealogyDataRecord(
                    data_point_id=uuid.uuid4(),
                    definition_code="TEMP",
                    value_numeric=25.0,
                    collected_at=now,
                ),
            ],
        )
        assert len(rec.steps) == 1
        assert len(rec.materials) == 1
        assert len(rec.test_results) == 1
        assert len(rec.data_points) == 1

    def test_model_dump(self):
        rec = GenealogyRecord(
            unit_id=uuid.uuid4(),
            serial_number="SN-001",
            status="completed",
        )
        data = rec.model_dump()
        assert "unit_id" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)


# ═══════════════════════════════════════════════════════════════════
# Service / Route Import Tests
# ═══════════════════════════════════════════════════════════════════


class TestGenealogyServiceImport:
    def test_service_methods(self):
        from mes.core.genealogy.service import GenealogyService
        assert hasattr(GenealogyService, "get_unit_genealogy")
        assert hasattr(GenealogyService, "get_lot_genealogy")

    def test_router_paths(self):
        from mes.core.genealogy.routes import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/units/{unit_id}/genealogy" in paths
        assert "/api/v1/lots/{lot_id}/genealogy" in paths
