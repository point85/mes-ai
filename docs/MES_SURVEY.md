# MES AI — Phase 1: Commercial MES Survey & Required Functionality

> **Phase**: P1 — Survey & Requirements  
> **Date**: 2026-02-22  
> **Status**: Complete  

---

## 1. Industry Standards Foundation

### 1.1 MESA International — 11 Core MES Functions

The Manufacturing Enterprise Solutions Association (MESA) defined the original 11 core functions of a Manufacturing Execution System in the 1990s. These remain the canonical reference for MES scope:

| # | MESA Function | Description |
|---|---|---|
| 1 | **Resource Allocation & Status** | Manage equipment, tools, materials, labor, and other resources required for manufacturing. Track real-time status and availability. |
| 2 | **Operations/Detail Scheduling** | Sequence and time production activities based on priorities, attributes, characteristics, and recipes/rules associated with specific production equipment. |
| 3 | **Dispatching Production Units** | Manage the flow of production in the form of jobs, orders, batches, lots, and work orders. Dispatch to work cells based on real-time conditions. |
| 4 | **Document Control** | Control records and forms that must be maintained with the production unit, including work instructions, recipes, drawings, SOPs, batch records, ECN notifications, and as-planned/as-built records. |
| 5 | **Data Collection/Acquisition** | Collect real-time data from the shop floor via manual entry, equipment interfaces, or automated data collection systems. Provide an interface to production operations data. |
| 6 | **Labor Management** | Track personnel status, qualifications, certifications, and time. Provide ability to track indirect activities such as material preparation or tooling work. |
| 7 | **Quality Management** | Provide real-time analysis of measurements collected from manufacturing to assure proper product quality control. Identify problems requiring attention, recommend corrective actions, and correlate symptoms, actions, and results. Includes SPC/SQC. |
| 8 | **Process Management** | Monitor production and either automatically correct or provide decision support to operators for correcting and improving in-process activities. May include alarm management and equipment interlocks. |
| 9 | **Maintenance Management** | Track and direct the activities for maintaining equipment and tools to ensure their availability for manufacturing. Schedule periodic or preventive maintenance as well as reactive (emergency) repairs. Maintain history of past events/problems. |
| 10 | **Product Tracking & Genealogy** | Provide visibility to where work is at all times and its disposition. Status information may include who is working on it, current production conditions, and any alarms, rework, or other exceptions. Genealogy tracks the complete history of components and conditions used to produce a product. |
| 11 | **Performance Analysis** | Provide up-to-the-minute reporting of actual manufacturing operations results along with comparison to past history and expected business results. Includes KPIs such as OEE (Overall Equipment Effectiveness), yield, cycle time, and utilization. |

### 1.2 ISA-95 / IEC 62264 Standard

ISA-95 (international version: IEC 62264) is the international standard for enterprise-control system integration. It defines:

**Hierarchy Model (Purdue Reference Model)**:
- **Level 4**: Business Planning & Logistics (ERP)
- **Level 3**: Manufacturing Operations Management (MES/MOM) ← *Our target*
- **Level 2**: Supervisory Control (SCADA, DCS)
- **Level 1**: Direct Control (PLCs, microcontrollers)
- **Level 0**: Physical Process (sensors, actuators)

**Level 3 Operations Categories** (ISA-95 Part 3):
- **Production Operations**: Scheduling, dispatching, execution, data collection, tracking, performance analysis
- **Quality Operations**: Quality test management, SPC, corrective actions
- **Inventory/Logistics Operations**: Material receiving, storage, shipping, WIP tracking
- **Maintenance Operations**: Preventive/reactive maintenance, equipment history

**Key Object Models** (ISA-95 Parts 1, 2, 4):
- Personnel, Equipment, Material, Process Segment, Production Schedule, Production Performance
- These define the data exchanged between Level 4 (ERP) and Level 3 (MES)
- B2MML (Business to Manufacturing Markup Language) is the XML implementation of these models

