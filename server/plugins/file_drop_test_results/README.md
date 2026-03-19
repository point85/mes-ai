# File-Drop Test Results Collector — Plugin Guide

This document walks through the steps an end user takes after writing a plugin
like `file_drop_test_results` to install, configure, and run it inside the MES
server.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| MES server installed | `pip install -e ".[dev]"` from `server/` |
| PostgreSQL running | `docker compose up -d` or native service |
| Database migrated | `alembic upgrade head` |
| Python venv active | `source .venv/bin/activate` (Linux) or `.venv\Scripts\activate` (Windows) |

---

## Step 1 — Create the Plugin Directory

Every plugin lives in its own subdirectory under `server/plugins/`.
The directory name should match the plugin id (hyphens or underscores are fine).
Two files are required:

```
server/plugins/file_drop_test_results/
├── manifest.yaml   ← plugin metadata + config schema
├── plugin.py       ← Python code (MESPlugin subclass)
└── README.md       ← optional documentation (this file)
```

> The MES server scans every subdirectory of `plugins/` for a `manifest.yaml`
> on startup. If the file is missing, the directory is silently skipped.

---

## Step 2 — Write the Manifest (`manifest.yaml`)

The manifest declares the plugin's identity, permissions, extension points,
and a JSON-Schema-based configuration:

```yaml
id: file-drop-test-results          # unique plugin identifier
name: File-Drop Test Results Collector
version: "1.0.0"
description: >
  Watches a directory for test equipment text files, parses them,
  writes results to a DB table, and moves files to success/failure folders.
author: Your Name
min_mes_version: "0.1.0"

permissions:                         # plugin-specific permissions
  - id: file_drop.config.read
    description: View file-drop collector configuration
  - id: file_drop.config.write
    description: Modify file-drop collector configuration

required_core_permissions:           # MES core permissions needed
  - data_collection.write

extension_points:                    # how the plugin integrates
  - type: data_processor
    name: file_drop_test_results
  - type: rest_endpoint
    prefix: /api/v1/plugins/file-drop

config_schema:                       # user-configurable settings
  type: object
  properties:
    watch_dir:
      type: string
      default: "./watch/test_results"
      description: Directory to poll for new test result files
    poll_interval_seconds:
      type: number
      default: 5.0
    # ... additional properties
```

### Extension point types

| Type | Purpose |
|------|---------|
| `dispatch_strategy` | Custom dispatching algorithm |
| `operation_hook` | Pre/post hooks on MES operations |
| `rest_endpoint` | Additional REST API routes |
| `event_handler` | React to event bus events |
| `data_processor` | Transform or collect data |
| `report_generator` | Custom reports |
| `equipment_driver` | Equipment communication adapter |
| `equipment_state_model` | Custom equipment state machine |

---

## Step 3 — Write the Plugin Code (`plugin.py`)

Create a class that subclasses `MESPlugin` and implements the three required
lifecycle methods:

```python
from mes.framework.plugin.base import MESPlugin

class FileDropTestResultsPlugin(MESPlugin):

    async def initialize(self, config: dict) -> None:
        """Called once at server boot with resolved config values."""
        self._watch_dir = Path(config.get("watch_dir", "./watch/test_results"))
        # ... store config, set up resources

    async def start(self) -> None:
        """Called after all plugins are initialized. Begin active work."""
        # Create background tasks, open connections, etc.

    async def stop(self) -> None:
        """Called on shutdown or when disabled via the management API."""
        # Cancel tasks, close connections, release resources
```

### Optional overrides

| Method | Return | Purpose |
|--------|--------|---------|
| `get_routes()` | `list[APIRouter]` | Mount additional REST endpoints |
| `get_event_handlers()` | `dict[str, handler]` | Subscribe to event bus events |

### Important conventions

- **One `MESPlugin` subclass per `plugin.py`** — the framework scans the
  module for the first class that inherits from `MESPlugin`.
- **Error isolation** — if your plugin raises during `initialize` or `start`,
  the server logs the error and continues; other plugins are not affected.
- **DB table naming** — prefix your tables with `plugin_` to avoid collisions
  (e.g. `plugin_file_drop_results`).
- **Async-first** — all lifecycle methods are async. Use `asyncio.create_task`
  for background loops and cancel them in `stop()`.

---

## Step 4 — Verify Discovery (CLI — No Server Required)

Before starting the server, verify the plugin is discoverable:

```powershell
# List all plugins found in the plugins/ directory
cd c:\dev\mes_ai\server
python -m mes.cli plugin list
```

Expected output:

```
Discovered plugins:
  file-drop-test-results   1.0.0   File-Drop Test Results Collector
  example-dispatch-plugin  0.1.0   Example Dispatch Plugin
```

Get full details:

```powershell
python -m mes.cli plugin info file-drop-test-results
```

This prints the manifest, extension points, permissions, and config keys —
all without starting the server.

---

## Step 5 — Start the MES Server

The server automatically discovers and loads all plugins on startup:

```powershell
cd c:\dev\mes_ai\server
$env:MES_AUTH_MODE = "none"    # or "local" for auth
uvicorn mes.main:app --reload --port 8000
```

On boot, the `PluginManager` will:

1. Scan `plugins/` for subdirectories containing `manifest.yaml`
2. Parse and validate each manifest
3. Import `plugin.py` and find the `MESPlugin` subclass
4. Call `initialize(config)` with default config values from the manifest
5. Call `start()` to begin active operation
6. Mount any REST routes returned by `get_routes()`
7. Register any event handlers returned by `get_event_handlers()`

Watch the console for:

