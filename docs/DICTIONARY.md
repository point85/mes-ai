# MES AI — Project Dictionary

> **Shared terminology** for communication between human and AI throughout all project phases.  
> All conversations, documents, code comments, and identifiers should use these terms consistently.

---

## How to Use This Document

- **Bold terms** are the canonical form — use them in conversation and code.
- **Module IDs** (e.g., `PHYS-MODEL`) are used in architecture references, commit messages, and task tracking.
- When a term has a common synonym, it is listed under "Also known as" — prefer the canonical term.

---

## 1. Manufacturing & MES Domain Terms

### Standards & Frameworks

| Term | Definition |
|---|---|
| **ISA-95** / **IEC 62264** | International standard that defines the integration between enterprise (ERP) and control (shop floor) systems. Provides object models for physical assets, product definitions, production schedules, and performance data. Our data model is aligned with ISA-95 Level 3. |
| **MESA International** | Manufacturing Enterprise Solutions Association. Defines the **MESA-11** model of 11 core MES functions (resource allocation, dispatching, data collection, quality management, etc.). Our module list covers all 11 functions. |
| **MESA-11** | The 11 core MES functions defined by MESA International: resource allocation & status, operations/detail scheduling, dispatching, document control, data collection/acquisition, labor management, quality management, process management, maintenance management, product tracking & genealogy, performance analysis. |
| **Level 3** | In the ISA-95 hierarchy, Level 3 = Manufacturing Operations Management (MOM). This is where MES lives — between Level 4 (ERP/business planning) and Level 2 (control systems/PLCs). |
| **MOM** | Manufacturing Operations Management — the ISA-95 Level 3 layer. Sometimes used interchangeably with MES, though MOM is broader (includes quality, maintenance, inventory operations). |

### Physical Model

| Term | Definition |
|---|---|
| **Site** | A physical manufacturing facility (factory, plant). Top-level in the ISA-95 physical hierarchy. Has a timezone and address. |
| **Area** | A section within a site (e.g., "Assembly Hall A", "Paint Shop"). Contains production lines. |
| **Production Line** | An ordered sequence of work cells that produce a product family. Also known as: *manufacturing line*, *line*. |
| **Work Cell** | A grouping of one or more pieces of equipment that perform a specific manufacturing operation. Has a type: `manual` or `automated`. Also known as: *work station*, *work center*. |
| **Equipment** | A single physical machine, device, or tool at a work cell (e.g., a CNC machine, oven, robot, test station). Has `capabilities` (JSON) describing what it can do. |
| **Equipment State** | The operational status of equipment: `running`, `idle`, `down_planned`, `down_unplanned`, `maintenance`. Tracked in `EquipmentStateLog`. |

### Product Definition

| Term | Definition |
|---|---|
| **Product Definition** | The master record describing what a product is — its name, code, version, unit of measure, and type (`discrete` or `process`). Links to BOMs and operations definitions. |
| **BOM** | **Bill of Materials** — the list of raw materials and sub-components needed to manufacture one unit of a product. Versioned. |
| **BOM Item** | A single line in a BOM specifying a material, its required quantity, and unit of measure. |
| **Operations Definition** | ISA-95 Part 2 "Operations Definition". The ordered sequence of process segments required to produce a product. A product can have multiple versions; one is marked `is_default`. Also known as: *process route*, *routing*, *recipe* (in process manufacturing). Class: `OperationsDefinition` (formerly `ProcessRoute`). |
| **Process Segment** | ISA-95 Part 2 "Process Segment". A single manufacturing operation within an Operations Definition. Defines the required equipment class, cycle time, and segment type: `production`, `inspection`, or `rework`. Class: `ProcessSegment` (formerly `RouteStep`). |
| **Segment Parameter** | A measurable or settable parameter for a process segment (e.g., temperature, pressure, torque). Has target value and upper/lower limits. Class: `SegmentParameter` (formerly `StepParameter`). |
| **Process Segment Dependency** | ISA-95 Part 2 "Process Segment Dependency". A directed edge between two process segments supporting non-linear routing (rework loops, MRB branches, disposition-driven paths). Class: `ProcessSegmentDependency` (formerly `StepTransition`). |
| **Cycle Time** | The expected duration (in seconds) for one unit/lot to complete a process segment. Used for scheduling and OEE calculations. |

### Production

| Term | Definition |
|---|---|
| **Production Order** | A directive to manufacture a specific quantity of a product. Also known as: *work order*, *manufacturing order*, *shop order*. Has statuses: `created` → `released` → `in_progress` → `completed` → `closed`. Links to an ERP reference for traceability. |
| **Unit** | A single serialized item being tracked through the manufacturing process. Each unit has a unique `serial_number`, a current step, current equipment, and status: `queued`, `in_process`, `completed`, `scrapped`, `on_hold`. |
| **Lot** | A batch of items tracked as a group (used when individual serialization is impractical). Has a `lot_number` and quantity. Also known as: *batch*. |
| **WIP** | **Work In Process** — units and lots currently moving through the manufacturing process (not yet completed or shipped). |
| **Dispatching** | The act of assigning a unit or lot to a specific piece of equipment for its next route step. Can be manual or automatic (via a dispatch strategy). |
| **Dispatch Strategy** | The algorithm used to select equipment for a unit/lot. Built-in strategies: `manual`, `first_available`, `shortest_queue`, `round_robin`, `capability_match`. Custom strategies can be added via plugins. |

