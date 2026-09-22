---
status: approved
feature: get-all-employees
---

# Tasks: Get All Employees

## Execution strategy

**MVP First** — this is a single, small feature (one endpoint). Tasks proceed end-to-end through one path: verify → scaffold → data layer → service → API layer → tests → manual sign-off. Limited parallelism exists only at the very start (schema verification and project scaffolding touch no shared state) and briefly mid-stream (response schema vs. config/exception-handler work).

## Tasks

- [x] **T001 [P]:** Verify the live `employees` table schema against `plan.md`'s data model by connecting to the real PostgreSQL database and inspecting the table (e.g. `\d employees` in `psql`, or querying `information_schema.columns`). Satisfies: de-risks FR-001–FR-004 (plan.md Risk #1).
      Verify: actual column names/types are captured and diffed column-by-column against plan.md's 5-column table (`id INT, department VARCHAR, email VARCHAR, name VARCHAR, salary NUMERIC`). Any mismatch is documented and `plan.md` is updated before T004 begins.
      **DONE 2026-09-21:** table is actually named `employee` (singular). Columns: `id INTEGER NOT NULL PK`, `department VARCHAR(255) NULL`, `email VARCHAR(255) NULL UNIQUE`, `name VARCHAR(255) NULL`, `salary NUMERIC(38,2) NULL`. Mismatch documented and `spec.md`/`plan.md` updated — see `notes.md`.

- [x] **T002 [P]:** Scaffold the project structure — create the `app/` package (`__init__.py`, `main.py`, and empty `models/`, `routes/`, `services/`, `schemas/` subpackages), `requirements.txt` (fastapi, uvicorn, sqlalchemy, psycopg2-binary, pydantic, python-dotenv, pytest, pytest-asyncio, httpx), and `.env.example` with `DATABASE_URL` and `APP_ENV` placeholders. Satisfies: infrastructure for FR-001–FR-004.
      Verify: `pip install -r requirements.txt` completes with no errors in a clean virtualenv; `find app -type d` lists all 4 subpackages.
      **DONE 2026-09-21:** scaffolded in a `.venv`. Package versions in `requirements.txt` bumped from plan.md's originals — the local Python is 3.14, which has no prebuilt wheels for the originally planned pydantic 2.5.0/psycopg2 2.9.9. Pinned to the latest versions that installed cleanly instead (fastapi 0.141.1, pydantic 2.13.5, etc.) — see `notes.md`.

- [x] **T003:** Implement `app/config.py` — load `DATABASE_URL` and `APP_ENV` from environment variables (via `python-dotenv` for local `.env`), failing fast by raising at import time if `DATABASE_URL` is unset. Satisfies: constitution "secrets via env vars"; plan.md Risk "DATABASE_URL misconfigured at deploy time".
      Verify: running `python -c "import app.config"` with `DATABASE_URL` unset raises a clear exception; with it set, the import succeeds silently.
      Depends on: T002
      **DONE 2026-09-21:** verified both branches manually — `KeyError: 'DATABASE_URL'` when unset, clean import when set via `.env`.

- [x] **T004:** Implement `app/models/employee.py` — SQLAlchemy engine, `SessionLocal` factory, `get_db` FastAPI dependency, and the `Employee` declarative model using the schema confirmed in T001. Satisfies: FR-001, FR-004 (ADR-1, ADR-2, ADR-3).
      Verify: `python -c "from app.models.employee import SessionLocal, Employee; db = SessionLocal(); print(db.query(Employee).all())"` runs against the real DB and returns a list of `Employee` objects (or `[]`) without error, with `id` as `int` and `salary` as `Decimal`.
      Depends on: T001, T003
      **DONE 2026-09-21:** ran against the real `employee_db` — returned 1 seeded row with `id: int`, `salary: Decimal('5000.00')`.

- [x] **T005 [P]:** Implement `app/schemas/employee.py` — Pydantic `EmployeeResponse` model (`id: int, department: Optional[str], email: Optional[str], name: Optional[str], salary: Optional[float]`) for response serialization. Satisfies: FR-004.
      Verify: `EmployeeResponse(id=1, department="Eng", email="a@b.com", name="Jane", salary=95000).model_dump()` produces a dict with `salary` as a JSON-serializable `float`, not `Decimal`; all-`None` case also validates cleanly.
      Depends on: T001
      **DONE 2026-09-21:** verified both the populated and all-`None` cases.