---

## 2. Commercial MES Systems Surveyed

### 2.1 Siemens Opcenter (formerly SIMATIC IT / Camstar)

**Market Position**: Leader (Gartner MQ). Heavy in discrete, pharmaceutical, electronics.

| Capability | Details |
|---|---|
| Production Management | Work order management, routing enforcement, WIP tracking, serialization |
| Quality Management | CAPA, non-conformance, SPC/SQC, inline inspection, sampling plans |
| Scheduling | Advanced Planning & Scheduling (APS) integration, finite capacity scheduling |
| Material Management | Bill of materials (BOM), material consumption, lot tracking, genealogy |
| Equipment Integration | OPC-UA native, PLC/SCADA connectivity, equipment state tracking |
| Data Collection | Automated + manual, electronic batch records (EBR) |
| Genealogy/Traceability | Full as-built record, bidirectional traceability |
| Performance Analysis | OEE, dashboards, KPI management, real-time reporting |
| ERP Integration | SAP certified integration, B2MML support |
| Architecture | Client/server, web-based, on-premise or cloud hybrid |
| Extensibility | API-based customization, plug-in model for custom logic |

### 2.2 Rockwell Automation Plex (formerly Plex Systems)

**Market Position**: Leader in cloud-native MES. Strong in automotive, food/beverage, industrial.

| Capability | Details |
|---|---|
| Production Management | Cloud-based WIP tracking, operator control panels, error-proofed workflows |
| Quality Management | Closed-loop quality control, inline inspection, statistical process control |
| Scheduling | Finite scheduling engine, resource-aware job scheduling |
| Material/Inventory | Real-time inventory tracking, end-to-end traceability |
| Equipment Integration | IoT/IIoT device connectivity, edge-to-cloud architecture |
| Human Capital Management | Workforce tracking, skills/certifications, labor reporting |
| ERP Integration | Built-in ERP functionality, API integration to external ERPs |
| Architecture | Cloud-native SaaS, elastic/modular, edge-to-cloud |
| Extensibility | No-code customization, API-driven, modular add-ons |

### 2.3 SAP Manufacturing Execution (SAP ME / SAP MII / SAP DMC)

**Market Position**: Leader. Dominant in enterprises already using SAP ERP.

| Capability | Details |
|---|---|
| Production Management | Work order management, routing, WIP tracking, shop floor control |
| Quality Management | Integrated with SAP QM, inline inspections, non-conformance management |
| Scheduling | Integration with SAP PP (Production Planning), finite scheduling |
| Material Management | Deep SAP MM integration, BOM management, consumption posting |
| Equipment Integration | SAP Plant Connectivity (PCo), OPC-UA, custom connectors |
| Data Collection | Manual/automated, electronic work instructions |
| Genealogy | Serialization, batch traceability, as-built records |
| Performance Analysis | SAP MII for analytics, OEE, dashboards |
| ERP Integration | Native SAP ERP integration (RFC/BAPI, IDoc, OData) |
| Architecture | On-premise (ME) or cloud (DMC), web-based clients |
| Extensibility | SAP BTP (Business Technology Platform), custom extensions |

### 2.4 GE Proficy (now part of GE Vernova)

**Market Position**: Strong in process industries, CPG, pharma.

| Capability | Details |
|---|---|
| Production Management | Batch execution, continuous process tracking, work order management |
| Quality Management | SPC/SQC, specification management, CAPA |
| Scheduling | Integration with scheduling tools, batch scheduling |
| Material Management | Material tracking, genealogy, lot/batch management |
| Equipment Integration | OPC-UA/DA, direct PLC connectivity, historian integration |
| Data Collection | Proficy Historian for time-series, real-time data collection |
| Performance Analysis | OEE, Pareto, downtime analysis, Plant Applications |
| ERP Integration | SAP/Oracle adapters, B2MML |
| Architecture | On-premise, hybrid cloud options, web-based |
| Extensibility | SDK, scripting engine, workflow customization |