### Tracking & History

| Term | Definition |
|---|---|
| **Unit History** | A record of a unit passing through a route step — when it entered, when it exited, the result (`pass`/`fail`/`rework`), which equipment and operator, plus a data snapshot. |
| **Lot History** | Same as unit history but for lot-based tracking, including quantity in/out/scrapped. |
| **Genealogy** | The complete as-built record for a unit or lot — all materials consumed, steps performed, data collected, tests executed. Built by querying across `UnitHistory`, `MaterialConsumption`, `TestResult`, and `DataPoint`. No separate table needed. |
| **Traceability** | The ability to trace a finished product back to its raw materials, process conditions, and test results. Genealogy provides full traceability. |

### Quality

| Term | Definition |
|---|---|
| **Quality Test** | A defined test to be performed at a route step. Types: `inline` (during production), `offline` (at a separate station), `destructive` (sample is destroyed). |
| **Test Result** | The outcome of executing a quality test on a unit or lot. Contains measured values (JSON), pass/fail result, operator, equipment, and timestamp. |
| **Non-Conformance** (**NC**) | A record that a unit or lot failed to meet specifications. Types: `defect`, `out_of_spec`, `other`. Dispositions: `rework`, `scrap`, `use_as_is`, `return`. Also known as: *defect record*, *NCR*. |
| **SPC** | **Statistical Process Control** — monitoring process stability using control charts and statistical methods. Relevant to `PERF-ANALYSIS` and `DATA-COLLECT` modules. |

### Materials

| Term | Definition |
|---|---|
| **Material Definition** | The master record for a type of material. Types: `raw`, `intermediate`, `finished`. |
| **Material Lot** | A specific received batch of a material with quantity, supplier, expiry date, and status: `available`, `reserved`, `consumed`, `expired`. |
| **Material Consumption** | A record that a specific quantity of a material lot was consumed by a unit or lot at a specific route step. Enables material traceability. |

### Performance

| Term | Definition |
|---|---|
| **OEE** | **Overall Equipment Effectiveness** — the standard manufacturing KPI calculated as: $OEE = Availability \times Performance \times Quality$. Derived from `EquipmentStateLog` and `ProductionCounter` data. |
| **Availability** | The ratio of actual production time to planned production time. Downtime reduces availability. |
| **Performance** (KPI) | The ratio of actual throughput to ideal throughput (based on ideal cycle time). Slow cycles reduce performance. |
| **Quality** (KPI) | The ratio of good units to total units produced. Rejects and rework reduce quality. |
| **Downtime** | Period when equipment is not producing. Can be `planned` (maintenance window) or `unplanned` (breakdown). |

---

## 2. Architecture & Technical Terms

### System Components

| Term | Definition |
|---|---|
| **MES Server** | The Python/FastAPI backend application that houses all business logic, API endpoints, event bus, and plugin framework. |
| **Runtime Client** (**RT-CLIENT**) | The React web application used by shop floor operators and supervisors during production. Real-time dashboards, WIP tracking, data entry. |
| **Runtime Headless Client** (**RT-HEADLESS**) | A Python `httpx`-based client for automation scripts, equipment integration, and headless workflows (no UI). |
| **Design-Time Client** (**DT-CLIENT**) | The React web application used by manufacturing engineers and admins to configure products, routes, equipment, and plugins. |
| **Plugin** | A self-contained extension package that adds or modifies MES behavior without changing core code. Defined by a `manifest.yaml` and a Python class extending `MESPlugin`. |
| **Core Module** | One of the 12 built-in functional modules that implement the MESA-11 MES functions. Core modules are not plugins — they ship with the server. |
| **Adapter** | An abstraction layer between the MES core and an external system (ERP, equipment, test equipment). Each adapter type has an abstract interface with a mock implementation for development. |

### Module IDs

These short identifiers are used in architecture docs, code paths, commit messages, and task tracking:

