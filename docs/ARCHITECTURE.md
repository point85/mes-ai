# MES AI — Architecture Document

> **Living document** — updated as architectural decisions are made.  
> Current status: **Phase 2 Complete** — fully populated with technology stack, data model, API design, plugin framework, event bus, and integration adapter specifications.

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
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Data Layer      │  │ ERP Adapter  │  │ Equipment       │   │
│  │ (Multi-RDBMS)   │  │ (ERP-*)      │  │ Adapter         │   │
│  └────────────────┘  └──────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────┘
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

### 3.3 Development & CI

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
│   ├── plugins/                       # Built-in example plugins
│   │   └── example_plugin/
│   │       ├── manifest.yaml
│   │       └── plugin.py
│   │
│   └── tests/                         # Automated tests
│       ├── conftest.py                # Shared fixtures (test DB, client)
│       ├── unit/                      # Unit tests (per module)
│       └── integration/               # Integration tests (API-level)
│
├── clients/                           # Client implementations
│   ├── runtime_gui/                   # RT-GUI (React)
│   ├── runtime_headless/              # RT-HEADLESS (Python)
│   └── design_time/                   # DT-CLIENT (React)
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
│  WorkCenter ──1:N──▶ Equipment                               │
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
│  EquipmentStateLog ──▶ Equipment (up/down/idle/maint)        │
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
| **ProductionLine** | `id`, `name`, `code`, `description`, `area_id` | → Area, → WorkCenters |
| **WorkCenter** | `id`, `name`, `code`, `description`, `line_id`, `wc_type` (manual/automated) | → ProductionLine, → Equipment |
| **Equipment** | `id`, `name`, `code`, `description`, `work_center_id`, `equipment_type`, `status` (up/down/idle), `capabilities` (JSON) | → WorkCenter, → RouteSteps (M:N) |

#### Product Definition (PROD-DEF)

| Entity | Fields | Relations |
|---|---|---|
| **ProductDefinition** | `id`, `name`, `code`, `version`, `description`, `uom`, `product_type` (discrete/process) | → BillOfMaterials, → ProcessRoutes |
| **BillOfMaterial** | `id`, `product_id`, `version`, `effective_date`, `expiry_date` | → ProductDefinition, → BOMItems |
| **BOMItem** | `id`, `bom_id`, `material_id`, `quantity`, `uom`, `position` | → BillOfMaterial, → MaterialDefinition |
| **ProcessRoute** | `id`, `product_id`, `version`, `name`, `description`, `is_default` | → ProductDefinition, → RouteSteps |
| **RouteStep** | `id`, `route_id`, `sequence`, `name`, `step_type` (production/inspection/rework), `work_center_id`, `expected_cycle_time_sec` | → ProcessRoute, → WorkCenter, → StepParameters |
| **StepParameter** | `id`, `step_id`, `name`, `data_type`, `uom`, `target_value`, `lower_limit`, `upper_limit`, `is_required` | → RouteStep |

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
| **EquipmentStateLog** | `id`, `equipment_id`, `state` (running/idle/down_planned/down_unplanned/maintenance), `started_at`, `ended_at`, `reason_code`, `notes` | → Equipment |
| **ProductionCounter** | `id`, `equipment_id`, `order_id`, `shift_date`, `good_count`, `reject_count`, `rework_count`, `ideal_cycle_time_sec`, `actual_run_time_sec` | → Equipment, → ProductionOrder |

#### Genealogy (GENEALOGY)

Genealogy is built from the relationships between `Unit/Lot`, `UnitHistory/LotHistory`, `MaterialConsumption`, `TestResult`, and `DataPoint`. No separate genealogy table is needed — it is a query that traverses existing records to build the full as-built record for a unit or lot.

#### Auth (AUTH)

