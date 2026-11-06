import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

import db
import plots
from main import app

PROBLEM_JSON = "application/problem+json"
PLOT_FIELDS = {
    "id", "farm_id", "name", "area_m2", "crop_id", "planting_date", "soil_id",
    "row_spacing_m", "emitter_spacing_m", "emitter_id", "lat", "lon",
}
client = TestClient(app)


def new_farm(name: str = "Demo cooperative") -> str:
    response = client.post("/v1/farms", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def plot_body(farm_id: str, **overrides) -> dict:
    body = {
        "farm_id": farm_id,
        "name": "North block",
        "area_m2": 1000,
        "crop_id": "tomato",
        "planting_date": "2026-03-01",
        "soil_id": "loam",
        "row_spacing_m": 1.5,
        "emitter_spacing_m": 0.4,
        "emitter_id": "dripnet-pc-1.0",
        "lat": 31.25,
        "lon": 34.79,
    }
    body.update(overrides)
    return body


def create_plot(farm_id: str, **overrides) -> dict:
    response = client.post("/v1/plots", json=plot_body(farm_id, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_returns_201_with_exactly_the_spec_fields(test_db):
    farm_id = new_farm()

    response = client.post("/v1/plots", json=plot_body(farm_id))

    assert response.status_code == 201
    plot = response.json()
    assert set(plot) == PLOT_FIELDS
    assert str(uuid.UUID(plot["id"])) == plot["id"]
    assert plot["planting_date"] == "2026-03-01"
    assert client.get(f"/v1/plots/{plot['id']}").json() == plot


def test_create_ignores_extra_fields(test_db):
    farm_id = new_farm()

    response = client.post("/v1/plots", json=plot_body(farm_id, color="red"))

    assert response.status_code == 201
    assert set(response.json()) == PLOT_FIELDS


def test_create_trims_the_name(test_db):
    farm_id = new_farm()

    plot = create_plot(farm_id, name="  South block  ")

    assert plot["name"] == "South block"


def test_numeric_strings_are_converted_to_numbers(test_db):
    farm_id = new_farm()

    plot = create_plot(farm_id, area_m2="1000", lat="31.25")

    assert plot["area_m2"] == 1000
    assert plot["lat"] == 31.25


def test_thousands_separators_are_converted_to_numbers(test_db):
    farm_id = new_farm()

    plot = create_plot(farm_id, area_m2="1,234,567.5")

    assert plot["area_m2"] == 1234567.5


def test_create_accepts_boundary_coordinates(test_db):
    farm_id = new_farm()

    plot = create_plot(farm_id, lat=90, lon=-180)

    assert (plot["lat"], plot["lon"]) == (90, -180)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("area_m2", 0),
        ("area_m2", -5),
        ("area_m2", "abc"),
        ("area_m2", True),
        ("area_m2", "inf"),
        ("area_m2", "1_000"),
        ("area_m2", "1,5"),
        ("row_spacing_m", 0),
        ("emitter_spacing_m", -1),
        ("lat", 91),
        ("lat", -91),
        ("lon", 181),
        ("lon", -181),
        ("planting_date", "2999-01-01"),
        ("planting_date", "03/01/2026"),
        ("crop_id", "rice"),
        ("soil_id", "mud"),
        ("emitter_id", "drip-9.9"),
    ],
)
def test_create_with_bad_field_returns_422_validation(test_db, field, value):
    farm_id = new_farm()

    response = client.post("/v1/plots", json=plot_body(farm_id, **{field: value}))

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "VALIDATION"


def test_create_for_unknown_farm_returns_422_validation(test_db):
    response = client.post("/v1/plots", json=plot_body(str(uuid.uuid4())))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert response.json()["detail"] == "Unknown farm"


def test_same_name_on_the_same_farm_returns_409_conflict(test_db):
    farm_id = new_farm()
    create_plot(farm_id, name="North block")

    response = client.post("/v1/plots", json=plot_body(farm_id, name="North block"))

    assert response.status_code == 409
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "CONFLICT"


def test_same_name_on_another_farm_is_allowed(test_db):
    create_plot(new_farm("Demo cooperative"), name="North block")

    plot = create_plot(new_farm("East farm"), name="North block")

    assert plot["name"] == "North block"


def test_duplicate_name_caught_by_the_database_returns_409(test_db, monkeypatch):
    farm_id = new_farm()
    create_plot(farm_id, name="North block")
    # The first check misses the existing plot; the re-check after the database error finds it.
    real_name_taken = plots.name_taken
    calls = []

    def first_check_misses(conn, farm, name, ignore_id=None):
        calls.append(name)
        return False if len(calls) == 1 else real_name_taken(conn, farm, name, ignore_id)

    monkeypatch.setattr(plots, "name_taken", first_check_misses)

    response = client.post("/v1/plots", json=plot_body(farm_id, name="North block"))

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_farm_deleted_during_create_returns_422_unknown_farm(test_db, monkeypatch):
    # The first reference check passes, then the farm disappears before the insert.
    real_check = plots.check_references
    calls = []

    def first_check_passes(conn, body):
        calls.append(body)
        if len(calls) > 1:
            real_check(conn, body)

    monkeypatch.setattr(plots, "check_references", first_check_passes)
    response = client.post("/v1/plots", json=plot_body(str(uuid.uuid4())))

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown farm"


def test_list_returns_every_plot(test_db):
    farm_id = new_farm()
    first = create_plot(farm_id, name="North block")
    second = create_plot(farm_id, name="South block")

    response = client.get("/v1/plots")

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda plot: plot["id"]) == sorted(
        [first, second], key=lambda plot: plot["id"]
    )


