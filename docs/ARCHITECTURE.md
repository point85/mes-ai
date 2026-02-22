# MES AI — Architecture Document

> **Living document** — updated as architectural decisions are made.  
> Current status: **Placeholder** — will be fully populated during Phase 2 (Architecture & Design).

---

## 1. Overview

An open-source Manufacturing Execution System (MES) framework with a plugin architecture, designed and maintained entirely by AI.

**Key constraints:**
- Optimized for AI maintainability, not human readability
- Plugin-based extensibility (end users customize via AI-driven IDE)
- Client/server with REST HTTP/HTTPS interface
- RDBMS for persistence
- All external integrations (ERP, PLC, test equipment) abstracted behind adapter interfaces with mock implementations

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Clients                            │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Runtime GUI  │  │  Headless   │  │  Design-Time   │  │
│  │   Client    │  │   Client    │  │    Client      │  │
│  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │ REST HTTP/HTTPS              │
├──────────────────────────┼──────────────────────────────┤
│                     MES Server                          │
│  ┌───────────────────────┼───────────────────────────┐  │
│  │              Plugin Framework                     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │   Core   │ │ Built-in │ │    User/Custom    │  │  │
│  │  │ Modules  │ │ Plugins  │ │     Plugins       │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  RDBMS      │  │ ERP Adapter  │  │ Equipment    │   │
│  │  (Data)     │  │  Interface   │  │  Adapter     │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 3. Module Registry

> Modules are registered in `PROJECT_STATE.json` under `modules.registry`.  
> Each module has a short ID (e.g., `WIP-TRACK`, `DISPATCH-ENGINE`) for quick reference.

*No modules implemented yet — will be populated starting in Phase 3.*

## 4. Technology Stack

*To be decided in Phase 2. Candidates will be evaluated for:*
- AI-friendliness (well-documented, widely used, predictable patterns)
- Plugin extensibility support
- Cross-platform compatibility
- Mature REST framework availability
- RDBMS ORM support

## 5. Data Model

*To be designed in Phase 2, informed by Phase 1 survey results.*

## 6. Plugin Architecture

*To be designed in Phase 2. Key requirements:*
- Clean extension points with stable contracts
- Discovery and registration mechanism
- Isolation (plugins must not break core)
- AI-driven customization workflow

## 7. Integration Adapters

*To be designed in Phase 2. Adapter types:*
- **ERP Adapter**: Production orders in, WIP/consumption reporting out
- **Equipment Adapter**: PLC/microcontroller communication (OPC-UA, Modbus, MQTT)
- **Test Equipment Adapter**: Test result collection

All adapters will have mock implementations for testing.

---

*Last updated: 2026-02-22 — Session S001*
