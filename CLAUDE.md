# CLAUDE.md — User Management Backend Service

## Project Overview
**user_mgmt** is a User Management backend service built with FastAPI. It provides REST APIs for managing employee data stored in an existing PostgreSQL database.

**Planned Features:**
1. Get all employees (current focus)
2. Create an employee

## Stack
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM/Database Library:** SQLAlchemy (recommended) or psycopg2
- **Package Manager:** pip
- **Testing:** pytest + pytest-asyncio (for async tests)

## Project Structure
```
user_mgmt/
├── CLAUDE.md                 ← This file
├── .claude/                  ← AI workflow config
│   ├── agents/              ← Phase-owner agents
│   └── skills/              ← Review tools
├── specs/                   ← Feature specs
│   └── get-all-employees/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       └── notes.md
├── app/
│   ├── __init__.py
│   ├── main.py              ← FastAPI app entry point
│   ├── models/              ← SQLAlchemy models
│   │   └── employee.py
│   ├── routes/              ← API route handlers
│   │   └── employees.py
│   ├── services/            ← Business logic layer
│   │   └── employee_service.py
│   ├── schemas/             ← Pydantic request/response models
│   │   └── employee.py
│   └── config.py            ← Configuration & environment variables
├── tests/
│   ├── __init__.py
│   ├── conftest.py          ← Pytest fixtures
│   └── test_employees.py
├── requirements.txt         ← Python dependencies
├── .env.example             ← Example environment variables
└── README.md

```

## Configuration & Environment Variables
**Required environment variables:**
- `DATABASE_URL` — PostgreSQL connection string (format: `postgresql://user:password@host:port/database`)
- `APP_ENV` — Environment name (`development`, `production`)

**Example `.env` file:**
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/employees
APP_ENV=development
```

Load variables using `python-dotenv` or similar. **Never hardcode secrets.**

## Running the Project

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests
```bash
pytest tests/ -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Project Conventions

### 1. Architecture: Separation of Concerns
- **Routes** (`app/routes/`) — Only handle HTTP request/response, validate input, call services
- **Services** (`app/services/`) — Business logic, orchestration, database queries
- **Models** (`app/models/`) — SQLAlchemy database models (ORM definitions)
- **Schemas** (`app/schemas/`) — Pydantic models for request/response validation
- **Config** (`app/config.py`) — Environment variables and settings

**Example flow:** `Request → Route Handler → Service → Database Model → Response`

### 2. REST API Conventions
- Use standard HTTP methods: `GET`, `POST`, `PUT`, `DELETE`
- Use standard status codes: `200` (OK), `201` (Created), `400` (Bad Request), `404` (Not Found), `500` (Server Error)
- All endpoints return JSON responses
- Use plural nouns for resource paths: `/api/employees` (not `/api/employee`)
- Namespace all routes under `/api/v1/` for future versioning

**Example:**
- `GET /api/v1/employees` — Get all employees
- `POST /api/v1/employees` — Create an employee

### 3. Request/Response Validation
- Use Pydantic models (`schemas/`) for validating all incoming requests
- Validate data types, required fields, and value constraints
- Return `400 Bad Request` with error details when validation fails
- Example response for validation errors:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

### 4. Error Handling
- Return meaningful error messages
- Use appropriate HTTP status codes
- Never expose database errors directly to clients
- Log errors for debugging

**Example error response:**
```json
{
  "error": "Employee not found",
  "status": 404
}
```

### 5. Database Access
- Use SQLAlchemy ORM (not raw SQL strings)
- All database queries go in `services/`
- Use dependency injection for database sessions in routes
- Never perform business logic in route handlers

### 6. Testing
- Write tests for all business logic in `services/`
- Write integration tests for API endpoints
- Use pytest fixtures for common setup (database, test client, etc.)
- Aim for >80% code coverage
- Test both success and error cases

**Example test structure:**
```python
# tests/test_employees.py
def test_get_all_employees_returns_list(client):
    response = client.get("/api/v1/employees")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_employee_with_valid_data(client):
    payload = {"name": "John Doe", "email": "john@example.com"}
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "john@example.com"
```

### 7. Code Quality
- Use type hints for all functions and variables
- Keep functions small and focused (single responsibility)
- Use meaningful variable/function names
- Format code with Black or similar
- Use linting with Flake8 or Pylint

## Security Notes
- **Environment Variables:** All secrets (database passwords, API keys) must be in `.env`, never committed to git
- **Input Validation:** Validate all incoming request data with Pydantic schemas
- **SQL Injection:** Always use SQLAlchemy ORM; never build SQL strings with user input
- **CORS:** Configure CORS appropriately if frontend is separate
- **Database Credentials:** Use environment variables, not hardcoded strings

## Dependencies (requirements.txt)
```
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.0
psycopg2-binary==2.9.0
pydantic==2.0.0
python-dotenv==1.0.0
pytest==7.0.0
pytest-asyncio==0.21.0
httpx==0.24.0
```

## Workflow: Building Features
1. **Spec Phase** → Write what the feature must do (use `/product-manager` agent)
2. **Plan Phase** → Design how it will be built (use `/architect` agent)
3. **Tasks Phase** → Break into atomic steps (use `/planner` agent)
4. **Implementation** → Write code following tasks (use `/developer` agent)
5. **Quality Gates** → Run `/spec-check`, `/phase-gate`, `/code-review`, `/security-review`

**Do NOT implement code before spec and plan are approved.**

## Next Steps
1. Start with the "Get All Employees" feature
2. Use the Product Manager agent to write `specs/get-all-employees/spec.md`
3. Wait for approval before proceeding to plan phase
