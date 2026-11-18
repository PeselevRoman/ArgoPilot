"""The catch-all handler: an unexpected exception becomes a generic 503 UNAVAILABLE problem+json.

The planner's own 503s for a failed upstream keep UPSTREAM_UNAVAILABLE. No real network.
"""

import logging

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import make_settings
from tests.fakes import PLOT_ID, FakeUpstreams

PROBLEM_JSON = "application/problem+json"
SECRET = "secret-token-123 http://user:pw@host/x?apikey=abc"


def make_app(**steps):
    app = create_app(make_settings(), FakeUpstreams(**steps).transport)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET)

    @app.get("/http/{status}")
    def http_status(status: int) -> None:
        raise HTTPException(status_code=status, detail="Specific", headers={"Retry-After": "7"})

    return app


def test_unexpected_exception_returns_generic_503_unavailable_not_upstream(caplog):
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
    with TestClient(make_app(plot=500), raise_server_exceptions=False) as client:
        not_found = client.get("/http/404")
        explicit = client.get("/http/503")
        invalid = client.get(f"/v1/plots/{PLOT_ID}/plan?days=0")
        unknown = client.get("/no-such-route")
        upstream = client.get(f"/v1/plots/{PLOT_ID}/plan")

    assert (not_found.status_code, not_found.json()["code"]) == (404, "NOT_FOUND")
    assert explicit.status_code == 503
    assert explicit.headers["retry-after"] == "7"
    assert explicit.json()["code"] == "UPSTREAM_UNAVAILABLE"
    assert (invalid.status_code, invalid.json()["code"]) == (422, "VALIDATION")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "NOT_FOUND")
    assert upstream.status_code == 503
    assert upstream.json()["code"] == "UPSTREAM_UNAVAILABLE"
    assert "registry-service" in upstream.json()["detail"]
