---
status: approved
feature: get-all-employees
---

# Plan: Get All Employees

## Architecture overview

```
HTTP Client
    │
    │ GET /api/v1/employees
    ▼
FastAPI Route Handler        (app/routes/employees.py)
    │  - no request validation needed (no params/body)
    │  - calls service layer
    │  - serializes result via Pydantic response schema
    ▼
Employee Service             (app/services/employee_service.py)
    │  - owns the query: SELECT all rows
    │  - no business logic beyond a straight read (v1)
    ▼
SQLAlchemy ORM Session        (app/models/employee.py + DB session dependency)
    │  - Employee declarative model mapped to existing table
    ▼
PostgreSQL — existing `employee` table (external, pre-existing, not owned by this app)
```

**Data flow:** request → route → service.get_all_employees(db) → ORM `SELECT * FROM employee` → list[Employee] → route maps to list[EmployeeResponse] (Pydantic) → JSON array, 200.

**System boundary:** this service only *reads* the existing `employee` table. It does not run migrations against it, does not own its DDL, and does not assume responsibility for its schema evolving — see Risks.

## Tech stack choices

| Component | Choice | Rationale |
|---|---|---|
| Web framework | FastAPI | Given by CLAUDE.md |
| ORM | SQLAlchemy 2.0 (declarative) | See ADR-1 |
| DB driver | psycopg2-binary (sync) | See ADR-3 |
| Response validation | Pydantic (via FastAPI) | Already bundled with FastAPI; enforces FR-004 field types |
| Config loading | python-dotenv | Loads `DATABASE_URL` from `.env` in local dev; real env vars in deployed environments |

## Data model

`Employee` (SQLAlchemy declarative model, `__tablename__ = "employee"` — table is **not** created/migrated by this app):

| Column | Type (DB) | Nullable | Type (Python/ORM) |
|---|---|---|---|
| id | INTEGER | NOT NULL | `int`, primary key |
| department | VARCHAR(255) | nullable | `Optional[str]` |
| email | VARCHAR(255) | nullable, UNIQUE | `Optional[str]` |
| name | VARCHAR(255) | nullable | `Optional[str]` |
| salary | NUMERIC(38,2) | nullable | `Optional[Decimal]` (serialized as JSON number or `null`) |

No relationships — single table, no foreign keys in scope. `email` carries a UNIQUE constraint in the DB, which this read-only feature does not need to enforce or validate against.

`EmployeeResponse` (Pydantic schema, `app/schemas/employee.py`): mirrors the model 1:1 for v1 — `id: int, department: Optional[str], email: Optional[str], name: Optional[str], salary: Optional[float]`. Nullable fields serialize `NULL` DB values as JSON `null`, per FR-004.

## API contracts

### `GET /api/v1/employees`

**Request:** no path/query params, no body, no auth header required.

**Success — 200:**
```json
[
  {
    "id": 1,
    "department": "Engineering",
    "email": "jane@example.com",
    "name": "Jane Doe",
    "salary": 95000
  },
  {
    "id": 2,
    "department": null,
    "email": "unassigned@example.com",
    "name": "New Hire",
    "salary": null
  }
]
```
Nullable columns (`department`, `email`, `name`, `salary`) serialize as JSON `null` when `NULL` in the DB — never omitted (FR-004). Empty table → `200` with body `[]` (FR-002).

**Failure — 500** (DB unreachable / query error):
```json
{ "error": "Unable to retrieve employees" }
```
No stack trace, DB error text, or connection string is ever included (FR-003).

## Integration points

- **PostgreSQL** (existing, external) — connection string via `DATABASE_URL` env var. No schema migration tooling in scope for this feature since the table pre-exists.
- No other external services, queues, or events.

## ADRs

### ADR-1: ORM choice — SQLAlchemy vs raw psycopg2
- **Problem:** need a safe, maintainable way to query the `employee` table from Python.
- **Options considered:** (a) raw psycopg2 with hand-written SQL strings, (b) SQLAlchemy Core (expression language, no model classes), (c) SQLAlchemy ORM (declarative models).
- **Chosen solution:** SQLAlchemy ORM (declarative).
- **Reasoning:** ORM queries are parameterized by construction, satisfying the project's "no raw SQL with user input" security convention without relying on developer discipline. It integrates cleanly with FastAPI's dependency-injected session pattern, and typed model objects (vs. raw tuples from Core) will be reused by the upcoming "Create an Employee" feature. Raw psycopg2 was rejected — no safety net against injection, more boilerplate. SQLAlchemy Core was rejected — no advantage over full ORM for this simple case, and loses typed model reuse across the two planned features.

