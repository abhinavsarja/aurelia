-- AURELIA — schema
-- Runs automatically on first container start.

CREATE EXTENSION IF NOT EXISTS vector;

-- ------------------------------------------------------------------ control
-- One row per load attempt. This table is the state machine, the history,
-- and the switch that makes data visible.
CREATE TABLE data_load (
    load_id        BIGSERIAL PRIMARY KEY,
    week           TEXT,                      -- null for a backfill spanning weeks
    kind           TEXT NOT NULL DEFAULT 'weekly',   -- weekly | backfill
    status         TEXT NOT NULL,             -- detected|loading|validated|published|failed
    attempt_no     INT  NOT NULL DEFAULT 1,
    files_found    JSONB,
    row_counts     JSONB,
    checks_passed  JSONB,
    failure_reason TEXT,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at   TIMESTAMPTZ
);
CREATE INDEX ON data_load (status, week);

-- ------------------------------------------------------------------ master
CREATE TABLE products (
    sku          TEXT PRIMARY KEY,
    model        TEXT NOT NULL,
    department   TEXT NOT NULL,
    colour       TEXT,
    size         TEXT,
    price        NUMERIC(10,2) NOT NULL,
    cost         NUMERIC(10,2) NOT NULL,
    launch_date  DATE,
    status       TEXT NOT NULL DEFAULT 'active',   -- active|clearance|discontinued
    load_id      BIGINT REFERENCES data_load(load_id)
);
CREATE INDEX ON products (department, model);
CREATE INDEX ON products (status);

-- ------------------------------------------------------------------ commercial
CREATE TABLE sales (
    week         TEXT NOT NULL,
    sku          TEXT NOT NULL REFERENCES products(sku),
    channel      TEXT NOT NULL,               -- store | ecom
    units        INT NOT NULL CHECK (units >= 0),
    revenue      NUMERIC(12,2) NOT NULL CHECK (revenue >= 0),
    discount_pct NUMERIC(5,3) NOT NULL DEFAULT 0,
    load_id      BIGINT NOT NULL REFERENCES data_load(load_id),
    PRIMARY KEY (week, sku, channel, load_id)
);
CREATE INDEX ON sales (sku, week);
CREATE INDEX ON sales (week);

-- ------------------------------------------------------------------ operational
CREATE TABLE stock (
    week          TEXT NOT NULL,
    sku           TEXT NOT NULL REFERENCES products(sku),
    units_on_hand INT NOT NULL CHECK (units_on_hand >= 0),
    load_id       BIGINT NOT NULL REFERENCES data_load(load_id),
    PRIMARY KEY (week, sku, load_id)
);
CREATE INDEX ON stock (sku, week);

CREATE TABLE returns (
    week           TEXT NOT NULL,
    sku            TEXT NOT NULL REFERENCES products(sku),
    units_returned INT NOT NULL CHECK (units_returned >= 0),
    reason         TEXT,
    load_id        BIGINT NOT NULL REFERENCES data_load(load_id),
    PRIMARY KEY (week, sku, load_id)
);
CREATE INDEX ON returns (sku, week);

CREATE TABLE receipts (
    week           TEXT NOT NULL,
    sku            TEXT NOT NULL REFERENCES products(sku),
    units_received INT NOT NULL CHECK (units_received >= 0),
    expected_date  DATE,
    actual_date    DATE,
    load_id        BIGINT NOT NULL REFERENCES data_load(load_id),
    PRIMARY KEY (week, sku, load_id)
);
CREATE INDEX ON receipts (sku, week);

-- ------------------------------------------------------------------ planning
CREATE TABLE targets (
    month           TEXT NOT NULL,            -- YYYY-MM
    sku             TEXT NOT NULL REFERENCES products(sku),
    target_units    INT NOT NULL,
    target_revenue  NUMERIC(12,2) NOT NULL,
    source_document TEXT,
    load_id         BIGINT NOT NULL REFERENCES data_load(load_id),
    PRIMARY KEY (month, sku, load_id)
);
CREATE INDEX ON targets (sku, month);

-- ------------------------------------------------------------------ documents
CREATE TABLE documents (
    doc_id       TEXT PRIMARY KEY,            -- deterministic: hash of path + content
    source_type  TEXT NOT NULL,               -- internal | external
    doc_type     TEXT NOT NULL,               -- campaign_plan | meeting_notes | ops_report | news
    title        TEXT,
    doc_date     DATE,                        -- when it was written
    period_start TEXT,                        -- weeks it talks about
    period_end   TEXT,
    entities     JSONB,                       -- skus, models, departments, brands
    source_path  TEXT,
    content_hash TEXT NOT NULL,
    file_mtime   TIMESTAMPTZ,
    file_size    BIGINT,
    indexed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON documents (doc_type, doc_date);
CREATE INDEX ON documents (source_type);

CREATE TABLE doc_chunks (
    chunk_id     TEXT PRIMARY KEY,            -- deterministic: doc_id + position + content
    doc_id       TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    position     INT NOT NULL,
    page         INT,
    content      TEXT NOT NULL,
    entities     JSONB,                       -- entities named in THIS chunk
    -- copied down from the parent document so a chunk can still be filtered
    doc_type     TEXT NOT NULL,
    doc_date     DATE,
    period_start TEXT,
    period_end   TEXT,
    embedding    vector(3072)                 -- openai text-embedding-3-large, full dimension
);
-- No vector index, deliberately.
--   pgvector's hnsw and ivfflat cap at 2000 dimensions, so vector(3072) can be
--   stored but not indexed. At this corpus size that is the better trade anyway:
--   a sequential scan over ~5,000 chunks is 20-60ms and gives EXACT results,
--   where hnsw would give approximate ones. Retrieval is also filtered by period,
--   product and doc_type first, so the scan usually covers tens of rows, not thousands.
--   Revisit past roughly 50,000 chunks: switch to halfvec(3072), which indexes up
--   to 4000 dimensions, or re-embed at dimensions=1024.
CREATE INDEX ON doc_chunks (doc_id);
CREATE INDEX ON doc_chunks (doc_type, doc_date);

-- ------------------------------------------------------------------ audit
CREATE TABLE answer_log (
    answer_id   BIGSERIAL PRIMARY KEY,
    asked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    question    TEXT NOT NULL,
    resolved    JSONB,      -- sku, period, metric the question resolved to
    findings    JSONB,      -- the evidence contract handed to the model
    answer      TEXT,
    citations   JSONB,
    gate_opened BOOLEAN,
    validated   BOOLEAN,
    latency_ms  INT
);
CREATE INDEX ON answer_log (asked_at DESC);

-- ------------------------------------------------------------------ read path
-- Everything downstream reads these, never the base tables.
CREATE VIEW published_load AS
    SELECT load_id FROM data_load WHERE status = 'published';

CREATE VIEW v_sales    AS SELECT s.* FROM sales    s JOIN published_load p USING (load_id);
CREATE VIEW v_stock    AS SELECT s.* FROM stock    s JOIN published_load p USING (load_id);
CREATE VIEW v_returns  AS SELECT r.* FROM returns  r JOIN published_load p USING (load_id);
CREATE VIEW v_receipts AS SELECT r.* FROM receipts r JOIN published_load p USING (load_id);
CREATE VIEW v_targets  AS SELECT t.* FROM targets  t JOIN published_load p USING (load_id);