- [x] **T006:** Implement `app/services/employee_service.py` — `get_all_employees(db: Session) -> list[Employee]` running `db.query(Employee).all()`, with no business logic beyond the read. Satisfies: FR-001, FR-002.
      Verify: unit test with a test DB session seeded with 2 rows returns exactly those 2 rows; with 0 rows, returns `[]`.
      Depends on: T004
      **DONE 2026-09-21:** covered by `tests/test_employees.py` (T010) — `test_get_all_employees_returns_seeded_rows` and `test_get_all_employees_returns_empty_array_when_no_rows`, both passing.

- [x] **T007:** Implement `app/main.py` — FastAPI app instance and a global exception handler for `SQLAlchemyError` (and generic unhandled DB errors) that returns `500` with body `{"error": "Unable to retrieve employees"}`, logging the real exception server-side without exposing it in the response. Satisfies: FR-003 (ADR-4).
      Verify: with the DB stopped/unreachable, `GET /api/v1/employees` returns `500` with body exactly `{"error": "Unable to retrieve employees"}` and no stack trace or connection string anywhere in the response.
      Depends on: T002, T003
      **DONE 2026-09-21:** verified live against an unreachable port (5999) — `500`, exact error body, response text grepped for leaks (none found).

- [x] **T008:** Implement `app/routes/employees.py` — `GET /api/v1/employees` handler calling `employee_service.get_all_employees(db)` via `Depends(get_db)`, returning `list[EmployeeResponse]`; register the router in `main.py`. Satisfies: FR-001, FR-002, FR-004.
      Verify: `curl http://localhost:8000/api/v1/employees` against a seeded DB returns `200` with a JSON array whose objects' fields and types match the seeded rows exactly.
      Depends on: T005, T006, T007
      **DONE 2026-09-21:** verified live against the real DB — `200`, matching JSON array.

- [x] **T009 [P]:** Write `tests/conftest.py` — pytest fixtures for a test DB session/engine (transactional rollback per test, or a dedicated test database) and a FastAPI `TestClient`. Satisfies: testing infrastructure for FR-001–FR-004.
      Verify: `pytest tests/ --collect-only` succeeds with no fixture errors.
      Depends on: T004
      **DONE 2026-09-21:** used an in-memory SQLite DB (`StaticPool`) rather than a real Postgres test instance — faster, no external dependency for the test suite. Deviation logged in `notes.md`.

- [x] **T010:** Write `tests/test_employees.py` covering FR-001 (seeded employees returned with correct fields/types), FR-002 (empty table → `[]`), FR-003 (simulated DB failure → `500` + `{"error": ...}`), FR-004 (JSON field types correct, including nulls). Satisfies: FR-001, FR-002, FR-003, FR-004.
      Verify: `pytest tests/test_employees.py -v` passes all test cases with zero failures.
      Depends on: T008, T009
      **DONE 2026-09-21:** 5/5 tests passing.

- [x] **T011:** Manual end-to-end verification — start the app against the real (non-test) PostgreSQL database with `uvicorn app.main:app --reload` and call `GET /api/v1/employees`. Satisfies: final sign-off on FR-001, FR-002, FR-004 against real data.
      Verify: response status is `200`, body is a JSON array, and at least one returned row's values exactly match a row queried directly via `psql -c "SELECT * FROM employee LIMIT 1"`.
      Depends on: T010
      **DONE 2026-09-21:** API response `{"id":1,"department":"IT","email":"test@example.com","name":"Test Employee","salary":5000.0}` matches `psql` output exactly (5000.0 vs. displayed 5000.00 — same numeric value).

## Dependency tree

```
Level 0 (no dependencies — can start immediately, in parallel)
  T001 [P]  Verify live schema
  T002 [P]  Scaffold project

Level 1
  T003  ← T002              Config (env vars, fail-fast)
  T005 [P]  ← T001           Response schema (Pydantic)

Level 2
  T004  ← T001, T003         Employee model + DB session
  T007  ← T002, T003         FastAPI app + global exception handler

Level 3
  T006  ← T004               Employee service (query layer)
  T009 [P]  ← T004           Test fixtures (conftest.py)

Level 4
  T008  ← T005, T006, T007   Route handler (wires everything together)

Level 5
  T010  ← T008, T009         Automated tests

Level 6
  T011  ← T010               Manual real-DB verification
```