```
INFO: FileDropTestResults initialized — watch_dir=./watch/test_results ...
INFO: Ensured table 'plugin_file_drop_results' exists
INFO: FileDropTestResults started
```

---

## Step 6 — Verify the Plugin Is Running

### Option A: REST API

```powershell
# List all plugins and their status
Invoke-RestMethod http://localhost:8000/api/v1/plugins

# Get this plugin's full detail (config, permissions, status)
Invoke-RestMethod http://localhost:8000/api/v1/plugins/file-drop-test-results

# Check the plugin's own status endpoint
Invoke-RestMethod http://localhost:8000/api/v1/plugins/file-drop/status
```

### Option B: DT-CLIENT UI

1. Start the DT-CLIENT: `cd clients/design_time && npm run dev`
2. Open http://localhost:5173/plugins
3. The plugin appears in the list with a **Running** badge
4. Click to view detail, configuration, and permissions

---

## Step 7 — Configure the Plugin

Plugin configuration can be customized at runtime without restarting the server.

### Option A: REST API

```powershell
$body = @{
    config_overrides = @{
        watch_dir = "C:/factory/test_results"
        poll_interval_seconds = 2.0
        simulator_enabled = $false
    }
} | ConvertTo-Json

Invoke-RestMethod -Method PUT `
    -Uri http://localhost:8000/api/v1/plugins/file-drop-test-results/config `
    -ContentType "application/json" `
    -Body $body
```

Config overrides are persisted in the `plugin_config` database table so they
survive server restarts. Manifest defaults are used for any key not overridden.

### Option B: DT-CLIENT UI

1. Navigate to http://localhost:5173/plugins/file-drop-test-results
2. Edit the JSON config in the configuration panel
3. Click **Save Configuration**

---

## Step 8 — Enable / Disable the Plugin

### Disable (stops the plugin immediately)

```powershell
Invoke-RestMethod -Method POST `
    http://localhost:8000/api/v1/plugins/file-drop-test-results/disable
```

This calls `stop()` on the plugin, cancels background tasks, and persists
`enabled=false` in the database. The plugin will not auto-start on next boot.

### Re-enable (starts the plugin immediately)

```powershell
Invoke-RestMethod -Method POST `
    http://localhost:8000/api/v1/plugins/file-drop-test-results/enable
```

This calls `start()` and persists `enabled=true`.

### DT-CLIENT UI

Use the **Enable** / **Disable** toggle on the plugin list or detail page.

---

## Step 9 — Monitor Results

### Plugin status endpoint

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/plugins/file-drop/status
```

Returns:

```json
{
  "plugin": "file-drop-test-results",
  "status": "running",
  "stats": {
    "files_processed": 42,
    "files_succeeded": 38,
    "files_failed": 4,
    "watch_dir": "./watch/test_results",
    "simulator_enabled": true,
    "is_running": true
  }
}
```

### Recent results

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/plugins/file-drop/results
```

Returns the last 50 processed test results with parsed data and DB write status.

### Trigger a simulated file

```powershell
Invoke-RestMethod -Method POST `
    http://localhost:8000/api/v1/plugins/file-drop/simulate
```

This creates a single test file in the watch directory — useful for testing
without waiting for the simulator interval.

---

## Step 10 — Uninstall the Plugin

To remove the plugin:

1. **Disable it first** (Step 8) so background tasks are stopped
2. **Delete the plugin directory**: `Remove-Item -Recurse server/plugins/file_drop_test_results`
3. **Restart the server** — the plugin will no longer appear in the list

The `plugin_config` row in the database is retained so that re-installing
the same plugin preserves previous configuration. To fully clean up:

```sql
-- Optional: remove the config row
DELETE FROM plugin_config WHERE plugin_id = 'file-drop-test-results';

-- Optional: drop the plugin's data table
DROP TABLE IF EXISTS plugin_file_drop_results;
```

---

## File Layout Reference

```
server/plugins/file_drop_test_results/
├── manifest.yaml    ← Plugin identity, permissions, config schema
├── plugin.py        ← FileDropTestResultsPlugin (MESPlugin subclass)
│                      ├── parse_test_result_file()  — file parser
│                      ├── generate_test_file()      — simulator
│                      ├── write_result_to_db()      — async DB writer
│                      ├── _ensure_table()           — DDL on first run
│                      ├── _poll_loop()              — background watcher
│                      ├── _simulator_loop()         — background generator
│                      └── REST: /status, /results, /simulate
└── README.md        ← This guide
```

---

## Test Equipment File Format

The plugin expects plain-text key=value files:

```
# Comment lines start with #
TEST_ID=TR-00042
EQUIPMENT_ID=CMM-3000
SERIAL=SN-1234
LOT=LOT-A
TIMESTAMP=2026-03-19T14:30:00Z
RESULT=pass
dimension_x=10.02
dimension_y=5.01
weight=100.3
surface_roughness=0.42
```

**Header keys** (mapped to DB columns): `TEST_ID`, `EQUIPMENT_ID`, `SERIAL`,
`LOT`, `TIMESTAMP`, `RESULT`.

**All other keys** are treated as measurements and stored as JSON in the
`measurements` column.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Plugin not listed | Missing `manifest.yaml` | Ensure file exists in plugin subdirectory |
| Plugin listed but not running | `enabled=false` in DB | Call the `/enable` endpoint |
| "Table does not exist" errors | DB connection issue | Check PostgreSQL is running and `db_url` config |
| Files not being processed | Wrong `watch_dir` or `file_pattern` | Update config via REST API or DT-CLIENT |
| All files going to `failed/` | `simulator_failure_rate` too high | Set to `0.0` for production use |
