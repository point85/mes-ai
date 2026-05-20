# MES AI Architecture

This document is the authoritative technical reference for the MES AI platform. It covers system structure, API design, authentication, the event bus, and configuration. See [README.md](../README.md) for the product overview and [docs/USER_GUIDE.md](USER_GUIDE.md) for end-user setup instructions.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Layout](#2-repository-layout)
3. [Backend Structure](#3-backend-structure)
4. [Frontend Clients](#4-frontend-clients)
5. [Database Layer](#5-database-layer)
6. [REST API](#6-rest-api)
7. [WebSocket Event Stream](#7-websocket-event-stream)
8. [Event Bus](#8-event-bus)
9. [Plugin System](#9-plugin-system)
10. [Logging](#10-logging)
11. [Authentication and Authorization](#11-authentication-and-authorization)
12. [Configuration Reference](#12-configuration-reference)

---

## 1. System Overview

MES AI is a FastAPI-based Manufacturing Execution System framework. The server owns the domain model, business rules, persistence, and event publication. Multiple Vite/React browser clients provide focused user experiences for engineering, operations, and simulation. A plugin system extends the platform without modifying the core.

```
Browser Clients (Vite/React)
  dt-client   run-client   erp-sim   equip-sim
         |         |           |         |
         └─────────┴───────────┴─────────┘
                       HTTP / WebSocket
                            │
                     MES Server (FastAPI)
                     ┌──────┴──────┐
                   Core         Plugins
                  Domain       (system/user)
                     │
                  PostgreSQL / MSSQL / Oracle
```

---

## 2. Repository Layout

```
mes_ai/
├── server/              # Python FastAPI application
│   ├── src/mes/
│   │   ├── core/        # Domain modules (wip, dispatch, operations, ...)
│   │   ├── framework/   # Auth, DB, events, plugins, admin API
│   │   ├── adapters/    # ERP and protocol adapters
│   │   ├── config.py    # Pydantic-settings configuration
│   │   ├── main.py      # FastAPI app factory and lifespan
│   │   └── cli.py       # Plugin management CLI
│   ├── plugins/
│   │   ├── system/      # Built-in plugins (equipment, MQTT, historians, ...)
│   │   └── user/        # Site-specific user plugins
│   ├── alembic/         # Database migration scripts
│   └── tests/           # Unit and integration tests
├── clients/
│   ├── design_time/     # dt-client: configuration and master data
│   ├── run_time/        # rt-client: shop-floor execution
│   ├── erp_simulator/   # ERP inbound/outbound flow simulator
│   └── equipment_simulator/  # Equipment-facing behavior simulator
└── docs/                # Architecture, diagrams, user guide
```

---

## 3. Backend Structure

### 3.1 Domain Modules (`server/src/mes/core/`)

Each domain module follows the same layout:

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy ORM models |
| `schemas.py` | Pydantic request/response schemas |
| `service.py` | Business logic |
| `routes.py` | FastAPI router |
| `events.py` | Typed event factory functions |

Domain modules: `wip`, `operations`, `dispatch`, `material`, `physical_model`, `product_definition`, `performance`, `quality`, `data_collection`, `inventory`, `genealogy`.

### 3.2 Framework Modules (`server/src/mes/framework/`)

| Module | Purpose |
|--------|---------|
| `auth/` | Authentication, JWT, RBAC (see §11) |
| `db.py` | SQLAlchemy async engine and session factory |
| `events/` | Internal pub/sub event bus and WebSocket gateway (see §8) |
| `plugin/` | Plugin lifecycle management |
| `admin/` | Server configuration API |
| `api/` | Shared response helpers and exception types |

---

## 4. Frontend Clients

### 4.1 Design-Time Client (`clients/design_time/`)

Manages configuration-heavy workflows: products, routes, dispositions, equipment, plugins, user administration, and server settings. This is the only client with full authentication support — it implements the `AuthContext`, `AuthGuard`, login page, and JWT token lifecycle (see §11.5).

### 4.2 Runtime Client (`clients/run_time/`)

Shop-floor execution: WIP creation and step processing, dispatch decisions, inventory movements, hold and disposition handling. Subscribes to the WebSocket event stream for near-real-time updates. Makes unauthenticated requests to the server; `AUTH_MODE` does not affect this client.

### 4.3 ERP Simulator (`clients/erp_simulator/`)

Exercises inbound planning and order-release scenarios and outbound reporting touch points without a real ERP connection. Sends a custom `X-MES-ERP-PLUGIN` header. The `/api/v1/erp/*` routes it calls carry no auth guards; `AUTH_MODE` does not affect this client.

### 4.4 Equipment Simulator (`clients/equipment_simulator/`)

Mimics equipment interactions for development and integration testing of equipment-facing workflows. Makes unauthenticated requests; `AUTH_MODE` does not affect this client.

---

## 5. Database Layer

- **ORM**: SQLAlchemy 2 async with `asyncpg` (PostgreSQL), `aiomysql` (MySQL), or appropriate drivers for MSSQL / Oracle.
- **Migrations**: Alembic, managed via `alembic upgrade head` on server start (or manually).
- **Session**: One `AsyncSession` per request via a FastAPI dependency (`get_db_session`).
- **Supported engines**: PostgreSQL (default), SQL Server, Oracle.
- **Configuration**: `MES_DATABASE_URL` in `server/.env`. This setting is intentionally excluded from the admin settings API and must be set directly in the environment or `.env` file.

---

## 6. REST API

All routes are versioned under `/api/v1/`. The OpenAPI spec is available at `/docs` (Swagger UI) and `/redoc`.

### 6.1 Route Prefixes

| Prefix | Domain |
|--------|--------|
| `/api/v1/auth/` | Authentication and user management |
| `/api/v1/admin/config` | Server configuration (admin only) |
| `/api/v1/units/` | WIP units |
| `/api/v1/lots/` | WIP lots |
| `/api/v1/orders/` | Operations requests |
| `/api/v1/dispatch/` | Dispatch strategies and evaluation |
| `/api/v1/equipment/` | Equipment and physical model |
| `/api/v1/materials/` | Material definitions and lots |
| `/api/v1/inventory/` | Inventory balances and transactions |
| `/api/v1/erp/` | ERP adapter inbound/outbound |
| `/api/v1/plugins/` | Plugin management |
| `/api/v1/ws/events` | WebSocket event stream |
| `/health` | Server health and current auth mode |

### 6.2 Response Envelope

All successful responses use a standard envelope:

```json
{ "status": "success", "data": <payload> }
```

List responses:

```json
{ "status": "success", "data": [...], "total": <int> }
```

### 6.3 Auth Endpoints

Defined in `server/src/mes/framework/auth/routes.py`. See §11 for full authentication documentation.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/local/login` | Username/password login (local mode only) |
| `POST` | `/api/v1/auth/local/refresh` | Exchange refresh token for new access + refresh tokens |
| `GET` | `/api/v1/auth/me` | Current authenticated user profile and roles |
| `GET` | `/api/v1/auth/users` | List all active users (admin only) |
| `POST` | `/api/v1/auth/users` | Create a local user (admin only; blocked in OIDC mode) |
| `PUT` | `/api/v1/auth/users/{id}` | Update user profile or password (admin only) |
| `DELETE` | `/api/v1/auth/users/{id}` | Soft-delete user (admin only) |
| `GET` | `/api/v1/auth/roles` | List roles and permissions |
| `POST` | `/api/v1/auth/roles` | Create role (admin only) |

---

## 7. WebSocket Event Stream

The server exposes a WebSocket endpoint at `/api/v1/ws/events`. On connect, all server-side `MESEvent` objects are forwarded as JSON to every connected client.

**Client-side filtering**: After connecting, a client may send a subscribe message to receive only matching topics:

```json
{ "action": "subscribe", "topics": ["wip.unit.*", "dispatch.*"] }
```

If no subscribe message is sent, the client receives all events. Topic patterns follow dot-notation with `*` as a wildcard for a segment and all descendants (e.g. `wip.*` matches `wip.unit.moved`, `wip.lot.created`, etc.).

**MESEvent schema**:

```json
{
  "event_id": "<uuid>",
  "event_type": "wip.unit.moved",
  "source": "WIP-TRACK",
  "timestamp": "<ISO-8601>",
  "payload": { ... }
}
```

---

## 8. Event Bus

### 8.1 Purpose

The internal event bus decouples domain services from plugins, integrations, and the WebSocket gateway. Services publish typed events; handlers (plugins, the WS gateway, other services) subscribe without knowing about each other.

### 8.2 Implementation

`EventBus` is an in-process async pub/sub singleton in `server/src/mes/framework/events/bus.py`. It is available throughout the server as `from mes.framework.events import event_bus`.

**Publish**:

```python
await event_bus.publish(MESEvent(event_type="wip.unit.moved", source="WIP-TRACK", payload={...}))
```

**Subscribe**:

```python
event_bus.subscribe("wip.unit.*", my_async_handler)
```

### 8.3 Topic Matching

Topics use dot-notation. Subscription patterns support:

| Pattern | Matches |
|---------|---------|
| `wip.unit.moved` | Exact match only |
| `wip.unit.*` | Any event whose first two segments are `wip.unit` |
| `wip.*` | Any event under `wip.` (all depths) |
| `*` | All events |

### 8.4 Error Isolation

Handlers are invoked concurrently via `asyncio.gather`. A failing handler logs the error but does not affect other handlers or the publisher.

### 8.5 Transport Configuration

The current implementation is in-process only. The `MES_EVENT_BUS_TYPE` setting and the `EventBus` interface are designed to allow swapping the transport to Redis, Kafka, or NATS without changing publisher or subscriber code.

| `MES_EVENT_BUS_TYPE` | Description |
|----------------------|-------------|
| `memory` (default) | In-process; no external infrastructure; suitable for single-server deployments |
| `redis` | Distributed via Redis pub/sub; required when running multiple MES server instances that must share events across processes |

When `redis` is selected, `MES_REDIS_URL` must also be set (default: `redis://localhost:6379`).

These settings are editable from the dt-client **Admin → Settings** page under the **Event Bus** section. Changes are written to `server/.env` and require a server restart.

---

## 9. Plugin System

Plugins are Python packages discovered from two directories:

- `server/plugins/system/` — built-in platform plugins
- `server/plugins/user/` — site-specific user plugins

Each plugin has a `manifest.yaml` and a `plugin.py` implementing a `MESPlugin` subclass with `initialize()`, `start()`, and `stop()` lifecycle methods. Plugins can contribute FastAPI routes, event bus handlers, and integration logic.

Plugins are managed through the dt-client **Admin → Plugins** page or via the CLI:

```
python -m mes.cli plugin list
python -m mes.cli plugin install <plugin_id>
```

Plugin directories are configurable via `MES_PLUGIN_DIR` and `MES_PLUGIN_USER_DIR`.

---

## 10. Logging

Server logs are written to `server/logs/<MES_LOG_FILE>` with rotation. Console output is controlled by `MES_LOG_TO_CONSOLE`.

| Setting | Default | Description |
|---------|---------|-------------|
| `MES_LOG_LEVEL` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `MES_LOG_FILE` | `mes_server.log` | Log filename inside `server/logs/` |
| `MES_LOG_MAX_BYTES` | `10485760` | Max file size before rotation (10 MB) |
| `MES_LOG_BACKUP_COUNT` | `5` | Number of rotated files to retain |
| `MES_LOG_TO_CONSOLE` | `true` | Mirror log output to stdout |

Log level and file name are editable from dt-client **Admin → Settings** under the **Logging** section.

---

## 11. Authentication and Authorization

### 11.1 Auth Modes

The server supports three authentication modes, controlled by `MES_AUTH_MODE` in `server/.env`:

| Mode | Description | Use Case |
|------|-------------|----------|
| `none` | All requests are accepted without credentials. A synthetic `dev-admin` user with full permissions is injected into every request. | Local development only. **Never use in production.** |
| `local` | Username/password authentication. Credentials are stored in the MES database (PBKDF2-SHA256 hashed). JWTs are issued on login. | Air-gapped environments, evaluation installs, small internal deployments. |
| `oidc` | Authentication is delegated to an external OpenID Connect Identity Provider (IdP). JWTs are issued after the IdP flow completes. Users are provisioned Just-in-Time. | Production deployments with enterprise SSO (Keycloak, Okta, Azure AD, Auth0, etc.). |

The `AUTH_MODE` is also exposed by the `GET /health` endpoint so browser clients can discover the mode at startup without requiring credentials:

```json
{ "status": "ok", "auth_mode": "local", "event_bus": "memory", ... }
```

**Only the dt-client** implements authentication. The rt-client, ERP simulator, and equipment simulator make unauthenticated requests and are not affected by the auth mode setting.

### 11.2 Local Mode Flow

1. User submits credentials to `POST /api/v1/auth/local/login`.
2. Server verifies the PBKDF2-SHA256 password hash stored in `users.hashed_password`.
3. Server returns a JWT access token (short-lived, default 15 min) and a refresh token (long-lived, default 7 days).
4. The dt-client stores both tokens in `localStorage` via `tokenStorage`.
5. Every subsequent API request carries the access token as `Authorization: Bearer <token>`.
6. An Axios interceptor in the dt-client transparently refreshes expired access tokens via `POST /api/v1/auth/local/refresh`.

On first boot with an empty users table, the server auto-seeds a default `admin` / `admin` user. **Change this password immediately in any non-development environment.**

Creating local users while `AUTH_MODE=oidc` is blocked by the server with an explicit error.

### 11.3 OIDC Mode Flow

1. Browser is redirected to the IdP's authorization endpoint.
2. IdP authenticates the user and redirects to `MES_OIDC_REDIRECT_URI` with an authorization code.
3. The server exchanges the code for an ID token, validates it against `MES_OIDC_ISSUER`.
4. The server reads the claim named by `MES_OIDC_ROLE_CLAIM` (default `groups`) to map IdP groups to MES roles.
5. If no matching MES user exists for the IdP `sub` + `iss` combination, one is created Just-in-Time (JIT provisioning). No password is stored.
6. The server issues its own MES JWT; from this point the token lifecycle is the same as local mode.

OIDC user records carry `idp_subject` (the IdP `sub` claim) and `idp_issuer` (the IdP `iss` claim) instead of `hashed_password`.

#### §11.3.1 Permission Wildcards

Permissions use dot-notation with wildcard support:

| Permission string | Grants |
|-------------------|--------|
| `*` | All permissions (admin) |
| `wip.*` | All WIP permissions |
| `*.read` | All read permissions across every domain |
| `wip.unit.move` | Exact permission only |

#### §11.3.2 Built-in Roles

| Role | Permissions |
|------|-------------|
| `admin` | `["*"]` — full access |
| `engineer` | `physical_model.*`, `product_def.*`, `production.order.*`, `dispatch.*`, `material.*`, `data_collect.*`, `performance.*`, `wip.read`, `plugin.read` |
| `operator` | `wip.*`, `dispatch.read`, `dispatch.execute`, `data_collect.read`, `data_collect.record`, `material.read`, `material.consume`, `performance.read`, plus `.read` on most other domains |
| `viewer` | `*.read` — read-only across all domains |

#### §11.3.3 Default Roles and Seeding

Default roles and their permissions are seeded at server startup by `AuthService.seed_default_roles()`. This is idempotent — existing roles are not overwritten.

### 11.4 JWT Structure

Access token payload:

```json
{
  "sub":         "<user-uuid>",
  "username":    "alice",
  "roles":       ["engineer"],
  "permissions": ["wip.*", "dispatch.read", ...],
  "exp":         <unix-timestamp>,
  "iat":         <unix-timestamp>,
  "type":        "access"
}
```

Permissions are flattened into the token so that `require_permission()` route guards do not need a database round-trip.

Signing algorithm is controlled by `MES_ALGORITHM` (default `HS256`; `HS384`, `HS512`, `RS256` also supported).

### 11.5 DT-Client Authentication

The dt-client reads `auth_mode` from `GET /health` once on startup (`AuthContext`). Behaviour per mode:

| `auth_mode` | dt-client behaviour |
|-------------|---------------------|
| `none` | `AuthGuard` passes all routes through without checking for a token. No login page is shown. |
| `local` | `AuthGuard` requires a valid access token. Users are redirected to `/login` if no token is present or if the token is expired and the refresh attempt fails. The login page calls `POST /api/v1/auth/local/login`. |
| `oidc` | Same token gate as `local`. The login page initiates the OIDC redirect instead of a username/password form. |

`AuthContext` exposes `{ authMode, isLoading, currentUser, login(), logout() }` to all child components.

`logout()` clears `localStorage` tokens and redirects the browser to `/login`.

### 11.6 Settings Page — Auth Configuration

Authentication settings are configurable from the dt-client **Admin → Settings** page (`GET`/`PATCH /api/v1/admin/config`). Settings are persisted to `server/.env` and take effect after a server restart (a banner is shown after saving).

#### Authentication section

| Label | Env var | Type | Description |
|-------|---------|------|-------------|
| Authentication Mode | `MES_AUTH_MODE` | Select | `none` / `local` / `oidc` |
| JWT Secret Key | `MES_SECRET_KEY` | Password (masked) | Signs all JWTs. Must be changed from the default in production. |
| JWT Algorithm | `MES_ALGORITHM` | Select | `HS256` / `HS384` / `HS512` / `RS256` |
| Access Token Expiry (minutes) | `MES_ACCESS_TOKEN_EXPIRE_MINUTES` | Number | How long access tokens remain valid. Default: 15. |
| Refresh Token Expiry (days) | `MES_REFRESH_TOKEN_EXPIRE_DAYS` | Number | How long refresh tokens remain valid. Default: 7. |

#### OIDC Settings section

These settings are only relevant when `MES_AUTH_MODE=oidc`.

| Label | Env var | Type | Description |
|-------|---------|------|-------------|
| OIDC Issuer URL | `MES_OIDC_ISSUER` | Text | IdP discovery URL (e.g. `https://auth.company.com/realms/mes`) |
| OIDC Client ID | `MES_OIDC_CLIENT_ID` | Text | Client ID registered with the IdP |
| OIDC Client Secret | `MES_OIDC_CLIENT_SECRET` | Password (masked) | Client secret. Write-only once saved. |
| OIDC Scopes | `MES_OIDC_SCOPES` | Text | Comma-separated scopes. Default: `openid,profile,email` |
| OIDC Role Claim | `MES_OIDC_ROLE_CLAIM` | Text | JWT claim carrying the user's groups/roles. Default: `groups` |
| OIDC Redirect URI | `MES_OIDC_REDIRECT_URI` | Text | OAuth callback URL registered with the IdP |

`MES_DATABASE_URL` and database pool settings are intentionally excluded from the settings API and must be configured directly in `server/.env` or the host environment.

### 11.7 Auth Recovery

If authentication is misconfigured and access to the dt-client is lost:

1. Edit `server/.env` directly and set `MES_AUTH_MODE=none`.
2. Restart the MES server.
3. Open dt-client — the login gate is bypassed.
4. Reconfigure authentication in **Admin → Settings**.

The helper script `reset-auth.ps1` (Windows) or `reset-auth.sh` (Linux/macOS) automates step 1.

---

## 12. Configuration Reference

All settings are loaded by `pydantic-settings` from environment variables prefixed with `MES_` or from `server/.env`. In-memory values are frozen at process start; changes to `.env` require a server restart.

| Env var | Default | Description |
|---------|---------|-------------|
| `MES_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai` | SQLAlchemy async database URL. **Excluded from settings API.** |
| `MES_DB_POOL_SIZE` | `20` | SQLAlchemy connection pool size. **Excluded from settings API.** |
| `MES_DB_MAX_OVERFLOW` | `10` | Max overflow connections above pool size. **Excluded from settings API.** |
| `MES_DB_ECHO` | `false` | Log all SQL statements (debug only). **Excluded from settings API.** |
| `MES_AUTH_MODE` | `none` | Authentication mode: `none`, `local`, or `oidc`. |
| `MES_SECRET_KEY` | `CHANGE_ME_IN_PRODUCTION` | JWT signing secret. Masked in settings API. |
| `MES_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `MES_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime in minutes. |
| `MES_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days. |
| `MES_OIDC_ISSUER` | _(empty)_ | OIDC provider issuer URL. |
| `MES_OIDC_CLIENT_ID` | _(empty)_ | OIDC client ID. |
| `MES_OIDC_CLIENT_SECRET` | _(empty)_ | OIDC client secret. Masked in settings API. |
| `MES_OIDC_SCOPES` | `openid,profile,email` | OIDC token scopes. |
| `MES_OIDC_ROLE_CLAIM` | `groups` | JWT claim for role/group mapping. |
| `MES_OIDC_REDIRECT_URI` | _(empty)_ | OIDC OAuth callback URI. |
| `MES_EVENT_BUS_TYPE` | `memory` | Event bus transport: `memory` or `redis`. |
| `MES_REDIS_URL` | `redis://localhost:6379` | Redis URL (used when `EVENT_BUS_TYPE=redis`). |
| `MES_LOG_LEVEL` | `WARNING` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `MES_LOG_FILE` | `mes_server.log` | Log filename inside `server/logs/`. |
| `MES_LOG_MAX_BYTES` | `10485760` | Log file size before rotation (bytes). |
| `MES_LOG_BACKUP_COUNT` | `5` | Number of rotated log files to keep. |
| `MES_LOG_TO_CONSOLE` | `true` | Mirror log output to stdout. |
| `MES_PLUGIN_DIR` | `plugins/system` | System plugin directory path. |
| `MES_PLUGIN_USER_DIR` | `plugins/user` | User plugin directory path. |