### 2.5 Dassault Systèmes DELMIA Apriso

**Market Position**: Strong in aerospace, automotive, complex discrete manufacturing.

| Capability | Details |
|---|---|
| Production Management | Global process execution, WIP tracking across plants, work order management |
| Quality Management | Inline quality, non-conformance, CAPA, SPC |
| Material Management | Warehouse integration, material consumption, kitting |
| Equipment Integration | Equipment connectivity framework, IoT integration |
| Genealogy | Full build history, regulatory compliance traceability |
| Performance Analysis | OEE, real-time dashboards, cross-plant analytics |
| ERP Integration | SAP/Oracle connectors, web services |
| Architecture | Web-based, cloud/on-premise, multi-plant architecture |
| Extensibility | Process Builder (visual workflow), custom business logic |

### 2.6 MPDV MES HYDRA

**Market Position**: Mid-market leader in Europe. Strong in discrete manufacturing.

| Capability | Details |
|---|---|
| Production Management | Order management, detailed scheduling, WIP tracking |
| Quality Management | Inspection planning, SPC, CAPA |
| Human Resource Management | Time tracking, personnel scheduling, skills management |
| Material Management | Material tracking, inventory, tool management |
| Equipment Integration | Machine data acquisition via PLC/OPC, tool integration |
| Performance Analysis | OEE, KPI dashboards, production analytics |
| ERP Integration | SAP/Oracle/Microsoft certified adapters |
| Architecture | Client/server, on-premise, web clients |
| Extensibility | MES Ecosystem with partner applications, API customization |

### 2.7 Notable Open-Source MES Projects

| Project | Notes |
|---|---|
| **OpenMES** | Minimal, abandoned. No ISA-95 alignment. |
| **QAD Redzone** | Connected workforce focused, not full MES. |
| **Apache OFBiz Manufacturing** | ERP with basic manufacturing module. Not a full MES. |
| **ERPNext Manufacturing** | Open-source ERP with shop floor module. Limited MES depth. |

**Key Observation**: There is **no mature, full-featured open-source MES** aligned with ISA-95/MESA standards. This is the gap MES AI aims to fill.

---

## 3. Feature Comparison Matrix

Consolidated view of which functions are supported across surveyed systems:

| Function | Siemens | Plex | SAP | GE Proficy | Dassault | MPDV |
|---|---|---|---|---|---|---|
| Resource Allocation & Status | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Operations Scheduling | ✅ | ✅ | ✅ | ◐ | ◐ | ✅ |
| Dispatching | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Document Control | ✅ | ◐ | ✅ | ✅ | ✅ | ◐ |
| Data Collection/Acquisition | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Labor Management | ✅ | ✅ | ◐ | ◐ | ◐ | ✅ |
| Quality Management | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Process Management | ✅ | ✅ | ✅ | ✅ | ✅ | ◐ |
| Maintenance Management | ◐ | ◐ | ◐ | ✅ | ◐ | ◐ |
| Product Tracking & Genealogy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Performance Analysis (OEE) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ERP Integration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Equipment/PLC Integration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Plugin/Extension Framework | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

✅ = Full support | ◐ = Partial/integrated via partner | ○ = Not supported

---

## 4. Required Functionality for MES AI

Based on the survey, the following is the prioritized list of required functionality for the MES AI framework. Each function is assigned a **module ID** for project tracking and cross-reference.

### 4.1 Core Modules (Must Have — Phase 3)

