## Introduction

The MES AI application empowers you to create a MES that is 100% tailored to your business nees.  It empowers you in many ways:
- no vendor licensing fees or ongoing support fees.  These funds can be redeployed to small AI knowledgeable development teams in your area of expertise.
- software quality assurance can be performed by AI in a CI workflow, therefore there is no need to hire and train SQA engineers with potential competing priorities with other business software development
- avoid vendor lock-in.  You are in complete control over what functionality is implemented and when it is released.  There is no business risk by having to request vendor support to fix bugs or implement needed features or finding work-arounds.

## MES AI Architecture Overview

MES AI is an open-source Manufacturing Execution System built around a FastAPI server, multiple Vite-based web clients, and a plugin-oriented extension model. The platform is designed to support ISA-95-style manufacturing workflows while staying practical for iterative development, simulation, and AI-assisted customization. 

## System at a Glance

At the center of the system is the MES server in `server/src/mes`, which exposes a versioned REST API and WebSocket event stream. Around that core are several browser-based applications in `clients/` that support different user roles and development workflows:

- `clients/design_time`: the design-time application for configuring products, routes, dispositions, equipment, plugins, and other master data.
- `clients/run_time`: the runtime operator application for creating and processing WIP, dispatching work, recording inventory activity, and handling shop-floor execution.
- `clients/erp_simulator`: a simulator used to create and release operations requests and exercise ERP-style inbound flows.
- `clients/equipment_simulator`: a lightweight simulator used for equipment-centric development and testing.

These apps communicate with the MES server over HTTP, and the runtime-facing experiences can also consume WebSocket events for near-real-time updates.

## High-Level Architecture

The architecture follows a client-server model with clear separation between core execution logic, user interfaces, and integration points.

1. The FastAPI MES server owns the domain model, persistence, business rules, API surface, and event publication.
2. The Vite applications provide focused user experiences for engineering, operations, and simulation.
3. Plugins extend the platform without requiring direct modification of the core for every site-specific workflow or adapter.
4. PostgreSQL is the default system of record, while SQLAlchemy and Alembic handle object mapping and schema evolution.

In practice, a typical flow looks like this: engineering users define products, process segments, equipment requirements, material requirements, and dispositions in the design-time client; an ERP-facing flow creates and releases operations requests; runtime users create or process lots and units against released work; server-side services update inventory, genealogy, dispatch queues, and event streams; and simulator apps make it possible to exercise the platform without external systems.

## FastAPI MES Server

The MES server is the core of the platform. It is implemented with FastAPI and organized into domain-focused modules under `server/src/mes/core`. These modules cover areas such as operations requests, WIP, dispatch, material management, physical model, product definition, performance, authentication, and plugins.

Key responsibilities of the server include:

- Exposing REST endpoints for configuration, execution, inventory, dispatch, and reporting workflows.
- Managing lots, units, operations requests, material lots, inventory balances, and equipment state.
- Publishing domain events through an internal async event bus and surfacing selected events to clients over WebSocket.
- Running plugin lifecycle management so built-in and user plugins can register routes, event handlers, and integration behavior.
- Enforcing authentication and role-based access control across both API and UI-backed workflows.

The server is intentionally modular. Core services implement business rules, route modules expose those capabilities through HTTP endpoints, and shared framework pieces such as the event bus and plugin manager support extension without tightly coupling new behavior into the base application.

## Vite Applications

The front end is not a single monolith. Instead, MES AI uses multiple Vite apps so each workflow can evolve with minimal cross-coupling.

### Design-Time Client

The design-time app is aimed at engineers and administrators. It manages configuration-heavy workflows such as products, process definitions, dispositions, plugin management, and reference data. It uses React, TypeScript, React Router, TanStack Query, Axios, Zod, and React Hook Form to provide structured forms and API-driven screens.

### Runtime Client

The runtime app is aimed at operators and supervisors. It focuses on active WIP, step processing, dispatch decisions, inventory movements, and hold or disposition handling. It uses the same core React and TypeScript stack as the design-time app, with TanStack Query and Axios handling server communication.

### ERP Simulator

The ERP simulator is a Vite app that exercises inbound planning and order-release scenarios without requiring a real ERP connection. It is useful for demos, development, and integration testing of operations-request flows.

### Equipment Simulator

The equipment simulator is a smaller React and Vite application used to mimic equipment interactions in development environments. It supports fast feedback when validating server behavior and equipment-facing workflows.

## Technology Stack

### Backend

- Python 3.12+
- FastAPI for the HTTP API and OpenAPI generation
- SQLAlchemy 2 async ORM for persistence
- Alembic for migrations
- Pydantic v2 and `pydantic-settings` for schemas and configuration
- PostgreSQL as the default database
- Uvicorn and `asyncio` for the ASGI runtime
- PyJWT-based token handling for authentication flows

The Python package also defines optional dependencies for protocol and integration scenarios such as OPC UA, MQTT, SAP, SQL Server, Oracle, Modbus, Kafka, NATS, RabbitMQ, Redis, STOMP, and AVEVA-related integration work.

### Frontend

- React 19
- TypeScript 5
- Vite 6
- React Router
- TanStack Query
- Axios
- Tailwind CSS 4

The design-time app additionally uses Headless UI, Heroicons, Zod, React Hook Form, Mermaid, and the React Hook Form resolver package to support richer authoring and visualization workflows.

### Quality and Developer Tooling

- Pytest and `pytest-asyncio` for server testing
- Playwright and pytest-based SQA flows for end-to-end browser coverage
- Ruff for linting and formatting in the Python codebase
- Pyright for type checking
- ESLint for the Vite applications

## Extension Model

One of the defining architectural choices in MES AI is the plugin model. Rather than treating integrations and custom workflows as hard-coded special cases, the system uses a plugin framework that can load built-in and user-defined plugins. Plugins can contribute REST endpoints, event handlers, equipment behavior, dispatch strategies, and other extension logic.

This matters because manufacturing implementations are rarely identical. Site-specific behavior, ERP mappings, equipment protocols, and workflow rules can be introduced through plugins while the core platform stays stable.

## Deployment and Operating Model

MES AI is developed as a multi-application workspace. The server runs as a FastAPI service, and each client runs as its own Vite application during development. In local workflows, simulators and operator clients can be launched independently against the same server instance. This makes it straightforward to test design-time configuration, runtime execution, ERP release flows, and equipment-facing behavior side by side.

The default persistence model is PostgreSQL, with schema management handled through Alembic migrations and environment-driven configuration on the server side.

## When to Read the Full Architecture Document

This overview is intended to help a reader quickly understand what the project is, how the main pieces fit together, and which technologies are in use. For deeper detail on domain modules, API surfaces, data model decisions, plugin lifecycles, event topics, or ISA-95 alignment, see `docs/ARCHITECTURE.md`.