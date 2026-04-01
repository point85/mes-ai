# MES AI — Architecture Document

> **Living document** — updated as architectural decisions are made.  
> Current status: **Phase 5 In Progress** — equipment state machine (D025), availability simulator, OPC 40083 state-change wiring, hierarchical reason codes with manual transition, production counter data collection framework with PackML OPC-UA and MQTT plugins, 1293 unit tests passing. Technology stack, data model, API, plugin framework, event bus, and integration adapter specifications fully populated.

---

## 1. Overview

An open-source Manufacturing Execution System (MES) framework with a plugin architecture, designed and maintained entirely by AI. Aligned with ISA-95/IEC 62264 and MESA International standards.

**Key constraints:**
- Optimized for AI maintainability, not human readability
- Plugin-based extensibility (end users customize via AI-driven IDE)
- Client/server with REST HTTP/HTTPS interface
- RDBMS for persistence
- All external integrations (ERP, PLC, test equipment) abstracted behind adapter interfaces with mock implementations

**Key differentiator:** The plugin framework and codebase are optimized for AI-driven customization — an end user describes what they need to an AI coding agent, and the agent implements it as a plugin.

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Clients                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Runtime GUI   │  │  Headless    │  │  Design-Time      │  │
│  │ Client (Web)  │  │  Client      │  │  Client (Web)     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │              │
│         └─────────────────┼────────────────────┘              │
│                           │ REST HTTP/HTTPS + WebSocket       │
├───────────────────────────┼──────────────────────────────────┤
│                      MES Server (Python/FastAPI)              │
│  ┌────────────────────────┼──────────────────────────────┐   │
│  │            Plugin Framework (PLUGIN-FW)                │   │
│  │  ┌───────────────┐ ┌────────────┐ ┌────────────────┐  │   │
│  │  │ Core Modules   │ │  Built-in  │ │  User/Custom   │  │   │
│  │  │ (12 modules)   │ │  Plugins   │ │   Plugins      │  │   │
│  │  └───────────────┘ └────────────┘ └────────────────┘  │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Event Bus       │  │ REST API     │  │ Auth            │   │
│  │ (EVENT-BUS)     │  │ (REST-API)   │  │ (AUTH)          │   │
│  └────────────────┘  └──────────────┘  └─────────────────┘   │
│  ┌────────────────┐  ┌──────────────────────────────────────┐   │
│  │ Data Layer      │  │ Adapters (ERP / Equipment / Test)     │   │
│  │ (Multi-RDBMS)   │  │ managed as Plugins (see §9.1)        │   │
│  └────────────────┘  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

> **Architectural Decision D037 — Unified Adapter-Plugin Architecture:**
> All integration adapters (ERP, equipment, test equipment) are managed as
> plugins through the Plugin Framework. There is no separate `AdapterFactory`
> or `BaseAdapter` class. Adapter libraries live in `adapters/` as importable
> Python code; thin plugin wrappers in `plugins/system/` handle lifecycle,
> configuration, and health checks via the `MESPlugin` ABC. The `PluginManager`
> is the single entry point for adapter discovery, configuration, and runtime
> management. See §7 and §9.1 for details.
```

## 3. Technology Stack

### 3.1 Server

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | #1 AI-friendly language; massive training corpus; predictable patterns; strong typing via type hints |
| **Web Framework** | FastAPI | Async, automatic OpenAPI/Swagger docs, Pydantic integration, excellent REST support |
| **ORM** | SQLAlchemy 2.0 (async) | Best-in-class Python ORM; declarative + core patterns; mature ecosystem |
| **Migrations** | Alembic | Standard SQLAlchemy migration tool; auto-generates diffs |
| **Validation** | Pydantic v2 | Integrated with FastAPI; performant; type-safe schemas |
| **RDBMS (default)** | PostgreSQL 16+ | Full-featured, JSON support, industrial-grade; SQLite for dev/test |
| **RDBMS (optional)** | SQL Server, Oracle | Supported via SQLAlchemy dialect swap; end user configures connection string |
| **Async Runtime** | uvicorn + asyncio | Production ASGI server; non-blocking I/O |
| **Testing** | pytest + pytest-asyncio | De facto Python testing framework; excellent async support |
| **Dependency Mgmt** | uv | Fast, modern Python package manager; lockfile support |
| **Containerization** | Docker + docker-compose | Standard deployment; reproducible environments |
| **Real-time** | WebSocket (FastAPI native) | Push events to clients in real-time |

### 3.2 Clients

| Client | Technology | Rationale |
|---|---|---|
| **Runtime GUI** | React + TypeScript | Widely known; AI-friendly; large component ecosystem |
| **Runtime Headless** | Python (httpx) | Same language as server; simplifies testing and automation |
| **Design-Time** | React + TypeScript | Shared component library with Runtime GUI |

### 3.3 Multi-Language Client Integration

The MES server exposes a **language-agnostic REST API** over HTTP/HTTPS. Any programming language with an HTTP client can integrate — C, C++, Java, C#/.NET, Go, Rust, etc. This is critical for manufacturing environments where equipment controllers, ERP bridges, and shop-floor applications are written in diverse languages.

#### 3.3.1 OpenAPI Specification & SDK Generation

FastAPI auto-generates an **OpenAPI 3.1** specification at runtime:

| Endpoint | Format | Purpose |
|---|---|---|
| `/api/v1/openapi.json` | JSON | Machine-readable spec for code generators |
| `/api/v1/docs` | Swagger UI | Interactive API explorer (browser) |
| `/api/v1/redoc` | ReDoc | Alternative API documentation |

**Client SDK generation** via [OpenAPI Generator](https://openapi-generator.tech/):

```bash
# Generate a C# client library
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g csharp -o ./clients/csharp_client

# Generate a Java client library
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g java -o ./clients/java_client

# Generate a C++ client library (using cpp-restsdk)
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g cpp-restsdk -o ./clients/cpp_client
```

Supported generators include: `csharp`, `java`, `cpp-restsdk`, `go`, `rust`, `kotlin`, `python`, `typescript-axios`, and [many more](https://openapi-generator.tech/docs/generators/).

#### 3.3.2 Authentication from Non-Browser Clients

Non-browser clients authenticate using JWT bearer tokens:

1. **Obtain token** — `POST /api/v1/auth/local/login` with `{"username": "...", "password": "..."}` (local mode) or exchange an OIDC token via the OIDC flow (production mode).
2. **Attach to requests** — Include `Authorization: Bearer <token>` header on every subsequent API call.
3. **Refresh** — Tokens expire per `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). Re-authenticate or use refresh token before expiry.

**C# example** (equipment controller posting a data collection point):
```csharp
using var client = new HttpClient { BaseAddress = new Uri("http://mes-server:8000") };

// Authenticate
var loginResponse = await client.PostAsJsonAsync("/api/v1/auth/local/login",
    new { username = "equipment_svc", password = "secret" });
var token = (await loginResponse.Content.ReadFromJsonAsync<JsonElement>())
    .GetProperty("access_token").GetString();
client.DefaultRequestHeaders.Authorization = new("Bearer", token);

// Post data collection point
await client.PostAsJsonAsync("/api/v1/data-collection/collect", new {
    definition_id = "uuid-of-temperature-def",
    unit_id = "uuid-of-current-unit",
    value_numeric = 72.5,
    source = "equipment"
});
```

**Java example** (ERP bridge creating a production order):
```java
HttpClient client = HttpClient.newHttpClient();

// Authenticate
HttpRequest loginReq = HttpRequest.newBuilder()
    .uri(URI.create("http://mes-server:8000/api/v1/auth/local/login"))
    .header("Content-Type", "application/json")
    .POST(BodyPublishers.ofString("{\"username\":\"erp_svc\",\"password\":\"secret\"}"))
    .build();
String token = JsonParser.parseString(
    client.send(loginReq, BodyHandlers.ofString()).body())
    .getAsJsonObject().get("access_token").getAsString();

// Create production order
HttpRequest orderReq = HttpRequest.newBuilder()
    .uri(URI.create("http://mes-server:8000/api/v1/production/orders"))
    .header("Authorization", "Bearer " + token)
    .header("Content-Type", "application/json")
    .POST(BodyPublishers.ofString("{\"order_number\":\"WO-2026-001\","
        + "\"product_id\":\"uuid\",\"quantity_ordered\":100}"))
    .build();
client.send(orderReq, BodyHandlers.ofString());
```

#### 3.3.3 Common Integration Patterns

| Pattern | Language | Use Case |
|---|---|---|
| **Equipment controller → MES** | C, C++, C# | PLC/microcontroller reports state changes, data collection, unit completions via REST calls to the MES server |
| **ERP bridge → MES** | Java, C# | ERP system pushes production orders, material definitions, BOM updates to MES inbound endpoints |
| **MES → ERP bridge** | Java, C# | MES posts WIP completions, material consumption, scrap reports to an ERP adapter service |
| **Test equipment → MES** | C, C++, LabVIEW | Test stations post quality test results and data collection points |
| **Custom dashboard → MES** | Any | Read-only client queries performance OEE, production status, genealogy |
| **MES → MOM/MQ** | Java, C# | Message-oriented middleware bridge subscribes to MES WebSocket events and publishes to Kafka/RabbitMQ/JMS |

#### 3.3.4 WebSocket Events for Non-Browser Clients

The MES event bus exposes a WebSocket gateway for real-time event streaming. Non-browser clients connect using any WebSocket library:

- **C#**: `System.Net.WebSockets.ClientWebSocket`
- **Java**: `jakarta.websocket` or Tyrus
- **C/C++**: libwebsockets, Boost.Beast
- **Go**: `gorilla/websocket`

Clients subscribe to dot-notation event topics (e.g., `wip.unit.completed`, `equipment.state.changed`, `dispatch.executed`) and receive JSON-encoded `MESEvent` payloads in real-time.

### 3.4 Development & CI

| Component | Technology |
|---|---|
| **Linting** | Ruff |
| **Type Checking** | Pyright |
| **Formatting** | Ruff (formatter) |
| **CI** | GitHub Actions |
| **Code Coverage** | pytest-cov |

## 4. Project Structure

```
mes_ai/
├── docs/                              # Project documentation
│   ├── MES AI.txt                     # Project requirements
│   ├── PROJECT_STATE.json             # AI session state tracking
│   ├── SESSION_LOG.md                 # Chronological session narrative
│   ├── ARCHITECTURE.md                # This document
│   └── MES_SURVEY.md                  # Phase 1 survey results
│
├── server/                            # MES Server application
│   ├── pyproject.toml                 # Project metadata & dependencies
│   ├── alembic.ini                    # Alembic configuration
│   ├── alembic/                       # Database migrations
│   │   ├── env.py
│   │   └── versions/                  # Migration scripts
│   │
│   ├── src/
│   │   └── mes/                       # Main Python package
│   │       ├── __init__.py
│   │       ├── main.py                # FastAPI app factory & startup
│   │       ├── config.py              # Pydantic Settings configuration
│   │       │
│   │       ├── core/                  # Core domain modules
│   │       │   ├── __init__.py
│   │       │   ├── physical_model/    # PHYS-MODEL
│   │       │   ├── wip/               # WIP-TRACK
│   │       │   ├── routing/           # ROUTE-DEF + ROUTE-ENGINE
│   │       │   ├── dispatch/          # DISPATCH
│   │       │   ├── production/        # PROD-ORDER
│   │       │   ├── material/          # MAT-MGMT
│   │       │   ├── data_collection/   # DATA-COLLECT
│   │       │   ├── product_def/       # PROD-DEF
│   │       │   ├── quality/           # QUAL-MGMT
│   │       │   ├── performance/       # PERF-ANALYSIS
│   │       │   └── genealogy/         # GENEALOGY
│   │       │
│   │       ├── framework/             # Framework infrastructure
│   │       │   ├── __init__.py
│   │       │   ├── plugin/            # PLUGIN-FW
│   │       │   ├── api/               # REST-API (common middleware, versioning)
│   │       │   ├── db/                # DATA-LAYER (engine, session, base model)
│   │       │   ├── events/            # EVENT-BUS
│   │       │   └── auth/              # AUTH
│   │       │
│   │       └── adapters/              # Integration adapters
│   │           ├── __init__.py
│   │           ├── erp/               # ERP-IBOUND + ERP-OBOUND
│   │           ├── equipment/         # EQUIP-INTFC
│   │           └── test_equipment/    # TEST-INTFC
│   │
│   ├── plugins/                       # Plugin directories
│   │   ├── system/                    # Plugins by project contributors
│   │   │   ├── example_plugin/        # General plugin example
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── file_drop_test_results/
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── mock_erp/             # Mock ERP adapter plugin (dev/test)
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── mock_equipment/       # Mock equipment adapter plugin (dev/test)
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── mock_test_equipment/  # Mock test equipment adapter plugin (dev/test)
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── sap_s4hana_erp/       # SAP S/4HANA ERP adapter plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── oracle_cloud_erp/     # Oracle Cloud ERP adapter plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── opcua_equipment/      # OPC-UA equipment adapter plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── mqtt_equipment/       # MQTT equipment adapter plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── packml_availability/  # PackML state model plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── semi_e10_availability/ # SEMI E10 state model plugin
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── packml_opcua_counters/ # PackML OPC-UA production counter collector (OPC 30050)
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   ├── mqtt_counters/         # MQTT production counter collector
│   │   │   │   ├── manifest.yaml
│   │   │   │   └── plugin.py
│   │   │   └── availability_simulator/ # Availability simulator companion plugin
│   │   │       ├── manifest.yaml
│   │   │       └── plugin.py
│   │   └── user/                      # End-user plugins (copied here)
│   │
│   └── tests/                         # Automated tests
│       ├── conftest.py                # Shared fixtures (test DB, client)
│       ├── unit/                      # Unit tests (per module)
│       └── integration/               # Integration tests (API-level)
│
├── clients/                           # Client implementations
│   ├── shared/                        # @mes/ui shared component library
│   ├── runtime_gui/                   # RT-GUI (React)
│   ├── runtime_headless/              # RT-HEADLESS (Python)
│   ├── design_time/                   # DT-CLIENT (React)
│   ├── erp_simulator/                 # ERP Simulator GUI (React)
│   ├── availability_simulator/        # Availability Simulator GUI (React)
│   └── test_client/                   # TEST-CLIENT (Python TUI)
│
├── docker/
│   ├── Dockerfile                     # Server container
│   └── docker-compose.yml             # Full stack (server + db + clients)
│
└── README.md
```

### 4.1 Module Internal Structure (Convention)

Every core module follows an identical internal layout for AI predictability:

```
module_name/
├── __init__.py           # Public exports (service, schemas, models)
├── models.py             # SQLAlchemy ORM models
├── schemas.py            # Pydantic request/response schemas
├── service.py            # Business logic (stateless functions)
├── routes.py             # FastAPI router (REST endpoints)
├── events.py             # Event definitions and handlers
└── exceptions.py         # Module-specific exception classes
```

**Why this matters for AI:** An AI agent navigating the codebase can predict exactly where to find any piece of logic. To add a new field, it knows: `models.py` → `schemas.py` → `service.py` → `routes.py`. No guessing, no searching.

## 5. Data Model

### 5.1 Entity Relationship Overview

The data model is organized by domain and aligned with ISA-95 object models. All entities inherit from a common `BaseModel` providing `id` (UUID), `created_at`, `updated_at`, and `is_active` fields.

```
┌─────────────────────── Physical Model ───────────────────────┐
│                                                               │
│  Site ──1:N──▶ Area ──1:N──▶ ProductionLine ──1:N──▶        │
│  WorkCell ──1:N──▶ Equipment                                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌──────────────────── Product Definition ──────────────────────┐
│                                                               │
│  ProductDefinition ──1:N──▶ BillOfMaterial ──1:N──▶ BOMItem │
│        │                                                      │
│        └──1:N──▶ ProcessRoute ──1:N──▶ RouteStep             │
│                                         │                     │
│                                         └──1:N──▶ StepParam  │
│                                         └──M:N──▶ Equipment  │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌──────────────────── Production & WIP ────────────────────────┐
│                                                               │
│  ProductionOrder ──1:N──▶ Unit  (serialized)                 │
│        │                   │                                  │
│        │                   └──1:N──▶ UnitHistory              │
│        │                                                      │
│        └──1:N──▶ Lot (batch)                                 │
│                   │                                           │
│                   └──1:N──▶ LotHistory                       │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌──────────────────── Quality & Data ──────────────────────────┐
│                                                               │
│  DataDefinition ──1:N──▶ DataPoint                           │
│  QualityTest ──1:N──▶ TestResult                             │
│  NonConformance ──▶ Unit/Lot                                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌──────────────────── Material ────────────────────────────────┐
│                                                               │
│  MaterialDefinition ──1:N──▶ MaterialLot                     │
│  MaterialConsumption ──▶ Unit/Lot + MaterialLot              │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌──────────────────── Performance ─────────────────────────────┐
│                                                               │
│  EquipmentStateLog ──▶ Equipment (state machine state)      │
│  ProductionCounter ──▶ Equipment + ProductionOrder           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 Core Entities

#### Physical Model (PHYS-MODEL)

| Entity | Fields | Relations |
|---|---|---|
| **Site** | `id`, `name`, `code`, `description`, `timezone`, `address` | → Areas |
| **Area** | `id`, `name`, `code`, `description`, `site_id` | → Site, → ProductionLines |
| **ProductionLine** | `id`, `name`, `code`, `description`, `area_id` | → Area, → WorkCells |
| **WorkCell** | `id`, `name`, `code`, `description`, `line_id`, `wc_type` (manual/automated) | → ProductionLine, → Equipment |
| **Equipment** | `id`, `name`, `code`, `description`, `work_cell_id`, `equipment_type`, `capabilities` (JSON), `state_model_id` (nullable, refs EquipmentStateModel.model_id — null = 100% available) | → WorkCell, → RouteSteps (M:N), → EquipmentMaterials |
| **EquipmentMaterial** | `id`, `equipment_id`, `material_id`, `design_speed`, `design_speed_uom` (FK → UoM rate symbol), `reject_uom` (FK → UoM symbol), `target_oee` (0–100%) | → Equipment, → MaterialDefinition, → UnitOfMeasure (×2) |

#### Product Definition (PROD-DEF)

| Entity | Fields | Relations |
|---|---|---|
| **ProductDefinition** | `id`, `name`, `code`, `version`, `description`, `uom`, `product_type` (discrete/process) | → BillOfMaterials, → ProcessRoutes |
| **BillOfMaterial** | `id`, `product_id`, `version`, `effective_date`, `expiry_date` | → ProductDefinition, → BOMItems |
| **BOMItem** | `id`, `bom_id`, `material_id`, `quantity`, `uom`, `position` | → BillOfMaterial, → MaterialDefinition |
| **ProcessRoute** | `id`, `product_id`, `version`, `name`, `description`, `is_default` | → ProductDefinition, → RouteSteps |
| **RouteStep** | `id`, `route_id`, `sequence`, `name`, `step_type` (production/inspection/rework), `work_cell_id`, `expected_cycle_time_sec` | → ProcessRoute, → WorkCell, → StepParameters |
| **StepParameter** | `id`, `step_id`, `name`, `data_type`, `uom`, `target_value`, `lower_limit`, `upper_limit`, `is_required` | → RouteStep |

> **ISA-95 Route Ownership Boundary**
>
> Routes and operations are **ERP master data** (Level 4). The ERP owns route creation,
> versioning, and cost-rate assignments. The MES **does not** perform cost rollups, capacity
> planning, or standard cost maintenance.
>
> However, the MES must hold a **local execution copy** of routes for four reasons:
>
> 1. **Execution sequencing** — When a unit completes step 20 the MES must know step 30 is next
>    and which work cells can run it. Calling the ERP on every unit move would introduce
>    unacceptable latency, tight coupling, and loss of offline resilience.
> 2. **Data collection anchoring** — Every quality test, data point, material consumption,
>    non-conformance, and history record is captured per `RouteStep`. The step is the foreign-key
>    anchor for `QualityTest`, `DataPoint`, `MaterialConsumption`, `NonConformance`,
>    `UnitHistory`, and `LotHistory`.
> 3. **Outbound reporting** — `ERPOutboundAdapter.report_completion()` reports per-operation
>    actuals (labor, material, yield). The MES must know which operation just finished to map it
>    back to the ERP's cost-posting structure.
> 4. **Shop floor deviation** — The MES may need to deviate from the ERP route at execution time
>    (rework loops, skip steps, alternate routes based on equipment availability). The ERP route
>    is the *plan*; the MES route is the *execution reality*.
>
> Routes are synced via `ERPInboundAdapter.sync_routings()` (§9.2.4). The `ROUTE-DEF` module
> stores them; the `ROUTE-ENGINE` module interprets them at execution time.

#### Production Order (PROD-ORDER)

| Entity | Fields | Relations |
|---|---|---|
| **ProductionOrder** | `id`, `order_number`, `product_id`, `quantity_ordered`, `quantity_completed`, `quantity_scrapped`, `status` (created/released/in_progress/completed/closed), `priority`, `planned_start`, `planned_end`, `actual_start`, `actual_end`, `erp_reference` | → ProductDefinition, → Units, → Lots |

#### WIP Tracking (WIP-TRACK)

| Entity | Fields | Relations |
|---|---|---|
| **Unit** | `id`, `serial_number`, `order_id`, `product_id`, `current_step_id`, `current_equipment_id`, `status` (queued/in_process/completed/scrapped/on_hold), `created_at` | → ProductionOrder, → RouteStep, → Equipment |
| **Lot** | `id`, `lot_number`, `order_id`, `product_id`, `quantity`, `current_step_id`, `current_equipment_id`, `status` | → ProductionOrder, → RouteStep, → Equipment |
| **UnitHistory** | `id`, `unit_id`, `step_id`, `equipment_id`, `entered_at`, `exited_at`, `result` (pass/fail/rework), `operator_id`, `data_snapshot` (JSON) | → Unit, → RouteStep, → Equipment |
| **LotHistory** | `id`, `lot_id`, `step_id`, `equipment_id`, `entered_at`, `exited_at`, `quantity_in`, `quantity_out`, `quantity_scrapped`, `operator_id` | → Lot, → RouteStep, → Equipment |

#### Material Management (MAT-MGMT)

| Entity | Fields | Relations |
|---|---|---|
| **MaterialDefinition** | `id`, `name`, `code`, `description`, `material_type` (raw/intermediate/finished), `uom`, `shelf_life_days` | → MaterialLots |
| **MaterialLot** | `id`, `material_id`, `lot_number`, `quantity_on_hand`, `quantity_reserved`, `status` (available/reserved/consumed/expired), `received_date`, `expiry_date`, `supplier` | → MaterialDefinition |
| **MaterialConsumption** | `id`, `unit_id`/`lot_id`, `material_lot_id`, `quantity_consumed`, `consumed_at`, `step_id` | → Unit/Lot, → MaterialLot, → RouteStep |

#### Quality Management (QUAL-MGMT)

| Entity | Fields | Relations |
|---|---|---|
| **QualityTest** | `id`, `name`, `code`, `description`, `test_type` (inline/offline/destructive), `step_id`, `parameters` (JSON) | → RouteStep |
| **TestResult** | `id`, `test_id`, `unit_id`/`lot_id`, `result` (pass/fail), `measured_values` (JSON), `operator_id`, `equipment_id`, `tested_at` | → QualityTest, → Unit/Lot |
| **NonConformance** | `id`, `unit_id`/`lot_id`, `step_id`, `nc_type` (defect/out_of_spec/other), `description`, `disposition` (rework/scrap/use_as_is/return), `status` (open/investigating/resolved/closed), `created_at`, `resolved_at` | → Unit/Lot, → RouteStep |

#### Data Collection (DATA-COLLECT)

| Entity | Fields | Relations |
|---|---|---|
| **DataDefinition** | `id`, `name`, `code`, `data_type` (numeric/string/boolean/enum), `uom`, `step_id`, `source` (manual/equipment/sensor), `is_required` | → RouteStep |
| **DataPoint** | `id`, `definition_id`, `unit_id`/`lot_id`, `value_numeric`, `value_string`, `value_boolean`, `collected_at`, `source_equipment_id`, `operator_id` | → DataDefinition, → Unit/Lot |

#### Performance Analysis (PERF-ANALYSIS)

| Entity | Fields | Relations |
|---|---|---|
| **EquipmentStateModel** | `id`, `model_id` (unique, e.g. "packml"), `name`, `description`, `initial_state`, `states` (JSON — canonical dispatch + OEE mappings), `transitions` (JSON — valid from→to pairs) | Registered by availability plugins |
| **EquipmentStateLog** | `id`, `equipment_id`, `state_model`, `state`, `sub_state` (nullable), `dispatch_category` (available/busy/unavailable_planned/unavailable_unplanned), `oee_bucket`, `started_at`, `ended_at`, `reason_code`, `notes` | → Equipment |
| **ProductionCounter** | `id`, `equipment_id`, `order_id`, `shift_date`, `good_count`, `reject_count`, `rework_count`, `ideal_cycle_time_sec`, `actual_run_time_sec` | → Equipment, → ProductionOrder. Incremented atomically via `ProductionCounterService.increment_counter()` by counter-collection plugins (PackML OPC-UA, MQTT) or the REST `POST /counters/increment` endpoint. |
| **Reason** | `id`, `code` (4-char, unique), `name`, `description`, `oee_bucket`, `parent_id` (self FK, nullable) | Self-referential hierarchy; used by manual-transition endpoint |

#### Genealogy (GENEALOGY)

Genealogy is built from the relationships between `Unit/Lot`, `UnitHistory/LotHistory`, `MaterialConsumption`, `TestResult`, and `DataPoint`. No separate genealogy table is needed — it is a query that traverses existing records to build the full as-built record for a unit or lot.

#### Auth (AUTH)

| Entity | Fields | Relations |
|---|---|---|
| **User** | `id`, `username`, `email`, `full_name`, `idp_subject` (IdP unique ID), `idp_issuer`, `is_active`, `is_superuser`, `last_login` | → UserRoles |
| **Role** | `id`, `name`, `description`, `permissions` (JSON array of permission strings) | → UserRoles |
| **UserRole** | `id`, `user_id`, `role_id`, `assigned_at`, `assigned_by` (auto/manual) | → User, → Role |
| **IdPGroupMapping** | `id`, `idp_group_name`, `role_id`, `is_active` | → Role |

> **Note**: The `User` table has no `hashed_password` field. Credentials are managed by the external Identity Provider. The `idp_subject` + `idp_issuer` pair uniquely identifies a user across providers. Users are auto-provisioned (JIT) on first OIDC login.

### 5.3 Database Conventions

- **Primary keys**: UUIDs (uuid4), using SQLAlchemy's `Uuid` type (maps to `UUID` on PostgreSQL, `UNIQUEIDENTIFIER` on SQL Server, `RAW(16)` on Oracle)
- **Timestamps**: All `created_at`/`updated_at` use SQLAlchemy's `DateTime(timezone=True)`, defaults to UTC
- **Soft deletes**: `is_active` boolean flag (no physical deletes)
- **Naming**: `snake_case` for all table and column names
- **Indexes**: On all foreign keys, `code` fields, `status` fields, and `created_at`
- **Constraints**: Foreign keys with `ON DELETE RESTRICT`, unique constraints on `code` within parent scope
- **JSON columns**: Use SQLAlchemy's generic `JSON` type (maps to `JSONB` on PostgreSQL, `NVARCHAR(MAX)` on SQL Server, `JSON`/`CLOB` on Oracle)
- **No database-specific SQL**: All queries use SQLAlchemy ORM/Core API exclusively — no raw SQL or dialect-specific operators in core modules

### 5.4 Multi-RDBMS Support

The data layer supports multiple RDBMS backends via SQLAlchemy's dialect system. The end user selects their RDBMS by setting the connection string in configuration.

**Supported Databases:**

| RDBMS | Async Driver | Connection String | Install Extra |
|---|---|---|---|
| **PostgreSQL 16+** (default) | `asyncpg` | `postgresql+asyncpg://user:pass@host:5432/mes_db` | *(included by default)* |
| **SQL Server 2019+** | `aioodbc` | `mssql+aioodbc://user:pass@host:1433/mes_db?driver=ODBC+Driver+18` | `pip install mes-ai[sqlserver]` |
| **Oracle 21c+** | `oracledb` | `oracle+oracledb://user:pass@host:1521/mes_db` | `pip install mes-ai[oracle]` |
| **SQLite** (dev/test) | `aiosqlite` | `sqlite+aiosqlite:///./mes_test.db` | *(included by default)* |

**Portability Rules** (enforced in code review and CI):

1. **ORM-only queries**: All data access uses SQLAlchemy ORM `select()`, `insert()`, `update()`, `delete()` — never `text()` with raw SQL
2. **Generic column types**: Use `Uuid`, `JSON`, `DateTime(timezone=True)`, `Boolean`, `String`, `Integer`, `Numeric` — never PostgreSQL-specific types like `JSONB`, `ARRAY`, `INET`
3. **Alembic dialect awareness**: Alembic auto-generates correct DDL per target database; migrations tested against all supported RDBMS in CI
4. **Database-specific features via plugins**: If an end user needs PostgreSQL full-text search or Oracle partitioning, they implement it as a plugin — not in core
5. **CI matrix testing**: The test suite runs against PostgreSQL (primary), SQLite (fast/local), and optionally SQL Server and Oracle in the CI pipeline

### 5.5 ORM Relationship Cardinality

SQLAlchemy supports all standard relationship types. The patterns used throughout the data model:

#### One-to-Many / Many-to-One

Two sides of the same relationship using `relationship()` + `ForeignKey`:

```python
class WorkCell(Base):
    __tablename__ = "work_cell"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_line.id"))

    # Many-to-One: each work cell belongs to one production line
    production_line: Mapped["ProductionLine"] = relationship(back_populates="work_cells")

    # One-to-Many: each work cell has many equipment
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="work_cell")
```

**Used for:** Site→Areas, Area→Lines, Line→WorkCells, WorkCell→Equipment, ProductionOrder→Units, ProductionOrder→Lots, Route→Steps, Step→Parameters, and all other parent-child hierarchies.

#### Many-to-Many

Uses an association table with `relationship(secondary=...)`:

```python
# Association table
step_equipment = Table(
    "step_equipment",
    Base.metadata,
    Column("step_id", ForeignKey("route_step.id"), primary_key=True),
    Column("equipment_id", ForeignKey("equipment.id"), primary_key=True),
)

class RouteStep(Base):
    __tablename__ = "route_step"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    # Many-to-Many: steps can run on multiple equipment
    eligible_equipment: Mapped[list["Equipment"]] = relationship(
        secondary=step_equipment, back_populates="eligible_steps"
    )

class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    # Many-to-Many: equipment can serve multiple steps
    eligible_steps: Mapped[list["RouteStep"]] = relationship(
        secondary=step_equipment, back_populates="eligible_equipment"
    )
```

**Used for:** RouteStep↔Equipment (a step can run on multiple equipment, equipment can serve multiple steps).

#### Many-to-Many with Extra Data (Association Object)

When the join table needs additional columns, an explicit ORM class is used:

```python
class UserRole(Base):
    __tablename__ = "user_role"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"))
    assigned_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)  # Extra data

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")
```

**Used for:** User↔Role (with assignment metadata).

#### Summary

