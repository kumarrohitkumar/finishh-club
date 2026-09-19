-- 001_initial.sql
-- R1 schema. See docs/DATABASE.md for the diagram and the reasoning.
--
-- Two design choices worth knowing:
--   1. "assets", not "funds" - a stock is the same shape, so R3 adds rows, not tables
--   2. NUMERIC for every price - float loses money (0.1 + 0.2 = 0.30000000000000004)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------- assets
CREATE TABLE assets (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_type    TEXT        NOT NULL DEFAULT 'fund'
                  CHECK (asset_type IN ('fund', 'stock', 'index')),
    source_code   TEXT        NOT NULL,
    name          TEXT        NOT NULL,
    fund_house    TEXT        NOT NULL DEFAULT '',
    category      TEXT        NOT NULL
                  CHECK (category IN ('equity', 'debt', 'hybrid', 'stock')),
    sub_category  TEXT        NOT NULL DEFAULT '',
    plan          TEXT        NOT NULL DEFAULT '',
    option        TEXT        NOT NULL DEFAULT '',
    isin          TEXT,
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (asset_type, source_code)
);
CREATE INDEX assets_browse_idx ON assets (asset_type, category) WHERE is_active;
CREATE INDEX assets_name_idx   ON assets USING gin (to_tsvector('simple', name));

-- ------------------------------------------------------------ price_history
-- The big one: about 6 million rows for R1.
CREATE TABLE price_history (
    asset_id    BIGINT      NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    price_date  DATE        NOT NULL,
    price       NUMERIC(18, 6) NOT NULL CHECK (price > 0),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, price_date)
);

-- ------------------------------------------------------------ meter_results
-- Rule M-4: computed nightly, never on request.
CREATE TABLE meter_results (
    asset_id             BIGINT  NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    period_years         INT     NOT NULL CHECK (period_years IN (1, 3, 5)),
    shown_period_years   INT     NOT NULL,
    pct_strong           NUMERIC(5, 1) NOT NULL DEFAULT 0,
    pct_moderate         NUMERIC(5, 1) NOT NULL DEFAULT 0,
    pct_flat             NUMERIC(5, 1) NOT NULL DEFAULT 0,
    pct_loss             NUMERIC(5, 1) NOT NULL DEFAULT 0,
    window_count         INT     NOT NULL DEFAULT 0,
    scale_used           TEXT    NOT NULL,
    data_start           DATE,
    data_end             DATE,
    insufficient_history BOOLEAN NOT NULL DEFAULT FALSE,
    note                 TEXT    NOT NULL DEFAULT '',
    computed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, period_years),
    -- rule M-3: the four buckets must total 100, unless there is no meter to show
    CHECK (insufficient_history
           OR abs(pct_strong + pct_moderate + pct_flat + pct_loss - 100) < 0.05)
);

-- ---------------------------------------------------------------- users
CREATE TABLE users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         CITEXT      NOT NULL UNIQUE,
    password_hash TEXT,
    state         TEXT        NOT NULL DEFAULT 'unverified'
                  CHECK (state IN ('unverified', 'active', 'deleted')),
    google_sub    TEXT UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);

-- ---------------------------------------------------------------- sessions
-- Postgres for personal use. Redis when there are real users (DEPLOYMENT section 5).
CREATE TABLE sessions (
    id           TEXT        PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    user_agent   TEXT NOT NULL DEFAULT '',
    ip           INET
);
CREATE INDEX sessions_user_idx    ON sessions (user_id);
CREATE INDEX sessions_expires_idx ON sessions (expires_at);

-- ---------------------------------------------------------------- otp_codes
-- Rule A-3: hashed, never stored as plain digits.
CREATE TABLE otp_codes (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash  TEXT        NOT NULL,
    purpose    TEXT        NOT NULL CHECK (purpose IN ('signup', 'reset', 'link')),
    attempts   INT         NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX otp_user_purpose_idx ON otp_codes (user_id, purpose);

-- ------------------------------------------------------------- saved_assets
CREATE TABLE saved_assets (
    user_id  BIGINT      NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    asset_id BIGINT      NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, asset_id)
);

-- ---------------------------------------------------------------- documents
-- What Isaa searches. Text and its embedding in the same row - the reason
-- pgvector means we do not need a second database.
CREATE TABLE documents (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection TEXT NOT NULL CHECK (collection IN ('concepts', 'drhp', 'methodology')),
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    embedding  VECTOR(1536),
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX documents_collection_idx ON documents (collection);
CREATE INDEX documents_embedding_idx  ON documents
       USING hnsw (embedding vector_cosine_ops);

-- ----------------------------------------------------------- ingestion_runs
-- Rule D-4: the safety check needs yesterday's count to compare against.
CREATE TABLE ingestion_runs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source      TEXT        NOT NULL,
    run_date    DATE        NOT NULL,
    rows_seen   INT         NOT NULL DEFAULT 0,
    rows_written INT        NOT NULL DEFAULT 0,
    status      TEXT        NOT NULL CHECK (status IN ('ok', 'failed', 'rejected')),
    error       TEXT        NOT NULL DEFAULT '',
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX ingestion_runs_recent_idx ON ingestion_runs (source, run_date DESC);