| Module ID | Full Name | Code Path |
|---|---|---|
| `PHYS-MODEL` | Physical Model | `server/src/mes/core/physical_model/` |
| `PROD-DEF` | Product Definition | `server/src/mes/core/product_def/` |
| `PROD-ORDER` | Production Order | `server/src/mes/core/production/` |
| `WIP-TRACK` | WIP Tracking | `server/src/mes/core/wip/` |
| `ROUTE-DEF` | Route Definition | `server/src/mes/core/routing/` |
| `ROUTE-ENGINE` | Route Engine | `server/src/mes/core/routing/` |
| `DISPATCH` | Dispatching Engine | `server/src/mes/core/dispatch/` |
| `MAT-MGMT` | Material Management | `server/src/mes/core/material/` |
| `DATA-COLLECT` | Data Collection | `server/src/mes/core/data_collection/` |
| `QUAL-MGMT` | Quality Management | `server/src/mes/core/quality/` |
| `PERF-ANALYSIS` | Performance Analysis | `server/src/mes/core/performance/` |
| `GENEALOGY` | Genealogy | `server/src/mes/core/genealogy/` |
| `DATA-LAYER` | Data Layer (framework) | `server/src/mes/framework/db/` |
| `EVENT-BUS` | Event Bus (framework) | `server/src/mes/framework/events/` |
| `REST-API` | REST API (framework) | `server/src/mes/framework/api/` |
| `AUTH` | Authentication & Authorization | `server/src/mes/framework/auth/` |
| `PLUGIN-FW` | Plugin Framework | `server/src/mes/framework/plugin/` |
| `ERP-IBOUND` | ERP Inbound Adapter | `server/src/mes/adapters/erp/` |
| `ERP-OBOUND` | ERP Outbound Adapter | `server/src/mes/adapters/erp/` |
| `EQUIP-INTFC` | Equipment Interface | `server/src/mes/adapters/equipment/` |
| `TEST-INTFC` | Test Equipment Interface | `server/src/mes/adapters/test_equipment/` |
| `RT-CLIENT` | Runtime Client | `clients/run_time/` |
| `RT-HEADLESS` | Runtime Headless Client | `clients/runtime_headless/` |
| `DT-CLIENT` | Design-Time Client | `clients/design_time/` |
| `SESSION-META` | Session/Configuration | `server/src/mes/config.py` |

### Framework & Infrastructure

| Term | Definition |
|---|---|
| **Event Bus** | In-process async publish/subscribe system using dot-notation topics (e.g., `wip.unit.moved`). Decouples modules. Can be swapped for a distributed MOM transport (Kafka, NATS, Redis Streams) for multi-server deployments. |
| **Event Topic** | A dot-notation string identifying an event type (e.g., `production.order.released`, `quality.nc.created`). Supports wildcard subscriptions (`wip.*`). |
| **MESEvent** | The standard event schema: `event_id` (UUID), `topic`, `timestamp`, `source_module`, `payload` (dict), `correlation_id`. |
| **Plugin Manifest** | The `manifest.yaml` file in every plugin directory that declares metadata, dependencies, extension points, configuration schema, required permissions, and MES version compatibility. |
| **Extension Point** | A named hook where plugins can inject behavior. Seven types: `dispatch_strategy`, `operation_hook`, `rest_endpoint`, `event_handler`, `data_processor`, `report_generator`, `equipment_driver`. |
| **MESPlugin Base Class** | The abstract Python class all plugins extend. Provides lifecycle methods: `on_load()`, `on_start()`, `on_stop()`, `on_unload()`. |
| **Plugin Lifecycle** | The states a plugin passes through: `discover` → `validate` → `load` → `initialize` → `start` → `stop`. Managed by the plugin framework. |
| **Data Layer** | The framework module that manages SQLAlchemy engines, async sessions, the base ORM model, and Alembic migrations. Abstracts multi-RDBMS support. |
| **Response Envelope** | The standard JSON structure wrapping all API responses: `{ data, meta, errors }`. Ensures consistent client-side parsing. |
| **Cursor-Based Pagination** | Pagination using an opaque cursor token (not page numbers). More stable for real-time data where records are constantly being inserted. Returned in `meta.next_cursor`. |

### Authentication & Authorization

| Term | Definition |
|---|---|
| **OIDC** | **OpenID Connect** — the authentication protocol used by the MES. Delegates login to an external Identity Provider. MES never stores passwords. |
| **IdP** | **Identity Provider** — the external system that authenticates users (e.g., Microsoft Entra ID, Keycloak, WSO2, Okta). |
| **JWT** | **JSON Web Token** — the token format used for API authentication. Issued by the IdP, validated by the MES server. Contains user identity and claims. |
| **RBAC** | **Role-Based Access Control** — permission model where users are assigned roles, and roles grant permissions. |
| **Permission** | A dot-notation string representing a specific action on a resource (e.g., `production.orders.create`, `quality.nc.update`). Enforced per API endpoint. |
| **Role** | A named collection of permissions. Default roles: `operator`, `supervisor`, `engineer`, `admin`. `admin` has wildcard `*` permission. |
| **JIT Provisioning** | **Just-In-Time** user provisioning — when a user logs in via OIDC for the first time, their MES user record is automatically created from token claims. No manual user setup needed. |
| **IdP Group Mapping** | Automatic role assignment based on the user's group membership in the IdP (e.g., IdP group "MES_Supervisors" maps to MES role `supervisor`). |

### Communication Protocols