| Relationship | SQLAlchemy Pattern | Used In |
|---|---|---|
| One-to-Many | `relationship()` + `ForeignKey` | Site→Areas, Line→WorkCells, Order→Units, Route→Steps, etc. |
| Many-to-One | Same (reverse side) | Equipment→WorkCell, Unit→RouteStep, Unit→Equipment |
| Many-to-Many | `relationship(secondary=...)` | RouteStep↔Equipment |
| Many-to-Many + data | Association object class | User↔Role (via UserRole) |

All relationship types are fully portable across PostgreSQL, SQL Server, Oracle, and SQLite.

### 5.6 Database Migration Strategy

Schema evolution is inevitable — new modules, changed requirements, and plugin additions all drive schema changes on databases that already contain production data. Alembic (SQLAlchemy's migration framework) is the sole migration mechanism. This section defines the strategy, conventions, and safety patterns.

#### 5.6.1 Alembic Configuration

```
server/
├── alembic.ini                        # Points to alembic/ dir and DB URL (from env)
├── alembic/
│   ├── env.py                         # Loads all ORM models, configures async engine
│   ├── script.py.mako                 # Template for generated migration files
│   └── versions/                      # Core migration scripts (chronological)
│       ├── 0001_initial_schema.py
│       ├── 0002_add_equipment_capabilities.py
│       └── ...
```

**Key `env.py` requirements:**
- Imports **all** ORM models from `mes.core.*` and `mes.framework.*` so Alembic can detect model changes
- Uses the async engine from `mes.framework.db`
- Reads `MES_DB_URL` from environment (same as the application)
- Supports `--sql` mode for generating SQL scripts without a live database (for DBA review)

**`script.py.mako` template** (enforces structure on every generated migration):

```mako
"""${message}

Module: <MODULE_ID>
Date: ${create_date}
Revision: ${up_revision}
Down-revision: ${down_revision | comma,n}

## What this migration does:
<DESCRIBE THE CHANGE>

## Data impact:
<NONE | DESCRIBE DATA TRANSFORMATION | WARNING: Drops column X — data not recoverable>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "raise NotImplementedError('Implement upgrade')"}


def downgrade() -> None:
    ${downgrades if downgrades else "raise NotImplementedError('Implement downgrade — never leave as pass')"}
```

**What the template enforces:**
- Mandatory docstring with module ID, change description, and data impact statement
- `downgrade()` defaults to `raise NotImplementedError` instead of `pass` — forces explicit implementation
- Consistent import structure across all migrations

#### 5.6.2 Migration Naming Convention

Every migration file follows a strict naming pattern for AI predictability:

```
{sequence}_{module_id}_{description}.py
```

| Component | Rule | Example |
|---|---|---|
| `sequence` | 4-digit zero-padded, globally sequential | `0001`, `0042` |
| `module_id` | Lowercase module ID from §4 (or `multi` for cross-module) | `phys_model`, `wip_track`, `multi` |
| `description` | Snake_case imperative verb phrase | `add_equipment_capabilities`, `rename_lot_status_column` |

**Examples:**
```
0001_multi_initial_schema.py
0012_phys_model_add_equipment_capabilities_json.py
0013_wip_track_add_unit_hold_reason.py
0014_qual_mgmt_rename_nc_type_to_nc_category.py
0025_multi_add_audit_columns_to_all_entities.py
0026_perf_analysis_add_reasons_table.py
```

**Revision chain:** Each migration's `revision` ID is a short hash (Alembic default). The `down_revision` links to the previous migration, forming a linear chain. When branches occur (concurrent agent work), they are resolved with `alembic merge` before merging to `main`.

#### 5.6.3 Migration Generation Workflow

AI agents (and human developers) follow this workflow:

```
1. Modify models.py in the relevant module
2. Run: alembic revision --autogenerate -m "{sequence}_{module_id}_{description}"
3. Review the generated migration — verify up/down operations
4. Add data migration logic if needed (see §5.6.5)
5. Run: alembic upgrade head (apply to dev database)
6. Run: pytest (verify all tests pass with new schema)
7. Commit migration file alongside the model changes
```

**Autogenerate detects:**
- New tables, dropped tables
- Added/removed columns
- Changed column types, nullable, defaults
- Added/removed indexes and constraints
- Added/removed foreign keys

**Autogenerate does NOT detect (must be added manually):**
- Table or column renames (detected as drop + add — must fix to use `op.rename_table()` / `op.alter_column()`)
- Data migrations (backfilling values)
- Changes to check constraints or triggers
- Custom index types (partial indexes, expression indexes)

#### 5.6.4 Data-Safe Migration Patterns

All migrations on production databases must be **data-safe** — they must not lose data, corrupt references, or cause extended downtime. The following patterns are mandatory:

##### Adding a Column

```python
# SAFE: Add nullable column first, backfill, then optionally add NOT NULL
def upgrade():
    op.add_column("unit", sa.Column("hold_reason", sa.String(500), nullable=True))

# If NOT NULL is required, use a two-step migration:
# Migration A: Add column as nullable + backfill default
# Migration B: ALTER to NOT NULL after backfill is confirmed
```

**Rule:** Never add a `NOT NULL` column without a `server_default` in a single migration. Either:
- Add with `server_default=` so existing rows get the value automatically, or
- Add as nullable → backfill → alter to NOT NULL in a subsequent migration

##### Renaming a Column (Expand-Contract)

Renaming is risky because running application code may reference the old name during deployment. Use the **expand-then-contract** pattern:

```python
# Migration A (expand): Add new column, copy data, add trigger/default
def upgrade():
    op.add_column("equipment", sa.Column("equipment_category", sa.String(100), nullable=True))
    op.execute("UPDATE equipment SET equipment_category = equipment_type")
    # Old column remains — running application still works

# Migration B (contract): Drop old column after all code references are updated
def upgrade():
    op.drop_column("equipment", "equipment_type")
```

**Deploy sequence:** Deploy Migration A → deploy new application code → verify → deploy Migration B.

##### Changing a Column Type

```python
# SAFE: Use ALTER COLUMN with USING clause (PostgreSQL) or equivalent
def upgrade():
    # String → Integer example
    op.alter_column(
        "step_parameter", "target_value",
        type_=sa.Numeric(10, 4),
        postgresql_using="target_value::numeric(10,4)"
    )
```

**Rule:** Always test type conversions against real data. If the conversion can fail (e.g., string→integer with non-numeric strings), add a data cleanup step first.

##### Dropping a Column or Table

```python
# SAFE: Never drop in the same release as code changes
def upgrade():
    # Only drop after verifying no code references the column
    op.drop_column("production_order", "legacy_reference")

def downgrade():
    # Restore column — but data is lost. Document this.
    op.add_column("production_order", sa.Column("legacy_reference", sa.String(200), nullable=True))
```

**Rule:** Data in dropped columns is **irrecoverable**. The migration's docstring must explicitly state: `"WARNING: Drops column X — data is not recoverable from downgrade."`

##### Adding / Removing Indexes

```python
# SAFE: Indexes can be added/removed without data impact
# For large tables, use CONCURRENTLY on PostgreSQL to avoid locking
def upgrade():
    op.create_index(
        "ix_unit_history_entered_at",
        "unit_history", ["entered_at"],
        postgresql_concurrently=True   # Non-blocking on PostgreSQL
    )
```

##### Adding Foreign Keys to Existing Tables

```python
# SAFE: Validate existing data first
def upgrade():
    # Step 1: Clean up orphaned references
    op.execute("""
        UPDATE material_consumption SET material_lot_id = NULL
        WHERE material_lot_id NOT IN (SELECT id FROM material_lot)
    """)
    # Step 2: Add the foreign key
    op.create_foreign_key(
        "fk_consumption_material_lot",
        "material_consumption", "material_lot",
        ["material_lot_id"], ["id"]
    )
```

#### 5.6.5 Data Migrations

When a schema change requires transforming existing data (not just DDL), the logic goes **inside the Alembic migration file**:

```python
def upgrade():
    # DDL change
    op.add_column("production_order", sa.Column("priority_level", sa.Integer(), nullable=True))

    # Data migration: map old text priority to integer
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE production_order SET priority_level = CASE
            WHEN priority = 'low' THEN 1
            WHEN priority = 'normal' THEN 2
            WHEN priority = 'high' THEN 3
            WHEN priority = 'urgent' THEN 4
            ELSE 2
        END
    """))

    # Now safe to drop old column or alter new column to NOT NULL
    op.alter_column("production_order", "priority_level", nullable=False)
```

**Rules for data migrations:**
- Keep them **idempotent** where possible (safe to re-run)
- Use raw SQL (`op.execute` / `sa.text`) for performance — ORM models may not match the migration-time schema
- Test against a copy of production data before applying
- Log progress for long-running data migrations (batched updates)

**Batched data migration** for large tables:

```python
def upgrade():
    connection = op.get_bind()
    batch_size = 10_000
    while True:
        result = connection.execute(sa.text("""
            UPDATE unit SET normalized_serial = UPPER(serial_number)
            WHERE normalized_serial IS NULL
            LIMIT :batch
        """), {"batch": batch_size})
        if result.rowcount == 0:
            break
```

#### 5.6.6 Rollback Policy

| Scenario | Action |
|---|---|
| Migration failed mid-apply | Alembic wraps each migration in a transaction (on supported RDBMS). Failed migration auto-rolls back. PostgreSQL supports transactional DDL. SQL Server partially supports it. Oracle does not (DDL auto-commits). |
| Migration applied but needs reverting | Run `alembic downgrade -1` to execute the `downgrade()` function. Only works if `downgrade()` is properly implemented. |
| Data loss in downgrade | **Prefer forward-fix** (new migration that corrects the issue) over downgrade. Downgrades that lose data are a last resort. |
| Production rollback | Always take a **database backup before applying migrations** in production. Restore from backup if forward-fix and downgrade both fail. |

**Downgrade implementation rules:**
- Every migration **must** implement `downgrade()` — no empty stubs
- Downgrade should restore the schema to its previous state
- If data loss is unavoidable in downgrade, document it in the migration docstring
- CI runs both `upgrade` and `downgrade` for every migration to verify reversibility

#### 5.6.7 Zero-Downtime Migrations (Rolling Deployments)

For production environments requiring zero downtime, migrations must be **backward-compatible** — the old application code must still work against the new schema during the deployment window.

**Expand-Contract Pattern (mandatory for breaking changes):**

```
Phase 1 — EXPAND (backward-compatible schema change)
  ├── Add new columns (nullable or with defaults)
  ├── Add new tables
  ├── Create new indexes
  └── Deploy migration → old app code still works

Phase 2 — MIGRATE CODE
  ├── Deploy new application code that uses new schema
  ├── Old + new schema elements coexist
  └── Run data backfill if needed  

Phase 3 — CONTRACT (remove old schema elements)
  ├── Drop old columns, old tables, old indexes
  └── Only after all application instances use new schema
```

**Operations that are inherently backward-compatible (single-step):**
- Adding a nullable column
- Adding a new table
- Adding an index
- Widening a column (e.g., `VARCHAR(100)` → `VARCHAR(200)`)

**Operations that require expand-contract (multi-step):**
- Renaming a column or table
- Changing a column type (narrowing or incompatible)
- Splitting a table
- Adding a NOT NULL constraint
- Removing a column that existing code reads

#### 5.6.8 Plugin Schema Migrations

Plugins that define their own database tables need their own migration chains, **separate from core migrations**, to avoid coupling plugin lifecycle to core releases.

**Plugin migration structure:**
```
plugins/
└── sap_s4_adapter/
    ├── manifest.yaml
    ├── plugin.py
    ├── models.py                      # Plugin's SQLAlchemy models
    └── migrations/
        ├── env.py                     # Plugin-specific Alembic env
        └── versions/
            ├── 0001_sap_s4_initial.py
            └── 0002_sap_s4_add_idoc_log.py
```

**How it works:**
1. Core and plugin migrations use **separate Alembic revision chains** (different `version_locations` in `alembic.ini`)
2. Plugin tables are prefixed with the plugin ID: `plugin_sap_s4_idoc_log`, `plugin_sap_s4_mapping_cache`
3. The plugin framework runs plugin migrations **after** core migrations during startup
4. Plugin `manifest.yaml` declares `has_migrations: true` to trigger migration discovery
5. Uninstalling a plugin does **not** auto-drop its tables — an explicit `alembic downgrade base` on the plugin chain is required (safety measure)

**Plugin manifest addition:**
```yaml
# manifest.yaml
database:
  has_migrations: true
  table_prefix: "plugin_sap_s4_"     # Required — prevents table name collisions
```

**Plugin model convention:**
```python
# Plugin models inherit from the same Base but use prefixed table names
class SapIdocLog(Base):
    __tablename__ = "plugin_sap_s4_idoc_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idoc_number: Mapped[str] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(10))   # "inbound" | "outbound"
    status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

#### 5.6.9 Migration Testing in CI

| CI Check | What It Validates |
|---|---|
| **`alembic upgrade head`** | The full migration chain applies cleanly from an empty database |
| **`alembic downgrade base`** | Every migration's `downgrade()` works, full chain is reversible |
| **`alembic upgrade head` → seed → `alembic downgrade -1` → `alembic upgrade head`** | Migrations work correctly with data present, not just empty tables |
| **Alembic single-head check** | No branched migration heads (catches multi-agent conflicts) |
| **Multi-RDBMS matrix** | Migration chain runs against PostgreSQL, SQLite, and optionally SQL Server / Oracle |
| **Autogenerate diff check** | After applying all migrations, `alembic check` confirms no model-vs-schema drift (models.py matches the database) |

**CI command sequence:**
```bash
# 1. Check single head
alembic heads | wc -l   # Must be exactly 1

# 2. Full upgrade from scratch
alembic upgrade head

# 3. Seed test data
python -m mes.framework.db.seed

# 4. Downgrade and re-upgrade (verifies reversibility with data)
alembic downgrade -1
alembic upgrade head

# 5. Check for model drift
alembic check   # Exits non-zero if models.py has unapplied changes

# 6. Full downgrade to base (verifies all downgrades)
alembic downgrade base
```

#### 5.6.10 Production Migration Runbook

For applying migrations to a production database:

```
PRE-MIGRATION
  1. Notify stakeholders of maintenance window (if needed)
  2. Take a full database backup
  3. Review migration SQL: alembic upgrade head --sql > migration_review.sql
  4. Estimate migration time (test against production-size data copy)
  5. Verify current revision: alembic current

APPLY MIGRATION
  6. Apply: alembic upgrade head
  7. Verify: alembic current (confirm at expected head)
  8. Smoke test: hit critical API endpoints

POST-MIGRATION
  9. Monitor application logs for errors (15+ minutes)
  10. If issues found: decide forward-fix vs. downgrade vs. backup restore
  11. Document migration in the deployment log
```

**For zero-downtime deployments**, the expand-contract phases (§5.6.7) replace the single "Apply Migration" step with a phased rollout.

#### 5.6.11 AI Agent Migration Conventions

When an AI agent needs to modify the database schema:

1. **Modify `models.py` first** — the ORM model is the source of truth
2. **Run `alembic revision --autogenerate`** — let Alembic detect the diff
3. **Review the generated migration** — fix renames (autogenerate misdetects as drop+add), add data migrations
4. **Set the correct sequence number** — check existing files in `versions/` and use the next number
5. **Include the module ID** in the filename per §5.6.2
6. **Implement `downgrade()`** — never leave it as `pass`
7. **Test both directions** — `upgrade head` then `downgrade -1` then `upgrade head`
8. **One migration per logical change** — don't bundle unrelated schema changes
9. **Never edit a migration that has been applied to any shared database** — create a new migration instead

#### 5.6.12 Migration Linting & Pre-Commit Hooks

Automated checks that run **before commit** (via `pre-commit` framework) and **in CI** to enforce migration rules mechanically. These are not guidelines — they are **gate checks that block merges**.

##### Filename Convention Lint

```python
# tools/lint_migrations.py
import re, sys, pathlib

PATTERN = re.compile(r"^\d{4}_[a-z][a-z0-9_]+\.py$")
VALID_MODULES = {
    "multi", "phys_model", "prod_def", "prod_order", "wip_track",
    "route_def", "route_engine", "dispatch", "mat_mgmt",
    "data_collect", "qual_mgmt", "perf_analysis", "genealogy",
    "auth", "data_layer", "event_bus", "rest_api", "plugin_fw",
}

def check_filename(path: pathlib.Path) -> list[str]:
    errors = []
    name = path.name
    if not PATTERN.match(name):
        errors.append(f"{name}: Does not match pattern {{4-digit}}_{{module}}_{{description}}.py")
    else:
        parts = name.split("_", 2)
        module = parts[1] if len(parts) > 1 else ""
        # Module ID may span multiple underscored words — check prefix
        if not any(name[5:].startswith(m + "_") for m in VALID_MODULES):
            if name[5:].split("_")[0] not in VALID_MODULES:
                errors.append(f"{name}: Module ID not recognized — expected one of {VALID_MODULES}")
    return errors
```

##### AST-Based Migration Content Checks

```python
# tools/lint_migrations.py (continued)
import ast

def check_migration_content(path: pathlib.Path) -> list[str]:
    errors = []
    source = path.read_text()
    tree = ast.parse(source)

    # 1. Docstring must exist
    docstring = ast.get_docstring(tree)
    if not docstring:
        errors.append(f"{path.name}: Missing module-level docstring")
    else:
        # 2. Docstring must contain Module: tag
        if "Module:" not in docstring:
            errors.append(f"{path.name}: Docstring missing 'Module:' tag")
        # 3. Docstring must contain Data impact: tag
        if "Data impact:" not in docstring:
            errors.append(f"{path.name}: Docstring missing 'Data impact:' tag")

    # 4. downgrade() must not be empty or just 'pass'
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            body = node.body
            # Strip docstring if present
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]
            if not body:
                errors.append(f"{path.name}: downgrade() is empty")
            elif len(body) == 1 and isinstance(body[0], ast.Pass):
                errors.append(f"{path.name}: downgrade() is just 'pass' — must implement rollback")
            break
    else:
        errors.append(f"{path.name}: Missing downgrade() function")

    return errors
```

##### Plugin Table Prefix Check

```python
# tools/lint_migrations.py (continued)
def check_plugin_tables(path: pathlib.Path, expected_prefix: str) -> list[str]:
    """For plugin migrations, verify all table operations use the declared prefix."""
    errors = []
    source = path.read_text()
    # Scan for op.create_table / op.drop_table calls with non-prefixed names
    for i, line in enumerate(source.splitlines(), 1):
        if "create_table(" in line or "drop_table(" in line:
            # Extract the table name argument
            match = re.search(r'(?:create_table|drop_table)\(["\']([^"\']+)', line)
            if match and not match.group(1).startswith(expected_prefix):
                errors.append(
                    f"{path.name}:{i}: Table '{match.group(1)}' missing prefix '{expected_prefix}'"
                )
    return errors
```

##### No Raw SQL in ORM Models Check

```python
# tools/lint_models.py
def check_no_raw_sql(path: pathlib.Path) -> list[str]:
    """Ensure models.py files don't contain text() or raw SQL strings."""
    errors = []
    source = path.read_text()
    for i, line in enumerate(source.splitlines(), 1):
        if "text(" in line and "sa.text" not in line and "sqlalchemy.text" not in line:
            continue  # Only flag sa.text / sqlalchemy.text in model files
        if re.search(r'\btext\s*\(', line):
            errors.append(f"{path.name}:{i}: Raw SQL text() found in model — use ORM queries only")
    return errors
```

##### Pre-Commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: lint-migrations
        name: Lint Alembic migrations
        entry: python tools/lint_migrations.py
        language: python
        files: 'server/alembic/versions/.*\.py$'
        pass_filenames: true

      - id: lint-plugin-migrations
        name: Lint plugin migrations
        entry: python tools/lint_plugin_migrations.py
        language: python
        files: 'server/plugins/.*/migrations/versions/.*\.py$'
        pass_filenames: true

      - id: lint-models-no-raw-sql
        name: No raw SQL in models
        entry: python tools/lint_models.py
        language: python
        files: '.*/models\.py$'
        pass_filenames: true
```

##### CI Integration

The same lint scripts run in CI as a **required check** that blocks PR merges:

```yaml
# In CI pipeline (e.g., GitHub Actions)
- name: Lint migrations
  run: python tools/lint_migrations.py server/alembic/versions/*.py

- name: Lint plugin migrations
  run: |
    for dir in server/plugins/*/migrations/versions; do
      python tools/lint_plugin_migrations.py "$dir"/*.py
    done

- name: Verify single Alembic head
  run: |
    heads=$(alembic heads 2>/dev/null | wc -l)
    if [ "$heads" -ne 1 ]; then
      echo "ERROR: $heads migration heads found — run 'alembic merge' to resolve"
      exit 1
    fi
```

**Summary of enforced rules:**

| Rule | Enforcement Point | Blocks Merge? |
|---|---|---|
| Filename matches `{4-digit}_{module}_{desc}.py` | Pre-commit + CI lint | Yes |
| Module-level docstring with `Module:` and `Data impact:` tags | Pre-commit + CI lint | Yes |
| `downgrade()` implemented (not empty/pass) | Pre-commit + CI lint | Yes |
| Plugin tables use declared prefix | Pre-commit + CI lint | Yes |
| No raw SQL in `models.py` | Pre-commit + CI lint | Yes |
| Single Alembic head (no branches) | CI | Yes |
| Full upgrade/downgrade cycle passes | CI | Yes |
| Model drift check (`alembic check`) | CI | Yes |
| Multi-RDBMS compatibility | CI matrix | Yes |

#### 5.6.13 Runtime Schema Validation

Enforcement doesn't end at CI — the MES server validates the database schema at **startup** to prevent running application code against the wrong schema version.

##### Core Schema Version Check

During `FastAPI` `lifespan` startup:

```python
# mes/framework/db/startup.py
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

async def verify_schema_version(engine) -> None:
    """Refuse to start if database is not at expected migration head."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    expected_head = script.get_current_head()

    async with engine.connect() as conn:
        context = await conn.run_sync(
            lambda sync_conn: MigrationContext.configure(sync_conn)
        )
        current_rev = await conn.run_sync(
            lambda sync_conn: MigrationContext.configure(sync_conn).get_current_revision()
        )

    if current_rev != expected_head:
        raise SystemExit(
            f"FATAL: Database schema mismatch.\n"
            f"  Database is at:  {current_rev}\n"
            f"  Expected head:   {expected_head}\n"
            f"  Run 'alembic upgrade head' before starting the server."
        )
```

**Behavior:**
- If the database is **behind**: Server refuses to start with a clear error message and the exact command to fix it
- If the database is **ahead** (newer than the code): Server refuses to start — indicates code rollback without schema rollback
- If the database has **no Alembic version table**: Server refuses to start — indicates uninitialized database

##### Plugin Schema Version Check

The plugin framework checks each plugin's migration chain during plugin activation:

```python
# mes/framework/plugin/loader.py
async def activate_plugin(plugin_manifest: dict, engine) -> None:
    if not plugin_manifest.get("database", {}).get("has_migrations"):
        return  # No migrations to check

    plugin_id = plugin_manifest["id"]
    migrations_dir = f"plugins/{plugin_id}/migrations"

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", migrations_dir)

    script = ScriptDirectory.from_config(alembic_cfg)
    expected_head = script.get_current_head()

    # Check plugin's revision in the 'alembic_version_plugin_{id}' table
    current_rev = await get_plugin_revision(engine, plugin_id)

    if current_rev is None:
        # First activation — run plugin migrations
        logger.info(f"Plugin {plugin_id}: Initializing database tables...")
        await run_plugin_migrations(engine, plugin_id, migrations_dir)
    elif current_rev != expected_head:
        logger.warning(
            f"Plugin {plugin_id}: Schema mismatch "
            f"(db={current_rev}, expected={expected_head}). "
            f"Running pending migrations..."
        )
        await run_plugin_migrations(engine, plugin_id, migrations_dir)
```

**Plugin migration behavior differs from core:**
- Core migrations **block startup** if behind — safety-first for production data
- Plugin migrations **auto-apply** on activation — plugins may be added/updated dynamically
- Plugin migrations use a **separate version table** (`alembic_version_plugin_{id}`) to avoid conflicts with core

##### Startup Health Report

The server logs a schema health summary at startup:

```
[2026-02-23 08:00:01] INFO  Schema validation:
  Core:     ✓ at revision 0042_qual_mgmt_add_spc_limits (head)
  Plugin sap_s4_adapter:  ✓ at revision 0003 (head)
  Plugin custom_dispatch:  ✓ at revision 0001 (head)
  Plugin oee_dashboard:    – no migrations
  Database: PostgreSQL 16.2
  Server:   MES AI v0.4.0
```

**Summary of runtime enforcement:**

| Check | When | Behavior |
|---|---|---|
| Core schema at expected head | Server startup | **Refuse to start** if mismatch |
| Plugin schema at expected head | Plugin activation | **Auto-apply** pending migrations |
| Database reachable | Server startup | **Refuse to start** if cannot connect |
| Alembic version table exists | Server startup | **Refuse to start** if missing (uninitialized DB) |

### 5.7 Equipment State Machine

Equipment state management is central to OEE calculation, dispatch decisions, and ERP downtime
reporting. Rather than inventing an ad-hoc state model, this MES must adopt a recognized industry
standard. This section surveys the candidates and documents the selection criteria.

#### 5.7.1 Why a Standard Model Matters

The `EquipmentStateLog` entity (§5.2) records every state transition for every piece of equipment.
The set of valid states and legal transitions between them determines:

| Concern | How Equipment States Are Used |
|---|---|
| **OEE Calculation** | Availability = Planned Production Time − Downtime. Which states count as "downtime" must be unambiguous. |
| **Dispatching** | DISPATCH module only assigns work to equipment in an available/idle state. The state model defines what "available" means. |
| **ERP Reporting** | `ERPOutboundAdapter` reports downtime events. ERP expects states mapped to its own categories (planned vs. unplanned). |
| **Equipment Adapter** | Equipment adapters (§9.3) translate raw PLC/OPC-UA signals into state transitions. The state model defines the target vocabulary. |
| **Dashboards** | RT-GUI Andon boards and performance dashboards color-code equipment by state. |

#### 5.7.2 Industry Standard Candidates

##### PackML / ISA-TR88 (OMAC)

- **Origin:** ISA-88 Technical Report, adopted by OMAC (Organization for Machine Automation and Control).
- **Scope:** Machine-level execution states for packaging and discrete manufacturing.
- **States:** 17 states organized across 3 operating modes (Production, Maintenance, Manual).

```
                    ┌─── Production Mode ───────────────────────────────┐
                    │                                                    │
   ┌────────┐  Start   ┌──────────┐  SC   ┌───────────┐  SC   ┌──────────┐
   │  Idle  │────────▶│ Starting  │─────▶│ Execute    │─────▶│Completing│
   └────────┘         └──────────┘       └───────────┘       └──────────┘
       ▲                                    │    │                  │
       │                                 Hold  Suspend             │
       │                                    ▼    ▼                 ▼
       │                              ┌────────┐ ┌───────────┐ ┌──────────┐
       │                              │ Held   │ │ Suspended │ │ Complete │
       │                              └────────┘ └───────────┘ └──────────┘
       │                                 │           │              │
       │                              Unhold     Unsuspend       Reset
       │                                 │           │              │
       │                                 ▼           ▼              │
       │                              (back to    (back to          │
       │                               Execute)   Execute)          │
       │                                                            │
       └────────────────────────────────────────────────────────────┘
                                                              
   Any State ──Stop──▶ Stopping ──▶ Stopped ──Reset──▶ Idle
   Any State ──Abort─▶ Aborting ──▶ Aborted ──Clear──▶ Stopped
```

**Full PackML state list (17):**

| # | State | Description |
|---|---|---|
| 1 | Idle | Machine is powered, ready to start |
| 2 | Starting | Transitioning from idle to execute |
| 3 | Execute | Machine is producing |
| 4 | Completing | Production ending normally |
| 5 | Complete | Production batch/run finished |
| 6 | Resetting | Returning to idle from complete/stopped |
| 7 | Holding | Pausing due to internal condition |
| 8 | Held | Paused, waiting for operator intervention |
| 9 | Unholding | Resuming from held |
| 10 | Suspending | Pausing due to external condition (upstream/downstream) |
| 11 | Suspended | Waiting for external condition to clear |
| 12 | Unsuspending | Resuming from suspended |
| 13 | Stopping | Controlled stop initiated |
| 14 | Stopped | Machine stopped, safe state |
| 15 | Aborting | Emergency stop in progress |
| 16 | Aborted | Machine aborted, requires clear + reset |
| 17 | Clearing | Clearing fault after abort |

**Strengths:**
- Formal standard (ISA-TR88.00.02)
- OPC-UA companion specification exists (OPC 40083 / PackML)
- Widely adopted in CPG, food & beverage, packaging, discrete assembly
- Rich execution granularity (hold/suspend distinction)

**Weaknesses:**
- High complexity (17 states) — may be overkill for simpler equipment
- Originally designed for packaging machines — naming can feel foreign to other industries
- Requires all equipment to implement the full state model, even if many states are unused

---

##### SEMI E10 / E58 (Semiconductor)

- **Origin:** SEMI (Semiconductor Equipment and Materials International).
- **Scope:** Equipment utilization and availability classification.
- **States:** 6 top-level states with E58 sub-state expansion.

