-- Table definitions for the test database.
-- Used by tests/seed_test_db.sh. The course seed script in tasks/ keeps its own copy.

CREATE TABLE farms (
  id   TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE crops (
  id   TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE soils (
  id                         TEXT PRIMARY KEY,
  name                       TEXT NOT NULL,
  available_water_mm_per_m   INTEGER NOT NULL
);

CREATE TABLE emitters (
  id       TEXT PRIMARY KEY,
  name     TEXT NOT NULL,
  flow_lph REAL NOT NULL
);

CREATE TABLE plots (
  id                 TEXT PRIMARY KEY,
  farm_id            TEXT NOT NULL REFERENCES farms(id),
  name               TEXT NOT NULL,
  area_m2            REAL NOT NULL,
  crop_id            TEXT NOT NULL REFERENCES crops(id),
  planting_date      TEXT NOT NULL,
  soil_id            TEXT NOT NULL REFERENCES soils(id),
  row_spacing_m      REAL NOT NULL,
  emitter_spacing_m  REAL NOT NULL,
  emitter_id         TEXT NOT NULL REFERENCES emitters(id),
  lat                REAL NOT NULL,
  lon                REAL NOT NULL,
  UNIQUE (farm_id, name)
);
