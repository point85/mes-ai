"""
Unit tests for the File-Drop Test Results Collector plugin.

Tests cover:
  - file parsing
  - simulated file generation
  - file movement logic
  - plugin lifecycle (initialize, start, stop)
  - REST status / results endpoints
  - simulator toggling
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ─── Import plugin code ──────────────────────────────────────────────

# We import from the plugin package directly — adjust sys.path so tests
# can locate the plugins directory.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "system" / "file_drop_test_results"))

from plugin import (  # type: ignore[import-not-found]  # noqa: E402
    FileDropTestResultsPlugin,
    generate_test_file,
    parse_test_result_file,
    router,
)
import plugin as plugin_mod  # type: ignore[import-not-found]  # noqa: E402


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a minimal test result file."""
    content = textwrap.dedent("""\
        # Sample test result
        TEST_ID=TR-UNIT001
        EQUIPMENT_ID=CMM-3000
        SERIAL=SN-12345
        LOT=LOT-A
        TIMESTAMP=2026-03-19T14:30:00Z
        RESULT=pass
        dimension_x=10.0200
        dimension_y=5.0100
        weight=100.300
    """)
    f = tmp_path / "TR-UNIT001.txt"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def malformed_file(tmp_path: Path) -> Path:
    """A file with some invalid lines."""
    content = textwrap.dedent("""\
        TEST_ID=TR-BAD
        EQUIPMENT_ID=X
        this line has no equals sign
        RESULT=fail
        not_a_number=abc
    """)
    f = tmp_path / "TR-BAD.txt"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def plugin() -> FileDropTestResultsPlugin:
    return FileDropTestResultsPlugin()


@pytest.fixture
def app() -> FastAPI:
    a = FastAPI()
    a.include_router(router)
    return a


# ─── File Parsing Tests ──────────────────────────────────────────────


class TestParseTestResultFile:
    def test_parse_valid_file(self, sample_file: Path):
        record = parse_test_result_file(sample_file)

        assert record["test_id"] == "TR-UNIT001"
        assert record["equipment_id"] == "CMM-3000"
        assert record["serial"] == "SN-12345"
        assert record["lot"] == "LOT-A"
        assert record["result"] == "pass"
        assert record["timestamp"] == "2026-03-19T14:30:00Z"
        assert record["source_file"] == "TR-UNIT001.txt"

        assert abs(record["measurements"]["dimension_x"] - 10.02) < 0.001
        assert abs(record["measurements"]["dimension_y"] - 5.01) < 0.001
        assert abs(record["measurements"]["weight"] - 100.3) < 0.01

    def test_parse_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        record = parse_test_result_file(f)

        assert record["test_id"] == ""
        assert record["measurements"] == {}

    def test_parse_comments_ignored(self, tmp_path: Path):
        f = tmp_path / "commented.txt"
        f.write_text("# This is a comment\nTEST_ID=TR-C01\n# Another\n", encoding="utf-8")
        record = parse_test_result_file(f)

        assert record["test_id"] == "TR-C01"
        assert record["measurements"] == {}

    def test_parse_malformed_file(self, malformed_file: Path):
        record = parse_test_result_file(malformed_file)

        assert record["test_id"] == "TR-BAD"
        assert record["result"] == "fail"
        # "not_a_number=abc" should be stored as string, not float
        assert record["measurements"]["not_a_number"] == "abc"

    def test_parse_result_lowercased(self, tmp_path: Path):
        f = tmp_path / "upper.txt"
        f.write_text("TEST_ID=X\nRESULT=PASS\n", encoding="utf-8")
        record = parse_test_result_file(f)

        assert record["result"] == "pass"


# ─── File Generator Tests ─────────────────────────────────────────────


class TestGenerateTestFile:
    def test_generates_file_in_directory(self, tmp_path: Path):
        filepath = generate_test_file(tmp_path)

        assert filepath.exists()
        assert filepath.suffix == ".txt"
        assert filepath.parent == tmp_path

    def test_generated_file_is_parseable(self, tmp_path: Path):
        filepath = generate_test_file(tmp_path)
        record = parse_test_result_file(filepath)

        assert record["test_id"].startswith("TR-")
        assert record["equipment_id"] in ["CMM-3000", "TENSILE-500", "HARDNESS-100", "XRAY-200"]
        assert record["result"] in ["pass", "fail", "inconclusive"]
        assert len(record["measurements"]) > 0

    def test_creates_directory_if_missing(self, tmp_path: Path):
        deep = tmp_path / "a" / "b" / "c"
        filepath = generate_test_file(deep)

        assert deep.exists()
        assert filepath.exists()


# ─── Plugin Lifecycle Tests ───────────────────────────────────────────