```
┌───────────────────── Equipment ──────────────────────────────┐
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Scheduled Time                           │    │
│  │  ┌────────────────────────────────────────────────┐  │    │
│  │  │  ┌──────────────┐  ┌───────────────────────┐   │  │    │
│  │  │  │ PRODUCTIVE   │  │ STANDBY               │   │  │    │
│  │  │  │ (producing)  │  │ (ready, no work/mat)  │   │  │    │
│  │  │  └──────────────┘  └───────────────────────┘   │  │    │
│  │  │                  Operations Time                │  │    │
│  │  ├────────────────────────────────────────────────┤  │    │
│  │  │  ┌──────────────┐  ┌───────────────────────┐   │  │    │
│  │  │  │ ENGINEERING  │  │ SCHED. DOWNTIME       │   │  │    │
│  │  │  │ (qual/test)  │  │ (planned maint/setup) │   │  │    │
│  │  │  └──────────────┘  └───────────────────────┘   │  │    │
│  │  └────────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  ├───────────────────────────────────────────────────────┤   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │ UNSCHEDULED DOWNTIME                          │    │   │
│  │  │ (breakdown, unplanned repair)                 │    │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ NON-SCHEDULED                                         │   │
│  │ (no production planned — weekends, holidays, etc.)    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**SEMI E10 state definitions (6):**

| # | State | OEE Category | Description |
|---|---|---|---|
| 1 | **Productive** | Uptime (value-add) | Equipment is actively processing product |
| 2 | **Standby** | Uptime (non-value) | Equipment is operational but waiting (no WIP, no material, no operator) |
| 3 | **Engineering** | Downtime (planned) | Equipment used for qualification, process development, testing |
| 4 | **Scheduled Downtime** | Downtime (planned) | Planned maintenance, setup, changeover, cleaning |
| 5 | **Unscheduled Downtime** | Downtime (unplanned) | Breakdown, repair, unexpected failure |
| 6 | **Non-Scheduled** | Excluded | No production planned (weekends, holidays, off-shift) |

**SEMI E58 sub-states** allow each top-level state to be broken down further. For example,
Scheduled Downtime → {Setup, PM, Changeover, Cleaning, Calibration}.

**Strengths:**
- Clean, direct OEE mapping — each state maps unambiguously to availability/downtime category
- Simple top-level model (6 states) with optional E58 sub-state granularity
- Widely used beyond semiconductor — adopted in electronics, medical devices, automotive
- Natural fit for ERP downtime reporting

**Weaknesses:**
- No execution-level detail (doesn't model Starting → Execute → Completing transitions)
- Semiconductor-centric naming ("Engineering" state may confuse non-semi users)
- Less granular than PackML for machine control scenarios

---

##### ISA-95 / IEC 62264 Capability States

- **Origin:** ISA-95 Part 3 — Activity Models of Manufacturing Operations Management.
- **Scope:** Equipment capability declaration (not execution states).
- **States:** 3 capability levels.

| State | Meaning |
|---|---|
| **Committed** | Equipment is allocated to a specific production order/segment |
| **Available** | Equipment is operational and can accept work |
| **Unattainable** | Equipment cannot be used (down, under maintenance, not installed) |

**Strengths:**
- Already aligned with the ISA-95 data model used throughout this architecture
- Vendor-neutral, industry-agnostic
- Useful for capacity/availability queries

**Weaknesses:**
- Very abstract — only 3 states, no operational detail
- Not meant as an equipment state machine — it's a capability declaration
- Insufficient alone for OEE, dispatching, or ERP downtime reporting
- Would need to be combined with another model for actual state tracking

---

##### OEE-Based / TPM State Model (Nakajima)

- **Origin:** Total Productive Maintenance (Seiichi Nakajima, 1988).
- **Scope:** Equipment loss categorization for OEE calculation.
- **States:** Typically 6, mapping directly to the Six Big Losses.

| # | State | OEE Component | Maps to Loss |
|---|---|---|---|
| 1 | Running | Performance | (ideal vs actual cycle time) |
| 2 | Planned Stop | Availability loss | Changeover, setup, planned maintenance |
| 3 | Unplanned Stop | Availability loss | Breakdowns, failures |
| 4 | Setup / Changeover | Availability loss | Product changeover |
| 5 | Reduced Speed | Performance loss | Minor stops, slow cycles |
| 6 | Idle | Performance loss | No work, starved, blocked |

**Strengths:**
- Universally understood across all manufacturing sectors
- Maps directly to OEE formula — no translation needed
- Simple (6 states)

**Weaknesses:**
- Not a formal standard — a widely used convention without a governing body
- No formal state transition rules
- No OPC-UA or protocol-level specification
- Conflates equipment state with production loss category

---

##### Weihenstephan Standards (WS)

- **Origin:** Technical University of Munich (TUM) / Weihenstephan.
- **Scope:** Food & beverage production equipment.
- **States:** Similar to PackML with additional hygiene-specific states (CIP — Clean-in-Place, SIP — Sterilize-in-Place).
- **Assessment:** Too niche for a general-purpose MES. Mentioned for completeness only.

#### 5.7.3 Comparison Matrix

| Criterion | PackML (ISA-TR88) | SEMI E10/E58 | ISA-95 Capability | OEE / TPM | Weihenstephan |
|---|---|---|---|---|---|
| **Formal standard** | ✅ ISA-TR88 | ✅ SEMI E10/E58 | ✅ IEC 62264 | ❌ Convention | ✅ WS (regional) |
| **Industry breadth** | Packaging, discrete, CPG | Semi, electronics, auto | Universal | Universal | Food & beverage |
| **OEE mapping** | Indirect (needs mapping table) | ✅ Native | ❌ Too abstract | ✅ Native | Indirect |
| **Execution granularity** | ✅ High (17 states) | ❌ Low (6 states) | ❌ Very low (3) | ❌ Low (6) | ✅ High |
| **OPC-UA companion spec** | ✅ OPC 40083 | ✅ SEMI standards | ✅ IEC 62264 | ❌ None | ❌ Limited |
| **Implementation complexity** | High | Low–Medium | Low | Low | High |
| **Sub-state extensibility** | Via modes (Prod/Maint/Manual) | ✅ E58 sub-states | Via sub-reasons | Not defined | Via CIP/SIP states |
| **Dispatch integration** | Map Execute+Idle→available | Map Productive+Standby→available | ✅ Native (Available) | Map Running+Idle→available | Same as PackML |
| **ERP downtime reporting** | Map to planned/unplanned | ✅ Native categories | ❌ Insufficient | Partial | Same as PackML |

#### 5.7.4 Previous Ad-Hoc Model (Removed)

> **Decision D040 — Remove equipment status field:** The original `Equipment.status`
> field (up/down/idle) was a simplified S95 operational status that conflated equipment
> availability with state machine state. It has been **removed**. Equipment availability
> is now determined exclusively by the assigned state machine model via `state_model_id`.
> If no state model is assigned (`state_model_id = null`), the equipment is assumed
> **100% available** — no state tracking, no downtime classification. The DISPATCH engine
> and OEE calculator read from `EquipmentStateLog.dispatch_category` only.

The previous `EquipmentStateLog.state` ad-hoc values (running, idle, down_planned,
down_unplanned, maintenance) have been replaced by the pluggable state models below.

#### 5.7.5 Pluggable State Machine Architecture (Decision D025)

Rather than choosing a single standard, the MES supports **all three viable models as
plugins**. Each piece of equipment declares which state model it uses via the `state_model_id`
field (nullable FK to `EquipmentStateModel.model_id`). Different equipment in the same plant
can use different models — e.g. packaging lines on PackML, semiconductor tools on SEMI E10.
If `state_model_id` is null, the equipment has **no state machine** and is assumed to be
**100% available** for OEE and dispatching purposes.

##### Design Principle: Canonical Dispatch Categories

Every state model — regardless of how many states it defines — must map each of its states to
exactly one of **four canonical dispatch categories**. These categories are the contract between
the state model plugin and all consumers (DISPATCH, OEE, ERP reporting, dashboards):

```python
from enum import Enum

class DispatchCategory(str, Enum):
    """Canonical equipment availability categories.
    
    Every equipment state model plugin MUST map each of its states
    to exactly one of these categories. The DISPATCH engine, OEE
    calculator, and ERP reporter consume ONLY these categories —
    never raw plugin states.
    """
    AVAILABLE = "available"        # Can accept WIP (idle, ready, standby)
    BUSY = "busy"                  # Currently processing WIP — do not double-assign
    UNAVAILABLE_PLANNED = "unavailable_planned"    # Planned downtime (maintenance, setup, changeover)
    UNAVAILABLE_UNPLANNED = "unavailable_unplanned"  # Unplanned downtime (breakdown, abort, fault)
```

**Dispatch rule (invariant):** The DISPATCH engine **only** routes WIP to equipment whose
current state maps to `AVAILABLE`. Equipment in `BUSY`, `UNAVAILABLE_PLANNED`, or
`UNAVAILABLE_UNPLANNED` is **never** a dispatch candidate. This rule is enforced in core, not
in the plugin. **If no state model is assigned** (i.e. `state_model_id` is null and no
`EquipmentStateLog` exists), the equipment is treated as `AVAILABLE` (100% availability
assumption).

```
  Get eligible equipment at next step(s)     ← from ROUTE-ENGINE
       │
       ▼
  Filter: equipment.dispatch_category == AVAILABLE     ← CORE enforced
       │
       ▼
  Apply dispatch strategy (first_available, shortest_queue, etc.)
       │
       ▼
  Assign unit/lot → equipment state transitions to BUSY
```

##### Abstract Interface: EquipmentStateModelPlugin

```python
from abc import ABC, abstractmethod
from typing import Sequence

class EquipmentStateModelPlugin(ABC):
    """Base class for equipment state model plugins.
    
    Multiple state model plugins can be active simultaneously.
    Each equipment declares its model via Equipment.state_model_id.
    Registered via extension_points: [{type: equipment_state_model}].
    """

    @abstractmethod
    def get_states(self) -> list[EquipmentStateDefinition]:
        """Return all valid states in this model.
        
        Each state definition includes:
          - id: str           (e.g., "execute", "productive", "running")
          - name: str         (human-readable display name)
          - description: str
          - dispatch_category: DispatchCategory
          - oee_bucket: OEEBucket  (uptime_value_add, uptime_non_value, 
                                     downtime_planned, downtime_unplanned, excluded)
          - color: str        (hex color for dashboard rendering)
        """
        ...

    @abstractmethod
    def get_transitions(self) -> list[EquipmentStateTransition]:
        """Return all legal state transitions.
        
        Each transition includes:
          - from_state: str
          - to_state: str
          - trigger: str      (e.g., "start", "hold", "abort", "clear")
          - auto: bool        (True = system-triggered, False = requires operator/command)
        """
        ...

    @abstractmethod
    def validate_transition(
        self, current_state: str, requested_state: str
    ) -> bool:
        """Return True if the transition from current_state to requested_state is legal."""
        ...

    @abstractmethod
    def get_initial_state(self) -> str:
        """Return the state ID for newly registered equipment."""
        ...

    @abstractmethod
    def map_to_dispatch_category(self, state: str) -> DispatchCategory:
        """Map a plugin-specific state to a canonical dispatch category.
        
        This is the CRITICAL contract method. The DISPATCH engine calls
        this to determine whether equipment can accept WIP.
        """
        ...

    @abstractmethod
    def map_to_oee_bucket(self, state: str) -> OEEBucket:
        """Map a plugin-specific state to an OEE time bucket.
        
        Used by PERF-ANALYSIS for OEE availability calculation.
        """
        ...

    def map_to_erp_downtime_category(self, state: str) -> str | None:
        """Map a state to an ERP downtime category for outbound reporting.
        
        Returns None if the state is not a downtime state.
        Default implementation derives from dispatch_category.
        """
        cat = self.map_to_dispatch_category(state)
        if cat == DispatchCategory.UNAVAILABLE_PLANNED:
            return "planned_downtime"
        elif cat == DispatchCategory.UNAVAILABLE_UNPLANNED:
            return "unplanned_downtime"
        return None
```

##### OEE Bucket Enum

```python
class OEEBucket(str, Enum):
    """OEE time classification for equipment states."""
    UPTIME_VALUE_ADD = "uptime_value_add"          # Actively producing
    UPTIME_NON_VALUE = "uptime_non_value"          # Available but not producing
    DOWNTIME_PLANNED = "downtime_planned"           # Planned maintenance, setup
    DOWNTIME_UNPLANNED = "downtime_unplanned"       # Breakdown, unplanned downtime
    EXCLUDED = "excluded"                            # Not counted (non-scheduled time)
```

**OEE availability formula** (computed from OEE buckets):

$$\text{Availability} = \frac{\text{UPTIME\_VALUE\_ADD} + \text{UPTIME\_NON\_VALUE}}{\text{UPTIME\_VALUE\_ADD} + \text{UPTIME\_NON\_VALUE} + \text{DOWNTIME\_PLANNED} + \text{DOWNTIME\_UNPLANNED}}$$

`EXCLUDED` time is removed from the denominator entirely (non-scheduled = not counted).

##### Plugin 1: PackML State Model

```yaml
id: state-model-packml
name: PackML Equipment State Model (ISA-TR88)
version: 1.0.0
description: "17-state PackML model with Production/Maintenance/Manual modes"
extension_points:
  - type: equipment_state_model
    name: packml
```

**State → Dispatch Category → OEE Bucket mapping:**

| PackML State | Dispatch Category | OEE Bucket | Rationale |
|---|---|---|---|
| Idle | `AVAILABLE` | Uptime (non-value) | Ready to accept work |
| Starting | `BUSY` | Uptime (value-add) | Transitioning into production |
| Execute | `BUSY` | Uptime (value-add) | Actively producing |
| Completing | `BUSY` | Uptime (value-add) | Finishing current item |
| Complete | `AVAILABLE` | Uptime (non-value) | Batch done, ready for next |
| Resetting | `BUSY` | Uptime (non-value) | Returning to idle |
| Holding | `BUSY` | Downtime (unplanned) | Internal pause in progress |
| Held | `UNAVAILABLE_UNPLANNED` | Downtime (unplanned) | Waiting for intervention |
| Unholding | `BUSY` | Uptime (value-add) | Resuming production |
| Suspending | `BUSY` | Downtime (planned) | External pause in progress |
| Suspended | `UNAVAILABLE_PLANNED` | Downtime (planned) | Waiting for upstream/downstream |
| Unsuspending | `BUSY` | Uptime (value-add) | Resuming production |
| Stopping | `BUSY` | Downtime (planned) | Controlled stop in progress |
| Stopped | `UNAVAILABLE_PLANNED` | Downtime (planned) | Stopped, safe state |
| Aborting | `BUSY` | Downtime (unplanned) | Emergency stop in progress |
| Aborted | `UNAVAILABLE_UNPLANNED` | Downtime (unplanned) | Fault/emergency, requires clear |
| Clearing | `BUSY` | Downtime (unplanned) | Clearing fault condition |

**Transition states** (`Starting`, `Completing`, `Resetting`, `Holding`, `Unholding`,
`Suspending`, `Unsuspending`, `Stopping`, `Aborting`, `Clearing`) map to `BUSY` because the
equipment is occupied during the transition — it cannot accept new WIP.

**Hold vs. Suspend distinction (OEE impact):**
- **Hold/Held** → **Downtime (unplanned)**: An *internal* fault or condition requires operator
  intervention. The equipment cannot continue on its own. This is an unplanned availability loss.
- **Suspend/Suspended** → **Downtime (planned)**: An *external* condition (upstream starve,
  downstream block) caused the pause. The equipment itself is healthy — it will resume when the
  external condition clears. This is a planned availability loss.

##### Plugin 2: SEMI E10 State Model

```yaml
id: state-model-semi-e10
name: SEMI E10 Equipment State Model
version: 1.0.0
description: "6-state SEMI E10 model with optional E58 sub-states"
extension_points:
  - type: equipment_state_model
    name: semi_e10
```

**State → Dispatch Category → OEE Bucket mapping:**

| SEMI E10 State | Dispatch Category | OEE Bucket | Rationale |
|---|---|---|---|
| Productive | `BUSY` | Uptime (value-add) | Actively processing |
| Standby | `AVAILABLE` | Uptime (non-value) | Ready, waiting for work |
| Engineering | `UNAVAILABLE_PLANNED` | Downtime (planned) | Qualification / process dev |
| Scheduled Downtime | `UNAVAILABLE_PLANNED` | Downtime (planned) | PM, setup, changeover |
| Unscheduled Downtime | `UNAVAILABLE_UNPLANNED` | Downtime (unplanned) | Breakdown, failure |
| Non-Scheduled | `UNAVAILABLE_PLANNED` | Excluded | Off-shift, weekends |

**E58 sub-states** (optional — stored as `sub_state` in `EquipmentStateLog`):

| Parent State | Sub-States |
|---|---|
| Productive | Regular Production, Rework, Engineering Run |
| Standby | No Material, No Operator, No Carrier, Blocked |
| Scheduled Downtime | PM, Setup, Changeover, Cleaning, Calibration |
| Unscheduled Downtime | Breakdown, Repair, Out of Spec, Facility |

##### Plugin 3: OEE / TPM State Model

```yaml
id: state-model-oee-tpm
name: OEE/TPM Equipment State Model
version: 1.0.0
description: "6-state model based on TPM loss categories for direct OEE calculation"
extension_points:
  - type: equipment_state_model
    name: oee_tpm
```

**State → Dispatch Category → OEE Bucket mapping:**

| OEE/TPM State | Dispatch Category | OEE Bucket | Rationale |
|---|---|---|---|
| Running | `BUSY` | Uptime (value-add) | Actively producing |
| Idle | `AVAILABLE` | Uptime (non-value) | Ready, no work assigned |
| Planned Stop | `UNAVAILABLE_PLANNED` | Downtime (planned) | Maintenance, changeover |
| Unplanned Stop | `UNAVAILABLE_UNPLANNED` | Downtime (unplanned) | Breakdown, failure |
| Setup / Changeover | `UNAVAILABLE_PLANNED` | Downtime (planned) | Product changeover |
| Reduced Speed | `BUSY` | Uptime (value-add) | Producing below ideal rate |

##### Data Model Changes

The `EquipmentStateLog` entity is updated to be model-agnostic:

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `equipment_id` | FK → Equipment | Which equipment |
| `state_model` | string | Active plugin ID (`packml`, `semi_e10`, `oee_tpm`) |
| `state` | string | Plugin-specific state ID (e.g., `execute`, `productive`, `running`) |
| `sub_state` | string (nullable) | Optional sub-state (E58 sub-states, PackML modes) |
| `dispatch_category` | enum | Canonical category — **denormalized** for fast dispatch queries |
| `oee_bucket` | enum | OEE time bucket — **denormalized** for fast OEE queries |
| `started_at` | datetime | Transition timestamp |
| `ended_at` | datetime (nullable) | End timestamp (null = current state) |
| `reason_code` | string (nullable) | Why the transition occurred |
| `notes` | string (nullable) | Free-text annotation |

The `dispatch_category` and `oee_bucket` columns are **denormalized** from the plugin's mapping
methods at write time. This ensures:
- DISPATCH queries can filter by `dispatch_category = 'available'` without calling the plugin
- OEE calculations can aggregate by `oee_bucket` without calling the plugin
- Historical data remains correct even if the plugin is removed or swapped

The `Equipment` entity also gains a denormalized `dispatch_category` field for its current state:

```python
class Equipment(Base):
    # ... existing fields ...
    current_state: Mapped[str]                    # Plugin-specific state
    current_dispatch_category: Mapped[DispatchCategory]  # Canonical — used by DISPATCH
```

##### Integration with DISPATCH

The DISPATCH engine never inspects plugin-specific states. It queries **only** the canonical
`dispatch_category`:

```python
async def get_eligible_equipment(
    step: RouteStep, db: AsyncSession
) -> list[Equipment]:
    """Return equipment eligible for dispatch at the given step.
    
    Eligibility requires:
      1. Equipment is linked to the step (M:N relationship)
      2. Equipment.current_dispatch_category == AVAILABLE
      3. Equipment has required capabilities (if step specifies them)
    """
    return await db.scalars(
        select(Equipment)
        .join(equipment_step_association)
        .where(
            equipment_step_association.c.step_id == step.id,
            Equipment.current_dispatch_category == DispatchCategory.AVAILABLE,
        )
    )
```

**Invariant enforced in core (not in plugin):**

> WIP is **never** dispatched to equipment where `dispatch_category != AVAILABLE`.  
> This holds regardless of which state model plugin is active.

When a unit/lot is dispatched to equipment, the core triggers a state transition:
- Equipment moves from `AVAILABLE` state → `BUSY` state (plugin-specific: `Idle→Execute` in
  PackML, `Standby→Productive` in SEMI E10, `Idle→Running` in OEE/TPM)
- When processing completes, equipment returns to its `AVAILABLE` state

##### Integration with OEE (PERF-ANALYSIS)

```python
async def calculate_availability(
    equipment_id: UUID,
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession,
) -> float:
    """Calculate OEE Availability using denormalized oee_bucket.
    
    Works identically regardless of active state model plugin.
    """
    logs = await db.scalars(
        select(EquipmentStateLog).where(
            EquipmentStateLog.equipment_id == equipment_id,
            EquipmentStateLog.started_at >= period_start,
            EquipmentStateLog.started_at <= period_end,
        )
    )
    
    buckets = defaultdict(float)
    for log in logs:
        duration = (log.ended_at or period_end) - log.started_at
        buckets[log.oee_bucket] += duration.total_seconds()
    
    uptime = buckets[OEEBucket.UPTIME_VALUE_ADD] + buckets[OEEBucket.UPTIME_NON_VALUE]
    downtime = buckets[OEEBucket.DOWNTIME_PLANNED] + buckets[OEEBucket.DOWNTIME_UNPLANNED]
    # EXCLUDED time is not in numerator or denominator
    
    total = uptime + downtime
    return uptime / total if total > 0 else 0.0
```

##### Plugin Extension Point Registration

A new extension point type is added to the plugin framework (§7.5):

| Type | Description | Example |
|---|---|---|
| **equipment_state_model** | Equipment state machine definition (states, transitions, mappings) | PackML, SEMI E10, OEE/TPM |

**Constraint:** Only **one** `equipment_state_model` plugin may be active at a time. If a user
activates a new state model, the system:
1. Validates that no equipment is currently in a `BUSY` state (refuse if WIP is in-flight)
2. Maps existing equipment current states to the new model's initial state
3. Closes all open `EquipmentStateLog` records
4. Opens new log records using the new model's initial state
5. Historical log records retain their original `state_model` value — queries filter by model

##### Reason Codes & Manual Transitions

Equipment state transitions normally originate from PLC signals via equipment adapters
(OPC-UA, MQTT, etc.). However, operators also need to **manually** transition equipment
— for example, logging a planned changeover, recording an unplanned breakdown, or noting a
material shortage. The **Reason** entity bridges operator intent to OEE classification.

**Hierarchical Reason Codes**

Reasons follow a 4-character code hierarchy. The code is free-form but conventionally
numeric, with levels implied by position:

```
1000  Electrical                  (downtime_unplanned)
├─ 1010  AC Motors                (downtime_unplanned)
│  └─ 1011  High temperature      (downtime_unplanned)
│  └─ 1012  Bearing failure        (downtime_unplanned)
├─ 1020  DC Drives                (downtime_unplanned)
2000  Planned Maintenance         (downtime_planned)
├─ 2010  Preventive               (downtime_planned)
├─ 2020  Changeover               (downtime_planned)
3000  Process                     (uptime_non_value)
├─ 3010  Warm-up                  (uptime_non_value)
├─ 3020  Cleaning                 (downtime_planned)
```

Each reason carries an `oee_bucket` that classifies the time for OEE calculation.
Child reasons inherit the parent's context but may override the bucket (e.g., cleaning
during a process halt may be `downtime_planned` while the parent category is
`uptime_non_value`).

**Reason → OEE Bucket → Dispatch Category Mapping**

When an operator triggers a manual transition, the reason's `oee_bucket` is mapped
to a canonical `dispatch_category` so DISPATCH and OEE consumers work without change:

| Reason `oee_bucket` | → `dispatch_category` | Equipment Available? |
|---|---|---|
| `downtime_planned` | `unavailable_planned` | ❌ |
| `downtime_unplanned` | `unavailable_unplanned` | ❌ |
| `uptime_non_value` | `available` | ✅ |
| `uptime_value_add` | `busy` | ❌ (already producing) |
| `excluded` | `unavailable_planned` | ❌ |

**Manual Transition Flow**

```
Operator selects reason in DT-CLIENT
    ──POST /equipment/{id}/manual-transition──►  routes.py
    ──look up Reason by reason_id──►  ReasonService.get_reason()
    ──map oee_bucket → dispatch_category──►  oee_to_dispatch dict
    ──record state change──►  EquipmentStateService.record_state_change(
                                state_model="manual",
                                state=reason.name,
                                dispatch_category=mapped,
                                oee_bucket=reason.oee_bucket,
                                reason_code=reason.code)
    ──persist──►  EquipmentStateLog row + equipment.state.changed event
```

The `state_model` is set to `"manual"` so that log analysis can distinguish
operator-initiated transitions from PLC-driven ones.

**DT-CLIENT Reason Codes Page**

The design-time client provides a dedicated **Reason Codes** page accessible from the
dashboard card grid. It renders the hierarchy as an indented tree table with columns:
Code, Name, Description, OEE Bucket (colour-coded badge). Each row has
add-child / edit / delete actions. A modal dialog handles create and edit
with fields: code (4-char, immutable after create), name, description, OEE bucket
(dropdown), and parent (dropdown of existing reasons).

##### Summary: How Each Consumer Uses the State Model

| Consumer | What It Reads | Plugin-Aware? |
|---|---|---|
| **DISPATCH** | `Equipment.current_dispatch_category` | ❌ No — uses canonical category only |
| **OEE (PERF-ANALYSIS)** | `EquipmentStateLog.oee_bucket` | ❌ No — uses canonical bucket only |
| **ERP Reporting** | `EquipmentStateModelPlugin.map_to_erp_downtime_category()` | ⚠️ Thin — calls one method |
| **Equipment Adapter** | `EquipmentStateModelPlugin.validate_transition()` | ✅ Yes — validates PLC signals |
| **RT-GUI / Dashboards** | `EquipmentStateLog.state` + plugin `get_states()` for display names/colors | ✅ Yes — renders plugin states |
| **DT-CLIENT** | Plugin `get_states()` + `get_transitions()` for state model visualization | ✅ Yes — shows state diagram |
| **DT-CLIENT** | `Reason` hierarchy via `/reasons` CRUD | ❌ No — standalone reason tree |

## 6. REST API

### 6.1 Design Principles

- **Versioned**: All routes under `/api/v1/`
- **Resource-oriented**: REST nouns, standard HTTP verbs
- **Consistent responses**: All responses wrapped in `{"data": ..., "meta": {...}}` or `{"error": {...}}`
- **Pagination**: Cursor-based for list endpoints (`?cursor=...&limit=50`)
- **Filtering**: Query parameters (`?status=active&site_id=...`)
- **Sorting**: `?sort=created_at&order=desc`
- **Content-Type**: `application/json` exclusively
- **Auth**: Bearer JWT tokens in `Authorization` header

### 6.2 Response Envelope

**Success (single resource):**
```json
{
  "data": { "id": "...", "name": "...", ... },
  "meta": { "timestamp": "2026-02-22T10:00:00Z" }
}
```

**Success (list):**
```json
{
  "data": [ ... ],
  "meta": {
    "timestamp": "2026-02-22T10:00:00Z",
    "pagination": {
      "cursor": "abc123",
      "limit": 50,
      "has_more": true
    }
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Unit with id '...' not found",
    "details": { ... }
  },
  "meta": { "timestamp": "2026-02-22T10:00:00Z" }
}
```

### 6.3 Endpoint Map

#### Physical Model (PHYS-MODEL)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/sites` | List all sites |
| `POST` | `/api/v1/sites` | Create a site |
| `GET` | `/api/v1/sites/{site_id}` | Get site by ID |
| `PUT` | `/api/v1/sites/{site_id}` | Update a site |
| `DELETE` | `/api/v1/sites/{site_id}` | Soft-delete a site |
| `GET` | `/api/v1/sites/{site_id}/areas` | List areas in a site |
| `POST` | `/api/v1/sites/{site_id}/areas` | Create area in a site |
| `GET` | `/api/v1/areas/{area_id}` | Get area by ID |
| `PUT` | `/api/v1/areas/{area_id}` | Update an area |
| `GET` | `/api/v1/areas/{area_id}/lines` | List production lines in an area |
| `POST` | `/api/v1/areas/{area_id}/lines` | Create production line in an area |
| `GET` | `/api/v1/lines/{line_id}` | Get production line by ID |
| `GET` | `/api/v1/lines/{line_id}/work-cells` | List work cells in a line |
| `POST` | `/api/v1/lines/{line_id}/work-cells` | Create work cell in a line |
| `GET` | `/api/v1/work-cells/{wc_id}` | Get work cell by ID |
| `GET` | `/api/v1/work-cells/{wc_id}/equipment` | List equipment in a work cell |
| `POST` | `/api/v1/work-cells/{wc_id}/equipment` | Create equipment in a work cell |
| `GET` | `/api/v1/equipment/{equip_id}` | Get equipment by ID |
| `PUT` | `/api/v1/equipment/{equip_id}` | Update equipment |
| `GET` | `/api/v1/equipment/{equip_id}/materials` | List material setups for equipment |
| `POST` | `/api/v1/equipment/{equip_id}/materials` | Create material setup for equipment |
| `GET` | `/api/v1/equipment-materials/{em_id}` | Get equipment-material setup by ID |
| `PUT` | `/api/v1/equipment-materials/{em_id}` | Update equipment-material setup |
| `DELETE` | `/api/v1/equipment-materials/{em_id}` | Soft-delete equipment-material setup |

#### Product Definition (PROD-DEF)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/products` | List / create product definitions |
| `GET/PUT` | `/api/v1/products/{product_id}` | Get / update product |
| `GET/POST` | `/api/v1/products/{product_id}/boms` | List / create BOMs for product |
| `GET/PUT` | `/api/v1/boms/{bom_id}` | Get / update BOM |
| `GET/POST` | `/api/v1/boms/{bom_id}/items` | List / create BOM items |
| `GET/POST` | `/api/v1/products/{product_id}/routes` | List / create routes for product |
| `GET/PUT` | `/api/v1/routes/{route_id}` | Get / update route |
| `GET/POST` | `/api/v1/routes/{route_id}/steps` | List / create route steps |
| `GET/PUT` | `/api/v1/steps/{step_id}` | Get / update route step |
| `GET/POST` | `/api/v1/steps/{step_id}/parameters` | List / create step parameters |

#### Production Orders (PROD-ORDER)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/orders` | List / create production orders |
| `GET/PUT` | `/api/v1/orders/{order_id}` | Get / update order |
| `POST` | `/api/v1/orders/{order_id}/release` | Release order for production |
| `POST` | `/api/v1/orders/{order_id}/complete` | Mark order as completed |

#### WIP Tracking (WIP-TRACK)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/units` | List / create units |
| `GET` | `/api/v1/units/{unit_id}` | Get unit with current state |
| `POST` | `/api/v1/units/{unit_id}/start` | Start processing at current step |
| `POST` | `/api/v1/units/{unit_id}/complete` | Complete current step |
| `POST` | `/api/v1/units/{unit_id}/move` | Move to next step (triggers dispatch) |
| `POST` | `/api/v1/units/{unit_id}/hold` | Place unit on hold |
| `POST` | `/api/v1/units/{unit_id}/release-hold` | Release from hold |
| `POST` | `/api/v1/units/{unit_id}/scrap` | Scrap the unit |
| `GET` | `/api/v1/units/{unit_id}/history` | Get unit processing history |
| `GET` | `/api/v1/units/{unit_id}/genealogy` | Get full genealogy (as-built record) |
| `GET/POST` | `/api/v1/lots` | List / create lots |
| `GET` | `/api/v1/lots/{lot_id}` | Get lot with current state |
| `POST` | `/api/v1/lots/{lot_id}/start` | Start processing lot at current step |
| `POST` | `/api/v1/lots/{lot_id}/complete` | Complete current step for lot |
| `POST` | `/api/v1/lots/{lot_id}/move` | Move lot to next step |
| `GET` | `/api/v1/lots/{lot_id}/history` | Get lot processing history |

#### Dispatching (DISPATCH)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/dispatch/evaluate` | Evaluate dispatch for a unit/lot (returns recommendation) |
| `POST` | `/api/v1/dispatch/execute` | Execute a dispatch decision |
| `GET` | `/api/v1/dispatch/strategies` | List available dispatch strategies |
| `GET` | `/api/v1/dispatch/queue/{work_cell_id}` | Get dispatch queue for a work cell |

#### Material Management (MAT-MGMT)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/materials` | List / create material definitions |
| `GET/PUT` | `/api/v1/materials/{material_id}` | Get / update material |
| `GET/POST` | `/api/v1/material-lots` | List / create material lots |
| `GET/PUT` | `/api/v1/material-lots/{lot_id}` | Get / update material lot |
| `POST` | `/api/v1/material-lots/{lot_id}/consume` | Record material consumption |
| `GET` | `/api/v1/units/{unit_id}/consumed-materials` | Materials consumed for a unit |

