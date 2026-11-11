-- Table definitions for PostgreSQL. Same tables and columns as schema.sql (SQLite).
-- Run once on the production database before release. The service never runs it.
-- COLLATE "C" on catalogue ids (and the columns that reference them) gives plain
-- byte-order comparison, matching SQLite's default, so sorting is the same on both engines.

CREATE TABLE farms (
  id   uuid PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE crops (
  id   text COLLATE "C" PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE soils (
  id                         text COLLATE "C" PRIMARY KEY,
  name                       text NOT NULL,
  available_water_mm_per_m   integer NOT NULL
);

CREATE TABLE emitters (
  id       text COLLATE "C" PRIMARY KEY,
  name     text NOT NULL,
  flow_lph double precision NOT NULL
);

CREATE TABLE plots (
  id                 uuid PRIMARY KEY,
  farm_id            uuid NOT NULL REFERENCES farms(id),
  name               text NOT NULL,
  area_m2            double precision NOT NULL,
  crop_id            text COLLATE "C" NOT NULL REFERENCES crops(id),
  planting_date      date NOT NULL,
  soil_id            text COLLATE "C" NOT NULL REFERENCES soils(id),
  row_spacing_m      double precision NOT NULL,
  emitter_spacing_m  double precision NOT NULL,
  emitter_id         text COLLATE "C" NOT NULL REFERENCES emitters(id),
  lat                double precision NOT NULL,
  lon                double precision NOT NULL,
  UNIQUE (farm_id, name)
);
