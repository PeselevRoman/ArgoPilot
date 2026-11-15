import pytest
from fastapi.testclient import TestClient

from main import app

PROBLEM_JSON = "application/problem+json"
client = TestClient(app)

CROPS = [
    {"id": "bell-pepper", "name": "Bell pepper"},
    {"id": "tomato", "name": "Tomato"},
]
SOILS = [
    {"id": "clay-loam", "name": "Clay loam", "available_water_mm_per_m": 200},
    {"id": "loam", "name": "Loam", "available_water_mm_per_m": 175},
    {"id": "sand", "name": "Sand", "available_water_mm_per_m": 83},
]
EMITTERS = [
    {"id": "dripnet-pc-0.6", "name": "DripNet PC", "flow_lph": 0.6},
    {"id": "dripnet-pc-1.0", "name": "DripNet PC", "flow_lph": 1.0},
    {"id": "dripnet-pc-1.6", "name": "DripNet PC", "flow_lph": 1.6},
    {"id": "dripnet-pc-2.0", "name": "DripNet PC", "flow_lph": 2.0},
]

# (collection name, expected rows, one id that exists)
CATALOGUES = [
    ("crops", CROPS, "tomato"),
    ("soils", SOILS, "loam"),
    ("emitters", EMITTERS, "dripnet-pc-1.0"),
]
COLLECTION_PATHS = ["/v1/crops", "/v1/soils", "/v1/emitters"]
ITEM_PATHS = ["/v1/crops/tomato", "/v1/soils/loam", "/v1/emitters/dripnet-pc-1.0"]


@pytest.mark.parametrize(("name", "rows", "item_id"), CATALOGUES)
def test_list_returns_every_row_with_only_spec_fields(test_db, name, rows, item_id):
    response = client.get(f"/v1/{name}")

    assert response.status_code == 200
    assert response.json() == rows


@pytest.mark.parametrize(("name", "rows", "item_id"), CATALOGUES)
def test_get_by_id_returns_one_row(test_db, name, rows, item_id):
    response = client.get(f"/v1/{name}/{item_id}")

    assert response.status_code == 200
    assert response.json() == next(row for row in rows if row["id"] == item_id)


@pytest.mark.parametrize("name", ["crops", "soils", "emitters"])
def test_unknown_id_returns_404_not_found(test_db, name):
    response = client.get(f"/v1/{name}/no-such-id")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize("path", COLLECTION_PATHS + ITEM_PATHS)
def test_write_methods_return_405_with_allow_header(path):
    response = client.post(path, json={})

    assert response.status_code == 405
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["allow"] == "GET"
    assert response.json()["code"] == "VALIDATION"


@pytest.mark.parametrize("path", COLLECTION_PATHS + ITEM_PATHS)
def test_database_unavailable_returns_503(tmp_path, path, set_database_url):
    set_database_url(f"sqlite:///{tmp_path / 'missing.db'}")

    response = client.get(path)

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.headers["retry-after"] == "5"
    assert response.json()["code"] == "UNAVAILABLE"


def test_lists_are_sorted_by_id(test_db):
    assert [row["id"] for row in client.get("/v1/crops").json()] == [
        "bell-pepper",
        "tomato",
    ]
    assert [row["id"] for row in client.get("/v1/soils").json()] == [
        "clay-loam",
        "loam",
        "sand",
    ]
    assert [row["id"] for row in client.get("/v1/emitters").json()] == [
        "dripnet-pc-0.6",
        "dripnet-pc-1.0",
        "dripnet-pc-1.6",
        "dripnet-pc-2.0",
    ]