| Term | Definition |
|---|---|
| **OPC-UA** | **Open Platform Communications Unified Architecture** — the primary industrial communication standard for equipment. Used to read/write tags from PLCs, SCADA, and DCS systems. Python library: `asyncua`. |
| **MQTT** | **Message Queuing Telemetry Transport** — lightweight pub/sub protocol for IoT devices and sensors. Python library: `aiomqtt`. |
| **Modbus TCP** | A legacy industrial protocol for communicating with PLCs and instrumentation over TCP/IP. Python library: `pymodbus`. |
| **AMQP** | **Advanced Message Queuing Protocol** — wire protocol for message brokers. Version 0-9-1 used by RabbitMQ (`aio-pika`). Version 1.0 used by ActiveMQ Artemis / IBM MQ (`proton`). |
| **STOMP** | **Simple Text Oriented Messaging Protocol** — text-based protocol for accessing JMS brokers (ActiveMQ, TIBCO). Python library: `stomp.py`. |
| **JMS** | **Java Message Service** — a Java API spec (not a wire protocol). Python accesses JMS brokers via STOMP or AMQP 1.0. |
| **MOM** | **Message-Oriented Middleware** — enterprise messaging systems (Kafka, RabbitMQ, ActiveMQ, IBM MQ, NATS) used for asynchronous communication between systems. |
| **Tag** | In equipment communication, a named data point on a PLC or SCADA system (e.g., `Oven.Temperature`, `Conveyor.Speed`). Read/written via OPC-UA or Modbus. |

### ERP Integration

| Term | Definition |
|---|---|
| **ERP** | **Enterprise Resource Planning** — the business system that manages financials, procurement, inventory, and production planning. MES receives production orders from ERP and reports completions back. |
| **Inbound Adapter** (`ERP-IBOUND`) | Receives data *from* ERP *into* MES (e.g., production orders, material masters, BOM updates). |
| **Outbound Adapter** (`ERP-OBOUND`) | Sends data *from* MES *to* ERP (e.g., production completions, material consumption, scrap reporting). |
| **Transform Layer** | The component within an ERP adapter that maps between ERP-specific field names and MES canonical schemas. Isolates vendor-specific knowledge. |
| **OData** | Open Data Protocol — REST-based API standard used by SAP S/4HANA and Microsoft D365 F&O. |
| **RFC** / **BAPI** | SAP-specific remote function call interfaces used by SAP ECC. Accessed via `pyrfc` (requires SAP NW RFC SDK). |
| **IDoc** | SAP Intermediate Document — asynchronous message format for SAP ECC integration. |

---

## 3. Development & Process Terms

### Project Phases

| Term | Definition |
|---|---|
| **Phase 1 (P1)** | Survey & Requirements — commercial MES analysis, module identification. Deliverable: `MES_SURVEY.md`. **Complete.** |
| **Phase 2 (P2)** | Architecture & Design — full system architecture. Deliverable: `ARCHITECTURE.md`. **Complete.** |
| **Phase 3 (P3)** | Core Server Implementation — build the server in 5 layers. **Next phase.** |
| **Phase 4 (P4)** | Client Implementation — build RT-CLIENT, DT-CLIENT, RT-HEADLESS. |
| **Phase 5 (P5)** | Integration & Testing — end-to-end integration, load testing, documentation. |

### Implementation Layers (Phase 3)

| Term | Definition |
|---|---|
| **Layer 0: Foundation** | `DATA-LAYER`, `EVENT-BUS`, `REST-API`, `AUTH`, `PLUGIN-FW` — framework infrastructure that all other modules depend on. Built first. |
| **Layer 1: Physical + Product** | `PHYS-MODEL`, `PROD-DEF` — define the factory and its products. No runtime dependencies. |
| **Layer 2: Production** | `PROD-ORDER`, `ROUTE-DEF`, `ROUTE-ENGINE`, `DISPATCH` — production execution modules. Depend on Layer 1. |
| **Layer 3: Execution** | `WIP-TRACK`, `MAT-MGMT`, `DATA-COLLECT` — real-time shop floor tracking. Depend on Layers 1–2. |
| **Layer 4: Quality + Analytics** | `QUAL-MGMT`, `GENEALOGY`, `PERF-ANALYSIS` — quality control and performance monitoring. Depend on Layers 1–3. |

### Code Conventions

| Term | Definition |
|---|---|
| **Module Internal Structure** | The mandatory file layout every core module follows: `models.py`, `schemas.py`, `service.py`, `routes.py`, `events.py`, `exceptions.py`. AI agents can predict where any logic lives. |
| **Service Layer** | The `service.py` file in each module — contains all business logic as stateless async functions. No direct ORM queries in routes; routes call service functions. |
| **Schemas** | Pydantic v2 models in `schemas.py` — define request/response shapes, validation rules, and serialization. Separate from ORM models. |
| **Soft Delete** | Records are never physically deleted. The `is_active` boolean is set to `False`. All queries filter by `is_active=True` unless explicitly requesting deleted records. |
| **Base Model** | The SQLAlchemy base class all entities inherit from. Provides `id` (UUID), `created_at`, `updated_at`, `is_active`. |

### AI-Specific Terms

