DROP SCHEMA IF EXISTS spike CASCADE;
CREATE SCHEMA spike;

CREATE TABLE spike.stations (
    station_id VARCHAR(8) PRIMARY KEY,
    station_name TEXT NOT NULL
);

CREATE TABLE spike.parameters (
    param_id SMALLINT PRIMARY KEY,
    param_code TEXT NOT NULL UNIQUE
);

CREATE TABLE spike.daily_wide_core (
    station_id VARCHAR(8) NOT NULL,
    obs_date DATE NOT NULL,
    rr DOUBLE PRECISION,
    qrr SMALLINT,
    tn DOUBLE PRECISION,
    qtn SMALLINT,
    tx DOUBLE PRECISION,
    qtx SMALLINT,
    tm DOUBLE PRECISION,
    qtm SMALLINT,
    tntxm DOUBLE PRECISION,
    qtntxm SMALLINT
    PRIMARY KEY (station_id, obs_date)
);

CREATE TABLE spike.daily_long_core (
    station_id VARCHAR(8) NOT NULL,
    obs_date DATE NOT NULL,
    param_id SMALLINT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality_code SMALLINT,
    PRIMARY KEY (station_id, obs_date, param_id)
);

CREATE TABLE spike.daily_wide_rr_t_vent_all (
    station_id VARCHAR(8) NOT NULL,
    obs_date DATE NOT NULL,
    rr DOUBLE PRECISION,
    qrr SMALLINT,
    tn DOUBLE PRECISION,
    qtn SMALLINT,
    tx DOUBLE PRECISION,
    qtx SMALLINT,
    tm DOUBLE PRECISION,
    qtm SMALLINT,
    tntxm DOUBLE PRECISION,
    qtntxm SMALLINT
    PRIMARY KEY (station_id, obs_date)
)

CREATE TABLE spike.daily_long_all (
    station_id VARCHAR(8) NOT NULL,
    obs_date DATE NOT NULL,
    param_id SMALLINT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality_code SMALLINT,
    status_code SMALLINT
    PRIMARY KEY (station_id, obs_date, param_id)
);
