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

# Custom permissions this plugin introduces (auto-registered on install)
permissions:
  - id: my_custom_plugin.config.read
    description: View optimizer configuration
  - id: my_custom_plugin.config.update
    description: Modify optimizer weights and parameters
  - id: my_custom_plugin.simulate
    description: Run dispatch simulations

# Existing core permissions this plugin's logic requires
required_core_permissions:
  - dispatch.read
  - wip.read

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
| **Work Center Master** | ERP work center definitions | PHYS-MODEL module | Initial setup + scheduled sync |

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

    async def sync_work_centers(self) -> list[WorkCenterDTO]: ...


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
| Work Centers | `API_WORK_CENTERS_SRV` | `BAPI_WORKCENTER_GET_DETAIL` |

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
| Work Centers / Resources | `GET /manufacturingResources` |

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

```python
# .env
MES_ERP_ADAPTER=sap_s4hana              # "sap_s4hana" | "sap_ecc" | "oracle_cloud" | "oracle_ebs" | "dynamics365" | "infor_m3" | "mock"
MES_ERP_BASE_URL=https://sap-server.factory.com/sap/opu/odata/sap
MES_ERP_AUTH_TYPE=oauth2                 # "oauth2" | "basic" | "api_key"
MES_ERP_CLIENT_ID=mes-integration
MES_ERP_CLIENT_SECRET=secret
MES_ERP_TOKEN_URL=https://sap-server.factory.com/oauth/token
MES_ERP_POLL_INTERVAL_SEC=300            # 5 minutes
MES_ERP_RETRY_MAX_ATTEMPTS=5
MES_ERP_RETRY_BACKOFF_SEC=30
```

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

```python
# .env — Direct equipment connection
MES_EQUIP_ADAPTER=opcua                     # "opcua" | "mqtt" | "modbus" | "rest" | "mock"
MES_EQUIP_OPCUA_URL=opc.tcp://plc-01:4840
MES_EQUIP_OPCUA_SECURITY_POLICY=Basic256Sha256
MES_EQUIP_OPCUA_CERT_PATH=/certs/client.pem
MES_EQUIP_OPCUA_KEY_PATH=/certs/client.key

# .env — MQTT
MES_EQUIP_MQTT_BROKER=mqtt://broker.factory.com:1883
MES_EQUIP_MQTT_TOPIC_PREFIX=factory/line-1
MES_EQUIP_MQTT_QOS=1

# .env — MOM-based equipment data
MES_EQUIP_MOM_TYPE=kafka                    # "kafka" | "rabbitmq" | "activemq" | "ibmmq"
MES_EQUIP_KAFKA_BOOTSTRAP=kafka:9092
MES_EQUIP_KAFKA_TOPIC=equipment-data
MES_EQUIP_KAFKA_GROUP_ID=mes-consumer

# .env — Modbus
MES_EQUIP_MODBUS_HOST=192.168.1.100
MES_EQUIP_MODBUS_PORT=502
MES_EQUIP_MODBUS_UNIT_ID=1
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
| **resource** | `site`, `area`, `line`, `work_center`, `equipment`, `product`, `route`, `order`, `unit`, `lot`, `test`, `nc`, `user`, `role`, etc. |
| **action** | `read`, `create`, `update`, `delete`, `execute` |

**Wildcard matching** is supported at any level:
- `*` — all permissions (admin only)
- `wip.*` — all WIP operations
- `*.read` — read access to everything
- `quality.*` — all quality operations

#### 11.3.2 Full Permission Map

| Module | Permission | Description | Endpoints Guarded |
|---|---|---|---|
| **PHYS-MODEL** | `physical_model.read` | View sites, areas, lines, work centers, equipment | All GET endpoints |
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

1. **Operator scans a unit at a work center**: Needs `wip.unit.move` — allowed. Tries to modify a production route — needs `product_def.update` — **denied (403)**.
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

## 15. Implementation Task Breakdown (Phase 3+)

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