| Term | Definition |
|---|---|
| **AI Maintainability** | The primary design objective: all code, structure, and conventions are optimized so that an AI agent (not a human) can navigate, understand, and modify the codebase predictably. |
| **Multi-Agent Workflow** | The Git-based workflow where multiple AI agents work on different modules/plugins simultaneously. Agents work on feature branches, CI validates, then merge. |
| **SESSION_LOG.md** | Chronological narrative of what happened in each AI coding session. Written for future AI sessions to quickly understand history. |
| **PROJECT_STATE.json** | Machine-readable project state file. Contains current phase, current task, all decisions, module registry. Read first on session start. |
| **Decision Record** | An entry in `PROJECT_STATE.json` (e.g., D001, D020) documenting an architectural decision, its rationale, and date. |

### Configuration

| Term | Definition |
|---|---|
| **Environment Variables** | All MES configuration is via environment variables (12-factor app), loaded by Pydantic Settings. Prefixed with `MES_` (e.g., `MES_DB_URL`, `MES_OIDC_ISSUER`). |
| **`.env` file** | Local file containing environment variables for development. Never committed to Git. |
| **Mock Adapter** | A development/test implementation of an adapter interface that simulates external system behavior in-memory. Every adapter (ERP, equipment, test equipment) has a mock. |

### Database Migration

| Term | Definition |
|---|---|
| **Migration** | A versioned script that changes the database schema (DDL) and optionally transforms existing data. Managed by Alembic. Each migration has an `upgrade()` and `downgrade()` function. |
| **Alembic** | The SQLAlchemy database migration framework. Auto-generates migration scripts by diffing ORM models against the current database schema. |
| **Revision** | A single Alembic migration identified by a short hash. Revisions form a linked chain via `down_revision` pointers. |
| **Revision Chain** | The linear sequence of migrations from the initial schema to the current head. Must be a single chain (no unresolved branches). |
| **Head** | The most recent migration revision — the target state for `alembic upgrade head`. |
| **Autogenerate** | Alembic's ability to auto-detect differences between ORM `models.py` and the live database, then generate a migration script. Does not detect renames or data transformations. |
| **Expand-Contract** | A two-phase migration pattern for breaking schema changes. **Expand**: add new schema alongside old (backward-compatible). **Contract**: remove old schema after all code is updated. Required for zero-downtime deployments. |
| **Data Migration** | Logic within a migration that transforms existing data (e.g., backfilling a new column, converting values). Written as SQL inside the migration file. |
| **Forward-Fix** | Creating a new corrective migration instead of rolling back (downgrading) a problematic one. Preferred over downgrade in production because it avoids data loss. |
| **Downgrade** | Rolling a migration back by executing its `downgrade()` function. Restores the previous schema. May lose data if columns or tables were dropped. |
| **Plugin Migration Chain** | A separate Alembic revision chain owned by a plugin, stored in `plugins/{name}/migrations/`. Isolated from core migrations. Plugin tables are prefixed with `plugin_{id}_`. |
| **Transactional DDL** | Database support for wrapping schema changes in a transaction (rollback on failure). PostgreSQL fully supports it. SQL Server partially. Oracle does not (DDL auto-commits). |
| **Model Drift** | When ORM `models.py` and the actual database schema are out of sync. Detected by `alembic check`. |

---

## 4. Abbreviations Quick Reference

| Abbreviation | Expansion |
|---|---|
| **AMQP** | Advanced Message Queuing Protocol |
| **API** | Application Programming Interface |
| **BOM** | Bill of Materials |
| **CI** | Continuous Integration |
| **CRUD** | Create, Read, Update, Delete |
| **DCS** | Distributed Control System |
| **DTO** | Data Transfer Object |
| **ERP** | Enterprise Resource Planning |
| **FIFO** | First In, First Out |
| **IdP** | Identity Provider |
| **IDoc** | Intermediate Document (SAP) |
| **IoT** | Internet of Things |
| **ISA** | International Society of Automation |
| **JIT** | Just-In-Time |
| **JMS** | Java Message Service |
| **JSON** | JavaScript Object Notation |
| **JWT** | JSON Web Token |
| **KPI** | Key Performance Indicator |
| **MES** | Manufacturing Execution System |
| **MESA** | Manufacturing Enterprise Solutions Association |
| **MOM** | Message-Oriented Middleware *or* Manufacturing Operations Management (context-dependent) |
| **MQTT** | Message Queuing Telemetry Transport |
| **NC** / **NCR** | Non-Conformance / Non-Conformance Report |
| **OData** | Open Data Protocol |
| **OEE** | Overall Equipment Effectiveness |
| **OIDC** | OpenID Connect |
| **OPC-UA** | Open Platform Communications Unified Architecture |
| **ORM** | Object-Relational Mapping |
| **PLC** | Programmable Logic Controller |
| **RBAC** | Role-Based Access Control |
| **REST** | Representational State Transfer |
| **RFC** | Remote Function Call (SAP) |
| **SCADA** | Supervisory Control and Data Acquisition |
| **SPC** | Statistical Process Control |
| **SSO** | Single Sign-On |
| **STOMP** | Simple Text Oriented Messaging Protocol |
| **UOM** | Unit of Measure |
| **UUID** | Universally Unique Identifier |
| **WIP** | Work In Process |