| Module ID | Module Name | ISA-95 Category | Description |
|---|---|---|---|
| `PHYS-MODEL` | Physical Model | Foundation | Define the physical hierarchy: Enterprise → Site → Area → Production Line → Work Cell → Equipment. All MES operations reference this model. |
| `WIP-TRACK` | WIP Tracking | Production Ops | Track units/lots as they move through the physical model. Maintain current location, status, quantity, and disposition of each WIP entity. |
| `ROUTE-DEF` | Route Definition | Production Ops | Define the sequence of steps (operations) a product must follow. Support linear, branching, and rework routes. |
| `ROUTE-ENGINE` | Routing Engine | Production Ops | Enforce routing rules: validate that WIP moves to permitted next steps, prevent out-of-sequence operations. |
| `DISPATCH` | Dispatching Engine | Production Ops | Decide where to move WIP next. Support manual dispatch (operator disposition) and automated dispatch (capability/capacity-based algorithms). |
| `PROD-ORDER` | Production Order Management | Production Ops | Receive, manage, and track production orders (from ERP or manual entry). Track order status, quantities planned/started/completed/scrapped. |
| `MAT-MGMT` | Material Management | Inventory Ops | Track raw materials, components, and consumables. Record consumption against WIP. Support lot/batch identification. |
| `DATA-COLLECT` | Data Collection | Production Ops | Collect production data: manual operator entry, equipment-sourced automated data, and test results. Timestamp and associate with WIP. |
| `PROD-DEF` | Product Definition | Foundation | Manage product/part definitions: BOM (Bill of Materials), BOR (Bill of Resources), process parameters, recipes. Version control for product definitions. |
| `QUAL-MGMT` | Quality Management | Quality Ops | Define quality checks (inspections, tests) at route steps. Record pass/fail, measurements, dispositions. Support SPC data feeds. |
| `PERF-ANALYSIS` | Performance Analysis | Production Ops | Calculate and report KPIs: OEE, yield, cycle time, throughput, utilization. Support real-time and historical analysis. |
| `GENEALOGY` | Product Genealogy/Traceability | Production Ops | Build complete as-built record: what materials went into a unit, what equipment processed it, what parameters were used, who operated it, what test results were recorded. Bidirectional traceability (forward: material → product; backward: product → material). |

### 4.2 Integration Modules (Must Have — Phase 4)

| Module ID | Module Name | Description |
|---|---|---|
| `ERP-IBOUND` | ERP Inbound Adapter | Receive production orders, product definitions (BOM/routing), and material master data from ERP systems. Abstract protocol (REST, OData, RFC, flat file). |
| `ERP-OBOUND` | ERP Outbound Adapter | Report back to ERP: production completions, material consumption, scrap, labor, WIP status. |
| `EQUIP-INTFC` | Equipment Interface Adapter | Communicate with PLCs/microcontrollers. Abstract protocol (OPC-UA, Modbus, MQTT). Receive machine state, counters, alarms. Send recipes/setpoints. |
| `TEST-INTFC` | Test Equipment Adapter | Collect test results from test equipment. Abstract data format and communication protocol. |

### 4.3 Client Modules (Must Have — Phase 5)

| Module ID | Module Name | Description |
|---|---|---|
| `RT-CLIENT` | Runtime Client | Web-based operator interface for WIP transactions: start, complete, move, scrap, rework, split, merge. Show current workstation state, queue, and work instructions. |
| `RT-HEADLESS` | Runtime Headless Client | API-driven client for automated equipment integration. Executes same transactions as GUI client but without UI, driven by equipment events. |
| `DT-CLIENT` | Design-Time Client | Web-based admin interface to configure the MES: define physical model, routes, products, quality checks, dispatching rules, and plugins. Browse module registry and visualize how components fit together. |

### 4.4 Framework Modules (Must Have — Phase 3)

