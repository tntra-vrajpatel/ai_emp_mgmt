# Notes: Get All Employees

Append-only decision log for this feature.

## 2026-09-21 — Spec clarification (Product Manager phase)

Initial request lacked enough detail to write testable acceptance criteria. Resolved via clarifying questions before drafting `spec.md`:

- **Employee schema**: user provided the real column list from the existing PostgreSQL `employees` table: `id INT, department VARCHAR, email VARCHAR, name VARCHAR, salary NUMERIC`.
- **Authentication**: none for v1 — endpoint is unauthenticated. Flagged as a tradeoff since the table includes `salary`.
- **Response shape**: bare JSON array (`[{...}, {...}]`), not a wrapped envelope like `{"employees": [...], "count": N}`.
- **Salary exposure**: explicitly decided to include `salary` in the response despite no auth in v1. This is a conscious risk acceptance for v1, not an oversight — worth revisiting if/when auth is added (see spec's "Out of scope").

## Template/docs gap

This project's `.claude/` setup was copied partially from the `ai-engineering-playbook` repo — only `agents/`, `skills/`, and `specs/README.md` were copied, not `templates/` or `docs/`. `spec.md` was written directly from the format embedded in `.claude/agents/product-manager.md` rather than from `templates/spec.md`. If the full playbook templates are added later, reconcile formatting against them.

## 2026-09-21 — Plan sparring partner review (Architect phase)

Per `.claude/agents/architect.md`, ran the attack / steelman / honest verdict review before marking the plan ready for review:

- **Attack:** Plan assumes the user-reported schema is correct without querying the live DB — if wrong, the model/contract break at runtime. Sync DB access (psycopg2) could bottleneck under concurrent load; no explicit connection pool size or query timeout configured — a hung connection could hang requests indefinitely.
- **Steelman:** For a v1, read-only, single-endpoint feature with no stated scale requirements, this is the simplest correct design and matches CLAUDE.md's conventions exactly. The schema risk isn't ignored — it's gated behind an explicit first implementation task. Default SQLAlchemy connection pooling is reasonable for this scale; tuning now would be optimizing without a measured need.
- **Honest verdict:** Plan is sound for v1 scope. The one real gap — unverified live schema — is explicitly called out in the plan's constitution check (left unchecked, not glossed over) and must become the first task in `tasks.md`. Connection pooling/timeout tuning is deferred as appropriate for the stated scale; revisit if this moves toward higher-traffic production use.

**Outcome:** plan.md written with `status: draft`. Constitution check is 3/4 fully green; the 4th item (live schema verification) is intentionally left unchecked and pushed into Phase 3 as the mandatory first task, per architect.md's rule that an unchecked box must be justified rather than hidden.

## 2026-09-21 — T001 schema verification: deviation from approved spec/plan (Developer phase)

Per `.claude/agents/developer.md`'s notes discipline: a requirement was found to be wrong in practice once verified against the real database. Ran `psql "postgresql://postgres@localhost:5432/employee_db" -c "\d employees"` — no such relation. `\dt` showed the actual table is named **`employee`** (singular).

Full verified schema via `\d employee`:
```
   Column   |          Type          | Nullable | Default
------------+-------------------------+----------+---------
 id         | integer                 | NOT NULL |
 department | character varying(255)  |          |
 email      | character varying(255)  |          |
 name       | character varying(255)  |          |
 salary     | numeric(38,2)           |          |
Indexes:
    "employee_pkey" PRIMARY KEY, btree (id)
    "ukfopic1oh5oln2khj8eat6ino0" UNIQUE CONSTRAINT, btree (email)
```

Two deviations from what was assumed at spec/plan time:
1. **Table name is `employee`, not `employees`.** The user's original schema description gave column names/types correctly but didn't mention the table name explicitly enough to catch this; it was assumed to match the spec's working title.
2. **Only `id` is `NOT NULL`.** `department`, `email`, `name`, `salary` are all nullable — the original spec/plan assumed all fields were always populated (FR-004 examples used only non-null values).

**Resolution:** `spec.md` FR-004 extended with a second Given/When/Then for the null case; `plan.md`'s data model, architecture diagram, API contract example, ADR-1/ADR-2, and Risks/Constitution-check sections updated to `employee` (singular) and `Optional[...]` typing; `tasks.md` T001 marked done with the verified schema, T011's verify line corrected to query `employee`. `email`'s UNIQUE constraint noted in `plan.md` as present but not relevant to this read-only feature.

This is exactly the scenario `plan.md`'s Risk #1 anticipated — schema mismatch caught by T001 before any model code was written, not after.

## 2026-09-21 — Implementation (T002–T011), two further deviations logged

**1. Dependency versions bumped from `plan.md`'s originals (T002).** The local environment runs Python 3.14.4, for which the plan's originally-listed versions (pydantic 2.5.0, psycopg2-binary 2.9.9, etc.) have no prebuilt wheels — `pip install` failed building `pydantic-core` from source (a `ForwardRef._evaluate()` incompatibility with 3.14's typing internals). Installed the latest available versions instead and pinned `requirements.txt` to what actually installed: fastapi 0.141.1, uvicorn 0.53.0, sqlalchemy 2.0.54, psycopg2-binary 2.9.13, pydantic 2.13.5, python-dotenv 1.2.3, pytest 9.1.1, pytest-asyncio 1.4.0, httpx 0.28.1. No API-shape or behavior impact — ADR-1/ADR-3's reasoning (SQLAlchemy ORM, sync driver) is unaffected by the version bump.

**2. Test database is in-memory SQLite, not Postgres (T009).** `tasks.md` T009 allowed either "transactional rollback per test, or a dedicated test database" without mandating Postgres. Chose `sqlite:///:memory:` with `StaticPool` (required — without it, SQLAlchemy opens a new connection, and thus a fresh empty DB, per checkout) for zero external dependencies and fast test runs. Tradeoff: SQLite's `NUMERIC` handling isn't byte-identical to Postgres's `NUMERIC(38,2)`, so this doesn't catch Postgres-specific numeric edge cases — acceptable for this feature's scope (a straight `SELECT *`, no arithmetic). T011's manual verification against the real Postgres DB is what actually closes that gap for this feature.

**Verification summary — all 11 tasks done and independently verified:**
- T001–T005: verified individually (schema dump, fail-fast config, live DB query, Pydantic serialization)
- T006, T010: covered by `tests/test_employees.py`, 5/5 passing (seeded rows, empty table, DB-failure 500, null serialization, field types)
- T007, T008: verified live — success path (200 + correct JSON) and failure path (DB down → 500, no leaked internals, confirmed via `grep` on the response body)
- T011: live API response diffed against direct `psql` query on the real `employee` table — exact match

All 4 FRs (FR-001–FR-004) are covered by at least one automated test and at least one live/manual check.