| Entity | Fields | Relations |
|---|---|---|
| **User** | `id`, `username`, `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser` | → UserRoles |
| **Role** | `id`, `name`, `description`, `permissions` (JSON array of permission strings) | → UserRoles |
| **UserRole** | `id`, `user_id`, `role_id` | → User, → Role |

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
class WorkCenter(Base):
    __tablename__ = "work_center"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_line.id"))

    # Many-to-One: each work center belongs to one production line
    production_line: Mapped["ProductionLine"] = relationship(back_populates="work_centers")

    # One-to-Many: each work center has many equipment
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="work_center")
```

**Used for:** Site→Areas, Area→Lines, Line→WorkCenters, WorkCenter→Equipment, ProductionOrder→Units, ProductionOrder→Lots, Route→Steps, Step→Parameters, and all other parent-child hierarchies.

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
| One-to-Many | `relationship()` + `ForeignKey` | Site→Areas, Line→WorkCenters, Order→Units, Route→Steps, etc. |
| Many-to-One | Same (reverse side) | Equipment→WorkCenter, Unit→RouteStep, Unit→Equipment |
| Many-to-Many | `relationship(secondary=...)` | RouteStep↔Equipment |
| Many-to-Many + data | Association object class | User↔Role (via UserRole) |

All relationship types are fully portable across PostgreSQL, SQL Server, Oracle, and SQLite.

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
| `GET` | `/api/v1/lines/{line_id}/work-centers` | List work centers in a line |
| `POST` | `/api/v1/lines/{line_id}/work-centers` | Create work center in a line |
| `GET` | `/api/v1/work-centers/{wc_id}` | Get work center by ID |
| `GET` | `/api/v1/work-centers/{wc_id}/equipment` | List equipment in a work center |
| `POST` | `/api/v1/work-centers/{wc_id}/equipment` | Create equipment in a work center |
| `GET` | `/api/v1/equipment/{equip_id}` | Get equipment by ID |
| `PUT` | `/api/v1/equipment/{equip_id}` | Update equipment |
| `PATCH` | `/api/v1/equipment/{equip_id}/status` | Update equipment status |

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
| `GET` | `/api/v1/dispatch/queue/{work_center_id}` | Get dispatch queue for a work center |

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
| `GET` | `/api/v1/performance/oee` | Calculate OEE (query params: equipment, time range) |
| `GET` | `/api/v1/performance/equipment-states` | Query equipment state history |
| `POST` | `/api/v1/performance/equipment-states` | Record equipment state change |
| `GET` | `/api/v1/performance/counters` | Query production counters |
| `POST` | `/api/v1/performance/counters` | Record/update production counter |

#### Auth (AUTH)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate, receive JWT |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT token |
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `GET/POST` | `/api/v1/auth/users` | List / create users (admin) |
| `GET/PUT` | `/api/v1/auth/users/{user_id}` | Get / update user (admin) |
| `GET/POST` | `/api/v1/auth/roles` | List / create roles (admin) |

#### Plugin Management (PLUGIN-FW)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/plugins` | List installed plugins |
| `POST` | `/api/v1/plugins/install` | Install a plugin |
| `DELETE` | `/api/v1/plugins/{plugin_id}` | Uninstall a plugin |
| `POST` | `/api/v1/plugins/{plugin_id}/enable` | Enable a plugin |
| `POST` | `/api/v1/plugins/{plugin_id}/disable` | Disable a plugin |
| `GET` | `/api/v1/plugins/{plugin_id}/config` | Get plugin configuration |
| `PUT` | `/api/v1/plugins/{plugin_id}/config` | Update plugin configuration |

#### Real-Time Events (WebSocket)

| Endpoint | Description |
|---|---|
| `WS /api/v1/events/ws` | WebSocket connection for real-time event streaming |
| `GET /api/v1/events/subscriptions` | List current event subscriptions |
| `POST /api/v1/events/subscriptions` | Subscribe to event topics |

## 7. Plugin Framework (PLUGIN-FW)

### 7.1 Plugin Structure

A plugin is a Python package with a standard layout:

```
my_plugin/
├── manifest.yaml          # Plugin metadata & declarations
├── plugin.py              # Plugin entry point (implements MESPlugin)
├── models.py              # Optional: additional DB models
├── schemas.py             # Optional: additional Pydantic schemas
├── routes.py              # Optional: additional REST endpoints
├── events.py              # Optional: event handlers
└── requirements.txt       # Optional: additional dependencies
```

### 7.2 Plugin Manifest

```yaml
id: my-custom-plugin
name: My Custom Plugin
version: 1.0.0
description: Adds custom dispatching logic for multi-criteria optimization
author: AI Agent
min_mes_version: "0.1.0"

# What this plugin extends
extension_points:
  - type: dispatch_strategy
    name: multi_criteria_dispatch
  - type: operation_hook
    hook: before_unit_move
    handler: plugin:on_before_unit_move
  - type: rest_endpoint
    prefix: /api/v1/custom/optimization

# Events this plugin subscribes to
event_subscriptions:
  - "wip.unit.moved"
  - "equipment.state.changed"

# Dependencies on other plugins
dependencies: []

# Plugin configuration schema (JSON Schema)
config_schema:
  type: object
  properties:
    optimization_weight:
      type: number
      default: 0.7
    max_queue_depth:
      type: integer
      default: 10
```

### 7.3 Plugin Base Class

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
```

### 7.4 Plugin Lifecycle

```
discover → validate manifest → load module → initialize(config)
    → start() → [running] → stop() → unload
