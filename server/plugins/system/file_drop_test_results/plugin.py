"""
File-Drop Test Results Collector plugin.

Demonstrates a realistic end-user plugin that:
  1. Polls a directory for new text files written by test equipment.
  2. Parses each file for measurement data.
  3. Writes parsed results to a database table.
  4. Moves files to "successful" or "failed" subfolders.
  5. Optionally runs a simulator that generates sample files.
  6. Exposes REST endpoints for status and recent results.

This plugin is fully self-contained — it creates its own DB table on
first run, manages its own background tasks, and cleans up on stop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.file_drop_test_results")

router = APIRouter(
    prefix="/api/v1/plugins/file-drop",
    tags=["plugins"],
)

# ─── Module-level state (populated by plugin instance) ─────────────────
_plugin_instance: FileDropTestResultsPlugin | None = None


# ─── File parser ──────────────────────────────────────────────────────

def parse_test_result_file(filepath: Path) -> dict[str, Any]:
    """
    Parse a test equipment result file.

    Expected format (line-oriented key=value text):
        TEST_ID=TR-00042
        EQUIPMENT_ID=CMM-3000
        SERIAL=SN-1234
        TIMESTAMP=2026-03-19T14:30:00Z
        RESULT=pass
        dimension_x=10.02
        dimension_y=5.01
        weight=100.3
        surface_roughness=0.42

    Lines starting with # are comments. Blank lines are skipped.
    Any key not in the header set is treated as a measurement.
    """
    header_keys = {"TEST_ID", "EQUIPMENT_ID", "SERIAL", "LOT", "TIMESTAMP", "RESULT"}
    record: dict[str, Any] = {
        "test_id": "",
        "equipment_id": "",
        "serial": None,
        "lot": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": "pass",
        "measurements": {},
        "source_file": filepath.name,
    }

    text = filepath.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if key == "TEST_ID":
            record["test_id"] = value
        elif key == "EQUIPMENT_ID":
            record["equipment_id"] = value
        elif key == "SERIAL":
            record["serial"] = value
        elif key == "LOT":
            record["lot"] = value
        elif key == "TIMESTAMP":
            record["timestamp"] = value
        elif key == "RESULT":
            record["result"] = value.lower()
        else:
            # Measurement — try to parse as float
            try:
                record["measurements"][key] = float(value)
            except ValueError:
                record["measurements"][key] = value

    return record


# ─── Simulated file generator ─────────────────────────────────────────

_EQUIPMENT_IDS = ["CMM-3000", "TENSILE-500", "HARDNESS-100", "XRAY-200"]
_RESULTS = ["pass", "pass", "pass", "pass", "fail", "inconclusive"]


def generate_test_file(watch_dir: Path) -> Path:
    """Create a simulated test result file in the watch directory."""
    watch_dir.mkdir(parents=True, exist_ok=True)
    test_id = f"TR-{uuid.uuid4().hex[:8].upper()}"
    equip_id = random.choice(_EQUIPMENT_IDS)
    serial = f"SN-{random.randint(10000, 99999)}"
    result = random.choice(_RESULTS)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# Test result generated at {now}",
        f"TEST_ID={test_id}",
        f"EQUIPMENT_ID={equip_id}",
        f"SERIAL={serial}",
        f"TIMESTAMP={now}",
        f"RESULT={result}",
        f"dimension_x={10.0 + random.gauss(0, 0.05):.4f}",
        f"dimension_y={5.0 + random.gauss(0, 0.03):.4f}",
        f"weight={100.0 + random.gauss(0, 0.5):.3f}",
        f"surface_roughness={0.4 + random.gauss(0, 0.02):.4f}",
    ]

    filename = f"{test_id}_{equip_id}_{now.replace(':', '-')}.txt"
    filepath = watch_dir / filename
    filepath.write_text("\n".join(lines), encoding="utf-8")
    logger.debug("Simulator: created %s", filepath.name)
    return filepath


# ─── DB writer (uses MES server's async engine by default) ────────────

async def write_result_to_db(
    record: dict[str, Any],
    db_table: str,
    simulate_failure: bool = False,
) -> bool:
    """
    Insert a parsed test result record into the database.

    Returns True on success, False on failure.
    When simulate_failure is True, randomly fails for demo purposes.
    """
    if simulate_failure and random.random() < 0.5:
        logger.warning("Simulated DB write failure for %s", record.get("test_id"))
        return False

    try:
        from sqlalchemy import text as sa_text

        from mes.framework.db import async_session_factory

        # Build a simple INSERT using the configured table name.
        # The table is created by _ensure_table() at plugin start.
        import json

        # MES timestamp convention: paired local (TIMESTAMPTZ) + UTC-naive (TIMESTAMP).
        tested_at_raw = record.get("timestamp")
        tested_at_dt: datetime | None
        if isinstance(tested_at_raw, datetime):
            tested_at_dt = tested_at_raw
        elif isinstance(tested_at_raw, str) and tested_at_raw:
            iso = tested_at_raw.replace("Z", "+00:00")
            try:
                tested_at_dt = datetime.fromisoformat(iso)
            except ValueError:
                tested_at_dt = None
        else:
            tested_at_dt = None

        if tested_at_dt is not None and tested_at_dt.tzinfo is None:
            tested_at_dt = tested_at_dt.replace(tzinfo=timezone.utc)
        tested_at_local = tested_at_dt.astimezone() if tested_at_dt else None
        tested_at_utc = (
            tested_at_dt.astimezone(timezone.utc).replace(tzinfo=None)
            if tested_at_dt else None
        )

        now_local = datetime.now().astimezone()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        async with async_session_factory() as session:
            stmt = sa_text(
                f"INSERT INTO {db_table} "  # noqa: S608
                "(id, test_id, equipment_id, serial, lot, result, "
                "measurements, source_file, tested_at, tested_at_utc, "
                "created_at, created_at_utc) "
                "VALUES (:id, :test_id, :equipment_id, :serial, :lot, "
                ":result, :measurements, :source_file, :tested_at, :tested_at_utc, "
                ":created_at, :created_at_utc)"
            )
            await session.execute(
                stmt,
                {
                    "id": str(uuid.uuid4()),
                    "test_id": record["test_id"],
                    "equipment_id": record["equipment_id"],
                    "serial": record.get("serial"),
                    "lot": record.get("lot"),
                    "result": record["result"],
                    "measurements": json.dumps(record.get("measurements", {})),
                    "source_file": record.get("source_file", ""),
                    "tested_at": tested_at_local,
                    "tested_at_utc": tested_at_utc,
                    "created_at": now_local,
                    "created_at_utc": now_utc,
                },
            )
            await session.commit()
        logger.info("Saved result %s to DB", record["test_id"])
        return True
    except Exception as exc:
        logger.error("DB write failed for %s: %s", record.get("test_id"), exc)
        return False


async def _ensure_table(db_table: str) -> None:
    """Create the results table if it doesn't already exist."""
    try:
        from sqlalchemy import text as sa_text

        from mes.framework.db import async_session_factory

        create_ddl = sa_text(
            f"CREATE TABLE IF NOT EXISTS {db_table} ("
            "  id UUID PRIMARY KEY,"
            "  test_id VARCHAR(100) NOT NULL,"
            "  equipment_id VARCHAR(100) NOT NULL,"
            "  serial VARCHAR(100),"
            "  lot VARCHAR(100),"
            "  result VARCHAR(20) NOT NULL DEFAULT 'pass',"
            "  measurements JSONB NOT NULL DEFAULT '{}'::jsonb,"
            "  source_file VARCHAR(500) NOT NULL DEFAULT '',"
            "  tested_at TIMESTAMPTZ,"
            "  tested_at_utc TIMESTAMP,"
            "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "  created_at_utc TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')"
            ")"
        )
        async with async_session_factory() as session:
            await session.execute(create_ddl)
            await session.commit()
        logger.info("Ensured table '%s' exists", db_table)
    except Exception as exc:
        logger.error("Failed to ensure table '%s': %s", db_table, exc)


