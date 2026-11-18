"""The catch-all handler: an unexpected exception becomes a generic 503 problem+json. No real network."""

import logging

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import make_settings
from tests.fakes import FakeClock, FakeProvider
from tests.test_api import START, URL

PROBLEM_JSON = "application/problem+json"
SECRET = "secret-token-123 http://user:pw@host/x?apikey=abc"


def make_app():
    app = create_app(make_settings(), FakeProvider().transport, FakeClock(START).now)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET)

    @app.get("/http/{status}")
    def http_status(status: int) -> None:
        raise HTTPException(status_code=status, detail="Specific", headers={"Retry-After": "7"})

    return app


def test_unexpected_exception_returns_generic_503_problem_json(caplog):
    with TestClient(make_app(), raise_server_exceptions=False) as client:
        with caplog.at_level(logging.ERROR):
            response = client.get("/boom?apikey=abc")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    assert response.json() == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "The service hit an unexpected error",
        "code": "UNAVAILABLE",
    }
    assert "retry-after" not in response.headers
    for leaked in ("secret-token-123", "apikey", "RuntimeError", "pw"):
        assert leaked not in response.text
    records = [r for r in caplog.records if r.exc_info and r.exc_info[0] is RuntimeError]
    assert records
    assert "GET /boom" in records[0].getMessage()
    assert "apikey" not in records[0].getMessage()


def test_catch_all_leaves_specific_answers_unchanged():
    with TestClient(make_app(), raise_server_exceptions=False) as client:
        not_found = client.get("/http/404")
        unavailable = client.get("/http/503")
        invalid = client.get("/v1/forecast?lat=abc&lon=34.79&days=7")
        unknown = client.get("/no-such-route")

    assert (not_found.status_code, not_found.json()["code"]) == (404, "NOT_FOUND")
    assert unavailable.status_code == 503
    assert unavailable.headers["retry-after"] == "7"
    assert unavailable.json()["detail"] == "Specific"
    assert (invalid.status_code, invalid.json()["code"]) == (422, "VALIDATION")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "NOT_FOUND")