#### Quality Management (QUAL-MGMT)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/quality/tests` | List / create quality test definitions |
| `GET/PUT` | `/api/v1/quality/tests/{test_id}` | Get / update quality test |
| `GET/POST` | `/api/v1/quality/results` | List / record test results |
| `GET` | `/api/v1/quality/results/{result_id}` | Get test result |
| `GET/POST` | `/api/v1/quality/non-conformances` | List / create non-conformances |
| `PUT` | `/api/v1/quality/non-conformances/{nc_id}` | Update / resolve non-conformance |

#### Data Collection (DATA-COLLECT)

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/v1/data/definitions` | List / create data definitions |
| `POST` | `/api/v1/data/collect` | Collect single data point |
| `POST` | `/api/v1/data/collect-batch` | Collect multiple data points |
| `GET` | `/api/v1/data/points` | Query data points (with filters) |

#### Performance Analysis (PERF-ANALYSIS)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/performance/state-models` | List registered equipment state models |
| `GET` | `/api/v1/performance/state-models/{model_id}` | Get state model definition by plugin ID |
| `GET` | `/api/v1/performance/equipment/{equip_id}/current-state` | Current state + valid transitions |
| `POST` | `/api/v1/performance/equipment/{equip_id}/transition` | Trigger a state transition |
| `POST` | `/api/v1/performance/equipment/{equip_id}/manual-transition` | Manual transition with a reason code |
| `GET` | `/api/v1/performance/reasons` | List all reason codes |
| `POST` | `/api/v1/performance/reasons` | Create a reason code |
| `GET` | `/api/v1/performance/reasons/{reason_id}` | Get a reason code |
| `PUT` | `/api/v1/performance/reasons/{reason_id}` | Update a reason code |
| `DELETE` | `/api/v1/performance/reasons/{reason_id}` | Soft-delete a reason code |
| `GET` | `/api/v1/performance/oee` | Calculate OEE (query params: equipment, time range) |
| `GET` | `/api/v1/performance/equipment-states` | Query equipment state history |
| `POST` | `/api/v1/performance/equipment-states` | Record equipment state change |
| `GET` | `/api/v1/performance/counters` | Query production counters |
| `POST` | `/api/v1/performance/counters` | Record/update production counter |
| `POST` | `/api/v1/performance/counters/increment` | Atomically increment counters (delta-based) |

#### Auth (AUTH)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/auth/login` | Redirect to IdP login page (OIDC Authorization Code flow) |
| `GET` | `/api/v1/auth/callback` | OIDC callback — exchange code for tokens, JIT provision user, issue MES JWT |
| `POST` | `/api/v1/auth/refresh` | Refresh MES JWT using refresh token |
| `POST` | `/api/v1/auth/logout` | Revoke tokens, optionally trigger IdP logout (front-channel) |
| `GET` | `/api/v1/auth/me` | Get current user profile and permissions |
| `GET/POST` | `/api/v1/auth/users` | List / create users (admin) |
| `GET/PUT` | `/api/v1/auth/users/{user_id}` | Get / update user (admin) |
| `GET/POST` | `/api/v1/auth/roles` | List / create roles (admin) |
| `GET/PUT` | `/api/v1/auth/group-mappings` | List / update IdP group → MES role mappings (admin) |
| `GET` | `/api/v1/auth/.well-known/openid-configuration` | Proxy/cache IdP discovery document |

#### Plugin Management (PLUGIN-FW)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/plugins` | List all discovered plugins (installed + available) |
| `GET` | `/api/v1/plugins/{plugin_id}` | Plugin detail (parameters, config, state) |
| `POST` | `/api/v1/plugins/{plugin_id}/install` | Install a plugin (provide parameter values) |
| `POST` | `/api/v1/plugins/{plugin_id}/uninstall` | Uninstall a plugin (stops if running, clears state) |
| `POST` | `/api/v1/plugins/{plugin_id}/enable` | Enable an installed plugin (load + start) |
| `POST` | `/api/v1/plugins/{plugin_id}/disable` | Disable a running plugin (stop) |
| `PUT` | `/api/v1/plugins/{plugin_id}/config` | Update plugin configuration overrides |
| `GET` | `/api/v1/plugins/catalog` | Adapter catalog (available extras) |

#### ERP Integration (ERP-IBOUND, ERP-OBOUND)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/erp/health` | ERP adapter health (inbound + outbound availability) |
| `POST` | `/api/v1/erp/sync/production-orders` | Sync production orders from ERP |
| `POST` | `/api/v1/erp/sync/materials` | Sync material master from ERP |
| `POST` | `/api/v1/erp/sync/products` | Sync product definitions from ERP |
| `POST` | `/api/v1/erp/sync/boms?product_id=X` | Sync BOMs for a product |
| `POST` | `/api/v1/erp/sync/routings?product_id=X` | Sync routings for a product |
| `POST` | `/api/v1/erp/sync/work-centers` | Sync work centers from ERP |
| `POST` | `/api/v1/erp/report/completion` | Report production completion to ERP |
| `POST` | `/api/v1/erp/report/consumption` | Report material consumption to ERP |
| `POST` | `/api/v1/erp/report/scrap` | Report scrap to ERP |
| `POST` | `/api/v1/erp/report/labor` | Report labor time to ERP |
| `POST` | `/api/v1/erp/report/downtime` | Report equipment downtime to ERP |
| `POST` | `/api/v1/erp/report/quality-result` | Report quality test result to ERP |
| `GET` | `/api/v1/erp/confirmations` | List outbound confirmation documents |
| `GET` | `/api/v1/erp/queue` | List failed outbound queue items |
| `GET` | `/api/v1/erp/queue/stats` | Outbound queue statistics |
| `POST` | `/api/v1/erp/queue/{id}/retry` | Retry a failed outbound item |

#### Real-Time Events (WebSocket)

| Endpoint | Description |
|---|---|
| `WS /api/v1/events/ws` | WebSocket connection for real-time event streaming |
| `GET /api/v1/events/subscriptions` | List current event subscriptions |
| `POST /api/v1/events/subscriptions` | Subscribe to event topics |

## 7. Plugin Framework (PLUGIN-FW)

### 7.1 Plugin Directory Structure

Plugins are organized into two directories under `server/plugins/`:

| Directory | Env Variable | Purpose |
|---|---|---|
| `plugins/system/` | `MES_PLUGIN_DIR` | Plugins authored by project contributors. Shipped with the repo. |
| `plugins/user/` | `MES_PLUGIN_USER_DIR` | End-user plugins. Users copy their plugin folder here. |

Each plugin is a folder with a standard layout:

```
my_plugin/
├── manifest.yaml          # Plugin metadata, parameters & declarations
├── plugin.py              # Plugin entry point (implements MESPlugin)
├── models.py              # Optional: additional DB models
├── schemas.py             # Optional: additional Pydantic schemas
├── routes.py              # Optional: additional REST endpoints
├── events.py              # Optional: event handlers
└── requirements.txt       # Optional: additional dependencies
```

The `origin` field in `manifest.yaml` identifies the source: `system` or `user`.

### 7.2 Plugin Manifest

The manifest declares plugin identity, metadata, parameters, and extension points:

```yaml
id: my-custom-plugin
name: My Custom Plugin
version: 1.0.0
description: Adds custom dispatching logic for multi-criteria optimization
author: AI Agent
comment: Concise purpose note shown in plugin lists.
category: dispatch          # Grouping: dispatch, data-collection, integration, general, etc.
origin: system              # system = project contributor, user = end-user
min_mes_version: "0.1.0"

# Parameters: declared config the end user provides at install time
parameters:
  - name: broker_url
    type: string
    description: MQTT broker connection URL
    required: true
  - name: poll_interval
    type: number
    description: Seconds between polling cycles
    required: false
    default: 5.0
  - name: api_key
    type: string
    description: API key for external service
    required: true
    secret: true              # Masked in UI, never logged

# Custom permissions this plugin introduces (auto-registered on install)
permissions:
  - id: my_custom_plugin.config.read
    description: View optimizer configuration
  - id: my_custom_plugin.config.update
    description: Modify optimizer weights and parameters

# Existing core permissions this plugin's logic requires
required_core_permissions:
  - dispatch.read
  - wip.read

# What this plugin extends
extension_points:
  - type: dispatch_strategy
    name: multi_criteria_dispatch
  - type: rest_endpoint
    prefix: /api/v1/custom/optimization

# Events this plugin subscribes to
event_subscriptions:
  - "wip.unit.moved"
  - "equipment.state.changed"

# Dependencies on other plugins
dependencies: []

# Legacy JSON-Schema config (still supported; merged with parameter defaults)
config_schema:
  type: object
  properties:
    optimization_weight:
      type: number
      default: 0.7
```

#### Manifest Fields Summary

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique plugin identifier (kebab-case) |
| `name` | Yes | Human-readable display name |
| `version` | Yes | SemVer string |
| `description` | No | Multi-line description |
| `author` | No | Author name or organization |
| `comment` | No | Short note shown in list views |
| `category` | No | Grouping tag (default: `general`) |
| `origin` | No | `system` or `user` (default: `user`) |
| `min_mes_version` | No | Minimum compatible MES version |
| `parameters` | No | List of `ManifestParameter` declarations |
| `permissions` | No | Custom permissions introduced by the plugin |
| `required_core_permissions` | No | Core permissions the plugin needs |
| `extension_points` | No | List of extension point registrations |
| `event_subscriptions` | No | Event types the plugin listens to |
| `dependencies` | No | Other plugin IDs this plugin depends on |
| `config_schema` | No | Legacy JSON Schema for default config values |

### 7.3 Plugin Parameters

Parameters are the primary mechanism for end-user configuration at install time:

```python
class ManifestParameter(BaseModel):
    name: str          # Parameter key (e.g. 'broker_url')
    type: str          # string, number, boolean, integer
    description: str   # Human-readable help text
    required: bool     # Must be provided at install time
    default: Any       # Default value (optional parameters only)
    secret: bool       # Masked in UI (passwords, API keys)
```

**Validation at install time:**
- All parameters with `required: true` must have values in the install request
- Type validation is performed against the declared type
- Secret values are stored in `parameter_values` JSONB but masked in API responses

**Config resolution order** (highest priority wins):
1. `config_overrides` (runtime changes via PUT /config)
2. `parameter_values` (provided at install time)
3. `config_schema` defaults (from manifest)
4. `parameter` defaults (from manifest)

### 7.4 Plugin Base Class

```python
from abc import ABC, abstractmethod
from typing import Any

class MESPlugin(ABC):
    """Base class all plugins must implement."""

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """Called when plugin is loaded. Set up resources."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Called after all plugins initialized. Begin operation."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Called on shutdown. Clean up resources."""
        ...

    def get_routes(self) -> list | None:
        """Return FastAPI router(s) to register, or None."""
        return None

    def get_event_handlers(self) -> dict[str, callable] | None:
        """Return mapping of event_type -> handler, or None."""
        return None

    async def health_check(self) -> bool:
        """Check if the plugin can communicate with its external system.
        Override for adapter plugins that connect to external services.
        Default returns True (healthy) for non-adapter plugins."""
        return True

    def get_adapter(self) -> Any:
        """Return the adapter interface instance(s) this plugin provides.

        For single-adapter plugins (e.g. equipment), return the adapter instance.
        For multi-adapter plugins (e.g. ERP with inbound + outbound), return a dict:
            {"erp_inbound": inbound_instance, "erp_outbound": outbound_instance}

        Returns None for non-adapter plugins."""
        return None
```

> **Decision D037 — Unified Adapter-Plugin Architecture:** The `health_check()` and
> `get_adapter()` methods were added as part of the adapter unification (S020). Every
> integration adapter is now a plugin. There is no separate `BaseAdapter` or `AdapterFactory`.
> The `PluginManager` is the single manager for all adapters. See §9.1 for the full design.

### 7.5 Plugin Lifecycle

Plugins follow a DB-driven lifecycle with explicit install/uninstall steps:

```
┌───────────┐    install     ┌───────────┐    enable    ┌─────────┐
│ Available  │──────────────▶│ Installed  │────────────▶│ Running  │
│ (on disk)  │               │ (disabled) │             │ (active) │
└───────────┘               └───────────┘             └─────────┘
      ▲                          │  ▲                      │
      │         uninstall        │  │       disable         │
      └──────────────────────────┘  └──────────────────────┘
```

| State | `installed` | `enabled` | Loaded in memory | Description |
|---|---|---|---|---|
| **Available** | `false` | `false` | No | Manifest discovered on disk, not yet installed |
| **Installed (disabled)** | `true` | `false` | No | Parameters provided, persisted in DB, not running |
| **Running (enabled)** | `true` | `true` | Yes | `initialize()` + `start()` called, actively processing |

**Server startup sequence:**
1. `discover_all()` — Scans both `plugins/system/` and `plugins/user/` for `manifest.yaml` files; creates `PluginInfo` objects (no code loaded yet)
2. `load_and_start(installed_ids)` — Queries `plugin_config` table for rows with `installed=True AND enabled=True`; for each matching plugin: imports module → `initialize(config)` → `start()`

**Runtime operations:**
- **Install** (`POST /install`): Validates required parameters → creates/updates `plugin_config` row with `installed=True`, `parameter_values` stored
- **Uninstall** (`POST /uninstall`): Stops plugin if running → clears DB row
- **Enable** (`POST /enable`): Requires `installed=True` → loads module → `initialize()` → `start()` → sets `enabled=True`
- **Disable** (`POST /disable`): Calls `stop()` → unloads module → sets `enabled=False`

### 7.6 Plugin Data Model

The `plugin_config` table persists plugin state across server restarts:

```sql
CREATE TABLE plugin_config (
    id              UUID PRIMARY KEY,
    plugin_id       VARCHAR(255) UNIQUE NOT NULL,  -- matches manifest.id
    installed       BOOLEAN NOT NULL DEFAULT false, -- parameters provided
    enabled         BOOLEAN NOT NULL DEFAULT false, -- should start on boot
    parameter_values JSONB NOT NULL DEFAULT '{}',   -- user-provided params
    config_overrides JSONB NOT NULL DEFAULT '{}',   -- runtime config changes
    notes           TEXT,                           -- admin annotations
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 7.7 Extension Points

Extension points define the categories of functionality a plugin can provide. Each plugin declares its extension points in `manifest.yaml`. The `ExtensionPointType` enum in code defines the complete set:

```python
class ExtensionPointType(str, Enum):
    DISPATCH_STRATEGY    = "dispatch_strategy"
    OPERATION_HOOK       = "operation_hook"
    REST_ENDPOINT        = "rest_endpoint"
    EVENT_HANDLER        = "event_handler"
    DATA_PROCESSOR       = "data_processor"
    REPORT_GENERATOR     = "report_generator"
    EQUIPMENT_DRIVER     = "equipment_driver"
    EQUIPMENT_STATE_MODEL = "equipment_state_model"
    ERP_INBOUND          = "erp_inbound"
    ERP_OUTBOUND         = "erp_outbound"
    TEST_EQUIPMENT       = "test_equipment"
```

| Type | Description | Example |
|---|---|---|
| **dispatch_strategy** | Custom dispatching algorithm for unit/lot routing | Multi-criteria optimizer, priority-based, load-balanced |
| **operation_hook** | Before/after hooks on core operations | Validate custom business rules before unit move |
| **rest_endpoint** | Additional REST API routes | Custom reporting endpoint, equipment-specific API |
| **event_handler** | React to system events | Send notification on quality failure, Update external system |
| **data_processor** | Transform/validate collected data points | Unit conversion, outlier detection, SPC calculation |
| **report_generator** | Custom report definitions | Shift summary, quality trends, yield analysis |
| **equipment_driver** | Equipment communication protocol adapter | OPC-UA, MQTT, Modbus, custom protocols |
| **equipment_state_model** | Equipment state machine definition (states, transitions, dispatch/OEE mappings). **Only one active at a time.** | PackML (ISA-TR88), SEMI E10/E58, OEE/TPM |
| **erp_inbound** | ERP-to-MES data synchronization adapter | SAP S/4HANA inbound, Oracle Cloud inbound, mock ERP |
| **erp_outbound** | MES-to-ERP reporting adapter | SAP S/4HANA outbound, Oracle Cloud outbound, mock ERP |
| **test_equipment** | Test equipment data collection adapter | File-drop CSV results, REST-based test equipment |

**Adapter extension point types** (`erp_inbound`, `erp_outbound`, `equipment_driver`, `test_equipment`) identify plugins that wrap integration adapters. The `PluginManager` uses these types to locate adapter instances at runtime via `get_adapter_by_type()` (see §9.1).

### 7.8 Plugin Isolation

- Plugins run in the same process but are loaded in separate module namespaces
- Plugin errors are caught and logged; a failing plugin does not crash the server
- Plugin database models use a schema prefix: `plugin_{plugin_id}_` to avoid table name conflicts
- Plugin configuration is stored in the `plugin_config` table, not in environment variables

### 7.9 CLI Plugin Commands

The MES CLI provides plugin management from the command line:

```bash
mes plugin list                  # List all discovered plugins (origin, category, status)
mes plugin info <plugin-id>      # Show plugin details, parameters, config
mes plugin install <plugin-id>   # Install via REST API (prompts for required params)
mes plugin uninstall <plugin-id> # Uninstall via REST API
mes plugin enable <plugin-id>    # Enable an installed plugin
mes plugin disable <plugin-id>   # Disable a running plugin
```

> **Note (D037):** The previous `mes adapter install` and `mes adapter extras` subcommands
> have been removed. Adapter pip extras (e.g., `opcua`, `mqtt`, `oracle`) are now installed
> directly via `pip install mes-ai[opcua]`. Adapters are managed exclusively through the
> plugin commands above.

### 7.10 Plugin Metadata Contract Enforcement

The plugin contract is enforced at **two layers**: Pydantic validation (manifest metadata) and Python ABC enforcement (lifecycle methods).

#### Layer 1: Pydantic Manifest Validation

When a plugin directory is discovered, its `manifest.yaml` is parsed and validated by the `PluginManifest` Pydantic model. Any field that fails validation (missing required `id`, `name`, `version`; invalid types; malformed extension points) raises `pydantic.ValidationError` and the plugin is rejected at discovery time — it never reaches the loading stage.

```python
class PluginManifest(BaseModel):
    id: str               # Required — unique plugin identifier
    name: str             # Required — display name
    version: str          # Required — semver string
    description: str = ""
    author: str = ""
    comment: str = ""
    category: str = "general"
    origin: str = "user"
    min_mes_version: str = "0.1.0"
    parameters: list[ManifestParameter] = []
    permissions: list[ManifestPermission] = []
    extension_points: list[ManifestExtensionPoint] = []
    event_subscriptions: list[str] = []
    dependencies: list[str] = []
    config_schema: dict[str, Any] = {}
```

#### Layer 2: ABC Enforcement (MESPlugin)

When a plugin is loaded (enabled), the `PluginManager`:

1. Imports the plugin's `plugin.py` module
2. Scans for a class that subclasses `MESPlugin`
3. Instantiates it — Python's ABC enforcement prevents instantiation of classes that have not implemented all abstract methods (`initialize`, `start`, `stop`)
4. Calls `initialize(config)` with the resolved configuration
5. Calls `start()` to begin operation

If any step fails, the plugin is marked with an error and remains unloaded. The server continues operating.

#### Parameter Validation at Install Time

Before a plugin can be enabled, **required parameters** must be provided. The `validate_parameters()` method checks:

```python
def validate_parameters(self, manifest: PluginManifest, parameter_values: dict) -> list[str]:
    errors = []
    for param in manifest.parameters:
        if param.required and param.name not in parameter_values:
            errors.append(f"Required parameter '{param.name}' is missing")
    return errors