---

## 5. ISA-95 Alignment Map (Phase 6 Refactor Contract)

> **Purpose:** This is the naming contract for the ISA-95 refactor (Phase 6 / P6). Every rename, addition, and deletion listed here will be applied across ORM models, Pydantic schemas, DB tables, REST paths, and event topics. Nothing here is implemented yet — this section is the **plan of record**. Each downstream refactor step (1–12) MUST match this map. Deviations require updating this section first.
>
> **Target database:** `mes_ai_s95` (empty, no Alembic history). A single fresh Alembic baseline will be generated at the end of Step 12.
>
> **Convention:**
> - **Class** names use ISA-95 Part 2/3/4 object names verbatim where practical (e.g., `ProcessSegment`, `OperationsRequest`, `OperationsResponse`).
> - **Table** names are `snake_case` plural of the class name (e.g., `process_segments`, `operations_requests`).
> - **Module** names under `server/src/mes/core/` match the ISA-95 object domain (e.g., `operations/`, `process_segment/`).
> - **REST** paths are kebab-case plural of the resource (e.g., `/api/v1/operations-requests`).
> - **Events** are dot-notation on the ISA-95 object name (e.g., `operations.request.released`, `segment.response.completed`).

### 5.1 Renames (current → ISA-95)

#### Product Definition domain (Part 2: Process Segment / Operations Definition)

| Current class | Current table | ISA-95 class | ISA-95 table | Notes |
|---|---|---|---|---|
| `ProcessRoute` | `process_routes` | `OperationsDefinition` | `operations_definitions` | ISA-95 Part 2 "Operations Definition". Represents the manufacturing recipe / route for a product. |
| `RouteStep` | `route_steps` | `ProcessSegment` | `process_segments` | ISA-95 Part 2 "Process Segment". A single manufacturing operation within an Operations Definition. |
| `StepTransition` | `step_transitions` | `ProcessSegmentDependency` | `process_segment_dependencies` | ISA-95 Part 2 "Process Segment Dependency". Graph edges between segments (including disposition-driven transitions). |
| `StepParameter` | `step_parameters` | `SegmentParameter` | `segment_parameters` | Parameter specification attached to a process segment (setpoint, limits). |
| `StepEquipmentRequirement` | `step_equipment_requirements` | `SegmentEquipmentRequirement` | `segment_equipment_requirements` | ISA-95 Part 2 "Equipment Requirement" scoped to a segment. |
| `StepMaterialRequirement` | `step_material_requirements` | `SegmentMaterialRequirement` | `segment_material_requirements` | ISA-95 Part 2 "Material Requirement" scoped to a segment. |
| `RouteProductAssignment` | `route_product_assignments` | `OperationsDefinitionProductAssignment` | `operations_definition_product_assignments` | Many-to-many: which products this Operations Definition produces. |
| `RouteMaterialAssignment` | `route_material_assignments` | `OperationsDefinitionMaterialAssignment` | `operations_definition_material_assignments` | Many-to-many: declared input materials for the Operations Definition. |
| `ProductDefinition` | `product_definitions` | `ProductDefinition` | `product_definitions` | **No rename** — ISA-95 Part 2 name is already correct. |
| `BillOfMaterial` | `bills_of_material` | `ProductProduction​Rule` *(no — see notes)* | `bills_of_material` | **Keep current name.** ISA-95 Part 2 calls this "Material Specification" but "BOM" is the universally understood industry term. Decision: keep as `BillOfMaterial`, cross-reference in docs. |
| `BOMItem` | `bom_items` | `BOMItem` | `bom_items` | **No rename** (consistent with `BillOfMaterial`). |
| `Disposition` | `dispositions` | `Disposition` | `dispositions` | **No rename** — operational concept, not an ISA-95 object. |

#### Production / Operations Management domain (Part 3: Operations Management)

| Current class | Current table | ISA-95 class | ISA-95 table | Notes |
|---|---|---|---|---|
| `ProductionOrder` | `production_orders` | `OperationsRequest` | `operations_requests` | ISA-95 Part 3 "Operations Request". Directive from ERP/scheduler to execute a quantity of an Operations Definition. |
| *(none — new)* | *(none)* | `OperationsSchedule` | `operations_schedules` | **New.** ISA-95 Part 3 "Operations Schedule". Groups one or more Operations Requests into a dispatchable schedule window. Optional in Phase 6; scaffolded in Step 5. |
| *(none — new)* | *(none)* | `OperationsResponse` | `operations_responses` | **New.** ISA-95 Part 3 "Operations Response". The as-performed aggregate record for a completed Operations Request. Composed of Segment Responses + Resource Actuals. |
| Module `production/` | — | Module `operations/` | — | Directory rename. All imports updated. |