| Module ID | Module Name | Description |
|---|---|---|
| `PLUGIN-FW` | Plugin Framework | Core extension mechanism. Discover, register, load, and manage plugins. Define extension points (hooks/events) that plugins can subscribe to. Plugin isolation and lifecycle management. |
| `REST-API` | REST API Layer | HTTP/HTTPS API serving all MES functionality. Versioned endpoints, authentication, authorization, input validation, error handling. |
| `DATA-LAYER` | Data Persistence Layer | RDBMS abstraction. Schema management, migrations, ORM, query builders. Support for transaction isolation and concurrent access. |
| `EVENT-BUS` | Event Bus | Internal publish/subscribe event system. Production events (WIP moved, order completed, alarm triggered) flow through the event bus. Plugins and dispatch engine subscribe to events. |
| `AUTH` | Authentication & Authorization | User/system authentication (API keys, tokens). Role-based access control for API endpoints and MES operations. |
| `SESSION-META` | AI Session Metadata | Machine-readable module registry, project state, decision log. Enables AI agents to resume work and reference modules by ID. |

### 4.5 Optional/Future Modules (Backlog)

| Module ID | Module Name | Description |
|---|---|---|
| `DOC-CTRL` | Document Control | Manage work instructions, SOPs, drawings associated with products/routes. Version control, electronic signatures. |
| `LABOR-MGMT` | Labor Management | Track operator time, certifications, skill-based work assignment. |
| `MAINT-MGMT` | Maintenance Management | Equipment preventive/reactive maintenance scheduling, work orders, history. |
| `SPC-ENGINE` | SPC/SQC Engine | Statistical process control: control charts, Cpk/Ppk, rule violations, automated alerts. |
| `BATCH-MGMT` | Batch Management | ISA-88 batch execution support for process industries. Recipe management, batch records. |
| `DASHBOARD` | Real-Time Dashboard | Live production floor visualization: equipment status, WIP flow, alarms, KPIs. |
| `REPORT-ENGINE` | Report Engine | Configurable production reports: yield, genealogy, quality, compliance reports. |
| `NOTIF` | Notification Service | Alert operators/supervisors via email, SMS, or in-app notifications on events (alarms, quality failures, order completion). |

---

## 5. Architectural Patterns Observed Across Commercial Systems

| Pattern | Prevalence | Relevance to MES AI |
|---|---|---|
| Client/Server with web-based clients | Universal | **Confirmed** — our approach |
| REST/HTTP APIs | Universal (modern) | **Confirmed** — our approach |
| RDBMS for transactional data | Universal | **Confirmed** — our approach |
| Event-driven architecture | High | **Required** — dispatching and plugin framework depend on it |
| Time-series historian (separate from RDBMS) | High (process industries) | **Deferred** — not in initial scope |
| Plugin/extension mechanism | High | **Confirmed** — core requirement |
| OPC-UA for equipment connectivity | High | **Required** — mock for initial scope |
| ISA-95 data model alignment | High | **Required** — our data model will align with ISA-95 object models |
| Multi-plant / multi-site support | High | **Deferred** — single-site first, extensible to multi-site |
| Cloud-native / SaaS | Growing | **Noted** — on-premise first, cloud-deployable architecture |

---

## 6. Key Design Conclusions

1. **ISA-95 alignment is non-negotiable.** Every major MES maps to ISA-95. Our data model, integration interfaces, and operations categories must align with the standard.

2. **The MESA 11 functions define the feature ceiling.** We don't need all 11 in the initial release, but the architecture must accommodate all of them as plugins.

3. **Event-driven architecture is essential.** Dispatching, plugin hooks, and equipment integration all depend on an event bus pattern.

4. **Plugin framework is the differentiator.** Commercial systems all have extensibility, but none are optimized for AI-driven customization. Our plugin framework must be the most AI-friendly extension mechanism possible.

5. **Equipment integration must be abstracted.** Use an adapter pattern so that OPC-UA, Modbus, MQTT, and custom protocols can all be supported without changing core logic.

6. **Start with a single site, discrete manufacturing model.** This covers the widest initial audience. Process/batch manufacturing (ISA-88) can be added as a plugin later.

7. **No mature open-source MES exists.** This confirms the value proposition of the project.

---

*Phase 1 Complete — Proceed to Phase 2: Architecture & Design*