```

If any required parameters are missing, the install/enable request is rejected with the list of errors.

#### Config Resolution Pipeline

Plugin configuration is resolved through a **priority merge pipeline** (highest priority wins):

```
1. Parameter defaults (from manifest.yaml → ManifestParameter.default)
2. config_schema defaults (from manifest.yaml → config_schema.properties.*.default)
3. parameter_values (provided at install time via REST/CLI/UI, persisted in DB JSONB)
4. config_overrides (runtime changes via PUT /plugins/{id}/config, persisted in DB JSONB)
```

```python
async def resolve_config_with_overrides(
    self, manifest: PluginManifest,
    parameter_values: dict[str, Any],
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = self._resolve_config(manifest)   # defaults from manifest
    config.update(parameter_values)            # user-provided install values
    if config_overrides:
        config.update(config_overrides)        # runtime overrides
    return config
```

The resolved config dict is what gets passed to `MESPlugin.initialize(config)`.

#### Persistence

Plugin state is persisted in the `plugin_config` database table (§7.6). The `parameter_values` and `config_overrides` are stored as JSONB columns, surviving server restarts. On each startup, the server queries `plugin_config` for rows with `installed=True AND enabled=True` and loads those plugins with their persisted configuration.

### 7.11 Adapter Plugins — Composition Pattern

Integration adapters (ERP, equipment, test equipment) are implemented as plugins using a **composition pattern**: the plugin wraps the adapter library code from `adapters/` and delegates to it.

#### Architecture

```
                    PluginManager                  Plugin Wrapper              Adapter Library
                    ─────────────                  ──────────────              ───────────────
discover_all() ──▶  manifest.yaml    ──────────▶  plugin.py (MESPlugin)  ──▶  adapters/erp/*.py
enable_plugin() ──▶  initialize()     ──────────▶  create adapter instance     (vendor API code)
                     start()          ──────────▶  adapter.connect()
                     stop()           ──────────▶  adapter.disconnect()
                     health_check()   ──────────▶  adapter.health_check()
                     get_adapter()    ──────────▶  return adapter instance
```

**The adapter library** (e.g., `mes.adapters.erp.mock_adapter`) contains the vendor-specific integration logic — HTTP calls, OPC-UA connections, data transformations. It has no knowledge of the plugin framework.

**The plugin wrapper** (e.g., `plugins/system/mock_erp/plugin.py`) implements `MESPlugin`, creates adapter instances in `initialize()`, and exposes them via `get_adapter()`.

#### Example: Mock ERP Adapter Plugin

**manifest.yaml:**
```yaml
id: mock-erp
name: Mock ERP Adapter
version: "1.0.0"
category: erp
origin: system

parameters:
  - name: latency_ms
    type: integer
    description: Simulated latency per API call in milliseconds
    required: false
    default: 0
  - name: failure_rate
    type: number
    description: Probability of simulated failures (0.0 to 1.0)
    required: false
    default: 0.0

extension_points:
  - type: erp_inbound
    name: mock_erp_inbound
  - type: erp_outbound
    name: mock_erp_outbound
```

**plugin.py:**
```python
from mes.adapters.erp.mock_adapter import MockERPInboundAdapter, MockERPOutboundAdapter
from mes.framework.plugin import MESPlugin

class MockERPPlugin(MESPlugin):
    def __init__(self):
        self._inbound = None
        self._outbound = None

    async def initialize(self, config):
        self._inbound = MockERPInboundAdapter(
            latency_ms=config.get("latency_ms", 0),
            failure_rate=config.get("failure_rate", 0.0),
        )
        self._outbound = MockERPOutboundAdapter(
            latency_ms=config.get("latency_ms", 0),
            failure_rate=config.get("failure_rate", 0.0),
        )

    async def start(self):
        await self._inbound.connect()
        await self._outbound.connect()

    async def stop(self):
        await self._inbound.disconnect()
        await self._outbound.disconnect()

    async def health_check(self):
        return (await self._inbound.health_check() and
                await self._outbound.health_check())

    def get_adapter(self):
        return {"erp_inbound": self._inbound, "erp_outbound": self._outbound}
```

#### Current Adapter Plugins

| Plugin ID | Category | Extension Points | Wraps |
|---|---|---|---|
| `mock-erp` | erp | `erp_inbound`, `erp_outbound` | `adapters.erp.mock_adapter` |
| `mock-equipment` | equipment | `equipment_driver` | `adapters.equipment.mock_adapter` |
| `mock-test-equipment` | test-equipment | `test_equipment` | `adapters.test_equipment.mock_adapter` |
| `sap-s4hana-erp` | erp | `erp_inbound`, `erp_outbound` | `adapters.erp.sap_s4hana` |
| `oracle-cloud-erp` | erp | `erp_inbound`, `erp_outbound` | `adapters.erp.oracle_cloud` |
| `opcua-equipment` | equipment | `equipment_driver` | `adapters.equipment.opcua_adapter` |
| `mqtt-equipment` | equipment | `equipment_driver` | `adapters.equipment.mqtt_adapter` |

## 8. Event Bus (EVENT-BUS)

### 8.1 Architecture

The event bus is an in-process async publish/subscribe system. Events are emitted by core modules and plugins, and consumed by event handlers registered by core modules, plugins, and WebSocket clients.

```
┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
│ Core Module  │────▶│   Event Bus   │────▶│ Plugin Handlers  │
│ (emitter)    │     │  (async)      │────▶│ Core Handlers    │
└─────────────┘     │               │────▶│ WebSocket Gateway│
┌─────────────┐     │               │     └─────────────────┘
│ Plugin       │────▶│               │
│ (emitter)    │     └───────┬───────┘
└─────────────┘             │
                   ┌────────▼────────┐
                   │ Event Log Table  │  (optional persistence)
                   └─────────────────┘
```

### 8.2 Event Schema

```python
@dataclass
class MESEvent:
    event_id: str          # UUID
    event_type: str        # Dot-notation topic (e.g., "wip.unit.moved")
    timestamp: datetime    # UTC
    source: str            # Module or plugin ID that emitted
    payload: dict          # Event-specific data
    correlation_id: str    # For tracing related events
```

### 8.3 Event Topics

| Topic Pattern | Emitted By | Payload |
|---|---|---|
| `wip.unit.created` | WIP-TRACK | `{unit_id, order_id, serial_number}` |
| `wip.unit.started` | WIP-TRACK | `{unit_id, step_id, equipment_id}` |
| `wip.unit.completed` | WIP-TRACK | `{unit_id, step_id, result}` |
| `wip.unit.moved` | WIP-TRACK | `{unit_id, from_step_id, to_step_id}` |
| `wip.unit.scrapped` | WIP-TRACK | `{unit_id, step_id, reason}` |
| `wip.unit.held` | WIP-TRACK | `{unit_id, reason}` |
| `wip.lot.*` | WIP-TRACK | (Same pattern as unit events) |
| `production.order.released` | PROD-ORDER | `{order_id, product_id, quantity}` |
| `production.order.started` | PROD-ORDER | `{order_id}` |
| `production.order.completed` | PROD-ORDER | `{order_id, quantity_completed}` |
| `equipment.state.changed` | PHYS-MODEL | `{equipment_id, old_state, new_state, reason}` |
| `production.counter.updated` | PERF-ANALYSIS | `{equipment_id, good_delta, reject_delta, rework_delta, source_plugin}` |
| `performance.oee.calculated` | PERF-ANALYSIS | `{equipment_id, oee}` |
| `quality.test.passed` | QUAL-MGMT | `{test_id, unit_id, result_id}` |
| `quality.test.failed` | QUAL-MGMT | `{test_id, unit_id, result_id}` |
| `quality.nc.created` | QUAL-MGMT | `{nc_id, unit_id, nc_type}` |
| `material.consumed` | MAT-MGMT | `{material_lot_id, unit_id, quantity}` |
| `dispatch.evaluated` | DISPATCH | `{unit_id, strategy, recommendation}` |
| `dispatch.executed` | DISPATCH | `{unit_id, destination_step_id}` |
| `data.collected` | DATA-COLLECT | `{definition_id, unit_id, value}` |
| `plugin.loaded` | PLUGIN-FW | `{plugin_id, version}` |
| `plugin.error` | PLUGIN-FW | `{plugin_id, error}` |
| `auth.login` | AUTH | `{user_id, auth_mode, idp_issuer}` |
| `auth.user.provisioned` | AUTH | `{user_id, idp_subject, idp_issuer}` |
| `auth.roles.synced` | AUTH | `{user_id, old_roles, new_roles}` |

### 8.4 Subscription

```python
# In a core module or plugin:
@event_handler("wip.unit.completed")
async def on_unit_completed(event: MESEvent) -> None:
    # React to unit completion
    ...

# Wildcard subscriptions:
@event_handler("wip.unit.*")
async def on_any_unit_event(event: MESEvent) -> None:
    ...

@event_handler("quality.*")
async def on_any_quality_event(event: MESEvent) -> None:
    ...
```

### 8.5 Future: Distributed Event Bus

For multi-server deployments, the in-process event bus can be replaced with an external message-oriented middleware (MOM) by swapping the transport layer. The `MESEvent` schema and handler interface remain identical.

**Supported MOM Transports:**

| MOM | Python Library | Protocol | Use Case |
|---|---|---|---|
| **Apache Kafka** | `aiokafka` (async) | Kafka native | High-throughput, persistent event streaming, replay |
| **NATS JetStream** | `nats-py` (async) | NATS native | Ultra-lightweight, low-latency |
| **Redis Streams** | `redis.asyncio` | Redis protocol | Simple deployment, adequate for most single-site MES |
| **RabbitMQ** | `aio-pika` (async) | AMQP 0-9-1 | Enterprise messaging, complex routing |
| **ActiveMQ / JMS brokers** | `stomp.py` / `proton` (Qpid) | STOMP / AMQP 1.0 | Environments with existing JMS infrastructure |

**Configuration:**
```python
# .env
MES_EVENT_BUS_TYPE=memory     # "memory" | "kafka" | "nats" | "redis" | "rabbitmq" | "activemq"
MES_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
MES_NATS_URL=nats://nats:4222
MES_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
MES_ACTIVEMQ_HOST=activemq
MES_ACTIVEMQ_PORT=61613       # STOMP port
```

## 9. Integration Adapters

### 9.1 Adapter Architecture (Unified with Plugin Framework — D037)

> **Architectural Decision D037:** All integration adapters are managed through the Plugin
> Framework. There is no separate `BaseAdapter` class or `AdapterFactory`. Adapter libraries
> remain in `adapters/` as importable Python packages; thin plugin wrappers in
> `plugins/system/` implement `MESPlugin` and handle lifecycle. The `PluginManager` is the
> single entry point for adapter discovery, configuration, health checks, and runtime access.

#### Terminology

| Term | Definition |
|---|---|
| **Plugin** | The user-facing management unit. Has a `manifest.yaml`, a `plugin.py`, and is installed/enabled/disabled through the REST API, CLI, or DT-CLIENT. |
| **Adapter** | The implementation library. Contains vendor-specific integration code (HTTP calls, OPC-UA connections, data transformations). Lives in `src/mes/adapters/`. No knowledge of the plugin framework. |
| **Plugin wraps Adapter** | A plugin's `plugin.py` creates adapter instances in `initialize()`, calls `connect()`/`disconnect()` in `start()`/`stop()`, and exposes instances via `get_adapter()`. |

#### No Separate Factory

Before D037, an `AdapterFactory` singleton selected adapters at startup based on environment variables (`MES_ERP_ADAPTER=sap_s4hana`, `MES_EQUIP_ADAPTER=opcua`). This created two parallel management systems — one for plugins, one for adapters — with separate configuration, lifecycle, and health check mechanisms.

After D037, the `PluginManager` handles everything:

```
Before (two systems):                        After (unified):
───────────────────                          ────────────────
AdapterFactory                               PluginManager
  ├── connect_all()                            ├── discover_all()
  ├── disconnect_all()                         ├── load_and_start()
  └── health_check()                           ├── stop_all()
                                               ├── get_adapter_by_type()
PluginManager                                  ├── get_adapter_plugin()
  ├── discover_all()                           ├── adapter_health()
  ├── load_and_start()                         └── enable_plugin() / disable_plugin()
  └── stop_all()
```

#### Adapter Access at Runtime

Core modules that need an adapter instance call `PluginManager` methods:

```python
# Get the ERP inbound adapter (returns the adapter interface instance)
erp_inbound = plugin_manager.get_adapter_by_type("erp_inbound")
if erp_inbound:
    orders = await erp_inbound.sync_production_orders()

# Get the equipment driver adapter
equipment = plugin_manager.get_adapter_by_type("equipment_driver")
if equipment:
    value = await equipment.read_tag("ns=2;s=Oven.Temperature")

# Check health of all adapter plugins
health = await plugin_manager.adapter_health()
# Returns: {"mock-erp": True, "mock-equipment": True}
```

**`get_adapter_by_type(adapter_type)`** scans running plugins for one whose manifest declares an extension point matching the requested type, then calls its `get_adapter()` method. For multi-adapter plugins (ERP with inbound + outbound), `get_adapter()` returns a dict keyed by extension point type.

**`adapter_health()`** calls `health_check()` on every running plugin that declares an adapter extension point type (`erp_inbound`, `erp_outbound`, `equipment_driver`, `test_equipment`). Returns a dict of `{plugin_id: bool}`.

#### Health Endpoint

The server health endpoint reports adapter status through the plugin system:

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "adapters": await plugin_manager.adapter_health(),
    }
```

#### Configuration

Adapter configuration is handled entirely through **plugin parameters** declared in `manifest.yaml` — not through environment variables. Users provide parameter values at install time via the REST API, CLI, or DT-CLIENT. Values are validated, persisted in the `plugin_config` DB table as JSONB, and resolved at startup.

See §7.10 for the config resolution pipeline and §7.11 for the full adapter plugin composition pattern.

### 9.2 ERP Adapters (ERP-IBOUND, ERP-OBOUND)

#### 9.2.1 Overview

The MES integrates with the enterprise ERP system at ISA-95 Level 3↔Level 4 boundaries. The adapter layer abstracts ERP-specific APIs behind a common interface, allowing the end user to swap ERP vendors by implementing a different adapter plugin — no core MES changes required.

**Integration Pattern:**

```
┌──────────────┐     ┌───────────────────────┐     ┌──────────────┐
│              │     │   MES ERP Adapter       │     │              │
│   ERP        │◄───►│   (vendor-specific      │◄───►│  MES Core    │
│   System     │     │    plugin)              │     │  Modules     │
│              │     │                         │     │              │
└──────────────┘     │  ┌───────────────────┐  │     └──────────────┘
                     │  │ ERPInboundAdapter  │  │
                     │  │ ERPOutboundAdapter │  │
                     │  │ ERPTransformLayer  │  │
                     │  └───────────────────┘  │
                     └───────────────────────────┘
```

#### 9.2.2 Inbound Data Flows (ERP → MES)

| Data | ERP Source | MES Destination | Trigger |
|---|---|---|---|
| **Production Orders** | ERP production planning/scheduling | PROD-ORDER module | Scheduled poll or ERP push (webhook/event) |
| **Material Master** | ERP material management | MAT-MGMT module | Scheduled sync or on-demand |
| **Bill of Materials** | ERP product engineering | PROD-DEF module | On production order receipt or scheduled sync |
| **Product/Item Master** | ERP product management | PROD-DEF module | Scheduled sync |
| **Routing** | ERP routing/recipe management | ROUTE-DEF module | On production order receipt |
| **Work Cell Master** | ERP work cell definitions | PHYS-MODEL module | Initial setup + scheduled sync |

#### 9.2.3 Outbound Data Flows (MES → ERP)

| Data | MES Source | ERP Destination | Trigger |
|---|---|---|---|
| **Production Completion** | WIP-TRACK (unit/lot completes final step) | ERP production confirmation | Event: `wip.unit.completed` at final step |
| **Material Consumption** | MAT-MGMT (materials consumed at step) | ERP goods movement (backflush or real-time) | Event: `material.consumed` |
| **Scrap Reporting** | WIP-TRACK (unit/lot scrapped) | ERP scrap posting | Event: `wip.unit.scrapped` |
| **Labor Reporting** | DATA-COLLECT (operator time at step) | ERP time confirmation | Event: `wip.unit.completed` (with labor data) |
| **Equipment Downtime** | PERF-ANALYSIS (equipment state log) | ERP maintenance notification | Event: `equipment.state.changed` (to down) |
| **Quality Results** | QUAL-MGMT (test pass/fail) | ERP quality notification | Event: `quality.test.failed` |
| **WIP Status** | WIP-TRACK (current quantities, status) | ERP WIP reporting | Scheduled or on-demand |

#### 9.2.3a Route & Operation Ownership (ISA-95 Boundary)

A common source of confusion: an MES is primarily concerned with the **physical model** defined
by ISA-95 (sites, areas, lines, work cells, equipment). An ERP, by contrast, deals with
**logical routing and operations** for cost rollups, capacity planning, and standard costing.
So why does this MES store `ProcessRoute` and `RouteStep` entities at all?

**What the ERP owns (Level 4 — out of scope for this MES):**

| Concern | Owner | Notes |
|---|---|---|
| Route creation & version control | ERP | New routes for new products |
| Operation cost rates | ERP | Standard cost per operation |
| Capacity planning (CRP / RCCP) | ERP | Long-horizon resource planning |
| Lead time rollups | ERP | Aggregate manufacturing time |
| Standard cost maintenance | ERP | Cost accounting |

**What the MES needs from routes (Level 3 — in scope):**

| Need | Why | Example |
|---|---|---|
| Execution sequencing | Know *what comes next* for every unit/lot in real time | Unit completes step 20 → engine selects step 30 → dispatches to eligible work cell |
| Data anchoring | Foreign-key target for quality, data, material, NC, history records | `QualityTest.step_id`, `DataPoint.step_id`, `MaterialConsumption.step_id` |
| Outbound mapping | Map completed step back to ERP operation for cost posting | `report_completion(order, operation, qty, labor_hours)` |
| Runtime deviation | Handle rework loops, step skips, alternate routes by equipment | ERP route = plan; MES execution = reality |

**Data flow:**

```
ERP (Level 4)                    MES (Level 3)
─────────────                    ─────────────
Route Master  ──sync_routings()──▶  ROUTE-DEF (local copy)
                                        │
                                   ROUTE-ENGINE (interprets at execution time)
                                        │
Cost Posting  ◀──report_completion()──  WIP-TRACK (actuals per step)
```

The MES **never** creates routes for new products — it receives them from the ERP via
`ERPInboundAdapter.sync_routings()`. In standalone / demo mode (no ERP connected), the
DT-CLIENT route editor (§15.5) provides manual route entry as a substitute.

#### 9.2.4 Abstract ERP Interface

```python
class ERPInboundAdapter(BaseAdapter):
    """Pulls data from ERP into MES."""

    async def sync_production_orders(
        self, since: datetime | None = None
    ) -> list[ProductionOrderDTO]: ...

    async def sync_materials(
        self, since: datetime | None = None
    ) -> list[MaterialDefinitionDTO]: ...

    async def sync_products(
        self, since: datetime | None = None
    ) -> list[ProductDefinitionDTO]: ...

    async def sync_boms(
        self, product_id: str
    ) -> list[BillOfMaterialDTO]: ...

    async def sync_routings(
        self, product_id: str
    ) -> list[ProcessRouteDTO]: ...

    async def sync_work_cells(self) -> list[WorkCellDTO]: ...


class ERPOutboundAdapter(BaseAdapter):
    """Pushes data from MES back to ERP."""

    async def report_completion(
        self, order_id: str, qty_good: int, qty_reject: int,
        step_id: str | None = None
    ) -> ERPConfirmation: ...

    async def report_consumption(
        self, order_id: str, materials: list[MaterialConsumptionDTO]
    ) -> ERPConfirmation: ...

    async def report_scrap(
        self, order_id: str, qty_scrapped: int, reason_code: str
    ) -> ERPConfirmation: ...

    async def report_labor(
        self, order_id: str, operator_id: str, duration_minutes: float
    ) -> ERPConfirmation: ...

    async def report_downtime(
        self, equipment_id: str, duration_minutes: float,
        reason_code: str, started_at: datetime
    ) -> ERPConfirmation: ...

    async def report_quality_result(
        self, order_id: str, test_id: str, result: str,
        details: dict
    ) -> ERPConfirmation: ...


class ERPTransformLayer(ABC):
    """Maps between MES internal models and ERP-specific data formats."""

    @abstractmethod
    def to_production_order(self, erp_data: dict) -> ProductionOrderDTO: ...

    @abstractmethod
    def from_completion(self, completion: CompletionReport) -> dict: ...

    @abstractmethod
    def to_material(self, erp_data: dict) -> MaterialDefinitionDTO: ...

    @abstractmethod
    def from_consumption(self, consumption: ConsumptionReport) -> dict: ...
```

#### 9.2.5 Supported ERP Vendors

Each ERP vendor is implemented as a plugin that provides concrete `ERPInboundAdapter`, `ERPOutboundAdapter`, and `ERPTransformLayer` implementations.

##### SAP S/4HANA & SAP ECC

**Protocol**: OData REST APIs (S/4HANA) / BAPIs via RFC (ECC) / IDocs (async messaging)

**Inbound APIs (ERP → MES):**

| MES Data | SAP S/4HANA API (OData) | SAP ECC API (BAPI) |
|---|---|---|
| Production Orders | `API_PRODUCTION_ORDER_2_SRV` | `BAPI_PRODORD_GET_DETAIL` |
| Material Master | `API_PRODUCT_SRV`, `API_MATERIAL_STOCK_SRV` | `BAPI_MATERIAL_GET_DETAIL` |
| Bill of Materials | `API_BILL_OF_MATERIAL_SRV` | `CSAP_MAT_BOM_READ` |
| Routing | `API_PRODUCTION_ROUTING` | `BAPI_ROUTING_GET` |
| Work Cells | `API_WORK_CELLS_SRV` | `BAPI_WORKCENTER_GET_DETAIL` |

**Outbound APIs (MES → ERP):**

| MES Report | SAP S/4HANA API (OData) | SAP ECC API (BAPI) |
|---|---|---|
| Production Confirmation | `API_PROD_ORDER_CONFIRMATION_2_SRV` | `BAPI_PRODORDCONF_CREATE_TT` |
| Goods Movement (consumption) | `API_MATERIAL_DOCUMENT_SRV` | `BAPI_GOODSMVT_CREATE` |
| Scrap Posting | `API_MATERIAL_DOCUMENT_SRV` (mvt type 551) | `BAPI_GOODSMVT_CREATE` (mvt type 551) |
| Quality Notification | `API_QUALITY_NOTIFICATION_SRV` | `BAPI_QUALNOT_CREATE` |

**Authentication**: OAuth 2.0 (S/4HANA Cloud), SAP Logon Ticket / Basic Auth (on-premise)

**Python Libraries**: `httpx` (OData REST), `pyrfc` (RFC/BAPI for ECC)

##### Oracle Cloud ERP (Fusion)

**Protocol**: Oracle REST API

**Inbound APIs (ERP → MES):**

| MES Data | Oracle Cloud ERP REST API |
|---|---|
| Production Orders (Work Orders) | `GET /manufacturingWorkOrders` |
| Item/Product Master | `GET /itemsV2` |
| Bill of Materials | `GET /workDefinitions/{id}/workDefinitionOperationResources` |
| On-hand Inventory | `GET /inventoryBalances` |
| Work Cells / Resources | `GET /manufacturingResources` |

**Outbound APIs (MES → ERP):**

| MES Report | Oracle Cloud ERP REST API |
|---|---|
| Work Order Completion | `POST /workOrderCompletions` |
| Material Transaction (consumption) | `POST /inventoryMaterialTransactions` |
| Quality Results | `POST /qualityResults` |

**Authentication**: OAuth 2.0 (Oracle Cloud); Oracle Integration Cloud (OIC) for on-premise EBS

**Python Libraries**: `httpx` (REST)

##### Oracle E-Business Suite (EBS) — Legacy

**Protocol**: PL/SQL APIs via Oracle Integration Cloud (OIC) or direct DB connection

| MES Data | Oracle EBS API |
|---|---|
| Work Orders | `WIP_MASSLOAD_PUB` |
| Inventory | `INV_QUANTITY_TREE_PUB` |
| Completions | `WIP_COMPLETION_PUB.complete` |
| Material Issues | `INV_TXN_MANAGER_PUB` |

##### Microsoft Dynamics 365 Finance & Operations

**Protocol**: OData REST APIs (data entities)

**Inbound APIs (ERP → MES):**

| MES Data | D365 F&O OData Entity |
|---|---|
| Production Orders | `ProductionOrders` |
| Released Products | `ReleasedProductsV2` |
| Bill of Materials | `BillOfMaterialsHeaders`, `BillOfMaterialsLines` |
| Route Operations | `RouteOperations` |
| On-hand Inventory | `InventoryOnhandEntities` |

**Outbound APIs (MES → ERP):**

| MES Report | D365 F&O OData Entity / Action |
|---|---|
| Production Completion | `ProductionOrderReportAsFinished` (action) |
| Material Consumption | `ProductionPickingListJournalLines` |
| Route Card (labor) | `ProductionRouteCardJournalLines` |
| Quality Orders | `QualityOrders` |

**Authentication**: OAuth 2.0 via Microsoft Entra ID (Azure AD)

**Python Libraries**: `httpx` (OData REST), `msal` (Microsoft auth)

##### Infor CloudSuite / M3

**Protocol**: Infor ION messaging (BODs) + Infor OS REST APIs

**Data Format**: OAGIS-based Business Object Documents (BODs)

| MES Data | Infor BOD / API |
|---|---|
| Production Orders | `SyncProductionOrder` BOD / REST `M3 MOS450MI` |
| Item Master | `SyncItemMaster` BOD / REST `M3 MMS200MI` |
| Bill of Materials | `SyncBillOfMaterial` BOD |
| Completion Confirmation | `ConfirmProductionOrder` BOD / REST `M3 MOS450MI` |
| Material Consumption | `SyncMaterialIssue` BOD |

**Authentication**: Infor ION API Gateway (OAuth 2.0)

**Python Libraries**: `httpx` (REST), XML libraries for BOD processing

#### 9.2.6 Data Transformation Layer

Each ERP vendor adapter includes a transform layer that maps between ERP-specific data formats and the MES canonical data model (DTOs). This isolates ERP-specific field names, data types, and conventions from core MES logic.

**Example — SAP Production Order transformation:**

```python
class SAPTransformLayer(ERPTransformLayer):
    def to_production_order(self, erp_data: dict) -> ProductionOrderDTO:
        return ProductionOrderDTO(
            erp_reference=erp_data["ManufacturingOrder"],
            product_code=erp_data["Material"],
            quantity_ordered=int(erp_data["TotalQuantity"]),
            planned_start=parse_sap_datetime(erp_data["MfgOrderPlannedStartDate"]),
            planned_end=parse_sap_datetime(erp_data["MfgOrderPlannedEndDate"]),
            priority=int(erp_data.get("MfgOrderPriority", 500)),
            uom=erp_data["ProductionUnit"],
            bom_id=erp_data.get("BillOfMaterial"),
            routing_id=erp_data.get("ProductionRouting"),
        )

    def from_completion(self, completion: CompletionReport) -> dict:
        return {
            "ManufacturingOrder": completion.erp_reference,
            "OrderConfirmationType": "10",  # Final confirmation
            "ConfirmationYieldQuantity": str(completion.qty_good),
            "ConfirmationScrapQuantity": str(completion.qty_reject),
            "ProductionUnit": completion.uom,
        }
```

#### 9.2.7 Integration Patterns

| Pattern | Description | When Used |
|---|---|---|
| **Polling** | MES periodically calls ERP APIs to check for new/changed data | Default for inbound; configurable interval (e.g., every 5 min) |
| **Webhook / Push** | ERP pushes events to MES REST endpoint when data changes | Where ERP supports it (S/4HANA Event Mesh, D365 Business Events) |
| **Message Queue** | Async messaging via middleware (Kafka, RabbitMQ, Infor ION) | High-volume environments; guaranteed delivery |
| **File-based** | CSV/XML file exchange in shared directory | Legacy ERPs; air-gapped environments |
| **Batch Sync** | Full table sync on schedule (nightly, shift start) | Initial load; master data refresh |

**Retry and Error Handling:**
- Failed outbound reports are queued in a `erp_outbound_queue` table with status (pending/sent/failed/retry)
- Exponential backoff retry with configurable max attempts
- Failed messages are logged and surfaced via event: `erp.outbound.failed`
- Admin API endpoint to view and retry failed messages

#### 9.2.8 ERP Adapter Configuration

> **Updated (D037):** ERP adapter configuration is no longer done via environment variables.
> Each ERP adapter is a plugin with its own `manifest.yaml` declaring parameters. Users
> provide values at install time via the REST API, CLI, or DT-CLIENT.

**Example — SAP S/4HANA ERP plugin parameters:**

```yaml
# plugins/system/sap_s4hana_erp/manifest.yaml
id: sap-s4hana-erp
name: SAP S/4HANA ERP Adapter
category: erp
extension_points:
  - type: erp_inbound
    name: sap_s4hana_inbound
  - type: erp_outbound
    name: sap_s4hana_outbound

parameters:
  - name: base_url
    type: string
    description: SAP OData base URL (e.g. https://sap-server/sap/opu/odata/sap)
    required: true
  - name: auth_type
    type: string
    description: "Authentication: oauth2 | basic | api_key"
    required: false
    default: oauth2
  - name: client_id
    type: string
    description: OAuth 2.0 client ID
    required: true
  - name: client_secret
    type: string
    description: OAuth 2.0 client secret
    required: true
    secret: true
  - name: token_url
    type: string
    description: OAuth 2.0 token endpoint URL
    required: true
  - name: poll_interval_sec
    type: integer
    description: Seconds between inbound sync polls
    required: false
    default: 300
  - name: retry_max_attempts
    type: integer
    description: Max retry attempts for failed outbound reports
    required: false
    default: 5
  - name: retry_backoff_sec
    type: integer
    description: Base backoff delay between retries
    required: false
    default: 30
```

**Install via CLI:**
```bash
mes plugin install sap-s4hana-erp \
  --param base_url=https://sap-server.factory.com/sap/opu/odata/sap \
  --param client_id=mes-integration \
  --param client_secret=secret \
  --param token_url=https://sap-server.factory.com/oauth/token
```

**Install via REST API:**
```json
POST /api/v1/plugins/sap-s4hana-erp/install
{
  "parameter_values": {
    "base_url": "https://sap-server.factory.com/sap/opu/odata/sap",
    "client_id": "mes-integration",
    "client_secret": "secret",
    "token_url": "https://sap-server.factory.com/oauth/token"
  }
}
```

Secret parameters are masked in API responses and UI displays.

#### 9.2.9 Mock ERP Adapter

For development, testing, and demo environments:

- **Inbound**: Reads production orders, materials, and BOMs from JSON files in a configurable directory
- **Outbound**: Writes completion/consumption reports to JSON files (verifiable in tests)
- **Simulates latency**: Configurable delay to mimic real ERP response times
- **Simulates failures**: Configurable failure rate to test retry logic

```python
class MockERPInboundAdapter(ERPInboundAdapter):
    async def sync_production_orders(self, since=None) -> list[ProductionOrderDTO]:
        data = await self._read_json("production_orders.json")
        return [self.transform.to_production_order(d) for d in data]

class MockERPOutboundAdapter(ERPOutboundAdapter):
    async def report_completion(self, order_id, qty_good, qty_reject, step_id=None):
        report = {"order_id": order_id, "qty_good": qty_good, "qty_reject": qty_reject}
        await self._write_json("completions.json", report)
        return ERPConfirmation(success=True, erp_doc_number="MOCK-001")
```

#### 9.2.10 ISA-95 / B2MML Alignment

The MES canonical data model (DTOs) aligns with ISA-95 Part 4 object models and can be serialized to B2MML XML for ERP systems that support it:

| MES DTO | ISA-95 Object | B2MML Element |
|---|---|---|
| `ProductionOrderDTO` | Production Schedule / Production Request | `<ProductionSchedule>` |
| `CompletionReport` | Production Performance | `<ProductionPerformance>` |
| `MaterialConsumptionDTO` | Material Consumed Actual | `<MaterialConsumedActual>` |
| `ProductDefinitionDTO` | Product Definition | `<ProductDefinition>` |
| `ProcessRouteDTO` | Process Segment / Operations Schedule | `<ProcessSegment>` |

#### 9.2.11 SAP ERP Simulator (SAP-SIMULATOR)

The SAP ERP Simulator is a **realistic in-memory mock** of SAP S/4HANA that exercises the full ERP integration pipeline without requiring a live SAP system. Unlike the generic mock ERP adapter (§9.2.9) which reads/writes JSON files, the SAP simulator generates data in **native SAP OData V4 format** with authentic field names and runs it through the production `SAPS4HANATransformLayer`.

**Plugin location:** `plugins/system/sap_erp_simulator/`

**Architecture:**

```
plugins/system/sap_erp_simulator/
├── manifest.yaml       # Plugin metadata, extension points, parameters
├── plugin.py           # MESPlugin wrapper — lifecycle, adapter exposure
├── simulator.py        # Inbound + Outbound adapter implementations
├── sap_data.py         # SAP OData V4 data catalog (materials, orders, etc.)
└── transform.py        # Re-exports SAPS4HANATransformLayer from adapters/erp/
```

**Why not call real SAP APIs?**  No SAP system is available during development. The simulator exists to:
1. Validate the full inbound sync path (SAP OData → Transform → MES DTOs)
2. Validate the full outbound report path (MES DTOs → Transform → SAP format → confirmation)
3. Test the ERP REST API endpoints (§6.3) end-to-end via the GUI client (§18)
4. Exercise configurable failure injection and latency simulation

##### Data Catalog

The simulator ships with a realistic SAP factory dataset in `sap_data.py`:

| Data Type | Count | SAP Fields Used | Example |
|---|---|---|---|
| Materials (MARA) | 20 | `Material`, `MaterialName`, `MaterialType`, `BaseUnit`, `IndustrySector` | `RM-STEEL-001`, `RM-COPPER-002` |
| Products (MARA FG) | 3 | `Material`, `MaterialName`, `MaterialType`, `BaseUnit` | `FG-WIDGET-100`, `FG-GADGET-300` |
| BOMs (STKO/STPO) | 3 | `BillOfMaterial`, `BillOfMaterialVariant`, `BOMItemNodeNumber`, `BOMItemQuantity` | 7-material widget BOM |
| Routings (PLKO/PLPO) | 3 | `Routing`, `RoutingSequence`, `Operation`, `WorkCenter`, `OperationStandardTextCode` | 5-step widget routing |
| Production Orders (AUFK) | 5 | `ManufacturingOrder`, `Material`, `MfgOrderPlannedTotalQty`, `OrderType` | `000001000100` (PP01) |
| Work Centers (CRHD) | 4 | `WorkCenter`, `WorkCenterText`, `CostCenter`, `WorkCenterCategoryCode` | `WC-ASSY-01`, `WC-TEST-01` |

All field names match SAP S/4HANA OData V4 API entity properties. The transform layer converts them bidirectionally to MES canonical DTOs.

##### Data Flow — Inbound Sync (ERP → MES)

```
┌────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌────────────┐
│  GUI Client    │     │  MES REST API        │     │  SAP Simulator      │     │ Transform  │
│  (port 5174)   │     │  (port 8000)         │     │  (in-memory)        │     │ Layer      │
│                │     │                      │     │                     │     │            │
│  Click "Sync   │────▶│  POST /api/v1/erp/   │────▶│  sync_materials()   │────▶│ SAP OData  │
│  Materials"    │     │  sync/materials       │     │  returns SAP_       │     │ → MES DTO  │
│                │◀────│                      │◀────│  MATERIALS list     │◀────│            │
│  Display table │     │  list_response(dtos) │     │                     │     │            │
└────────────────┘     └──────────────────────┘     └─────────────────────┘     └────────────┘
                                 │
                                 │  plugin_manager.get_adapter_by_type("erp_inbound")
                                 │  returns SAPSimulatorInboundAdapter instance
                                 ▼
```

**Step-by-step:**
1. GUI client sends `POST /api/v1/erp/sync/materials` to the MES server
2. Route handler calls `plugin_manager.get_adapter_by_type("erp_inbound")` to get the active adapter
3. Adapter's `sync_materials()` reads from `SAP_MATERIALS` dict (in-memory, no network)
4. `SAPS4HANATransformLayer.to_material()` converts each SAP OData record to `MaterialDefinitionDTO`
5. DTOs are returned through the REST API envelope as JSON

##### Data Flow — Outbound Report (MES → ERP)

```
┌────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌────────────┐
│  GUI Client    │     │  MES REST API        │     │  SAP Simulator      │     │ Transform  │
│  (port 5174)   │     │  (port 8000)         │     │  (in-memory)        │     │ Layer      │
│                │     │                      │     │                     │     │            │
│  Submit form:  │────▶│  POST /api/v1/erp/   │────▶│  report_completion()│────▶│ MES DTO →  │
│  order, qty,   │     │  report/completion    │     │  validate order     │     │ SAP BAPI   │
│  reject        │◀────│                      │◀────│  generate SAP doc#  │◀────│ payload    │
│  Show SAP doc# │     │  success_response()  │     │  store confirmation │     │            │
└────────────────┘     └──────────────────────┘     └─────────────────────┘     └────────────┘
```

**Step-by-step (completion report example):**
1. GUI client sends `POST /api/v1/erp/report/completion` with `{order_id, qty_good, qty_reject}`
2. Route handler calls `plugin_manager.get_adapter_by_type("erp_outbound")`
3. Adapter validates `order_id` exists in the known order book
4. `SAPS4HANATransformLayer.from_completion()` converts to SAP BAPI payload format
5. Simulator generates a SAP-style document number (e.g., `4900000001` for confirmations)
6. Confirmation record is stored in-memory (`adapter.confirmations` list)
7. `ERPConfirmation(success=True, erp_doc_number="4900000001")` returned to client

##### SAP Document Number Series

The simulator mimics SAP's document numbering conventions:

| Report Type | SAP Transaction | Number Pattern | Example |
|---|---|---|---|
| Production Completion | CO11N | `49XXXXXXXX` (10-digit) | `4900000001` |
| Material Consumption | MIGO 261 | `49XXXXXXXX` (10-digit) | `4900000001` |
| Scrap Report | MIGO 531 | `49XXXXXXXX` (10-digit) | `4900000001` |
| Labor Time | CATS | `CAT-XXXXXXXXXX` | `CAT-0000000001` |
| Downtime | PM Notification M2 | `PM-XXXXXXXXXX` | `PM-0000000001` |
| Quality Result | QM Recording | `QM-XXXXXXXXXX` | `QM-0000000001` |

##### Plugin Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `plant` | string | `"1000"` | SAP plant code (Werk) |
| `company_code` | string | `"1000"` | SAP company code (Buchungskreis) |
| `latency_ms` | integer | `0` | Simulated API latency per call (milliseconds) |
| `failure_rate` | number | `0.0` | Probability of simulated errors (0.0–1.0) |

##### How to Run

```bash
# 1. Install and enable the SAP simulator plugin
mes plugin install sap-erp-simulator
mes plugin enable sap-erp-simulator

# 2. Start the MES server
cd server
$env:MES_AUTH_MODE = "none"
uvicorn mes.main:app --reload --port 8000

# 3. Start the ERP Simulator GUI (separate terminal)
cd clients/erp_simulator
npm run dev
# → opens http://localhost:5174

# 4. Use the GUI:
#    - Dashboard: check adapter health (green = connected)
#    - Inbound tabs: click "Sync" to pull SAP data into MES
#    - Outbound tabs: fill forms to post reports back to SAP
#    - Confirmations: view all SAP document numbers generated
```

Or via REST API directly:
```bash
# Health check
curl http://localhost:8000/api/v1/erp/health

# Sync materials
curl -X POST http://localhost:8000/api/v1/erp/sync/materials

# Report completion
curl -X POST http://localhost:8000/api/v1/erp/report/completion \
  -H 'Content-Type: application/json' \
  -d '{"order_id": "000001000100", "qty_good": 95, "qty_reject": 5}'

# View confirmations
curl http://localhost:8000/api/v1/erp/confirmations
```

### 9.3 Equipment Adapter (EQUIP-INTFC)

Communicates with production equipment (PLCs, microcontrollers, sensors) and collects real-time data for WIP tracking, data collection, and equipment state monitoring.

#### 9.3.1 Supported Protocols and Libraries

| Protocol | Python Library | Async | Use Case | License |
|---|---|---|---|---|
| **OPC-UA** | `asyncua` | Yes (native) | PLCs, SCADA, DCS — primary industrial standard | LGPL |
| **MQTT** | `aiomqtt` | Yes | IoT sensors, lightweight telemetry, edge devices | BSD |
| **Modbus TCP** | `pymodbus` | Yes | Legacy PLCs, motor drives, power meters | BSD |
| **HTTP/REST** | `httpx` | Yes | Modern smart equipment, IIoT gateways | BSD |
| **ZeroMQ** | `pyzmq` | Yes | Brokerless direct equipment-to-MES, low-latency | BSD |

##### OPC-UA (Primary Industrial Protocol)

OPC-UA (Unified Architecture) is the industry-standard protocol for equipment communication in manufacturing. The `asyncua` library provides:

- **Client mode**: Connect to PLC/SCADA OPC-UA servers, read/write tags, browse node trees
- **Subscription mode**: Subscribe to tag value changes with configurable sampling intervals
- **Security**: Supports OPC-UA security policies (Basic256Sha256, certificate-based auth)
- **Discovery**: Browse server address space to discover available tags
- **Data types**: Full OPC-UA data type support (scalars, arrays, structures, enums)

```python
# OPC-UA usage example
async with OPCUAEquipmentAdapter("opc.tcp://plc-01.factory.com:4840") as adapter:
    # Read a tag
    temperature = await adapter.read_tag("ns=2;s=Oven.Temperature")

    # Subscribe to tag changes
    await adapter.subscribe_tag(
        "ns=2;s=Oven.Temperature",
        callback=on_temperature_change,
        sampling_interval_ms=500
    )

    # Write a setpoint
    await adapter.write_tag("ns=2;s=Oven.Setpoint", 180.0)
```

##### MQTT (IoT / Edge Devices)

MQTT is a lightweight publish/subscribe protocol widely used for IoT sensors and edge computing:

- **Topic-based**: Equipment publishes data to topics (e.g., `factory/line-1/oven-01/temperature`)
- **QoS levels**: 0 (at most once), 1 (at least once), 2 (exactly once)
- **Retained messages**: Last known equipment state available immediately on subscribe
- **MQTT 5.0**: Shared subscriptions for load balancing, message expiry, user properties

##### Message-Oriented Middleware (MOM) for Equipment Integration

In environments where equipment data flows through enterprise middleware rather than direct connections:

| MOM / JMS Broker | Python Access | Protocol | Notes |
|---|---|---|---|
| **Apache Kafka** | `aiokafka` (async) | Kafka native | High-throughput equipment telemetry streaming |
| **RabbitMQ** | `aio-pika` (async) | AMQP 0-9-1 | Equipment events via message queues |
| **Apache ActiveMQ Classic** | `stomp.py` | STOMP | JMS broker accessible via STOMP text protocol |
| **Apache ActiveMQ Artemis** | `proton` (Apache Qpid) | AMQP 1.0 | JMS broker accessible via AMQP 1.0 |
| **IBM MQ** | `proton` or `httpx` | AMQP 1.0 / REST | Enterprise JMS environments |
| **TIBCO EMS** | `stomp.py` or `httpx` | STOMP / REST | Enterprise JMS environments |
| **Oracle AQ** | `oracledb` | DB connector | Oracle-based messaging |

> **Note on JMS**: JMS is a Java API specification, not a wire protocol. Python clients access JMS brokers via STOMP or AMQP 1.0 protocols, which all major JMS brokers support. This is well-established and production-proven.

#### 9.3.2 Abstract Equipment Interface

```python
class EquipmentAdapter(BaseAdapter):
    """Abstract interface for equipment communication."""

    @abstractmethod
    async def read_tag(self, tag_name: str) -> TagValue: ...

    @abstractmethod
    async def write_tag(self, tag_name: str, value: Any) -> None: ...

    @abstractmethod
    async def subscribe_tag(
        self, tag_name: str, callback: Callable, interval_ms: int = 1000
    ) -> SubscriptionHandle: ...

    @abstractmethod
    async def unsubscribe(self, handle: SubscriptionHandle) -> None: ...

    @abstractmethod
    async def get_equipment_state(self) -> EquipmentState: ...

    @abstractmethod
    async def browse_tags(self, root: str | None = None) -> list[TagInfo]: ...


class MOMEquipmentAdapter(BaseAdapter):
    """Abstract interface for equipment data via message-oriented middleware."""

    @abstractmethod
    async def subscribe_topic(
        self, topic: str, callback: Callable
    ) -> SubscriptionHandle: ...

    @abstractmethod
    async def publish(
        self, topic: str, payload: dict
    ) -> None: ...

    @abstractmethod
    async def consume_queue(
        self, queue_name: str, callback: Callable
    ) -> None: ...
```

**Data types:**
```python
@dataclass
class TagValue:
    tag_name: str
    value: Any
    quality: str          # "good" | "bad" | "uncertain"
    timestamp: datetime   # Source timestamp from equipment
    data_type: str        # "float" | "int" | "bool" | "string" | "array"

@dataclass
class TagInfo:
    tag_name: str
    data_type: str
    access: str           # "read" | "write" | "readwrite"
    description: str
```

#### 9.3.3 Equipment Adapter Configuration

> **Updated (D037):** Equipment adapter configuration is no longer done via environment
> variables. Each equipment adapter is a plugin with parameters declared in `manifest.yaml`.

**Example — OPC-UA Equipment plugin parameters:**

```yaml
# plugins/system/opcua_equipment/manifest.yaml
id: opcua-equipment
name: OPC-UA Equipment Adapter
category: equipment
extension_points:
  - type: equipment_driver
    name: opcua_equipment

parameters:
  - name: endpoint_url
    type: string
    description: OPC-UA server endpoint (e.g. opc.tcp://plc-01:4840)
    required: true
  - name: namespace_index
    type: integer
    description: Default namespace index for tag resolution
    required: false
    default: 2
  - name: equipment_id
    type: string
    description: Equipment identifier for state tracking
    required: true
  - name: state_tag
    type: string
    description: Tag name to read for equipment state
    required: false
  - name: state_model_id
    type: string
    description: >
      State model for transitions driven by state_tag changes
      (e.g. "packml", "semi_e10"). Integer values are mapped via
      OPC 40083 PackML enum by default. Requires state_tag.
    required: false
  - name: security_mode
    type: string
    description: "Security mode: none, sign, or sign_and_encrypt"
    required: false
    default: none
  - name: auth_type
    type: string
    description: "Authentication: anonymous, username, or certificate"
    required: false
    default: anonymous
  - name: username
    type: string
    description: Username for username authentication
    required: false
  - name: password
    type: string
    description: Password for username authentication
    required: false
    secret: true
```

**Example — MQTT Equipment plugin parameters:**

```yaml
# plugins/system/mqtt_equipment/manifest.yaml
id: mqtt-equipment
name: MQTT Equipment Adapter
category: equipment
extension_points:
  - type: equipment_driver
    name: mqtt_equipment

parameters:
  - name: broker_url
    type: string
    description: MQTT broker URL (e.g. mqtt://broker.factory.com:1883)
    required: true
  - name: topic_prefix
    type: string
    description: Topic prefix for equipment data (e.g. factory/line-1)
    required: false
    default: "factory"
  - name: qos
    type: integer
    description: MQTT Quality of Service level (0, 1, or 2)
    required: false
    default: 1
  - name: username
    type: string
    description: MQTT broker username
    required: false
  - name: password
    type: string
    description: MQTT broker password
    required: false
    secret: true
```

**Install via REST API:**
```json
POST /api/v1/plugins/opcua-equipment/install
{
  "parameter_values": {
    "endpoint_url": "opc.tcp://plc-01.factory.com:4840",
    "equipment_id": "OVEN-001",
    "state_tag": "ns=2;s=MachineState",
    "state_model_id": "packml"
  }
}
```

##### OPC 40083 State-Change Wiring

When `state_tag` and `state_model_id` are both configured, the OPC-UA plugin
subscribes to OPC-UA data-change notifications on the tag at `start()` and
feeds each value change into `EquipmentStateEngine.transition_equipment()`.

1. **Integer values** — mapped via `PACKML_INT_TO_STATE` (OPC 40083 §6):

| Int | State | Int | State | Int | State |
|-----|-------|-----|-------|-----|-------|
| 0 | Undefined | 6 | Execute | 12 | Unholding |
| 1 | Clearing | 7 | Stopping | 13 | Suspending |
| 2 | Stopped | 8 | Aborting | 14 | Unsuspending |
| 3 | Starting | 9 | Aborted | 15 | Resetting |
| 4 | Idle | 10 | Holding | 16 | Completing |
| 5 | Suspended | 11 | Held | 17 | Complete |

2. **String values** — forwarded to the engine as-is (for PLCs that publish
   state names instead of integers).
3. **Duplicate suppression** — consecutive identical states are ignored.
4. **Error isolation** — engine exceptions are logged but never crash the
   OPC-UA subscription.

Data flow:
```
PLC CurrentState tag  ──OPC-UA subscription──►  _SubHandler.datachange_notification()
    ──TagValue callback──►  OPCUAEquipmentPlugin._on_state_change()
    ──int→name lookup──►  EquipmentStateEngine.transition_equipment(session, equip_id, state)
    ──validates & persists──►  EquipmentStateLog row + equipment.state.changed event
```

#### 9.3.4 Mock Equipment Adapter

For development, testing, and demo environments:

- **In-memory tag store** with configurable initial values
- **Simulated state changes**: Tags change on a configurable schedule (e.g., temperature fluctuates ±2°C every second)
- **Configurable latency**: Mimics real equipment response times
- **Configurable failures**: Simulates communication errors at a configurable rate
- **Record/replay**: Can replay recorded real equipment data from JSON files

```python
class MockEquipmentAdapter(EquipmentAdapter):
    async def read_tag(self, tag_name: str) -> TagValue:
        value = self._tag_store[tag_name] + random.gauss(0, self._noise)
        return TagValue(
            tag_name=tag_name, value=value,
            quality="good", timestamp=datetime.utcnow(), data_type="float"
        )
```

### 9.4 Test Equipment Adapter (TEST-INTFC)

Collects test results from quality/test equipment (e.g., coordinate measuring machines, electrical testers, optical inspection systems).

**Supported protocols:** Same as equipment adapter (OPC-UA, MQTT, REST, MOM). Test equipment typically exposes results via:
- **File drop**: Equipment writes result file (CSV/XML) to shared directory
- **REST API**: Modern test equipment serves results via HTTP
- **OPC-UA**: Inline test equipment integrated into PLC network
- **MOM**: Test results published to message queue/topic

**Interface:**
```python
class TestEquipmentAdapter(BaseAdapter):
    """Abstract interface for test equipment data collection."""

    async def get_test_result(self, test_id: str) -> TestResultDTO: ...

    async def subscribe_results(
        self, callback: Callable[[TestResultDTO], None]
    ) -> SubscriptionHandle: ...

    async def get_test_status(self, equipment_id: str) -> str: ...


class FileDropTestAdapter(TestEquipmentAdapter):
    """Watches a directory for test result files."""

    async def watch_directory(
        self, path: str, pattern: str = "*.csv"
    ) -> None: ...
```

**Mock implementation:** Generates random test results within configurable pass/fail distributions and measurement ranges.

### 9.5 Production Counter Data Collection

Production counters track good, rejected, and rework quantities per equipment per shift for OEE Performance and Quality calculations. The counter data collection framework provides a delta-based increment service and two reference plugin implementations.

#### 9.5.1 Architecture

```
Equipment (PLC / Edge Device)
    │
    ├── OPC-UA PackTags (OPC 30050)             ──► packml_opcua_counters plugin
    │   Admin.ProdProcessedCount[n]                    │
    │   Admin.ProdDefectiveCount[n]                    │
    │                                                  │
    └── MQTT topic                               ──► mqtt_counters plugin
        mes/equipment/{equipment_id}/counters          │
        {"good_delta": 10, "reject_delta": 1}          │
                                                       ▼
                               ProductionCounterService.increment_counter()
                                       │
                                       ├── Atomic upsert (equipment + shift_date + order)
                                       ├── Emits: production.counter.updated event
                                       └── Writes: production_counters table
```

#### 9.5.2 Core Service

`ProductionCounterService.increment_counter()` is the single entry point for all counter updates. It:

1. Looks up (or creates) a `ProductionCounter` row keyed by `(equipment_id, shift_date, order_id)`
2. Atomically adds the delta values (`good_delta`, `reject_delta`, `rework_delta`)
3. Publishes a `production.counter.updated` event with the deltas and source plugin identifier
4. Returns the updated counter row

The REST endpoint `POST /api/v1/performance/counters/increment` accepts a `CounterIncrementRequest` (equipment_id, good_delta, reject_delta, rework_delta, source) for manual or external integration use.

#### 9.5.3 PackML OPC-UA PackTags Plugin (`packml-opcua-counters`)

| Property | Value |
|---|---|
| **Plugin ID** | `packml-opcua-counters` |
| **Category** | `performance` |
| **Extension Point** | `data_processor` |
| **Protocol** | OPC-UA (asyncua library) |
| **Standard** | OPC 30050 — PackML PackTags |
| **Library** | `pip install mes-ai[opcua]` |

**OPC 30050 PackTags used:**

| PackTag | Type | Description |
|---|---|---|
| `Admin.ProdProcessedCount[n]` | UInt32 | Cumulative good units produced (per material index) |
| `Admin.ProdDefectiveCount[n]` | UInt32 | Cumulative defective/rejected units |
| `Admin.CurMachSpeed` | Float | Current machine speed (for future Performance OEE) |
| `Admin.MachDesignSpeed` | Float | Design speed (for future Performance OEE) |

**Delta detection:** The plugin stores the last-known absolute counter value for each equipment. When a data change notification arrives, it computes `delta = new_value - last_value` and calls `increment_counter()` only when the delta is positive. This handles:
- Counter resets (new value < old value → re-baseline, no negative delta)
- No-change notifications (delta = 0 → skip)
- First read (no baseline → store value, no increment)

**Equipment discovery:** At startup the plugin queries all active equipment with an `opcua_endpoint` in their `capabilities` JSON field. Expected capability keys:

| Key | Type | Default | Description |
|---|---|---|---|
| `opcua_endpoint` | string | *(required)* | `opc.tcp://10.0.0.1:4840` |
| `opcua_namespace` | int | `2` | OPC-UA namespace index |
| `opcua_good_node` | string | `Admin.ProdProcessedCount` | Override good count node path |
| `opcua_reject_node` | string | `Admin.ProdDefectiveCount` | Override reject count node path |

**Parameters** (configured via plugin install):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `poll_interval_sec` | int | `5` | Fallback polling interval when subscriptions fail |
| `subscription_interval_ms` | int | `1000` | OPC-UA publishing/sampling interval |

#### 9.5.4 MQTT Counter Plugin (`mqtt-counters`)

| Property | Value |
|---|---|
| **Plugin ID** | `mqtt-counters` |
| **Category** | `performance` |
| **Extension Point** | `data_processor` |
| **Protocol** | MQTT v3.1.1 / v5 (aiomqtt library) |
| **Library** | `pip install mes-ai[mqtt]` |

**Topic layout:**
```
mes/equipment/{equipment_id}/counters
```

The `equipment_id` (UUID) is extracted from the topic path. The `+` wildcard in the subscription pattern matches any equipment.

**Expected JSON payload:**
```json
{
    "good_delta": 10,
    "reject_delta": 1,
    "rework_delta": 0,
    "order_id": "optional-uuid-string"
}
```

All delta fields must be ≥ 0. Messages with all-zero deltas are ignored. Invalid JSON or non-object payloads are logged and skipped.

**Parameters** (configured via plugin install):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `broker_host` | string | `localhost` | MQTT broker hostname |
| `broker_port` | int | `1883` | MQTT broker port |
| `topic_pattern` | string | `mes/equipment/+/counters` | Subscription topic pattern |
| `username` | string | *(empty)* | Broker authentication username |
| `password` | string | *(empty)* | Broker authentication password |
| `qos` | int | `1` | MQTT QoS level (0, 1, or 2) |

#### 9.5.5 Adding Custom Counter Plugins

End users can implement additional counter collection plugins for other protocols (e.g., Modbus, REST polling, file drop) by:

1. Creating a plugin directory under `plugins/user/`
2. Declaring `extension_points: [{type: data_processor}]` in `manifest.yaml`
3. Implementing `MESPlugin.start()` to begin data collection
4. Calling `ProductionCounterService.increment_counter()` with appropriate deltas
5. Implementing `MESPlugin.stop()` to clean up connections/tasks

The `packml_opcua_counters` and `mqtt_counters` plugins serve as reference implementations.

## 10. Dispatching Engine (DISPATCH)

### 10.1 Overview

The dispatching engine determines where a unit or lot moves next after completing a step. It supports both manual and automated dispatching.

### 10.2 Dispatch Strategies

| Strategy | Type | Description |
|---|---|---|
| **manual** | Built-in | Operator selects destination from valid options |
| **first_available** | Built-in | Route to first available equipment at next step |
| **shortest_queue** | Built-in | Route to equipment with shortest queue |
| **round_robin** | Built-in | Distribute evenly across available equipment |
| **capability_match** | Built-in | Route based on equipment capability and product requirements |
| **custom** | Plugin | User-defined strategy via plugin extension point |

### 10.3 Dispatch Flow

```
Unit completes step
       │
       ▼
  Get next step(s) from route
       │
       ▼
  Get eligible equipment at next step(s)
       │
       ▼
  Apply dispatch strategy
       │
       ▼
  ┌────┴────┐
  │ Manual? │──Yes──▶ Present options to operator → Wait for selection
  │         │
  └────┬────┘
       │ No (automated)
       ▼
  Execute dispatch decision
       │
       ▼
  Emit dispatch.executed event
       │
       ▼
  Move unit/lot to destination
```

## 11. Authentication & Authorization (AUTH)

### 11.1 Authentication — OpenID Connect (OIDC) SSO

The MES delegates authentication to an external Identity Provider (IdP) via the **OpenID Connect** standard. The MES server never stores passwords.

**Supported Identity Providers** (any OIDC-compliant IdP):

| Provider | Type | Common In |
|---|---|---|
| **Microsoft Entra ID** (Azure AD) | Cloud | Microsoft-heavy enterprises, Office 365 shops |
| **Keycloak** | Self-hosted (open source) | On-premise factories, air-gapped environments |
| **WSO2 Identity Server** | Self-hosted (open source) | Manufacturing, integration-heavy environments |
| **Okta** / **Auth0** | Cloud | Mid-to-large enterprises, SaaS-heavy environments |
| **PingIdentity / PingFederate** | Hybrid | Large enterprises, legacy SAML environments |
| **AWS Cognito** | Cloud | AWS-hosted deployments |
| **Google Workspace** | Cloud | Google-centric organizations |
| **ADFS** | Self-hosted | Windows Server environments, legacy Microsoft shops |

**Authentication Flow** (OIDC Authorization Code with PKCE):

```
User opens MES client (browser)
       │
       ▼
GET /api/v1/auth/login → 302 redirect to IdP authorization endpoint
       │
       ▼
User authenticates at IdP (password, MFA, smart card, biometric, etc.)
       │
       ▼
IdP redirects to GET /api/v1/auth/callback?code=...&state=...
       │
       ▼
MES server exchanges authorization code for ID token + access token
       │
       ▼
MES server reads user claims (sub, name, email, groups) from ID token
       │
       ▼
JIT (Just-In-Time) user provisioning:
  - If user (idp_subject + idp_issuer) exists → update last_login
  - If user is new → create User record from token claims
       │
       ▼
Map IdP groups → MES roles (via IdPGroupMapping table)
       │
       ▼
Issue MES-internal JWT (short-lived) for subsequent API calls
```

**Token Details:**

| Token | Lifetime | Purpose |
|---|---|---|
| MES Access Token (JWT) | 15 minutes | API authorization (`Authorization: Bearer <token>`) |
| MES Refresh Token | 7 days | Obtain new access token without re-authenticating |
| IdP ID Token | per IdP config | Used once during callback to read claims; not stored |

**Key Design Points:**
- The MES server is an **OIDC Relying Party** — it only validates tokens, never issues them at the IdP level
- **PKCE** (Proof Key for Code Exchange) is required for public clients (browser SPAs)
- **Headless clients** (equipment adapters, automation) use OIDC **Client Credentials** flow (machine-to-machine)
- **Python library**: `authlib` — full OIDC client, async-compatible, well-maintained

### 11.2 Local Authentication (Development/Fallback)

For development, testing, and air-gapped environments where no IdP is available:

- **Mode**: `MES_AUTH_MODE=local` in configuration
- **Method**: Username/password with bcrypt hash, stored in `User.hashed_password` (nullable field, only populated in local mode)
- **Login**: `POST /api/v1/auth/local/login` with `{username, password}` → MES JWT
- **Disabled in production by default** — must be explicitly enabled via configuration

### 11.3 Authorization

- **Model**: Role-Based Access Control (RBAC)
- **Granularity**: Per-endpoint — every REST API endpoint declares its required permission(s)
- **Enforcement**: FastAPI dependency injection — routes declare required permissions; unauthorized requests receive HTTP 403
- **Role mapping**: Configurable IdP group → MES role mapping via `IdPGroupMapping` table and `/api/v1/auth/group-mappings` API
- **JIT role sync**: On every login, user's MES roles are re-synced from IdP group claims, ensuring changes in the IdP are immediately reflected

**Endpoint-Level Enforcement Example:**

```python
@router.post("/api/v1/units/{unit_id}/move")
async def move_unit(
    unit_id: UUID,
    current_user: User = Depends(require_permission("wip.unit.move"))
):
    ...
# A user without "wip.unit.move" permission gets HTTP 403 Forbidden
```

#### 11.3.1 Permission Structure

Permissions follow the pattern: **`module.resource.action`**

| Component | Values |
|---|---|
| **module** | `physical_model`, `product_def`, `production`, `wip`, `dispatch`, `material`, `quality`, `data_collect`, `performance`, `plugin`, `auth` |
| **resource** | `site`, `area`, `line`, `work_cell`, `equipment`, `product`, `route`, `order`, `unit`, `lot`, `test`, `nc`, `user`, `role`, etc. |
| **action** | `read`, `create`, `update`, `delete`, `execute` |

**Wildcard matching** is supported at any level:
- `*` — all permissions (admin only)
- `wip.*` — all WIP operations
- `*.read` — read access to everything
- `quality.*` — all quality operations

#### 11.3.2 Full Permission Map

| Module | Permission | Description | Endpoints Guarded |
|---|---|---|---|
| **PHYS-MODEL** | `physical_model.read` | View sites, areas, lines, work cells, equipment | All GET endpoints |
| | `physical_model.create` | Create physical model entities | All POST endpoints |
| | `physical_model.update` | Update entities, change equipment status | All PUT/PATCH endpoints |
| | `physical_model.delete` | Soft-delete entities | All DELETE endpoints |
| **PROD-DEF** | `product_def.read` | View products, BOMs, routes, steps | All GET endpoints |
| | `product_def.create` | Create products, routes, BOMs | All POST endpoints |
| | `product_def.update` | Modify products, routes, BOMs | All PUT endpoints |
| | `product_def.delete` | Soft-delete product definitions | All DELETE endpoints |
| **PROD-ORDER** | `production.order.read` | View production orders | GET endpoints |
| | `production.order.create` | Create production orders | POST create |
| | `production.order.update` | Update order details | PUT endpoints |
| | `production.order.execute` | Release, complete, close orders | POST release/complete |
| **WIP-TRACK** | `wip.read` | View units, lots, history, genealogy | All GET endpoints |
| | `wip.unit.create` | Create units | POST create |
| | `wip.unit.move` | Start, complete, move units | POST start/complete/move |
| | `wip.unit.hold` | Place/release hold on units | POST hold/release-hold |
| | `wip.unit.scrap` | Scrap units | POST scrap |
| | `wip.lot.*` | Same pattern for lots | Lot endpoints |
| **DISPATCH** | `dispatch.read` | View dispatch queues, strategies | GET endpoints |
| | `dispatch.execute` | Evaluate and execute dispatch decisions | POST evaluate/execute |
| **MAT-MGMT** | `material.read` | View materials, lots, consumption | All GET endpoints |
| | `material.create` | Create material definitions, lots | POST endpoints |
| | `material.update` | Update materials, lots | PUT endpoints |
| | `material.consume` | Record material consumption | POST consume |
| **QUAL-MGMT** | `quality.read` | View tests, results, non-conformances | All GET endpoints |
| | `quality.test.create` | Define quality tests | POST test definitions |
| | `quality.result.record` | Record test results | POST test results |
| | `quality.nc.create` | Create non-conformances | POST non-conformances |
| | `quality.nc.resolve` | Resolve/disposition non-conformances | PUT non-conformances |
| **DATA-COLLECT** | `data_collect.read` | View data definitions, data points | GET endpoints |
| | `data_collect.define` | Create data definitions | POST definitions |
| | `data_collect.record` | Collect data points | POST collect/collect-batch |
| **PERF-ANALYSIS** | `performance.read` | View OEE, states, counters | GET endpoints |
| | `performance.record` | Record equipment states, counters | POST endpoints |
| **PLUGIN-FW** | `plugin.read` | View installed plugins, config | GET endpoints |
| | `plugin.manage` | Install, uninstall, enable, disable, configure | POST/DELETE/PUT endpoints |
| **AUTH** | `auth.user.read` | View user list | GET users |
| | `auth.user.manage` | Create/update users | POST/PUT users |
| | `auth.role.manage` | Create/update roles, group mappings | POST/PUT roles, group-mappings |

#### 11.3.3 Default Roles

| Role | Permissions | Typical User |
|---|---|---|
| **admin** | `*` (all permissions) | System administrator, IT |
| **engineer** | `physical_model.*`, `product_def.*`, `production.order.*`, `dispatch.*`, `material.*`, `quality.*`, `data_collect.*`, `performance.*`, `wip.read`, `plugin.read` | Process engineer, manufacturing engineer |
| **operator** | `wip.*`, `dispatch.read`, `dispatch.execute`, `data_collect.read`, `data_collect.record`, `quality.result.record`, `quality.nc.create`, `material.read`, `material.consume`, `performance.read`, `physical_model.read`, `product_def.read`, `production.order.read` | Shop floor operator |
| **viewer** | `*.read` (all read permissions) | Management, reporting, auditors |

#### 11.3.4 Example Scenarios

1. **Operator scans a unit at a work cell**: Needs `wip.unit.move` — allowed. Tries to modify a production route — needs `product_def.update` — **denied (403)**.
2. **Engineer creates a new product definition**: Needs `product_def.create` — allowed. Tries to install a plugin — needs `plugin.manage` — **denied (403)**.
3. **Headless equipment client reporting data**: Uses service account with only `data_collect.record` + `wip.unit.move` + `performance.record`.
4. **Viewer dashboard querying OEE**: Needs `performance.read` — allowed. Tries to scrap a unit — needs `wip.unit.scrap` — **denied (403)**.

#### 11.3.5 Plugin Permissions

Plugins participate in the same RBAC permission system as core modules. No separate mechanism is needed.

**Declaration:** Plugins declare custom permissions in `manifest.yaml` under the `permissions` key (see §7.2):

```yaml
# manifest.yaml
permissions:
  - id: my_plugin.config.read
    description: View plugin configuration
  - id: my_plugin.config.update
    description: Modify plugin settings
  - id: my_plugin.simulate
    description: Run custom simulations
```

**Enforcement:** Plugin endpoints use the same `require_permission()` mechanism as core modules:

```python
# my_plugin/routes.py
from mes.framework.auth import require_permission

@router.get("/config")
async def get_config(
    user: User = Depends(require_permission("my_plugin.config.read"))
):
    ...

@router.post("/simulate")
async def run_simulation(
    user: User = Depends(require_permission("my_plugin.simulate"))
):
    ...
```

**Auto-Registration:** On plugin install, the framework:
1. Reads `permissions` from the manifest
2. Registers them in the `Permission` registry (namespaced by plugin ID)
3. Makes them available for assignment to roles via the admin API

**Naming Convention:** Plugin permissions must use the plugin ID as prefix to prevent collisions:

| Pattern | Example | Description |
|---|---|---|
| `{plugin_id}.read` | `my_plugin.read` | Read plugin data |
| `{plugin_id}.{resource}.{action}` | `my_plugin.config.update` | Specific resource action |
| `{plugin_id}.*` | `my_plugin.*` | Wildcard — all plugin permissions |

A plugin cannot declare permissions in another plugin's namespace or in the core namespace.

**Role Assignment:** Plugin permissions are assigned to roles the same way as core permissions:

```
POST /api/v1/auth/roles/{role_id}/permissions
{ "add": ["my_plugin.config.read", "my_plugin.simulate"] }
```

IdP group mappings can include plugin permissions via the role they map to:

```
IdP Group "DispatchEngineers"
  → MES Role "dispatch_engineer"
    → Permissions: ["dispatch.*", "my_plugin.*", "wip.read"]
```

**Permission Behavior by Extension Point Type:**

| Extension Point | Permission Behavior |
|---|---|
| **rest_endpoint** | Plugin declares and enforces its own custom permissions |
| **dispatch_strategy** | Guarded by core `dispatch.execute` — no separate plugin permission needed |
| **operation_hook** | Runs with the caller's existing core permissions (hook fires if the user can perform the core operation) |
| **event_handler** | Internal — no user-facing permission (events are system-level) |
| **data_processor** | Runs inline during data collection — guarded by `data_collect.record` |
| **report_generator** | Plugin declares read permission for custom report endpoints |
| **equipment_driver** | Runs as system service — uses service account credentials |

## 12. Configuration (SESSION-META / config)

### 12.1 Server Configuration

Using Pydantic Settings with `.env` file support:

```python
class MESConfig(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://mes:mes@localhost:5432/mes_db"
    database_echo: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["*"]

    # Auth
    auth_mode: str = "oidc"             # "oidc" | "local" (dev only)
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # OIDC (when auth_mode="oidc")
    oidc_issuer: str = ""               # e.g. https://login.microsoftonline.com/tenant/v2.0
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_scopes: list[str] = ["openid", "profile", "email"]
    oidc_role_claim: str = "groups"     # Token claim containing group/role info
    oidc_redirect_uri: str = ""         # e.g. https://mes.factory.com/api/v1/auth/callback

    # Plugins
    plugin_dirs: list[str] = ["plugins"]

    # Event Bus
    event_bus_type: str = "memory"  # "memory" | "redis"
    redis_url: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_prefix="MES_", env_file=".env")
```

## 13. AI Maintainability Conventions

These conventions ensure any AI coding agent can navigate and modify the codebase efficiently:

1. **Uniform module structure**: Every module follows the pattern in §4.1. No exceptions.
2. **Explicit imports**: No wildcard imports. Every dependency is visible.
3. **Type hints everywhere**: All function signatures, return types, and variables are typed.
4. **Docstrings on all public functions**: Google-style docstrings with Args/Returns/Raises.
5. **No magic**: No metaclass tricks, no dynamic attribute assignment, no decorator stacking. Patterns should be obvious from reading the code.
6. **Error messages include context**: Every exception includes the entity type, ID, and what went wrong.
7. **Test mirrors source**: `tests/unit/core/physical_model/test_service.py` mirrors `src/mes/core/physical_model/service.py`.
8. **Module ID in docstrings**: Each module's `__init__.py` starts with `"""Module: PHYS-MODEL — Physical Model"""` for grep-ability.
9. **Changelog in commits**: Every git commit message references the module ID and what changed.
10. **No database-specific SQL**: All queries use SQLAlchemy ORM/Core API. Never use `text()`, dialect-specific operators, or raw SQL in core modules. Database-specific features belong in plugins.

## 14. Multi-Agent Development Workflow

When multiple humans and AI agents work on the system simultaneously, coordination is required to prevent conflicts. The architecture addresses this at multiple levels.

### 14.1 Plugin Work: Fully Isolated (Zero Coordination Needed)

Plugins are the primary customization mechanism, and they are designed for complete isolation:

```
plugins/
├── custom_dispatch/          ← Agent A owns this entirely
│   ├── manifest.yaml
│   ├── plugin.py
│   ├── routes.py
│   └── ...
│
├── spc_engine/               ← Agent B owns this entirely
│   ├── manifest.yaml
│   ├── plugin.py
│   ├── routes.py
│   └── ...
```

| Isolation Dimension | How It's Enforced |
|---|---|
| **File system** | Each plugin in its own directory — no file overlap |
| **Database tables** | Plugin tables prefixed: `plugin_custom_dispatch_*` vs `plugin_spc_engine_*` |
| **API routes** | Plugin endpoints namespaced: `/api/v1/custom/dispatch/` vs `/api/v1/custom/spc/` |
| **Permissions** | Plugin permissions namespaced: `custom_dispatch.*` vs `spc_engine.*` |
| **Events** | Each plugin declares its own subscriptions in its manifest |
| **Configuration** | Plugin config stored per plugin ID in `plugin_config` table |

Multiple agents can build plugins simultaneously with **zero risk of conflict**. This is the same principle that makes VS Code extensions independent.

### 14.2 Core Modifications: Git-Based Coordination

When multiple agents modify core modules (less common but necessary), standard Git workflows apply:

**Branching Model:**

```
main (protected — no direct pushes)
  │
  ├── feature/agent-a/custom-dispatch    ← Agent A's plugin work
  │     └── PR → CI passes → review → merge
  │
  ├── feature/agent-b/spc-engine         ← Agent B's plugin work
  │     └── PR → CI passes → review → merge
  │
  ├── feature/agent-c/add-equipment-field ← Agent C's core modification
  │     └── PR → CI passes → review → merge
  │
  └── (each agent rebases from main before opening PR)
```

**Conflict Scenarios and Mitigations:**

| Scenario | Risk | Mitigation |
|---|---|---|
| Two agents add a field to the same model | Merge conflict in `models.py` | Feature branches + PR review |
| Two agents modify the same service function | Merge conflict in `service.py` | Feature branches + PR review |
| Two agents each add an Alembic migration | Branched migration revision chain | Alembic `merge` command resolves branched heads |
| An agent changes an API response schema | Could break another agent's client code | Versioned API (`/v1/` → `/v2/`) + backward compatibility tests |
| An agent changes an event payload | Could break plugins consuming that event | Contract tests (see §14.4) |

The uniform module structure (§4.1) helps — because every module has the same file layout, merge conflicts are localized and predictable. An AI agent resolving a conflict knows exactly which file does what.

### 14.3 Ownership and Responsibility

**Plugin ownership in manifest:**

```yaml
# manifest.yaml
id: custom-dispatch-optimizer
owner: "Team Dispatch / Agent A"
contact: "dispatch-team@factory.com"
```

**CODEOWNERS file for repository-level ownership:**

```
# .github/CODEOWNERS
# Core modules
server/src/mes/core/physical_model/   @team-infrastructure
server/src/mes/core/wip/              @team-production
server/src/mes/core/dispatch/         @team-dispatch
server/src/mes/core/quality/          @team-quality

# Plugins
plugins/custom_dispatch/              @agent-a
plugins/spc_engine/                   @agent-b
```

GitHub enforces CODEOWNERS — a PR touching `dispatch/` requires approval from `@team-dispatch` before merge.

### 14.4 Automated Safeguards

The CI pipeline includes checks specifically for multi-agent safety:

| CI Check | What It Catches |
|---|---|
| **Full test suite** | Any functional regression from any change |
| **Alembic head check** | Detects branched migration heads — blocks merge until resolved |
| **OpenAPI schema diff** | Compares current API schema to previous version, flags breaking changes |
| **Plugin contract tests** | Verifies event payload schemas haven't changed for cross-plugin dependencies |
| **Permission conflict check** | Ensures no two plugins declare permissions in the same namespace |
| **Route conflict check** | Ensures no two plugins register the same API path prefix |

### 14.5 Cross-Plugin Dependencies

If Plugin A emits custom events that Plugin B consumes, or Plugin B calls Plugin A's API:

1. **Plugin A declares its public contract** in `manifest.yaml` (event schemas, API schemas)
2. **Plugin B declares a dependency** on Plugin A in its `manifest.yaml`
3. **Contract tests** verify Plugin A's event payloads and API responses match the declared schema
4. **The plugin framework** ensures Plugin A is loaded before Plugin B (dependency resolution)

```yaml
# Plugin B manifest
dependencies:
  - plugin_id: custom-dispatch-optimizer
    min_version: "1.0.0"
```

### 14.6 Summary

| Work Type | Agents Involved | Coordination Required |
|---|---|---|
| Independent plugins | Any number | None — fully isolated |
| Plugins with cross-dependencies | 2+ | Dependency declared in manifest + contract tests |
| Core module modifications | 1 at a time preferred | Feature branch + PR + CI |
| Core + plugin simultaneously | Any number | Plugin work is isolated; core changes go through PR |

## 15. Design-Time Configuration Environment (DT-CLIENT)

The Design-Time Client is the **reference configuration environment** for defining the plant physical model, product definitions, process routes, quality tests, material masters, and all other foundational data that must exist before production begins. It is a React + TypeScript web application that communicates exclusively via the REST API (§6).

> **Key distinction:** The DT-CLIENT is the reference implementation for *configuring* the MES. End users may have their AI build a completely different configuration UI or use headless scripts. The DT-CLIENT proves the API is sufficient for full configuration and serves as a working example.

### 15.1 Scope & Responsibilities

The DT-CLIENT handles **definition-time** activities — everything that happens *before* a production order is released. It does **not** handle runtime operations (WIP tracking, dispatching, data collection) — those belong to the RT-GUI and RT-HEADLESS clients.

**In scope:**

| Domain | What the DT-CLIENT Configures |
|---|---|
| **Physical Model** | Sites, areas, production lines, work cells, equipment (with capabilities/properties) |
| **Product Definition** | Products, BOMs, BOM items, process routes, route steps, step parameters |
| **Material Masters** | Material definitions (raw, intermediate, finished), units of measure |
| **Quality Setup** | Quality test definitions, pass/fail criteria, sampling plans |
| **Data Collection Setup** | Data definitions (what to collect at each step), sources, limits |
| **Auth Administration** | Users, roles, permissions, IdP group mappings |
| **Plugin Management** | Install/uninstall/enable/disable plugins, plugin configuration |
| **System Configuration** | Environment settings, adapter configuration, event bus settings |
| **Import/Export** | Bulk import from CSV/JSON, export configuration snapshots |

**Out of scope** (belongs to RT-GUI / RT-HEADLESS):

| Activity | Why Not DT-CLIENT |
|---|---|
| Production order management | Runtime — orders change during production |
| WIP tracking & dispatching | Real-time shop floor activity |
| Data collection entry | Operator activity during production |
| Performance dashboards | Runtime monitoring |
| Equipment state recording | Real-time equipment integration |

> **Standalone mode note:** When an ERP is connected, product definitions, BOMs,
> and routes are **synced from the ERP** via `ERPInboundAdapter` (§9.2). The DT-CLIENT
> route and BOM editors serve primarily as a **view/override layer** and as the sole
> data-entry path in standalone / demo mode where no ERP is present. The DT-CLIENT
> does **not** replace ERP master data management.

### 15.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DT-CLIENT (React + TS)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    App Shell                          │   │
│  │  ┌────────┐  ┌────────────┐  ┌───────────────────┐   │   │
│  │  │ NavBar  │  │ Breadcrumb │  │  User / Logout    │   │   │
│  │  └────────┘  └────────────┘  └───────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Module Pages                        │   │
│  │                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │   │
│  │  │ Physical     │  │ Product     │  │ Material   │   │   │
│  │  │ Model Editor │  │ Definition  │  │ Masters    │   │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │   │
│  │  │ Quality     │  │ Data Collect │  │ Auth       │   │   │
│  │  │ Setup       │  │ Setup       │  │ Admin      │   │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘   │   │
│  │  ┌─────────────┐  ┌─────────────┐                    │   │
│  │  │ Plugin      │  │ Import/     │                    │   │
│  │  │ Manager     │  │ Export      │                    │   │
│  │  └─────────────┘  └─────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Shared Services Layer                     │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │   │
│  │  │ API      │  │ Auth      │  │ Notification     │   │   │
│  │  │ Client   │  │ Context   │  │ Manager          │   │   │
│  │  └──────────┘  └───────────┘  └──────────────────┘   │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │   │
│  │  │ Form     │  │ Table     │  │ Validation       │   │   │
│  │  │ Engine   │  │ Engine    │  │ Engine           │   │   │
│  │  └──────────┘  └───────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                    REST API (httpx / fetch)                   │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    MES Server (/api/v1/...)
```

### 15.3 Technology Stack

| Component | Choice | Rationale |
|---|---|---|
| **Framework** | React 18+ | Shared with RT-GUI; AI-friendly; large component ecosystem |
| **Language** | TypeScript 5+ | Type safety catches configuration errors at compile time |
| **Build Tool** | Vite | Fast HMR; simple config; standard for new React projects |
| **Routing** | React Router v6+ | Standard; nested routes map naturally to entity hierarchies |
| **State Management** | TanStack Query (React Query) | Server state management via REST API; caching, invalidation, optimistic updates |
| **Forms** | React Hook Form + Zod | Schema-driven validation; Zod schemas can mirror Pydantic server schemas |
| **UI Components** | Headless UI library (Radix or Ark) + Tailwind CSS | Unstyled primitives allow consistent theming; AI can generate Tailwind easily |
| **Tables** | TanStack Table | Headless table engine; sorting, filtering, pagination built-in |
| **Tree Views** | Custom (physical model) | Hierarchical navigation for Site→Area→Line→WorkCell→Equipment |
| **HTTP Client** | Native `fetch` + thin wrapper | TanStack Query handles caching; no need for axios |
| **Auth** | OIDC via `oidc-client-ts` | Standard OIDC client; handles Authorization Code flow + PKCE |
| **Testing** | Vitest + React Testing Library | Unit and component tests; Vitest is Vite-native |

#### Why TypeScript / React, Not Python?

The DT-CLIENT is a **web application** that runs in the user's browser — it needs HTML, CSS, and JavaScript. Python does not run in browsers. The three client types use different technologies for different reasons:

| Client | Technology | Why |
|---|---|---|
| **DT-CLIENT** (config UI) | React + TypeScript (PWA) | Browser-based GUI for manufacturing engineers to define plant model, products, routes, quality |
| **RT-GUI** (runtime UI) | React + TypeScript (PWA) | Browser-based GUI for shop floor operators to track WIP, enter data, view dashboards |
| **RT-HEADLESS** (automation) | **Python** (`httpx`) | No UI — scripts, equipment integration, batch automation. Same language as server. |

> **Progressive Web Applications (PWA):** Both browser-based clients (DT-CLIENT and RT-GUI)
> are built as PWAs. This provides:
>
> - **Offline resilience** — service worker caches the app shell and static assets so the UI
>   loads even when the network is intermittent (common on factory floors with spotty Wi-Fi).
>   API calls queue and retry when connectivity returns.
> - **Installable** — operators can "install" the app to tablet or PC home screens without an
>   app store. Launches in its own window, feels native.
> - **Auto-update** — service worker update cycle ensures all clients get the latest version
>   on next launch without IT manually deploying to each device.
> - **Push notifications** — web push API enables real-time alerts (quality hold, equipment
>   down, order completed) even when the browser tab is in the background.
>
> PWA capabilities are provided by Vite's `vite-plugin-pwa` (Workbox-based service worker
> generation). The manifest and service worker are configured per client.

**The DT-CLIENT has zero direct database access.** Every operation goes through the server's REST API:

```
┌─────────────────┐     REST / HTTP      ┌──────────────────┐     SQLAlchemy     ┌────────┐
│  DT-CLIENT      │ ──────────────────▶  │  MES Server      │ ─────────────────▶ │   DB   │
│  (TypeScript)   │ ◀──────────────────  │  (Python/FastAPI) │ ◀───────────────── │        │
│  Browser        │     JSON             │  Business Logic   │     ORM            │ PgSQL  │
└─────────────────┘                      └──────────────────┘                     └────────┘
```

This means:
- The **Python server** owns all business logic, validation, and data access
- The **TypeScript client** handles only presentation and client-side form validation (Zod mirrors Pydantic)
- An end user could **replace the DT-CLIENT entirely** with Python `httpx` scripts if they prefer command-line configuration — the REST API is the contract, not the UI
- The RT-HEADLESS client (Python) can perform any configuration operation the DT-CLIENT can — it uses the same API endpoints

### 15.4 Project Structure

```
clients/design_time/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
│
├── src/
│   ├── main.tsx                       # React app entry point
│   ├── App.tsx                        # App shell, routing, auth provider
│   │
│   ├── api/                           # REST API client layer
│   │   ├── client.ts                  # Base fetch wrapper (auth headers, error handling)
│   │   ├── types.ts                   # TypeScript interfaces matching server Pydantic schemas
│   │   ├── physical-model.ts          # PHYS-MODEL API functions
│   │   ├── product-def.ts             # PROD-DEF API functions
│   │   ├── material.ts                # MAT-MGMT API functions
│   │   ├── quality.ts                 # QUAL-MGMT API functions
│   │   ├── data-collection.ts         # DATA-COLLECT API functions
│   │   ├── auth.ts                    # AUTH API functions
│   │   └── plugins.ts                 # PLUGIN-FW API functions
│   │
│   ├── hooks/                         # TanStack Query hooks (one file per domain)
│   │   ├── use-sites.ts
│   │   ├── use-equipment.ts
│   │   ├── use-products.ts
│   │   ├── use-routes.ts
│   │   └── ...
│   │
│   ├── pages/                         # Route-level page components
│   │   ├── physical-model/
│   │   │   ├── SiteListPage.tsx
│   │   │   ├── SiteDetailPage.tsx
│   │   │   ├── AreaDetailPage.tsx
│   │   │   ├── LineDetailPage.tsx
│   │   │   ├── WorkCellDetailPage.tsx
│   │   │   ├── EquipmentDetailPage.tsx
│   │   │   └── PhysicalModelTreePage.tsx   # Full tree view
│   │   │
│   │   ├── product-def/
│   │   │   ├── ProductListPage.tsx
│   │   │   ├── ProductDetailPage.tsx
│   │   │   ├── BOMEditorPage.tsx
│   │   │   ├── RouteEditorPage.tsx
│   │   │   └── RouteStepEditorPage.tsx
│   │   │
│   │   ├── material/
│   │   │   ├── MaterialListPage.tsx
│   │   │   └── MaterialDetailPage.tsx
│   │   │
│   │   ├── quality/
│   │   │   ├── TestDefinitionListPage.tsx
│   │   │   └── TestDefinitionEditorPage.tsx
│   │   │
│   │   ├── data-collection/
│   │   │   ├── DataDefListPage.tsx
│   │   │   └── DataDefEditorPage.tsx
│   │   │
│   │   ├── auth/
│   │   │   ├── UserListPage.tsx
│   │   │   ├── RoleEditorPage.tsx
│   │   │   └── GroupMappingPage.tsx
│   │   │
│   │   ├── plugins/
│   │   │   ├── PluginListPage.tsx
│   │   │   └── PluginConfigPage.tsx
│   │   │
│   │   └── import-export/
│   │       ├── ImportPage.tsx
│   │       └── ExportPage.tsx
│   │
│   ├── components/                    # Reusable UI components
│   │   ├── layout/
│   │   │   ├── AppShell.tsx           # Main layout: sidebar + content
│   │   │   ├── Sidebar.tsx            # Navigation sidebar
│   │   │   └── Breadcrumbs.tsx
│   │   │
│   │   ├── shared/
│   │   │   ├── DataTable.tsx          # Generic CRUD table (TanStack Table wrapper)
│   │   │   ├── EntityForm.tsx         # Generic form component (React Hook Form wrapper)
│   │   │   ├── TreeView.tsx           # Hierarchical tree component
│   │   │   ├── ConfirmDialog.tsx      # Confirmation modal
│   │   │   ├── SearchInput.tsx        # Search/filter input
│   │   │   ├── StatusBadge.tsx        # Status indicator pill
│   │   │   ├── JsonEditor.tsx         # JSON editor for capabilities/config
│   │   │   └── Pagination.tsx         # Cursor-based pagination controls
│   │   │
│   │   └── domain/                    # Domain-specific components
│   │       ├── EquipmentCapabilitiesEditor.tsx
│   │       ├── RouteStepGraph.tsx     # Visual route step flow diagram
│   │       ├── BOMTreeView.tsx        # Nested BOM visualization
│   │       └── PermissionMatrix.tsx   # Role-permission assignment grid
│   │
│   ├── validation/                    # Zod schemas (mirror server Pydantic schemas)
│   │   ├── physical-model.ts
│   │   ├── product-def.ts
│   │   ├── material.ts
│   │   └── ...
│   │
│   ├── auth/                          # OIDC authentication
│   │   ├── oidc-config.ts             # OIDC provider settings
│   │   ├── AuthProvider.tsx           # React context for auth state
│   │   └── ProtectedRoute.tsx         # Route guard (redirects to login if unauthenticated)
│   │
│   └── utils/
│       ├── format.ts                  # Date, number, UOM formatting
│       └── constants.ts               # API base URL, pagination defaults
│
└── tests/                             # Vitest + React Testing Library
    ├── setup.ts
    ├── pages/
    └── components/
```

### 15.5 Core UI Patterns

Every configuration domain follows the same **List → Detail → Edit** interaction pattern for AI predictability:

#### Master-Detail Pattern

```
┌─────────────────────────────────────────────────────────┐
│  Sites                                        [+ New]   │
│─────────────────────────────────────────────────────────│
│  🔍 Search...                      Status ▼  Sort ▼    │
│─────────────────────────────────────────────────────────│
│  Name          Code    Timezone       Areas   Actions   │
│  Detroit Plant  DET    America/Det...    3    ✏️ 🗑️      │
│  Austin Plant   AUS    America/Chi...    2    ✏️ 🗑️      │
│  Monterrey      MTY    America/Mon...    4    ✏️ 🗑️      │
│─────────────────────────────────────────────────────────│
│  ← Prev                                   Next →  1/3  │
└─────────────────────────────────────────────────────────┘
                    │ click row
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Sites > Detroit Plant                       [Save] [↩] │
│─────────────────────────────────────────────────────────│
│  ┌─ General ──────────────────────────────────────────┐ │
│  │  Name:     [Detroit Plant         ]                │ │
│  │  Code:     [DET                   ]                │ │
│  │  Timezone: [America/Detroit       ▼]               │ │
│  │  Address:  [123 Industrial Blvd   ]                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ Areas (3) ──────────────────────────── [+ New] ──┐ │
│  │  Assembly Hall A    →  2 Lines, 8 Work Cells       │ │
│  │  Paint Shop         →  1 Line,  3 Work Cells       │ │  
│  │  Final Test         →  1 Line,  4 Work Cells       │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

#### Physical Model Tree View

The physical hierarchy is the most complex configuration UI. A dedicated tree page shows the full structure:

```
┌─────────────────────────────────────────────────────────┐
│  Physical Model                          [Expand All]   │
│─────────────────────────────────────────────────────────│
│                                                          │
│  ▼ 🏭 Detroit Plant (DET)                               │
│    ▼ 📦 Assembly Hall A                                  │
│      ▼ 🔧 Line 1 - Main Assembly                        │
│        ▼ ⚙️ WC-101 Chassis Mount (automated)             │
│            🔌 Robot Arm R-001 [running]                   │
│            🔌 Torque Driver T-001 [idle]                  │
│        ▶ ⚙️ WC-102 Wiring (manual)                       │
│        ▶ ⚙️ WC-103 Final Assembly (automated)            │
│      ▶ 🔧 Line 2 - Sub-Assembly                         │
│    ▶ 📦 Paint Shop                                       │
│    ▶ 📦 Final Test                                       │
│  ▶ 🏭 Austin Plant (AUS)                                │
│  ▶ 🏭 Monterrey (MTY)                                   │
│                                                          │
│  ─────────────── Detail Panel ───────────────────────── │
│  Equipment: Robot Arm R-001                              │
│  Code: R-001  Type: robotic_arm  Status: running         │
│  Work Cell: WC-101 Chassis Mount                         │
│  Capabilities: { "axes": 6, "payload_kg": 10 }          │
│  [Edit] [View History]                                   │
└─────────────────────────────────────────────────────────┘
```

**Interactions:**
- Click a tree node → detail panel shows entity properties
- Double-click or Edit → opens inline edit form
- Drag-and-drop → reparent equipment between work cells (with confirmation)
- Right-click → context menu (add child, delete, duplicate)

#### Route Step Visual Editor

Process routes are configured using a visual flow editor:

```
┌─────────────────────────────────────────────────────────┐
│  Product: Widget-A v2.0 > Route: Main Route             │
│─────────────────────────────────────────────────────────│
│                                                          │
│  ┌─────────┐    ┌───────────┐    ┌──────────┐          │
│  │ Step 1   │───▶│ Step 2     │───▶│ Step 3    │         │
│  │ Chassis  │    │ Wiring     │    │ Assembly  │         │
│  │ Mount    │    │            │    │           │         │
│  │ WC-101   │    │ WC-102     │    │ WC-103    │         │
│  │ 45s      │    │ 120s       │    │ 60s       │         │
│  └─────────┘    └───────────┘    └──────────┘          │
│       │                                │                 │
│       │         ┌───────────┐          │                 │
│       └────────▶│ Rework     │─────────┘                │
│                 │ Step 2R    │                            │
│                 │ WC-104     │                            │
│                 └───────────┘                            │
│                                                          │
│  [+ Add Step]  [+ Add Rework Path]  [Validate Route]   │
│                                                          │
│  ─────────── Step Detail ─────────────────────────────  │
│  Step: Chassis Mount (production)                        │
│  Work Cell: WC-101    Cycle Time: 45s                    │
│  Eligible Equipment: Robot Arm R-001, Robot Arm R-002    │
│  Parameters:                                             │
│    Torque (Nm)  target=25  min=23  max=27  [required]   │
│    Temp (°C)    target=22  min=20  max=25  [optional]   │
│  [Edit Step] [Delete]                                    │
└─────────────────────────────────────────────────────────┘
```

#### BOM Editor

```
┌─────────────────────────────────────────────────────────┐
│  Product: Widget-A v2.0 > BOM: v1.0                     │
│─────────────────────────────────────────────────────────│
│                                                          │
│  ▼ Widget-A                                              │
│    ├── Chassis Frame (raw)       qty: 1    ea            │
│    ├── Wiring Harness (raw)      qty: 1    ea            │
│    ├── Circuit Board (intermed.) qty: 2    ea            │
│    │   ├── PCB Blank (raw)       qty: 1    ea            │
│    │   ├── Resistor Pack (raw)   qty: 1    pack          │
│    │   └── Solder Wire (raw)     qty: 0.5  m             │
│    ├── Mounting Bolts (raw)      qty: 8    ea            │
│    └── Label (raw)               qty: 1    ea            │
│                                                          │
│  Total materials: 8          [+ Add Item] [Import CSV]  │
└─────────────────────────────────────────────────────────┘
```

### 15.6 Shared Component Library

Components shared between DT-CLIENT and RT-GUI are extracted into a common library:

```
clients/
├── shared/                            # Shared component library
│   ├── package.json                   # Published as @mes/ui
│   ├── src/
│   │   ├── components/
│   │   │   ├── DataTable.tsx
│   │   │   ├── EntityForm.tsx
│   │   │   ├── TreeView.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── SearchInput.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── ConfirmDialog.tsx
│   │   │   └── JsonEditor.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── use-api.ts             # Base API hook factory
│   │   │   └── use-auth.ts            # OIDC auth hook
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts              # Base HTTP client
│   │   │   └── types.ts               # Shared TypeScript interfaces
│   │   │
│   │   └── theme/
│   │       └── tailwind-preset.ts     # Shared Tailwind theme tokens
│   │
│   └── tests/
│
├── design_time/                       # DT-CLIENT (imports @mes/ui)
└── runtime_gui/                       # RT-GUI (imports @mes/ui)
```

### 15.7 API Interaction Layer

The DT-CLIENT communicates with the server **exclusively** via the REST API. No direct database access.

#### TypeScript API Client

```typescript
// api/client.ts
const API_BASE = import.meta.env.VITE_MES_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new ApiError(response.status, error);
  }

  const envelope = await response.json(); // { data, meta, errors }
  return envelope.data as T;
}

// Domain-specific API functions
// api/physical-model.ts
export const sitesApi = {
  list:   (cursor?: string) => request<Site[]>(`/sites?cursor=${cursor ?? ""}`),
  get:    (id: string)      => request<Site>(`/sites/${id}`),
  create: (data: SiteCreate)=> request<Site>("/sites", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: SiteUpdate) => request<Site>(`/sites/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string)      => request<void>(`/sites/${id}`, { method: "DELETE" }),
  areas:  (siteId: string)  => request<Area[]>(`/sites/${siteId}/areas`),
};
```

#### TanStack Query Hooks

```typescript
// hooks/use-sites.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sitesApi } from "../api/physical-model";

export function useSites() {
  return useQuery({ queryKey: ["sites"], queryFn: () => sitesApi.list() });
}

export function useSite(id: string) {
  return useQuery({ queryKey: ["sites", id], queryFn: () => sitesApi.get(id) });
}

export function useCreateSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: sitesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useUpdateSite(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SiteUpdate) => sitesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sites"] });
      qc.invalidateQueries({ queryKey: ["sites", id] });
    },
  });
}
```

### 15.8 Validation Strategy

Validation runs at **two levels** — client-side for instant feedback, server-side as the authoritative check.

| Level | Technology | Purpose |
|---|---|---|
| **Client** | Zod schemas + React Hook Form | Instant field validation, type checking, format enforcement, prevents invalid API calls |
| **Server** | Pydantic schemas + service layer | Authoritative validation, business rules, uniqueness checks, referential integrity |

```typescript
// validation/physical-model.ts
import { z } from "zod";

export const SiteCreateSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  code: z.string().min(1).max(50).regex(/^[A-Z0-9_-]+$/, "Code must be uppercase alphanumeric"),
  timezone: z.string().min(1, "Timezone is required"),
  description: z.string().max(1000).optional(),
  address: z.string().max(500).optional(),
});

// Mirrors server schema: mes/core/physical_model/schemas.py → SiteCreate
```

**Validation rules that only exist server-side** (cannot be checked client-side):
- Uniqueness: "site code must be unique" → requires database query
- Referential integrity: "work cell's line_id must exist" → requires database lookup
- Business rules: "cannot delete a site with active production orders" → requires cross-module query

The client handles these by displaying server-side error responses inline on the relevant form fields.

### 15.9 Import / Export

For initial setup and configuration migration between environments (dev → staging → production), the DT-CLIENT provides bulk import/export.

#### Export

```
POST /api/v1/config/export
Body: { "domains": ["physical_model", "product_def", "material"] }
Response: JSON snapshot of all configuration data in the requested domains
```

The export produces a **deterministic JSON document** with all entities and their relationships. Suitable for:
- Version control (commit configuration snapshots to Git)
- Environment promotion (export from dev, import to staging)
- Backup of configuration data (not production/runtime data)

#### Import

```
POST /api/v1/config/import
Body: { "data": <exported JSON>, "mode": "create" | "upsert" | "replace" }
```

| Mode | Behavior |
|---|---|
| `create` | Only insert new records. Fail if any already exist. |
| `upsert` | Insert new records, update existing (matched by `code`). |
| `replace` | Delete all existing records in the target domains, then insert. **Dangerous — requires admin role.** |

**Import validation:**
1. Parse and validate all records against Pydantic schemas
2. Check referential integrity (e.g., BOM items reference valid materials)
3. Report all errors **before** applying any changes (atomic — all-or-nothing)
4. Return a detailed import report: records created, updated, skipped, errors

#### CSV Import (simplified)

For users who maintain configuration in spreadsheets:

```
POST /api/v1/config/import-csv
Content-Type: multipart/form-data
Body: { "domain": "equipment", "file": <CSV file> }
```

CSV column headers must match the Pydantic schema field names. The server maps them to the appropriate entities.

### 15.10 Routing Map

```typescript
// App.tsx routes
const routes = [
  { path: "/",                      element: <DashboardPage /> },

  // Physical Model
  { path: "/physical-model",        element: <PhysicalModelTreePage /> },
  { path: "/sites",                 element: <SiteListPage /> },
  { path: "/sites/:siteId",         element: <SiteDetailPage /> },
  { path: "/areas/:areaId",         element: <AreaDetailPage /> },
  { path: "/lines/:lineId",         element: <LineDetailPage /> },
  { path: "/work-cells/:wcId",    element: <WorkCellDetailPage /> },
  { path: "/equipment/:equipId",    element: <EquipmentDetailPage /> },

  // Product Definition
  { path: "/products",              element: <ProductListPage /> },
  { path: "/products/:productId",   element: <ProductDetailPage /> },
  { path: "/boms/:bomId",           element: <BOMEditorPage /> },
  { path: "/routes/:routeId",       element: <RouteEditorPage /> },
  { path: "/steps/:stepId",         element: <RouteStepEditorPage /> },

  // Material Masters
  { path: "/materials",             element: <MaterialListPage /> },
  { path: "/materials/:materialId", element: <MaterialDetailPage /> },

  // Quality Setup
  { path: "/quality/tests",         element: <TestDefinitionListPage /> },
  { path: "/quality/tests/:testId", element: <TestDefinitionEditorPage /> },

  // Data Collection Setup
  { path: "/data-definitions",      element: <DataDefListPage /> },
  { path: "/data-definitions/:id",  element: <DataDefEditorPage /> },

  // Auth Administration
  { path: "/admin/users",           element: <UserListPage /> },
  { path: "/admin/roles",           element: <RoleEditorPage /> },
  { path: "/admin/group-mappings",  element: <GroupMappingPage /> },

  // Plugins
  { path: "/plugins",               element: <PluginListPage /> },
  { path: "/plugins/:pluginId",     element: <PluginConfigPage /> },

  // Import/Export
  { path: "/import",                element: <ImportPage /> },
  { path: "/export",                element: <ExportPage /> },
];
```

### 15.11 Authorization in the DT-CLIENT

The DT-CLIENT respects the server's RBAC model. The UI adapts based on the user's permissions:

| Permission | UI Behavior |
|---|---|
| User has `physical_model.sites.create` | "New Site" button visible |
| User lacks `physical_model.sites.create` | "New Site" button hidden |
| User has `physical_model.equipment.update` | Edit form fields enabled |
| User lacks `physical_model.equipment.update` | Fields shown as read-only |
| User has `admin.*` | Full access to auth admin, plugin management, import/export |
| User has `product_def.routes.read` only | Can view routes but all edit controls hidden |

**How it works:**
1. On login, DT-CLIENT calls `GET /api/v1/auth/me` to get the user's resolved permissions
2. Permissions are stored in React auth context
3. Components use a `usePermission("physical_model.sites.create")` hook to conditionally render controls
4. Even if UI controls are somehow bypassed, the server enforces permissions on every API call

### 15.12 Configuration Dashboard

The DT-CLIENT landing page provides a configuration completeness overview:

```
┌─────────────────────────────────────────────────────────┐
│  MES Configuration Dashboard                             │
│─────────────────────────────────────────────────────────│
│                                                          │
│  Physical Model          Product Definitions             │
│  ┌────────────────┐      ┌─────────────────┐            │
│  │ Sites:       3  │      │ Products:    12  │            │
│  │ Areas:       8  │      │ BOMs:        12  │            │
│  │ Lines:      14  │      │ Routes:      15  │            │
│  │ Work Ctrs:  42  │      │ Steps:      127  │            │
│  │ Equipment:  86  │      │ Parameters: 340  │            │
│  └────────────────┘      └─────────────────┘            │
│                                                          │
│  Materials                Quality                        │
│  ┌────────────────┐      ┌─────────────────┐            │
│  │ Materials:  45  │      │ Tests:       28  │            │
│  │ ⚠ 3 no UOM     │      │ ⚠ 5 no limits   │            │
│  └────────────────┘      └─────────────────┘            │
│                                                          │
│  Reason Codes             Plugins                        │
│  ┌────────────────┐      ┌─────────────────┐            │
│  │ Reasons:   18  │      │ Installed:    4  │            │
│  │ Top-level:  3  │      │ Active:       3  │            │
│  └────────────────┘      └─────────────────┘            │
│                                                          │
│  ⚠ Configuration Warnings:                              │
│  • 3 materials missing unit of measure                   │
│  • 5 quality tests missing pass/fail limits              │
│  • 2 route steps have no eligible equipment assigned     │
│  • 1 product has no default route                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

The dashboard queries a dedicated server endpoint:

```
GET /api/v1/config/health
Response: {
  "counts": { "sites": 3, "areas": 8, ... },
  "warnings": [
    { "domain": "material", "severity": "warning", "message": "3 materials missing UOM", "ids": [...] },
    ...
  ]
}
```

This helps manufacturing engineers verify their configuration is complete before releasing production orders.

### 15.13 New Server Endpoints for DT-CLIENT

The DT-CLIENT requires these additional server endpoints beyond what §6.3 already defines:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/config/health` | Configuration completeness check with warnings |
| `POST` | `/api/v1/config/export` | Export configuration data as JSON snapshot |
| `POST` | `/api/v1/config/import` | Import configuration from JSON (modes: create/upsert/replace) |
| `POST` | `/api/v1/config/import-csv` | Import single domain from CSV file |
| `GET` | `/api/v1/config/export-history` | List past export snapshots |
| `GET` | `/api/v1/physical-model/tree` | Full hierarchical tree (Site→Area→Line→WC→Equipment) in one call |
| `GET` | `/api/v1/products/{id}/full` | Full product with BOM, route, steps, parameters in one call |

These "aggregate" endpoints reduce round-trips for tree views and detail pages that need deeply nested data.

## 16. Test Client (TEST-CLIENT)

Since no real factory, ERP system, or production equipment is available during development, a **Test Client GUI** is required to exercise the full MES server. It serves as an API exerciser, mock ERP receiver, mock equipment simulator, and scenario runner — all in one tool.

> **This is a developer/QA tool, not an end-user application.** It is not intended for production use. It exists to prove the server works correctly end-to-end.

### 16.1 Scope & Responsibilities

| Responsibility | What It Does |
|---|---|
| **API Exerciser** | Make HTTP requests to every REST endpoint. View request/response. Build and save request collections. |
| **Mock ERP Receiver** | Run a lightweight HTTP server that receives outbound ERP calls (completion reports, consumption reports, scrap reports) from the MES server and logs them for inspection. |
| **Mock Equipment Simulator** | Publish simulated OPC-UA tag changes, MQTT messages, and equipment state transitions that the MES server's equipment adapter consumes. |
| **Event Monitor** | Connect to the MES WebSocket endpoint and display real-time events as they fire. |
| **Scenario Runner** | Execute pre-defined end-to-end test scenarios (e.g., "create order → release → move unit through 5 steps → complete → report to ERP") in sequence with assertions. |
| **Data Seeder** | Populate the database with realistic sample data (sites, equipment, products, routes, materials) in one click for demo/testing. |

### 16.2 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     TEST-CLIENT (Python + Textual TUI)           │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Tab Bar                                  │ │
│  │  [API Explorer] [ERP Sim] [Equip Sim] [Events] [Scenarios] │ │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
│  │  Endpoint Tree       │  │  Request / Response Panel        │  │
│  │                      │  │                                   │  │
│  │  ▼ Physical Model    │  │  POST /api/v1/sites              │  │
│  │    POST /sites       │  │  ──────────────────────          │  │
│  │    GET  /sites       │  │  Headers:                        │  │
│  │    GET  /sites/{id}  │  │    Authorization: Bearer ...     │  │
│  │    PUT  /sites/{id}  │  │  Body:                           │  │
│  │    ...               │  │    { "name": "Test Plant",       │  │
│  │  ▼ Product Def       │  │      "code": "TST",             │  │
│  │    ...               │  │      "timezone": "UTC" }         │  │
│  │  ▼ Production        │  │  ──────────────────────          │  │
│  │    ...               │  │  Response: 201 Created           │  │
│  │  ▼ WIP Tracking      │  │    { "data": { "id": "..." } }  │  │
│  │    ...               │  │                                   │  │
│  └──────────────────────┘  └──────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Log / Audit Panel                                          │ │
│  │  [12:01:05] → POST /api/v1/sites  201  45ms                │ │
│  │  [12:01:06] → GET  /api/v1/sites  200  12ms  (2 items)     │ │
│  │  [12:01:08] ← ERP callback: completion report received      │ │
│  │  [12:01:09] ⚡ Event: production.order.released             │ │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 16.3 Technology Stack

| Component | Choice | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | Same as server; AI maintains one language; full access to server's Pydantic schemas |
| **UI Framework** | Textual (TUI) | Rich terminal UI; no browser needed; runs in any terminal; AI-friendly |
| **HTTP Client** | `httpx` (async) | Same as RT-HEADLESS; async; HTTP/2 support |
| **WebSocket Client** | `websockets` | Async WebSocket for event monitoring |
| **Mock HTTP Server** | `uvicorn` + `FastAPI` (lightweight) | Receives outbound ERP/equipment callbacks from MES server |
| **OPC-UA Simulator** | `asyncua` (server mode) | Runs a mini OPC-UA server with configurable tags |
| **MQTT Simulator** | `aiomqtt` (publisher) | Publishes simulated sensor data to MQTT broker |
| **Scenario Engine** | Python `asyncio` + YAML scenario files | Declarative test scenarios with assertions |
| **Data Seeding** | Server's Pydantic schemas + `httpx` | Creates sample data via API calls (not direct DB) |

**Why Python TUI instead of React?**
- The test client needs to **import server Pydantic schemas directly** — it knows every endpoint's request/response shape without duplication
- It needs to **run OPC-UA and MQTT simulators** — these are Python libraries
- It needs to **run a mock HTTP server** to receive ERP callbacks — trivial in Python
- Terminal-based means it works over SSH, in containers, in CI — no browser needed
- Textual provides a rich TUI with mouse support, scrolling, tabs, trees — sufficient for a developer tool

### 16.4 Project Structure

```
clients/test_client/
├── pyproject.toml                     # Dependencies: httpx, textual, asyncua, aiomqtt, fastapi
├── README.md
│
├── src/
│   └── mes_test_client/
│       ├── __init__.py
│       ├── main.py                    # Textual app entry point
│       ├── config.py                  # Test client settings (MES URL, credentials)
│       │
│       ├── api/                       # API client layer
│       │   ├── client.py             # Base httpx async client (auth, error handling)
│       │   ├── endpoints.py          # Auto-generated endpoint registry from OpenAPI spec
│       │   └── auth.py               # OIDC token management (client credentials flow)
│       │
│       ├── tabs/                      # TUI tab panels
│       │   ├── api_explorer.py       # Endpoint tree + request/response editor
│       │   ├── erp_simulator.py      # Mock ERP receiver panel
│       │   ├── equipment_simulator.py # Equipment simulator panel
│       │   ├── event_monitor.py      # WebSocket event feed
│       │   └── scenario_runner.py    # Scenario executor with results
│       │
│       ├── simulators/                # Background simulators
│       │   ├── erp_server.py         # FastAPI app receiving ERP callbacks
│       │   ├── opcua_server.py       # asyncua OPC-UA server with simulated tags
│       │   ├── mqtt_publisher.py     # MQTT simulated sensor data publisher
│       │   └── equipment_state.py    # Equipment state change generator
│       │
│       ├── scenarios/                 # YAML scenario definitions
│       │   ├── 01_setup_plant.yaml
│       │   ├── 02_define_product.yaml
│       │   ├── 03_production_flow.yaml
│       │   ├── 04_quality_flow.yaml
│       │   ├── 05_full_lifecycle.yaml
│       │   └── schema.py            # Scenario YAML schema (Pydantic)
│       │
│       ├── seeders/                   # Data seeding scripts
│       │   ├── seed_physical_model.py
│       │   ├── seed_products.py
│       │   ├── seed_materials.py
│       │   └── seed_all.py
│       │
│       └── widgets/                   # Reusable Textual widgets
│           ├── endpoint_tree.py      # Collapsible endpoint tree
│           ├── json_viewer.py        # Syntax-highlighted JSON display
│           ├── request_editor.py     # HTTP method, path, headers, body editor
│           ├── log_panel.py          # Scrolling log with timestamps
│           └── status_bar.py         # Connection status, auth status
│
├── scenarios/                         # Built-in scenario YAML files
│   └── ...
│
└── tests/
    └── ...
```

### 16.5 Tab 1: API Explorer

The primary tab — makes HTTP requests to every MES server endpoint.

#### Endpoint Registry (Auto-Generated)

The test client reads the MES server's **OpenAPI spec** (`GET /openapi.json`) at startup to build the endpoint tree dynamically:

```python
# api/endpoints.py
async def load_endpoint_registry(base_url: str) -> dict:
    """Fetch OpenAPI spec and build endpoint tree grouped by tag."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/openapi.json")
        spec = resp.json()

    tree = {}
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            tag = details.get("tags", ["Other"])[0]
            tree.setdefault(tag, []).append({
                "method": method.upper(),
                "path": path,
                "summary": details.get("summary", ""),
                "parameters": details.get("parameters", []),
                "request_body": details.get("requestBody", {}),
                "responses": details.get("responses", {}),
            })
    return tree
```

This means the test client **automatically discovers all endpoints** — including endpoints added by plugins. No manual endpoint list maintenance needed.

#### Request Builder

When the user selects an endpoint from the tree:

1. **Path parameters** are shown as editable fields (e.g., `{site_id}` → text input pre-filled with last-used value)
2. **Query parameters** are shown as optional fields with defaults from the OpenAPI spec
3. **Request body** is pre-populated with the JSON schema from the OpenAPI spec (all fields shown with example/default values)
4. **Send** executes the request and displays the response with status code, headers, body, and timing
5. **History** — all requests are logged and can be replayed

#### Request Collections

Saved sets of requests for repeated testing:

```yaml
# collections/setup_plant.yaml
name: "Setup Detroit Plant"
requests:
  - name: "Create site"
    method: POST
    path: /api/v1/sites
    body:
      name: "Detroit Plant"
      code: "DET"
      timezone: "America/Detroit"
    expect_status: 201
    save_response:
      site_id: "$.data.id"           # Extract and save for next request

  - name: "Create Assembly area"
    method: POST
    path: /api/v1/sites/${site_id}/areas    # Uses saved variable
    body:
      name: "Assembly Hall A"
      code: "ASSY-A"
    expect_status: 201
    save_response:
      area_id: "$.data.id"

  - name: "Verify site has area"
    method: GET
    path: /api/v1/sites/${site_id}/areas
    expect_status: 200
    assert:
      - "$.data | length >= 1"
```

### 16.6 Tab 2: Mock ERP Simulator

The MES server's `ERPOutboundAdapter` sends completion reports, consumption reports, and scrap reports to the ERP. In production, this goes to SAP/Oracle/D365. In development, the test client **runs a mock ERP HTTP server** that receives these calls.

#### Mock ERP Server

```python
# simulators/erp_server.py
from fastapi import FastAPI

erp_app = FastAPI(title="Mock ERP Receiver")
received_messages: list[dict] = []

@erp_app.post("/erp/completions")
async def receive_completion(payload: dict):
    received_messages.append({"type": "completion", "payload": payload, "received_at": datetime.utcnow()})
    return {"status": "accepted", "erp_doc_number": f"MOCK-{len(received_messages):04d}"}

@erp_app.post("/erp/consumption")
async def receive_consumption(payload: dict):
    received_messages.append({"type": "consumption", "payload": payload, "received_at": datetime.utcnow()})
    return {"status": "accepted", "erp_doc_number": f"MOCK-{len(received_messages):04d}"}

@erp_app.post("/erp/scrap")
async def receive_scrap(payload: dict):
    received_messages.append({"type": "scrap", "payload": payload, "received_at": datetime.utcnow()})
    return {"status": "accepted", "erp_doc_number": f"MOCK-{len(received_messages):04d}"}

@erp_app.post("/erp/labor")
async def receive_labor(payload: dict):
    received_messages.append({"type": "labor", "payload": payload, "received_at": datetime.utcnow()})
    return {"status": "accepted", "erp_doc_number": f"MOCK-{len(received_messages):04d}"}
```

#### ERP Simulator Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Mock ERP Simulator                          [▶ Running]    │
│─────────────────────────────────────────────────────────────│
│  Listening on: http://localhost:9090/erp                     │
│  Messages received: 12                                       │
│                                                              │
│  ┌─ Inbound Feed ─────────────────────────────────────────┐ │
│  │  [12:05:01] completion  Order: ORD-001  Good: 50  Rej: 2│ │
│  │  [12:05:01] consumption Order: ORD-001  Material: MAT-A │ │
│  │  [12:07:15] completion  Order: ORD-002  Good: 100 Rej: 0│ │
│  │  [12:07:15] consumption Order: ORD-002  Material: MAT-B │ │
│  │  [12:07:16] scrap       Order: ORD-002  Qty: 3          │ │
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─ Controls ─────────────────────────────────────────────┐ │
│  │  Response delay: [0    ] ms     Failure rate: [0  ] %   │ │
│  │  Response mode:  ○ Accept all  ○ Reject all  ● Custom   │ │
│  │  [Clear Log]  [Export JSON]  [Pause]  [Stop Server]     │ │
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Configurable behaviors:**
- **Response delay**: Simulate slow ERP (0–10,000ms)
- **Failure rate**: Simulate ERP errors (0–100%) to test MES retry logic
- **Response mode**: Accept all, reject all, or custom rules (e.g., reject every 3rd request)
- **Export**: Save all received messages as JSON for test assertion

#### MES Server Configuration

Point the MES server's mock ERP adapter at the test client:

```bash
# .env
MES_ERP_ADAPTER=mock
MES_ERP_MOCK_OUTBOUND_URL=http://localhost:9090/erp
```

### 16.7 Tab 3: Equipment Simulator

Simulates production equipment that the MES server's equipment adapter connects to.

#### OPC-UA Server Simulator

Runs a mini OPC-UA server with configurable tags representing a virtual factory:

```python
# simulators/opcua_server.py
from asyncua import Server

async def start_opcua_simulator(port: int = 4840):
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}/mes-test/")

    # Create simulated equipment namespace
    ns = await server.register_namespace("urn:mes-test:equipment")

    # Oven
    oven = await server.nodes.objects.add_object(ns, "Oven-001")
    oven_temp = await oven.add_variable(ns, "Temperature", 180.0)
    oven_state = await oven.add_variable(ns, "State", "running")
    await oven_temp.set_writable()

    # Conveyor
    conveyor = await server.nodes.objects.add_object(ns, "Conveyor-001")
    conveyor_speed = await conveyor.add_variable(ns, "Speed", 1.5)
    conveyor_count = await conveyor.add_variable(ns, "PartCount", 0)

    await server.start()

    # Simulate changing values
    while True:
        current = await oven_temp.read_value()
        await oven_temp.write_value(current + random.gauss(0, 0.5))
        count = await conveyor_count.read_value()
        await conveyor_count.write_value(count + 1)
        await asyncio.sleep(1.0)
```

#### MQTT Publisher Simulator

Publishes simulated sensor messages to an MQTT broker:

```python
# simulators/mqtt_publisher.py
async def start_mqtt_simulator(broker: str = "localhost", port: int = 1883):
    async with aiomqtt.Client(broker, port) as client:
        while True:
            await client.publish(
                "factory/line-1/oven-001/temperature",
                json.dumps({"value": 180 + random.gauss(0, 1), "unit": "C", "ts": datetime.utcnow().isoformat()})
            )
            await client.publish(
                "factory/line-1/conveyor-001/speed",
                json.dumps({"value": 1.5 + random.gauss(0, 0.1), "unit": "m/s", "ts": datetime.utcnow().isoformat()})
            )
            await asyncio.sleep(1.0)
```

#### Equipment Simulator Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Equipment Simulator                                         │
│─────────────────────────────────────────────────────────────│
│  OPC-UA Server: opc.tcp://localhost:4840  [▶ Running]        │
│  MQTT Publisher: localhost:1883           [▶ Running]        │
│                                                              │
│  ┌─ Virtual Equipment ───────────────────────────────────┐  │
│  │  Equipment        Tag              Value    Acts       │  │
│  │  Oven-001         Temperature      180.3°C  [Edit]     │  │
│  │  Oven-001         State            running  [▼ Change] │  │
│  │  Oven-001         Setpoint         180.0°C  [Edit]     │  │
│  │  Conveyor-001     Speed            1.52 m/s [Edit]     │  │
│  │  Conveyor-001     PartCount        1,247    [Reset]    │  │
│  │  Robot-001        CycleTime        4.2s     [Edit]     │  │
│  │  Robot-001        State            idle     [▼ Change] │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Controls ─────────────────────────────────────────────┐ │
│  │  Update interval: [1.0] sec   Noise σ: [0.5]           │ │
│  │  [Trigger Breakdown: Oven-001]  [Trigger Maintenance]   │ │
│  │  [Reset All to Defaults]                                │ │
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Interactions:**
- **Edit tag value**: Manually override a simulated value
- **Change state**: Set equipment to running/idle/down_planned/down_unplanned/maintenance
- **Trigger breakdown**: Instantly simulate an unplanned stop (sets state to `down_unplanned`, publishes event)
- **Noise**: Controls random fluctuation amplitude for continuous values

### 16.8 Tab 4: Event Monitor

Connects to the MES server's WebSocket endpoint and displays real-time events:

```
┌─────────────────────────────────────────────────────────────┐
│  Event Monitor              Connected: ws://localhost:8000   │
│─────────────────────────────────────────────────────────────│
│  Filter: [production.*           ]  [Apply]  [Clear]        │
│                                                              │
│  Time      Topic                          Source    Payload  │
│  12:01:05  production.order.released      PROD-ORD  {...}   │
│  12:01:06  wip.unit.created               WIP-TRACK {...}   │
│  12:01:08  dispatch.decision.made         DISPATCH  {...}   │
│  12:01:09  wip.unit.moved                 WIP-TRACK {...}   │
│  12:01:10  data_collect.point.recorded    DATA-COLL {...}   │
│  12:01:12  wip.unit.completed             WIP-TRACK {...}   │
│  12:01:12  erp.outbound.completion_sent   ERP-OBOUND{...}   │
│                                                              │
│  Events: 7       Rate: 2.3/sec       [Pause]  [Export]      │
│─────────────────────────────────────────────────────────────│
│  ▼ Selected Event Detail:                                    │
│  {                                                           │
│    "event_id": "a1b2c3...",                                  │
│    "topic": "wip.unit.moved",                                │
│    "source_module": "WIP-TRACK",                             │
│    "timestamp": "2026-02-23T12:01:09Z",                      │
│    "payload": {                                              │
│      "unit_id": "...", "from_step": "Step 1",                │
│      "to_step": "Step 2", "equipment_id": "..."             │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- **Wildcard filter**: `production.*`, `wip.unit.*`, `*` (all)
- **Click event → detail**: Expand full JSON payload
- **Rate counter**: Events per second
- **Export**: Save event log as JSON for test verification

### 16.9 Tab 5: Scenario Runner

Executes pre-defined end-to-end test scenarios that exercise the full MES workflow.

#### Scenario YAML Format

```yaml
# scenarios/03_production_flow.yaml
name: "Full Production Flow"
description: "Create order, release, process 3 units through 3 steps, complete order, verify ERP reports"
prerequisites:
  - scenario: "01_setup_plant"
  - scenario: "02_define_product"

variables:
  order_qty: 3

steps:
  - name: "Create production order"
    action: api_call
    method: POST
    path: /api/v1/orders
    body:
      product_id: "${product_id}"
      quantity_ordered: "${order_qty}"
      priority: "normal"
    expect_status: 201
    save:
      order_id: "$.data.id"

  - name: "Release order"
    action: api_call
    method: POST
    path: /api/v1/orders/${order_id}/release
    expect_status: 200

  - name: "Verify units created"
    action: api_call
    method: GET
    path: /api/v1/units?order_id=${order_id}
    expect_status: 200
    assert:
      - "$.data | length == ${order_qty}"
    save:
      unit_ids: "$.data[*].id"

  - name: "Process each unit through all steps"
    action: loop
    over: "${unit_ids}"
    as: unit_id
    steps:
      - name: "Start unit at step"
        action: api_call
        method: POST
        path: /api/v1/units/${unit_id}/start
        expect_status: 200

      - name: "Wait for simulated cycle time"
        action: wait
        duration_sec: 2

      - name: "Complete unit at step"
        action: api_call
        method: POST
        path: /api/v1/units/${unit_id}/complete
        expect_status: 200

      - name: "Move unit to next step"
        action: api_call
        method: POST
        path: /api/v1/units/${unit_id}/move
        expect_status: 200

  - name: "Complete order"
    action: api_call
    method: POST
    path: /api/v1/orders/${order_id}/complete
    expect_status: 200

  - name: "Verify ERP received completion report"
    action: check_erp_messages
    filter:
      type: "completion"
      order_id: "${order_id}"
    assert:
      - "count >= 1"
      - "$.payload.qty_good == ${order_qty}"

  - name: "Verify genealogy"
    action: api_call
    method: GET
    path: /api/v1/units/${unit_ids[0]}/genealogy
    expect_status: 200
    assert:
      - "$.data.steps | length == 3"
```

#### Scenario Runner Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Scenario Runner                                             │
│─────────────────────────────────────────────────────────────│
│  Available Scenarios:                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ☑ 01 Setup Plant              ✅ Passed   (2.1s)    │   │
│  │  ☑ 02 Define Product           ✅ Passed   (1.8s)    │   │
│  │  ☑ 03 Full Production Flow     🔄 Running  (step 8)  │   │
│  │  ☐ 04 Quality Flow             ⬜ Pending             │   │
│  │  ☐ 05 Full Lifecycle           ⬜ Pending             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [▶ Run Selected]  [▶▶ Run All]  [⏹ Stop]  [Reset Data]    │
│                                                              │
│  ┌─ Step Log ──────────────────────────────────────────────┐│
│  │  ✅ Create production order         201  0.04s          ││
│  │  ✅ Release order                   200  0.03s          ││
│  │  ✅ Verify units created            200  0.02s  (3)     ││
│  │  ✅ Start unit 1 at step 1          200  0.02s          ││
│  │  ✅ Complete unit 1 at step 1       200  0.03s          ││
│  │  ✅ Move unit 1 to step 2           200  0.02s          ││
│  │  🔄 Start unit 1 at step 2          ...                 ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  Total: 24 steps  |  Passed: 18  |  Failed: 0  | Time: 4.2s│
└─────────────────────────────────────────────────────────────┘
```

### 16.10 Data Seeder

Populates a clean database with realistic sample data via API calls:

```python
# seeders/seed_all.py
async def seed_all(client: httpx.AsyncClient):
    """Create a complete sample factory setup via REST API."""

    # Physical model
    site = await create(client, "/sites", {"name": "Demo Plant", "code": "DEMO", "timezone": "UTC"})
    area = await create(client, f"/sites/{site['id']}/areas", {"name": "Assembly", "code": "ASSY"})
    line = await create(client, f"/areas/{area['id']}/lines", {"name": "Line 1", "code": "L1"})

    wc1 = await create(client, f"/lines/{line['id']}/work-cells",
                        {"name": "Chassis Mount", "code": "WC-101", "wc_type": "automated"})
    wc2 = await create(client, f"/lines/{line['id']}/work-cells",
                        {"name": "Wiring", "code": "WC-102", "wc_type": "manual"})
    wc3 = await create(client, f"/lines/{line['id']}/work-cells",
                        {"name": "Final Test", "code": "WC-103", "wc_type": "automated"})

    eq1 = await create(client, f"/work-cells/{wc1['id']}/equipment",
                        {"name": "Robot Arm", "code": "R-001", "equipment_type": "robotic_arm",
                         "capabilities": {"axes": 6, "payload_kg": 10}})

    # Products, BOMs, Routes...
    product = await create(client, "/products",
                           {"name": "Widget-A", "code": "WGT-A", "version": "1.0", "uom": "ea"})
    route = await create(client, f"/products/{product['id']}/routes",
                         {"name": "Main Route", "version": "1.0", "is_default": True})
    # ... steps, parameters, materials, quality tests

    print(f"Seeded: 1 site, 1 area, 1 line, 3 work cells, 1 equipment, 1 product, 1 route")
```

**Seeder is invoked via:**
- Test client TUI: "Seed Data" button on dashboard
- Command line: `python -m mes_test_client.seeders.seed_all --url http://localhost:8000`
- Scenario prerequisites: scenarios can declare `seed_all` as a prerequisite

### 16.11 Running the Test Client

```bash
# Start MES server (in one terminal)
cd server && uvicorn mes.main:app --reload

# Start test client (in another terminal)
cd clients/test_client
python -m mes_test_client

# Or run specific operations from CLI
python -m mes_test_client seed                          # Seed sample data
python -m mes_test_client scenario run 03_production    # Run a scenario headless
python -m mes_test_client erp-sim --port 9090           # Start mock ERP server only
python -m mes_test_client equip-sim --opcua-port 4840   # Start equipment simulator only
```

### 16.12 Docker Integration

```yaml
# docker/docker-compose.yml (additions)
services:
  test-client:
    build: ../clients/test_client
    depends_on: [server, mqtt-broker]
    environment:
      MES_TEST_SERVER_URL: http://server:8000
      MES_TEST_ERP_SIM_PORT: 9090
      MES_TEST_OPCUA_PORT: 4840
      MES_TEST_MQTT_BROKER: mqtt-broker:1883
    ports:
      - "9090:9090"    # Mock ERP receiver
      - "4840:4840"    # OPC-UA simulator

  mqtt-broker:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
```

## 17. ERP Simulator GUI Client (ERP-SIM-GUI)

A standalone React + TypeScript web application for visually operating the SAP ERP Simulator plugin (§9.2.11). It provides a point-and-click interface for triggering inbound syncs (ERP → MES) and outbound reports (MES → ERP) without using curl or writing code.

> **Key distinction:** This is **not** part of the DT-CLIENT (§15). It is a separate single-purpose application dedicated to ERP integration testing. The DT-CLIENT configures the MES; the ERP Simulator GUI exercises the ERP adapter pipeline.

### 17.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  ERP Simulator GUI (port 5174)                       │
│                  React 19 + Vite 8 + Tailwind 4                      │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐  │
│  │  Sidebar Nav      │  │  Page Content                           │  │
│  │                   │  │                                         │  │
│  │  ─ Dashboard      │  │  ┌─────────────────────────────────┐   │  │
│  │                   │  │  │  Dashboard: adapter health       │   │  │
│  │  INBOUND          │  │  │  Inbound: sync button + table   │   │  │
│  │  ─ Orders         │  │  │  Outbound: form + result card   │   │  │
│  │  ─ Materials      │  │  │  Confirmations: doc log table   │   │  │
│  │  ─ Products       │  │  └─────────────────────────────────┘   │  │
│  │  ─ BOMs           │  │                                         │  │
│  │  ─ Routings       │  └──────────────────────────────────────────┘  │
│  │  ─ Work Centers   │                                               │
│  │                   │     HTTP (axios)                               │
│  │  OUTBOUND         │        │                                      │
│  │  ─ Completion     │        │  /api/v1/erp/*                       │
│  │  ─ Consumption    │        ▼                                      │
│  │  ─ Scrap          │  ┌──────────────────────────────────────────┐ │
│  │  ─ Labor          │  │  Vite dev proxy → http://localhost:8000  │ │
│  │  ─ Downtime       │  └──────────────────────────────────────────┘ │
│  │  ─ Quality        │                                               │
│  │  ─ Confirmations  │                                               │
│  └──────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  MES Server (port 8000)                               │
│                                                                      │
│  /api/v1/erp/*  →  PluginManager  →  SAP ERP Simulator Plugin       │
│                     .get_adapter_by_type("erp_inbound")              │
│                     .get_adapter_by_type("erp_outbound")             │
└─────────────────────────────────────────────────────────────────────┘
```

### 17.2 Project Structure

```
clients/erp_simulator/
├── package.json              # React 19, Vite 8, Tailwind 4, axios
├── vite.config.ts            # Port 5174, proxy /api → localhost:8000
├── tsconfig.json
├── tsconfig.app.json
├── index.html
└── src/
    ├── main.tsx              # React root
    ├── App.tsx               # Tab state + page routing
    ├── index.css             # Tailwind imports
    ├── vite-env.d.ts         # Vite type declarations
    ├── api/
    │   ├── client.ts         # Axios instance (baseURL: /api/v1)
    │   └── erp.ts            # TypeScript interfaces + API functions
    ├── components/
    │   ├── Layout.tsx        # Sidebar layout + tab navigation
    │   ├── DataTable.tsx     # Generic typed table component
    │   └── StatusBadge.tsx   # Green/red health dot
    └── pages/
        ├── DashboardPage.tsx       # Adapter health check
        ├── OrdersPage.tsx          # Sync production orders
        ├── MaterialsPage.tsx       # Sync materials
        ├── ProductsPage.tsx        # Sync products
        ├── BOMsPage.tsx            # Sync BOMs (product selector)
        ├── RoutingsPage.tsx        # Sync routings (product selector)
        ├── WorkCentersPage.tsx     # Sync work centers
        ├── CompletionPage.tsx      # Report production completion
        ├── ConsumptionPage.tsx     # Report material consumption
        ├── ScrapPage.tsx           # Report scrap
        ├── LaborPage.tsx           # Report labor time
        ├── DowntimePage.tsx        # Report downtime
        ├── QualityPage.tsx         # Report quality result
        └── ConfirmationsPage.tsx   # View SAP confirmation log
```

### 17.3 Pages

**Inbound sync pages** (6): Each has a \"Sync\" button that calls the corresponding `POST /api/v1/erp/sync/*` endpoint and displays results in a `DataTable`. BOMs and Routings pages include a product selector dropdown (FG-WIDGET-100, FG-WIDGET-200, FG-GADGET-300).\n\n**Outbound report pages** (6): Each renders a form with pre-filled realistic defaults (e.g., order `000001000100`, qty 95 good / 5 reject). On submit, calls the corresponding `POST /api/v1/erp/report/*` endpoint and displays the SAP document number or error.\n\n**Dashboard**: Calls `GET /api/v1/erp/health` and shows inbound/outbound adapter availability with green/red status badges.\n\n**Confirmations**: Calls `GET /api/v1/erp/confirmations` and displays all SAP confirmation documents in a table with type, SAP doc number, order, timestamp, and expandable JSON payload.

### 17.4 How to Run

```powershell
# Terminal 1: MES server with SAP simulator enabled
cd c:\\dev\\mes_ai\\server
$env:MES_AUTH_MODE = \"none\"
uvicorn mes.main:app --reload --port 8000

# Terminal 2: ERP Simulator GUI
cd c:\\dev\\mes_ai\\clients\\erp_simulator
npm run dev
# → http://localhost:5174
```

**Workflow:**
1. Open http://localhost:5174 → Dashboard tab
2. Click \"Check Health\" → both adapters should show green
3. Navigate to Inbound → Materials → click \"Sync Materials\" → 20 SAP materials appear
4. Navigate to Outbound → Report Completion → fill form → submit → receive SAP doc number
5. Navigate to Confirmations → click \"Refresh\" → see all generated SAP documents

## 18. Implementation Task Breakdown (Phase 3+)

Phase 3 implementation will follow this dependency order:

```
Layer 0 (Foundation):
  DATA-LAYER → EVENT-BUS → REST-API → AUTH → PLUGIN-FW

Layer 1 (Physical Model + Product):
  PHYS-MODEL → PROD-DEF → ROUTE-DEF

Layer 2 (Production):
  PROD-ORDER → WIP-TRACK → ROUTE-ENGINE

Layer 3 (Execution):
  DISPATCH → DATA-COLLECT → MAT-MGMT

Layer 4 (Quality & Analysis):
  QUAL-MGMT → PERF-ANALYSIS → GENEALOGY

Layer 5 (Integration - Phase 4):
  ERP-IBOUND → ERP-OBOUND → EQUIP-INTFC → TEST-INTFC
```

Each module implementation will include:
1. Database models (`models.py`) + Alembic migration
2. Pydantic schemas (`schemas.py`)
3. Business logic (`service.py`)
4. REST endpoints (`routes.py`)
5. Event definitions (`events.py`)
6. Unit tests
7. Integration tests

---

*Last updated: 2026-03-22 — Session S021 (SAP ERP Simulator, ERP Simulator GUI Client, ERP REST API endpoints)*