### ADR-2: Explicit model definition vs automap reflection
- **Problem:** the `employee` table already exists in the DB — how should the app represent it in code?
- **Options considered:** (a) `automap_base()` to reflect the table's structure from the live DB at startup, (b) explicit declarative model with columns hand-defined to match the known schema.
- **Chosen solution:** explicit declarative model.
- **Reasoning:** the schema is small (5 columns) and was confirmed directly against the live database in T001 (not just user description — the table name and nullability both differed from the initial assumption, which the explicit model now reflects). An explicit model gives IDE/type-checker support and makes the schema self-documenting in code, with no runtime dependency on DB availability at startup just to discover columns. Automap was rejected — it couples app boot to DB reachability for schema introspection and hides column types behind runtime reflection, which is unnecessary overhead for a schema this small and stable.

### ADR-3: Sync vs async database access
- **Problem:** FastAPI supports both sync and async route handlers / DB drivers.
- **Options considered:** (a) sync SQLAlchemy engine + psycopg2, with FastAPI running the sync route handler in its threadpool, (b) async SQLAlchemy engine + asyncpg driver with fully async route handlers.
- **Chosen solution:** sync SQLAlchemy + psycopg2.
- **Reasoning:** v1 is a single, unfiltered, read-only endpoint with no stated throughput/concurrency requirement. Sync is simpler to implement, test, and debug, and FastAPI already runs sync handlers off the event loop via its threadpool, so it won't block other requests. Async was rejected as premature optimization — it adds driver complexity and async session-lifecycle management with no demonstrated need; revisit if load testing shows a bottleneck.

### ADR-4: Error response shape for database failures
- **Problem:** FR-003 requires DB failures return `500` with `{"error": string}` and never leak raw DB internals.
- **Options considered:** (a) let SQLAlchemy exceptions propagate to FastAPI's default handler, (b) catch DB exceptions inside each service method and raise a generic `HTTPException`, (c) register one global FastAPI exception handler for SQLAlchemy errors in `main.py`.
- **Chosen solution:** (c) global exception handler.
- **Reasoning:** centralizes the "never leak DB internals" rule in a single place instead of repeating try/except in every service method (this app will soon have a second endpoint — "Create an Employee" — that needs the same protection). Per-method catching was rejected as easy to forget on the next endpoint. Letting exceptions propagate raw was rejected outright — it directly violates FR-003.

## Risks

| Risk | Mitigation |
|---|---|
| ~~Actual live `employees` table schema may differ from what the user described~~ **RESOLVED (T001):** table is actually named `employee` (singular), and `department`, `email`, `name`, `salary` are all nullable (only `id` is `NOT NULL`); `email` also has a UNIQUE constraint. | Data model, API contracts, and ADRs above updated to the verified schema. `spec.md` FR-004 extended to require nullable fields serialize as JSON `null`. |
| `salary` (sensitive data) is returned with no authentication | Explicitly accepted for v1 per spec's "Out of scope" — flagged here for revisit when auth is introduced to the service. |
| `DATABASE_URL` missing/misconfigured at deploy time | App must fail fast at startup (raise on boot) rather than failing silently on the first request. |
| Unbounded result set — no pagination means the entire table returns in one response | Accepted as out-of-scope per spec for v1; revisit if the `employee` table grows large enough to matter. |

## Constitution check

- [x] No new infrastructure dependency introduced without an ADR. *(SQLAlchemy + psycopg2-binary — ADR-1)*
- [x] All API errors follow `{ error: string }` shape. *(ADR-4, FR-003)*
- [x] No business logic in route handlers — service layer owns it. *(Architecture overview: route → service → model)*
- [x] All secrets managed via environment variables, never hardcoded. *(`DATABASE_URL` via env, per CLAUDE.md)*

Feature-specific:
- [x] Response includes only the 5 confirmed columns — no extra fields.
- [x] No pagination/filtering introduced — matches spec's "Out of scope."
- [x] Live schema verification against the real database — **done (T001)**. Table is `employee` (singular); 4 of 5 columns are nullable. Plan updated accordingly — see Risks and `notes.md`.

## Sparring partner review

**Attack:** The plan assumes the user-reported schema is exactly correct without having queried the live DB — if wrong, the model and API contract break at runtime. Sync DB access could bottleneck under concurrent load since psycopg2 blocks a thread per request. No explicit connection pool size or query timeout is configured — a hung connection could hang requests indefinitely.

**Steelman:** For a v1, read-only, single-endpoint feature with no stated scale requirements, this is the simplest correct design — matches CLAUDE.md's conventions exactly, avoids speculative complexity (async, connection tuning) that has no current justification. The schema risk isn't ignored — it's gated behind an explicit first task rather than assumed away. SQLAlchemy's default connection pool is a reasonable default for this scale; tuning it now would be optimizing without a measured need.

**Honest verdict:** Plan is sound for v1 scope. The single real gap — unverified live schema — is explicitly called out, not hidden, and blocks the constitution check from being 100% green until resolved as Task 1. Connection pooling/timeout tuning is deferred, which is appropriate given the stated scale; log it as a future consideration if this moves toward higher-traffic production use.