#### WIP / Tracking domain (Part 3: Segment Response + Part 4: Resource Actuals)

| Current class | Current table | ISA-95 class | ISA-95 table | Notes |
|---|---|---|---|---|
| `Unit` | `units` | `Unit` | `units` | **No rename.** Serialized item identity is retained (ISA-95 does not define a serialized-unit object; `Unit` is our operational concept). |
| `Lot` | `lots` | `Lot` | `lots` | **No rename.** Same reasoning. |
| `UnitHistory` | `unit_histories` | `SegmentResponseUnit` | `segment_response_units` | ISA-95 Part 3 "Segment Response" specialization for a unit traversing a segment. One row per unit × segment execution. |
| `LotHistory` | `lot_histories` | `SegmentResponseLot` | `segment_response_lots` | ISA-95 Part 3 "Segment Response" specialization for a lot. |
| *(none — new)* | *(none)* | `MaterialActual` | `material_actuals` | **New.** ISA-95 Part 4 "Material Actual" — what was actually consumed/produced per Segment Response. |
| *(none — new)* | *(none)* | `EquipmentActual` | `equipment_actuals` | **New.** ISA-95 Part 4 "Equipment Actual" — which equipment actually performed the segment, time in/out, state. |
| *(none — new)* | *(none)* | `PersonnelActual` | `personnel_actuals` | **New.** ISA-95 Part 4 "Personnel Actual" — who (operator) performed the segment. |

#### Physical Model domain (Part 1: Physical Asset Hierarchy)

| Current class | Current table | ISA-95 class | ISA-95 table | Notes |
|---|---|---|---|---|
| `Site` | `sites` | `Site` | `sites` | **No rename.** |
| `Area` | `areas` | `Area` | `areas` | **No rename.** |
| `ProductionLine` | `production_lines` | `ProductionLine` | `production_lines` | **No rename.** ISA-95 uses "Production Line" under the "WorkCenter" supertype — acceptable as-is. |
| `WorkCell` | `work_cells` | `WorkCell` | `work_cells` | **No rename.** ISA-95 "Work Unit" is broader; `WorkCell` stays as our leaf grouping. |
| `Equipment` | `equipment` | `Equipment` | `equipment` | **No rename.** |
| `EquipmentClass` | `equipment_classes` | `EquipmentClass` | `equipment_classes` | **No rename.** ISA-95 Part 2 term. |
| `EquipmentClassProperty` | `equipment_class_properties` | `EquipmentClassProperty` | `equipment_class_properties` | **No rename.** |
| `EquipmentCapability` | `equipment_capabilities` | `EquipmentCapability` | `equipment_capabilities` | **No rename.** |
| `EquipmentCapabilityProperty` | `equipment_capability_properties` | `EquipmentCapabilityProperty` | `equipment_capability_properties` | **No rename.** |
| `EquipmentMaterial` | `equipment_materials` | `EquipmentMaterial` | `equipment_materials` | **No rename.** |
| *(none — optional)* | *(none)* | `Personnel` | `personnel` | **Deferred (Step 2 skipped).** ISA-95 Part 2 "Personnel". `PersonnelActual` (Step 6) will reference an operator by UUID string only; the full Personnel entity is out of scope for Phase 6. |
| *(none — optional)* | *(none)* | `PersonnelClass` | `personnel_classes` | **Deferred (Step 2 skipped).** |
| *(none — optional)* | *(none)* | `PhysicalAsset` | `physical_assets` | **Deferred (Step 2 skipped).** Non-equipment tangibles (tools, fixtures, molds) are out of scope for Phase 6. |

### 5.2 Deletions (Step 7 — drop legacy edges)

The following columns/attributes are dropped outright. No data migration (fresh database).

| Entity | Column / attribute | Reason |
|---|---|---|
| `OperationsDefinition` (née `ProcessRoute`) | `product_id` (FK) | Legacy 1:1 product link; replaced by `OperationsDefinitionProductAssignment` (many-to-many). |
| `ProcessSegment` (née `RouteStep`) | `work_cell_id` (FK) | Legacy direct WorkCell link; replaced by `SegmentEquipmentRequirement` referencing `EquipmentClass`. |
| `Equipment` | `equipment_type` (string) | Free-form string; replaced by `EquipmentClass` FK. |
| `Equipment` | `capabilities` (JSON) | Unstructured blob; replaced by `EquipmentCapability` + `EquipmentCapabilityProperty` rows. |

### 5.3 Out-of-scope / removals (Step 11)

Classes marked for deletion if no consumer remains after the rename sweep. Each will be re-verified before deletion in Step 11.

| Candidate class | Module | Disposition |
|---|---|---|
| `demo/` module contents | `core/demo/` | Evaluate — demo fixtures may be regenerated against new schema. Defer decision to Step 11. |
| Any `*_legacy` helpers in `routing/service.py` | `core/routing/` | Delete after call sites removed in Steps 4 and 7. |

