import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

import db
from main import app

PROBLEM_JSON = "application/problem+json"
client = TestClient(app)


def create(name: str) -> dict:
    response = client.post("/v1/farms", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_create_returns_201_with_id_and_name(test_db):
    farm = create("Demo cooperative")

    assert set(farm) == {"id", "name"}
    assert farm["name"] == "Demo cooperative"
    assert str(uuid.UUID(farm["id"])) == farm["id"]


def test_create_ignores_extra_fields(test_db):
    response = client.post("/v1/farms", json={"name": "East farm", "color": "red"})

    assert response.status_code == 201
    assert set(response.json()) == {"id", "name"}


def test_create_trims_surrounding_spaces_from_the_name(test_db):
    farm = create("  East farm  ")

    assert farm["name"] == "East farm"


def test_create_is_saved_before_the_response_returns(test_db):
    farm = create("Demo cooperative")

    conn = sqlite3.connect(test_db)
    row = conn.execute("SELECT name FROM farms WHERE id = ?", (farm["id"],)).fetchone()
    conn.close()
    assert row == ("Demo cooperative",)


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {}])
def test_create_with_bad_name_returns_422_validation(test_db, body):
    response = client.post("/v1/farms", json=body)

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "VALIDATION"


def test_list_is_empty_when_there_are_no_farms(test_db):
    response = client.get("/v1/farms")

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_every_farm(test_db):
    first = create("Demo cooperative")
    second = create("East farm")

    response = client.get("/v1/farms")

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda farm: farm["id"]) == sorted(
        [first, second], key=lambda farm: farm["id"]
    )


def test_get_by_id_returns_the_farm(test_db):
    farm = create("Demo cooperative")

    response = client.get(f"/v1/farms/{farm['id']}")

    assert response.status_code == 200
    assert response.json() == farm


def test_get_unknown_id_returns_404_not_found(test_db):
    response = client.get(f"/v1/farms/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "NOT_FOUND"


def test_patch_changes_only_the_name(test_db):
    farm = create("Demo cooperative")

    response = client.patch(f"/v1/farms/{farm['id']}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json() == {"id": farm["id"], "name": "Renamed"}
    assert client.get(f"/v1/farms/{farm['id']}").json()["name"] == "Renamed"


def test_patch_with_empty_body_changes_nothing(test_db):
    farm = create("Demo cooperative")

    response = client.patch(f"/v1/farms/{farm['id']}", json={})

    assert response.status_code == 200
    assert response.json() == farm


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {"name": None}])
def test_patch_with_bad_name_returns_422_validation(test_db, body):
    farm = create("Demo cooperative")

    response = client.patch(f"/v1/farms/{farm['id']}", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert client.get(f"/v1/farms/{farm['id']}").json()["name"] == "Demo cooperative"


def test_patch_unknown_id_returns_404_not_found(test_db):
    response = client.patch(f"/v1/farms/{uuid.uuid4()}", json={"name": "Renamed"})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_delete_returns_204_and_removes_the_farm(test_db):
    farm = create("Demo cooperative")

    response = client.delete(f"/v1/farms/{farm['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/v1/farms/{farm['id']}").status_code == 404


def test_delete_unknown_id_returns_404_not_found(test_db):
    response = client.delete(f"/v1/farms/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_delete_returns_409_when_a_plot_is_added_after_the_check(test_db, monkeypatch):
    farm = create("Demo cooperative")
    # Pretend the check ran before the plot existed, so only the database refuses the delete.
    monkeypatch.setattr("farms.farm_has_plots", lambda conn, farm_id: False)
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
        "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) VALUES "
        "(?, ?, 'North block', 1000, 'tomato', '2026-03-01', 'loam', 1.5, 0.4, "
        "'dripnet-pc-1.0', 31.25, 34.79)",
        (str(uuid.uuid4()), farm["id"]),
    )
    conn.commit()
    conn.close()

    response = client.delete(f"/v1/farms/{farm['id']}")

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    assert client.get(f"/v1/farms/{farm['id']}").status_code == 200


def test_delete_farm_with_plots_returns_409_conflict(test_db):
    farm = create("Demo cooperative")
    # Plots are not built yet, so insert one row directly to test the rule.
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
        "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) VALUES "
        "(?, ?, 'North block', 1000, 'tomato', '2026-03-01', 'loam', 1.5, 0.4, "
        "'dripnet-pc-1.0', 31.25, 34.79)",
        (str(uuid.uuid4()), farm["id"]),
    )
    conn.commit()
    conn.close()

    response = client.delete(f"/v1/farms/{farm['id']}")

    assert response.status_code == 409
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "CONFLICT"
    assert client.get(f"/v1/farms/{farm['id']}").status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/farms"),
        ("post", "/v1/farms"),
        ("get", "/v1/farms/some-id"),
        ("patch", "/v1/farms/some-id"),
        ("delete", "/v1/farms/some-id"),
    ],
)
def test_database_unavailable_returns_503(monkeypatch, tmp_path, method, path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "missing.db")

    body = {"json": {"name": "Demo"}} if method in ("post", "patch") else {}
    response = getattr(client, method)(path, **body)

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "UNAVAILABLE"