# ─── Plugin class ─────────────────────────────────────────────────────


class FileDropTestResultsPlugin(MESPlugin):
    """
    Polls a directory for test equipment result files, parses them,
    writes to a DB, and moves files to success/failure subfolders.
    """

    def __init__(self) -> None:
        self._watch_dir: Path = Path("./watch/test_results")
        self._poll_interval: float = 5.0
        self._file_pattern: str = "*.txt"
        self._db_table: str = "plugin_file_drop_results"
        self._simulator_enabled: bool = False
        self._simulator_interval: float = 8.0
        self._simulator_failure_rate: float = 0.2

        # Runtime state
        self._watcher_task: asyncio.Task | None = None
        self._simulator_task: asyncio.Task | None = None
        self._files_processed: int = 0
        self._files_succeeded: int = 0
        self._files_failed: int = 0
        self._recent_results: list[dict[str, Any]] = []
        self._running: bool = False

    # ── Lifecycle ────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        self._watch_dir = Path(config.get("watch_dir", "./watch/test_results"))
        self._poll_interval = float(config.get("poll_interval_seconds", 5.0))
        self._file_pattern = config.get("file_pattern", "*.txt")
        self._db_table = config.get("db_table", "plugin_file_drop_results")
        self._simulator_enabled = bool(config.get("simulator_enabled", False))
        self._simulator_interval = float(config.get("simulator_interval_seconds", 8.0))
        self._simulator_failure_rate = float(config.get("simulator_failure_rate", 0.2))

        logger.info(
            "FileDropTestResults initialized — watch_dir=%s  pattern=%s  table=%s  "
            "simulator=%s",
            self._watch_dir,
            self._file_pattern,
            self._db_table,
            self._simulator_enabled,
        )

    async def start(self) -> None:
        global _plugin_instance
        _plugin_instance = self
        self._running = True

        # Ensure directories exist
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        (self._watch_dir / "successful").mkdir(exist_ok=True)
        (self._watch_dir / "failed").mkdir(exist_ok=True)

        # Ensure DB table exists
        await _ensure_table(self._db_table)

        # Start background watcher
        self._watcher_task = asyncio.create_task(
            self._poll_loop(), name="file-drop-watcher"
        )

        # Start simulator if enabled
        if self._simulator_enabled:
            self._simulator_task = asyncio.create_task(
                self._simulator_loop(), name="file-drop-simulator"
            )

        logger.info("FileDropTestResults started")

    async def stop(self) -> None:
        self._running = False

        for task in (self._watcher_task, self._simulator_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._watcher_task = None
        self._simulator_task = None

        global _plugin_instance
        _plugin_instance = None

        logger.info(
            "FileDropTestResults stopped — processed=%d succeeded=%d failed=%d",
            self._files_processed,
            self._files_succeeded,
            self._files_failed,
        )

    # ── Extension points ─────────────────────────────────────

    def get_routes(self) -> list[APIRouter]:
        return [router]

    def get_event_handlers(self) -> dict[str, Any] | None:
        return None

    # ── Background loops ─────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Periodically scan the watch directory for new files."""
        while self._running:
            try:
                await self._process_pending_files()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watcher loop error: %s", exc, exc_info=True)
            await asyncio.sleep(self._poll_interval)

    async def _simulator_loop(self) -> None:
        """Periodically generate sample test result files."""
        while self._running:
            try:
                generate_test_file(self._watch_dir)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Simulator error: %s", exc, exc_info=True)
            await asyncio.sleep(self._simulator_interval)

    async def _process_pending_files(self) -> None:
        """Find and process all matching files in the watch directory."""
        if not self._watch_dir.exists():
            return

        for filepath in sorted(self._watch_dir.glob(self._file_pattern)):
            if not filepath.is_file():
                continue
            await self._process_file(filepath)

    async def _process_file(self, filepath: Path) -> None:
        """Parse a single file, write to DB, and move it."""
        logger.info("Processing file: %s", filepath.name)
        self._files_processed += 1

        try:
            record = parse_test_result_file(filepath)
        except Exception as exc:
            logger.error("Parse error for %s: %s", filepath.name, exc)
            self._move_file(filepath, success=False)
            self._files_failed += 1
            return

        # Simulate random failure using the configured failure rate
        simulate_failure = random.random() < self._simulator_failure_rate

        success = await write_result_to_db(
            record, self._db_table, simulate_failure=simulate_failure
        )

        self._move_file(filepath, success=success)

        if success:
            self._files_succeeded += 1
        else:
            self._files_failed += 1

        # Keep last 50 results for the REST status endpoint
        entry = {**record, "db_success": success, "processed_at": datetime.now(timezone.utc).isoformat()}
        self._recent_results.append(entry)
        if len(self._recent_results) > 50:
            self._recent_results = self._recent_results[-50:]

    def _move_file(self, filepath: Path, *, success: bool) -> None:
        """Move a processed file to the appropriate subfolder."""
        dest_dir = self._watch_dir / ("successful" if success else "failed")
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / filepath.name
        # Avoid collision by appending a counter
        counter = 0
        while dest.exists():
            counter += 1
            dest = dest_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
        try:
            shutil.move(str(filepath), str(dest))
            logger.debug("Moved %s → %s", filepath.name, dest.relative_to(self._watch_dir))
        except OSError as exc:
            logger.error("Failed to move %s: %s", filepath.name, exc)

    # ── Public accessors (used by REST endpoints) ────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "files_processed": self._files_processed,
            "files_succeeded": self._files_succeeded,
            "files_failed": self._files_failed,
            "watch_dir": str(self._watch_dir),
            "file_pattern": self._file_pattern,
            "db_table": self._db_table,
            "simulator_enabled": self._simulator_enabled,
            "is_running": self._running,
        }

    @property
    def recent_results(self) -> list[dict[str, Any]]:
        return list(self._recent_results)


# ─── REST endpoints ──────────────────────────────────────────────────


@router.get("/status")
async def plugin_status() -> dict[str, Any]:
    """Get current status and statistics for the file-drop plugin."""
    if _plugin_instance is None:
        return {"plugin": "file-drop-test-results", "status": "not running", "stats": {}}
    return {
        "plugin": "file-drop-test-results",
        "status": "running",
        "stats": _plugin_instance.stats,
    }


@router.get("/results")
async def recent_results() -> dict[str, Any]:
    """Get the most recent processed test results (up to 50)."""
    if _plugin_instance is None:
        return {"results": [], "count": 0}
    results = _plugin_instance.recent_results
    return {"results": results, "count": len(results)}


@router.post("/simulate")
async def trigger_simulation() -> dict[str, Any]:
    """Manually trigger generation of a single test result file."""
    if _plugin_instance is None:
        return {"error": "Plugin is not running"}
    filepath = generate_test_file(_plugin_instance._watch_dir)
    return {"generated": filepath.name, "watch_dir": str(_plugin_instance._watch_dir)}