### 5.4 REST path renames (Step 8)

| Current path | New path | Binds to |
|---|---|---|
| `/api/v1/process-routes` | `/api/v1/operations-definitions` | `OperationsDefinition` |
| `/api/v1/route-steps` | `/api/v1/process-segments` | `ProcessSegment` |
| `/api/v1/step-transitions` | `/api/v1/process-segment-dependencies` | `ProcessSegmentDependency` |
| `/api/v1/step-parameters` | `/api/v1/segment-parameters` | `SegmentParameter` |
| `/api/v1/production-orders` | `/api/v1/operations-requests` | `OperationsRequest` |
| *(new)* | `/api/v1/operations-schedules` | `OperationsSchedule` |
| *(new)* | `/api/v1/operations-responses` | `OperationsResponse` |
| `/api/v1/unit-histories` | `/api/v1/segment-responses/units` | `SegmentResponseUnit` |
| `/api/v1/lot-histories` | `/api/v1/segment-responses/lots` | `SegmentResponseLot` |
| *(new)* | `/api/v1/material-actuals` | `MaterialActual` |
| *(new)* | `/api/v1/equipment-actuals` | `EquipmentActual` |
| *(new)* | `/api/v1/personnel-actuals` | `PersonnelActual` |

Unchanged paths: `/api/v1/sites`, `/api/v1/areas`, `/api/v1/production-lines`, `/api/v1/work-cells`, `/api/v1/equipment`, `/api/v1/equipment-classes`, `/api/v1/product-definitions`, `/api/v1/boms`, `/api/v1/dispositions`, `/api/v1/units`, `/api/v1/lots`, `/api/v1/materials`, `/api/v1/dispatch/*`, `/api/v1/quality/*`, `/api/v1/uom/*`.

### 5.5 Event topic renames (Step 9)

| Current topic | New topic |
|---|---|
| `production.order.created` | `operations.request.created` |
| `production.order.released` | `operations.request.released` |
| `production.order.started` | `operations.request.started` |
| `production.order.completed` | `operations.request.completed` |
| `production.order.closed` | `operations.request.closed` |
| `routing.step.entered` | `segment.response.started` |
| `routing.step.exited` | `segment.response.completed` |
| `routing.step.failed` | `segment.response.failed` |

Unchanged topic prefixes: `wip.*`, `dispatch.*`, `quality.*`, `equipment.*`, `material.*`, `uom.*`, `plugin.*`.

### 5.6 Plugin-facing API changes (Step 10)

Extension point `dispatch_strategy`: no signature change (still operates on `Unit`/`Lot` and a candidate `Equipment` list).

Extension point `operation_hook`: parameter renames only.
- `production_order` → `operations_request`
- `route_step` → `process_segment`
- `unit_history` → `segment_response`

`MESPlugin` base class: no change.

### 5.7 Module directory renames

| Current path | New path |
|---|---|
| `server/src/mes/core/production/` | `server/src/mes/core/operations/` |
| `server/src/mes/core/routing/` | `server/src/mes/core/routing/` *(kept — routing engine is a service, not an ISA-95 object)* |
| `server/src/mes/core/product_def/` | `server/src/mes/core/product_def/` *(kept — houses Operations Definitions + Segments; rename deferred)* |
| `server/src/mes/core/wip/` | `server/src/mes/core/wip/` *(kept — houses Units, Lots, and Segment Responses; contents renamed per 5.1)* |

### 5.8 Module ID updates

Additions/renames to the Module ID table in §2:

| Module ID | Full Name | Code Path | Status |
|---|---|---|---|
| `OPS-REQUEST` | Operations Request (replaces `PROD-ORDER`) | `server/src/mes/core/operations/` | Renamed |
| `OPS-SCHEDULE` | Operations Schedule | `server/src/mes/core/operations/` | New |
| `OPS-RESPONSE` | Operations Response | `server/src/mes/core/operations/` | New |
| `RES-ACTUALS` | Resource Actuals (Material/Equipment/Personnel Actuals) | `server/src/mes/core/wip/` | New |
| ~~`PERSONNEL`~~ | ~~Personnel Model~~ | ~~`server/src/mes/core/personnel/`~~ | **Deferred (Step 2 skipped)** |

### 5.9 What is explicitly NOT changing

- `BaseModel` contract (`id`, `created_at`, `updated_at`, `is_active`). Unchanged.
- Soft-delete behavior. Unchanged.
- Response envelope `{ data, meta, errors }`. Unchanged.
- UOM domain (already ISA-95-compatible). Unchanged.
- Dispatch domain classes (`DispatchService`, strategies). Unchanged — dispatch is an operational engine, not an ISA-95 object.
- OEE / performance domain classes. Unchanged — KPIs are computed views, not ISA-95 objects.
- Genealogy domain — remains a query-only aggregate built from Segment Responses, Material Actuals, Equipment Actuals, and Test Results.
- Authentication, plugin framework, event bus, data layer, REST framework. Unchanged.

---

*Last updated: 2026-04-21*
