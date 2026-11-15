import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

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

    rows = test_db.fetch_all(
        "SELECT name FROM farms WHERE id = :id", id=uuid.UUID(farm["id"])
    )
    assert rows == [("Demo cooperative",)]


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
    test_db.execute(
        "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
        "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) VALUES "
        "(:id, :farm_id, 'North block', 1000, 'tomato', :planting_date, 'loam', 1.5, 0.4, "
        "'dripnet-pc-1.0', 31.25, 34.79)",
        id=uuid.uuid4(),
        farm_id=uuid.UUID(farm["id"]),
        planting_date=date(2026, 3, 1),
    )

    response = client.delete(f"/v1/farms/{farm['id']}")

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    assert client.get(f"/v1/farms/{farm['id']}").status_code == 200


def test_delete_farm_with_plots_returns_409_conflict(test_db):
    farm = create("Demo cooperative")
    # Plots are not built yet, so insert one row directly to test the rule.
    test_db.execute(
        "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
        "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) VALUES "
        "(:id, :farm_id, 'North block', 1000, 'tomato', :planting_date, 'loam', 1.5, 0.4, "
        "'dripnet-pc-1.0', 31.25, 34.79)",
        id=uuid.uuid4(),
        farm_id=uuid.UUID(farm["id"]),
        planting_date=date(2026, 3, 1),
    )

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
def test_database_unavailable_returns_503(tmp_path, method, path, set_database_url):
    set_database_url(f"sqlite:///{tmp_path / 'missing.db'}")

    body = {"json": {"name": "Demo"}} if method in ("post", "patch") else {}
    response = getattr(client, method)(path, **body)

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "UNAVAILABLE"


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_get_with_a_malformed_id_returns_404_not_found(test_db, method):
    body = {"json": {"name": "Demo"}} if method == "patch" else {}

    response = getattr(client, method)("/v1/farms/not-a-uuid", **body)

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "NOT_FOUND"


def test_get_accepts_an_uppercase_uuid(test_db):
    farm = create("Demo cooperative")

    response = client.get(f"/v1/farms/{farm['id'].upper()}")

    assert response.status_code == 200
    assert response.json()["id"] == farm["id"]


def test_get_accepts_a_uuid_without_hyphens(test_db):
    farm = create("Demo cooperative")

    response = client.get(f"/v1/farms/{farm['id'].replace('-', '')}")

    assert response.status_code == 200
    assert response.json()["id"] == farm["id"]


def test_existing_hyphenated_row_is_readable_and_deletable(test_db):
    farm_id = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"
    test_db.execute(
        "INSERT INTO farms (id, name) VALUES (:id, 'Seed farm')", id=uuid.UUID(farm_id)
    )

    got = client.get(f"/v1/farms/{farm_id}")
    deleted = client.delete(f"/v1/farms/{farm_id}")

    assert got.status_code == 200
    assert got.json() == {"id": farm_id, "name": "Seed farm"}
    assert deleted.status_code == 204