class TestPluginLifecycle:
    @pytest.mark.asyncio
    async def test_initialize_applies_config(self, plugin: FileDropTestResultsPlugin):
        config = {
            "watch_dir": "/tmp/custom",
            "poll_interval_seconds": 2.0,
            "file_pattern": "*.csv",
            "db_table": "my_results",
            "simulator_enabled": False,
            "simulator_interval_seconds": 15.0,
            "simulator_failure_rate": 0.1,
        }
        await plugin.initialize(config)

        assert plugin._watch_dir == Path("/tmp/custom")
        assert plugin._poll_interval == 2.0
        assert plugin._file_pattern == "*.csv"
        assert plugin._db_table == "my_results"
        assert plugin._simulator_enabled is False
        assert plugin._simulator_interval == 15.0
        assert plugin._simulator_failure_rate == 0.1

    @pytest.mark.asyncio
    async def test_initialize_applies_defaults(self, plugin: FileDropTestResultsPlugin):
        await plugin.initialize({})

        assert plugin._watch_dir == Path("./watch/test_results")
        assert plugin._poll_interval == 5.0
        assert plugin._file_pattern == "*.txt"

    @pytest.mark.asyncio
    async def test_start_creates_directories(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        await plugin.initialize({"watch_dir": str(tmp_path / "watch"), "simulator_enabled": False})

        with patch("plugin._ensure_table", new_callable=AsyncMock):
            await plugin.start()

        assert (tmp_path / "watch").exists()
        assert (tmp_path / "watch" / "successful").exists()
        assert (tmp_path / "watch" / "failed").exists()

        await plugin.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        await plugin.initialize({"watch_dir": str(tmp_path / "watch"), "simulator_enabled": True})

        with patch("plugin._ensure_table", new_callable=AsyncMock):
            await plugin.start()

        assert plugin._watcher_task is not None
        assert plugin._simulator_task is not None

        await plugin.stop()

        assert plugin._watcher_task is None
        assert plugin._simulator_task is None
        assert plugin._running is False

    @pytest.mark.asyncio
    async def test_start_without_simulator(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        await plugin.initialize({"watch_dir": str(tmp_path / "watch"), "simulator_enabled": False})

        with patch("plugin._ensure_table", new_callable=AsyncMock):
            await plugin.start()

        assert plugin._watcher_task is not None
        assert plugin._simulator_task is None

        await plugin.stop()

    def test_get_routes_returns_router(self, plugin: FileDropTestResultsPlugin):
        routes = plugin.get_routes()
        assert len(routes) == 1
        assert routes[0] is router

    def test_get_event_handlers_returns_none(self, plugin: FileDropTestResultsPlugin):
        assert plugin.get_event_handlers() is None


# ─── File Movement Tests ──────────────────────────────────────────────


class TestFileMovement:
    def test_move_to_successful(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        (tmp_path / "successful").mkdir()
        f = tmp_path / "test.txt"
        f.write_text("data")

        plugin._move_file(f, success=True)

        assert not f.exists()
        assert (tmp_path / "successful" / "test.txt").exists()

    def test_move_to_failed(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        (tmp_path / "failed").mkdir()
        f = tmp_path / "test.txt"
        f.write_text("data")

        plugin._move_file(f, success=False)

        assert not f.exists()
        assert (tmp_path / "failed" / "test.txt").exists()

    def test_move_avoids_collision(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        success_dir = tmp_path / "successful"
        success_dir.mkdir()

        # Create existing file with same name
        (success_dir / "test.txt").write_text("existing")

        f = tmp_path / "test.txt"
        f.write_text("new")

        plugin._move_file(f, success=True)

        assert not f.exists()
        assert (success_dir / "test.txt").exists()  # original
        assert (success_dir / "test_1.txt").exists()  # new one


# ─── Process File Tests ──────────────────────────────────────────────


class TestProcessFile:
    @pytest.mark.asyncio
    async def test_process_success(self, plugin: FileDropTestResultsPlugin, sample_file: Path, tmp_path: Path):
        plugin._watch_dir = tmp_path
        plugin._simulator_failure_rate = 0.0  # no simulated failures
        (tmp_path / "successful").mkdir()
        (tmp_path / "failed").mkdir()

        with patch("plugin.write_result_to_db", new_callable=AsyncMock, return_value=True):
            await plugin._process_file(sample_file)

        assert plugin._files_processed == 1
        assert plugin._files_succeeded == 1
        assert plugin._files_failed == 0
        assert len(plugin._recent_results) == 1
        assert plugin._recent_results[0]["db_success"] is True

    @pytest.mark.asyncio
    async def test_process_db_failure(self, plugin: FileDropTestResultsPlugin, sample_file: Path, tmp_path: Path):
        plugin._watch_dir = tmp_path
        plugin._simulator_failure_rate = 0.0
        (tmp_path / "successful").mkdir()
        (tmp_path / "failed").mkdir()

        with patch("plugin.write_result_to_db", new_callable=AsyncMock, return_value=False):
            await plugin._process_file(sample_file)

        assert plugin._files_processed == 1
        assert plugin._files_succeeded == 0
        assert plugin._files_failed == 1
        assert plugin._recent_results[0]["db_success"] is False

    @pytest.mark.asyncio
    async def test_process_parse_error(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        (tmp_path / "failed").mkdir()

        # Create a file that the parser can read but then we'll mock parse to raise
        f = tmp_path / "bad.txt"
        f.write_text("data")

        with patch("plugin.parse_test_result_file", side_effect=Exception("parse boom")):
            await plugin._process_file(f)

        assert plugin._files_processed == 1
        assert plugin._files_failed == 1


# ─── Stats / Properties Tests ────────────────────────────────────────


class TestStats:
    def test_stats_initial(self, plugin: FileDropTestResultsPlugin):
        stats = plugin.stats
        assert stats["files_processed"] == 0
        assert stats["files_succeeded"] == 0
        assert stats["files_failed"] == 0
        assert stats["is_running"] is False

    def test_recent_results_returns_copy(self, plugin: FileDropTestResultsPlugin):
        plugin._recent_results = [{"a": 1}]
        results = plugin.recent_results

        assert results == [{"a": 1}]
        assert results is not plugin._recent_results  # copy, not reference


# ─── REST Endpoint Tests ─────────────────────────────────────────────


class TestRestEndpoints:
    @pytest.mark.asyncio
    async def test_status_when_not_running(self, app: FastAPI):
        original = plugin_mod._plugin_instance
        plugin_mod._plugin_instance = None

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/plugins/file-drop/status")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "not running"
        finally:
            plugin_mod._plugin_instance = original

    @pytest.mark.asyncio
    async def test_status_when_running(self, app: FastAPI, plugin: FileDropTestResultsPlugin):
        plugin._running = True
        plugin._files_processed = 10
        plugin._files_succeeded = 8
        plugin._files_failed = 2
        plugin_mod._plugin_instance = plugin

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/plugins/file-drop/status")
            body = resp.json()
            assert body["status"] == "running"
            assert body["stats"]["files_processed"] == 10
            assert body["stats"]["files_succeeded"] == 8
        finally:
            plugin_mod._plugin_instance = None

    @pytest.mark.asyncio
    async def test_results_when_not_running(self, app: FastAPI):
        plugin_mod._plugin_instance = None

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/plugins/file-drop/results")
            body = resp.json()
            assert body["results"] == []
            assert body["count"] == 0
        finally:
            pass

    @pytest.mark.asyncio
    async def test_results_returns_recent(self, app: FastAPI, plugin: FileDropTestResultsPlugin):
        plugin._recent_results = [
            {"test_id": "TR-1", "db_success": True},
            {"test_id": "TR-2", "db_success": False},
        ]
        plugin_mod._plugin_instance = plugin

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/plugins/file-drop/results")
            body = resp.json()
            assert body["count"] == 2
            assert body["results"][0]["test_id"] == "TR-1"
        finally:
            plugin_mod._plugin_instance = None

    @pytest.mark.asyncio
    async def test_simulate_when_not_running(self, app: FastAPI):
        plugin_mod._plugin_instance = None

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/plugins/file-drop/simulate")
            body = resp.json()
            assert "error" in body
        finally:
            pass

    @pytest.mark.asyncio
    async def test_simulate_generates_file(self, app: FastAPI, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        plugin_mod._plugin_instance = plugin

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/plugins/file-drop/simulate")
            body = resp.json()
            assert "generated" in body
            assert (tmp_path / body["generated"]).exists()
        finally:
            plugin_mod._plugin_instance = None


# ─── Recent Results Buffer Tests ──────────────────────────────────────


class TestRecentResultsBuffer:
    @pytest.mark.asyncio
    async def test_buffer_caps_at_50(self, plugin: FileDropTestResultsPlugin, tmp_path: Path):
        plugin._watch_dir = tmp_path
        plugin._simulator_failure_rate = 0.0
        (tmp_path / "successful").mkdir()

        with patch("plugin.write_result_to_db", new_callable=AsyncMock, return_value=True):
            for i in range(55):
                f = tmp_path / f"test_{i}.txt"
                f.write_text(f"TEST_ID=TR-{i}\nEQUIPMENT_ID=X\nRESULT=pass\n")
                await plugin._process_file(f)

        assert len(plugin._recent_results) == 50
        # Should have the last 50 (indices 5-54)
        assert plugin._recent_results[0]["test_id"] == "TR-5"
        assert plugin._recent_results[-1]["test_id"] == "TR-54"