def test_list_filters_by_farm_id(test_db):
    farm_id = new_farm("Demo cooperative")
    other_farm_id = new_farm("East farm")
    mine = create_plot(farm_id, name="North block")
    create_plot(other_farm_id, name="West block")

    response = client.get("/v1/plots", params={"farm_id": farm_id})

    assert response.status_code == 200
    assert response.json() == [mine]


def test_list_for_unknown_farm_returns_empty_list(test_db):
    response = client.get("/v1/plots", params={"farm_id": str(uuid.uuid4())})

    assert response.status_code == 200
    assert response.json() == []


def test_get_unknown_id_returns_404_not_found(test_db):
    response = client.get(f"/v1/plots/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_patch_changes_only_the_sent_fields(test_db):
    plot = create_plot(new_farm())

    response = client.patch(f"/v1/plots/{plot['id']}", json={"area_m2": 1200})

    assert response.status_code == 200
    assert response.json() == {**plot, "area_m2": 1200}


def test_patch_with_empty_body_changes_nothing(test_db):
    plot = create_plot(new_farm())

    response = client.patch(f"/v1/plots/{plot['id']}", json={})

    assert response.status_code == 200
    assert response.json() == plot


def test_patch_to_a_name_used_on_the_same_farm_returns_409(test_db):
    farm_id = new_farm()
    create_plot(farm_id, name="North block")
    south = create_plot(farm_id, name="South block")

    response = client.patch(f"/v1/plots/{south['id']}", json={"name": "North block"})

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_patch_keeping_the_same_name_is_allowed(test_db):
    plot = create_plot(new_farm(), name="North block")

    response = client.patch(f"/v1/plots/{plot['id']}", json={"name": "North block", "area_m2": 900})

    assert response.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"crop_id": "rice"},
        {"farm_id": str(uuid.uuid4())},
        {"lat": 95},
        {"planting_date": "2999-01-01"},
        {"area_m2": "abc"},
    ],
)
def test_patch_with_bad_value_returns_422_validation(test_db, body):
    plot = create_plot(new_farm())

    response = client.patch(f"/v1/plots/{plot['id']}", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"
    assert client.get(f"/v1/plots/{plot['id']}").json() == plot


@pytest.mark.parametrize("field", ["name", "area_m2", "crop_id", "lat"])
def test_patch_with_null_returns_422_validation(test_db, field):
    plot = create_plot(new_farm())

    response = client.patch(f"/v1/plots/{plot['id']}", json={field: None})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION"


def test_patch_unknown_id_returns_404_not_found(test_db):
    response = client.patch(f"/v1/plots/{uuid.uuid4()}", json={"area_m2": 1200})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_delete_returns_204_and_removes_the_plot(test_db):
    plot = create_plot(new_farm())

    response = client.delete(f"/v1/plots/{plot['id']}")

    assert response.status_code == 204
    assert client.get(f"/v1/plots/{plot['id']}").status_code == 404


def test_delete_unknown_id_returns_404_not_found(test_db):
    response = client.delete(f"/v1/plots/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_farm_with_a_plot_cannot_be_deleted(test_db):
    farm_id = new_farm()
    create_plot(farm_id)

    response = client.delete(f"/v1/farms/{farm_id}")

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/plots"),
        ("post", "/v1/plots"),
        ("get", "/v1/plots/some-id"),
        ("patch", "/v1/plots/some-id"),
        ("delete", "/v1/plots/some-id"),
    ],
)
def test_database_unavailable_returns_503(monkeypatch, tmp_path, method, path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "missing.db")
    body = {"json": {"area_m2": 1200}} if method in ("post", "patch") else {}

    response = getattr(client, method)(path, **body)

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "UNAVAILABLE"
