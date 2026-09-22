from sqlalchemy.exc import OperationalError

from app.models.employee import get_db


def test_get_all_employees_returns_seeded_rows(client, seed_employees):
    seed_employees(
        [
            {
                "id": 1,
                "department": "Engineering",
                "email": "jane@example.com",
                "name": "Jane Doe",
                "salary": 95000,
            },
            {
                "id": 2,
                "department": "Sales",
                "email": "john@example.com",
                "name": "John Smith",
                "salary": 60000,
            },
        ]
    )

    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0] == {
        "id": 1,
        "department": "Engineering",
        "email": "jane@example.com",
        "name": "Jane Doe",
        "salary": 95000.0,
    }


def test_get_all_employees_returns_empty_array_when_no_rows(client):
    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_employees_handles_database_failure(client):
    from app.main import app

    def broken_get_db():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield  # pragma: no cover - never reached, keeps this a generator

    app.dependency_overrides[get_db] = broken_get_db
    try:
        response = client.get("/api/v1/employees")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 500
    assert response.json() == {"error": "Unable to retrieve employees"}
    body_text = response.text.lower()
    assert "connection refused" not in body_text
    assert "traceback" not in body_text


def test_get_all_employees_serializes_null_fields_as_json_null(client, seed_employees):
    seed_employees(
        [
            {
                "id": 3,
                "department": None,
                "email": "unassigned@example.com",
                "name": None,
                "salary": None,
            }
        ]
    )

    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["department"] is None
    assert body[0]["name"] is None
    assert body[0]["salary"] is None


def test_get_all_employees_field_types_match_spec(client, seed_employees):
    seed_employees(
        [
            {
                "id": 4,
                "department": "Engineering",
                "email": "a@b.com",
                "name": "Jane Doe",
                "salary": 95000,
            }
        ]
    )

    response = client.get("/api/v1/employees")
    row = response.json()[0]

    assert isinstance(row["id"], int)
    assert isinstance(row["salary"], float)
    assert isinstance(row["department"], str)
    assert isinstance(row["email"], str)
    assert isinstance(row["name"], str)
