-- Project Wedjat: TimescaleDB Schema
-- Executed once on first `docker compose up` via /docker-entrypoint-initdb.d/

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  Table 1: raw_frames — immutable archive of received packets   ║
-- ╚══════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS raw_frames (
    id          BIGSERIAL,
    timestamp   TIMESTAMPTZ     NOT NULL,
    norad_id    INTEGER         NOT NULL,
    station_id  TEXT,
    raw_frame   TEXT            NOT NULL,
    snr         DOUBLE PRECISION,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable(
    'raw_frames', 'timestamp',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_raw_norad_ts
    ON raw_frames (norad_id, timestamp DESC);

-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  Table 2: telemetry_frames — decoded features + ML results     ║
-- ╚══════════════════════════════════════════════════════════════════╝
-- Each row corresponds to a raw_frame after Kaitai decoding and
-- VAE inference.  JSONB `features` avoids schema migrations when
-- new satellite profiles with different golden-feature sets are added.

CREATE TABLE IF NOT EXISTS telemetry_frames (
    id                      BIGSERIAL,
    timestamp               TIMESTAMPTZ         NOT NULL,
    norad_id                INTEGER             NOT NULL,
    raw_frame_id            BIGINT,
    features                JSONB,
    anomaly_score           DOUBLE PRECISION,
    is_anomaly              BOOLEAN             DEFAULT FALSE,
    missing_fields          JSONB,
    frame_is_complete       BOOLEAN             DEFAULT TRUE,
    missing_raw_fields      TEXT,
    dropped_packet_suspect  BOOLEAN             DEFAULT FALSE,
    sampling_irregular      BOOLEAN             DEFAULT FALSE,
    pass_id                 INTEGER,
    pass_duration_sec       DOUBLE PRECISION,
    pass_frame_count        INTEGER,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable(
    'telemetry_frames', 'timestamp',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_telem_norad_ts
    ON telemetry_frames (norad_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_telem_anomaly
    ON telemetry_frames (norad_id, is_anomaly, timestamp DESC)
    WHERE is_anomaly = TRUE;

-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  Table 3: alembic_version — stamp schema version               ║
-- ╚══════════════════════════════════════════════════════════════════╝
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) 
VALUES ('da10ec576e56')
ON CONFLICT DO NOTHING;
