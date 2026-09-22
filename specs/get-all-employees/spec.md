---
status: approved
feature: get-all-employees
---

# Spec: Get All Employees

## Context

The `user_mgmt` service needs to expose the existing employee data stored in PostgreSQL through a REST API so that client applications can retrieve the current employee roster. This is the first of two planned features for this service and establishes the initial read path into the existing `employee` table.

## Technical requirements

- Expose a `GET /api/v1/employees` endpoint that returns all rows from the existing `employee` table.
- The endpoint reads from the existing PostgreSQL `employee` table (columns: `id INTEGER NOT NULL` (primary key), `department VARCHAR(255)` (nullable), `email VARCHAR(255)` (nullable, unique), `name VARCHAR(255)` (nullable), `salary NUMERIC(38,2)` (nullable)) without modifying its schema.
- The response body is a JSON array of employee objects, each containing all five columns. Nullable columns that are `NULL` in the database serialize as JSON `null`.
- The endpoint is unauthenticated in v1.
- No filtering, sorting, or pagination in v1 — all rows are returned in a single response.
- Database connectivity is configured via environment variables (e.g. `DATABASE_URL`) — no hardcoded credentials, per project conventions.

## Acceptance criteria

**FR-001: Return all employees when data exists**
Given the `employee` table contains one or more rows
When a client sends `GET /api/v1/employees`
Then the response has status `200` and a JSON array body containing one object per row, each with `id`, `department`, `email`, `name`, and `salary` fields matching the database values

**FR-002: Return empty array when no employees exist**
Given the `employee` table contains zero rows
When a client sends `GET /api/v1/employees`
Then the response has status `200` and a JSON body of `[]`

**FR-003: Handle database unavailability**
Given the PostgreSQL database is unreachable or the connection fails
When a client sends `GET /api/v1/employees`
Then the response has status `500` and a JSON body of the form `{"error": "<message>"}`, with no raw database error, stack trace, or connection string exposed in the response

**FR-004: Response field types match database column types, including nulls**
Given an `employee` row with `id=1, department="Engineering", email="a@b.com", name="Jane Doe", salary=95000`
When a client sends `GET /api/v1/employees`
Then the corresponding response object has `id` as a JSON number, `salary` as a JSON number, and `department`, `email`, `name` as JSON strings

Given an `employee` row where `department`, `email`, `name`, or `salary` is `NULL` in the database (all four are nullable columns)
When a client sends `GET /api/v1/employees`
Then the corresponding response field is JSON `null` — never omitted, never coerced to an empty string, and never causes a `500` error

## Out of scope

- Filtering, sorting, or pagination of results
- Creating, updating, or deleting employees (covered by the separate "Create an Employee" feature)
- Authentication or authorization on this endpoint
- Masking, redacting, or role-based visibility of the `salary` field
- Any modification to the existing `employee` table schema
- Enforcing non-null values at the API layer (the DB already allows `NULL`; this API is read-only and must not reject or alter existing rows)

## Open questions

None — all ambiguities were resolved with the user prior to writing this spec. See `notes.md` for the resolution log and the T001 schema-verification correction (table name is `employee`, singular, and 4 of 5 columns are nullable — discovered during implementation, not at spec time).