```

1. **Discover**: Scan `plugins/` directory and installed packages for `manifest.yaml`
2. **Validate**: Check manifest schema, version compatibility, dependency resolution
3. **Load**: Import Python module, instantiate `MESPlugin` subclass
4. **Initialize**: Call `initialize(config)` with merged default + user config
5. **Start**: Call `start()` — plugin is now active
6. **Stop**: Call `stop()` on shutdown or disable — plugin cleans up

### 7.5 Extension Points

| Type | Description | Example |
|---|---|---|
| **dispatch_strategy** | Custom dispatching algorithm for unit/lot routing | Multi-criteria optimizer, priority-based, load-balanced |
| **operation_hook** | Before/after hooks on core operations | Validate custom business rules before unit move |
| **rest_endpoint** | Additional REST API routes | Custom reporting endpoint, equipment-specific API |
| **event_handler** | React to system events | Send notification on quality failure, Update external system |
| **data_processor** | Transform/validate collected data points | Unit conversion, outlier detection, SPC calculation |
| **report_generator** | Custom report definitions | Shift summary, quality trends, yield analysis |
| **equipment_driver** | Custom equipment communication protocol | Proprietary PLC protocol, custom sensor interface |

### 7.6 Plugin Isolation

- Plugins run in the same process but are loaded in separate module namespaces
- Plugin errors are caught and logged; a failing plugin does not crash the server
- Plugin database models use a schema prefix: `plugin_{plugin_id}_` to avoid table name conflicts
- Plugin configuration is stored in a `plugin_config` table, not in environment variables

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
| `quality.test.passed` | QUAL-MGMT | `{test_id, unit_id, result_id}` |
| `quality.test.failed` | QUAL-MGMT | `{test_id, unit_id, result_id}` |
| `quality.nc.created` | QUAL-MGMT | `{nc_id, unit_id, nc_type}` |
| `material.consumed` | MAT-MGMT | `{material_lot_id, unit_id, quantity}` |
| `dispatch.evaluated` | DISPATCH | `{unit_id, strategy, recommendation}` |
| `dispatch.executed` | DISPATCH | `{unit_id, destination_step_id}` |
| `data.collected` | DATA-COLLECT | `{definition_id, unit_id, value}` |
| `plugin.loaded` | PLUGIN-FW | `{plugin_id, version}` |
| `plugin.error` | PLUGIN-FW | `{plugin_id, error}` |
| `auth.login` | AUTH | `{user_id}` |

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

For multi-server deployments, the in-process event bus can be replaced with Redis Pub/Sub or NATS by swapping the transport layer. The `MESEvent` schema and handler interface remain identical.

## 9. Integration Adapters

### 9.1 Adapter Architecture

All integration adapters implement a common abstract interface. Each adapter type has a mock implementation for testing and development.

```python
class BaseAdapter(ABC):
    """Base for all integration adapters."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

### 9.2 ERP Adapters (ERP-IBOUND, ERP-OBOUND)

**Inbound (ERP → MES):**
- Receive production orders (schedule, quantities, product, BOM)
- Receive material master data
- Receive product definition updates

**Outbound (MES → ERP):**
- Report production completions (good/reject quantities)
- Report material consumption (backflush or real-time)
- Report labor time
- Report equipment downtime

**Interface:**
```python
class ERPInboundAdapter(BaseAdapter):
    async def sync_production_orders(self) -> list[ProductionOrder]: ...
    async def sync_materials(self) -> list[MaterialDefinition]: ...
    async def sync_products(self) -> list[ProductDefinition]: ...

class ERPOutboundAdapter(BaseAdapter):
    async def report_completion(self, order_id, qty_good, qty_reject) -> None: ...
    async def report_consumption(self, order_id, materials: list) -> None: ...
    async def report_downtime(self, equipment_id, duration, reason) -> None: ...
```

**Mock implementation:** File-based (JSON import/export) for development and testing.

### 9.3 Equipment Adapter (EQUIP-INTFC)

Communicates with production equipment (PLCs, microcontrollers, sensors).

**Protocols supported (via plugins):**
- OPC-UA (primary industrial standard)
- MQTT (lightweight IoT)
- Modbus TCP (legacy equipment)
- HTTP/REST (modern smart equipment)

**Interface:**
```python
class EquipmentAdapter(BaseAdapter):
    async def read_tag(self, tag_name: str) -> Any: ...
    async def write_tag(self, tag_name: str, value: Any) -> None: ...
    async def subscribe_tag(self, tag_name: str, callback) -> None: ...
    async def get_equipment_state(self) -> EquipmentState: ...
```

**Mock implementation:** In-memory tag store with simulated state changes and configurable latency.

### 9.4 Test Equipment Adapter (TEST-INTFC)

Collects test results from quality/test equipment.

**Interface:**
```python
class TestEquipmentAdapter(BaseAdapter):
    async def get_test_result(self, test_id: str) -> TestResult: ...
    async def subscribe_results(self, callback) -> None: ...
```

**Mock implementation:** Generates random test results within configurable pass/fail distributions.

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

### 11.1 Authentication

- **Method**: JWT (JSON Web Token) via `Authorization: Bearer <token>` header
- **Token lifetime**: Access token (15 min), Refresh token (7 days)
- **Password storage**: bcrypt hash
- **Login flow**: `POST /api/v1/auth/login` with `{username, password}` → receive `{access_token, refresh_token}`

### 11.2 Authorization

- **Model**: Role-Based Access Control (RBAC)
- **Permissions**: Dot-notation strings (`physical_model.create`, `wip.unit.move`, `quality.nc.resolve`, `plugin.manage`, etc.)
- **Enforcement**: FastAPI dependency injection — routes declare required permissions
- **Default roles**: `admin` (all), `engineer` (design + data), `operator` (runtime WIP), `viewer` (read-only)

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
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

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

## 14. Implementation Task Breakdown (Phase 3+)

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

*Last updated: 2026-02-22 — Session S002 (Phase 2 Architecture & Design, updated for multi-RDBMS support)*
