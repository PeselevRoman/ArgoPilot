import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

import db
from errors import add_error_handlers
from main import app as registry_app

PROBLEM_JSON = "application/problem+json"


class Item(BaseModel):
    name: str


def make_test_app() -> FastAPI:
    # A small app with routes that trigger each error. main.py stays untouched.
    app = FastAPI()
    add_error_handlers(app)

    @app.post("/items")
    def create_item(item: Item) -> Item:
        return item

    @app.get("/database")
    def read_database(conn=Depends(db.get_connection)) -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/raise/{status}")
    def raise_status(status: int) -> None:
        raise HTTPException(status_code=status, detail="Test error")

    return app


client = TestClient(make_test_app())


def test_unknown_route_returns_problem_json_with_not_found_code():
    response = TestClient(registry_app).get("/no-such-route")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "NOT_FOUND"


def test_wrong_method_returns_405_with_allow_header_and_full_problem_body():
    response = TestClient(registry_app).post("/health")

    assert response.status_code == 405
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["allow"] == "GET"
    assert response.json() == {
        "type": "about:blank",
        "title": "Method Not Allowed",
        "status": 405,
        "detail": "Method Not Allowed",
        "code": "VALIDATION",
    }


def test_bad_body_returns_422_with_validation_code_and_field_in_detail():
    response = client.post("/items", json={})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    body = response.json()
    assert body["code"] == "VALIDATION"
    assert "name" in body["detail"]


def test_database_unavailable_returns_503_with_retry_after_and_unavailable_code(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")

    response = client.get("/database")

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["retry-after"] == "5"
    assert response.json()["code"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    ("status", "code"),
    [(400, "VALIDATION"), (404, "NOT_FOUND"), (409, "CONFLICT")],
)
def test_status_maps_to_its_spec_code(status, code):
    response = client.get(f"/raise/{status}")

    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == code
