-- CanonPulse Unity Catalog schema.
--
-- Governance is a demo asset here, not just hygiene: every warning the product
-- shows a writer traces back through these tables to the exact episode text that
-- justifies it. That lineage is the answer to "why should I believe this?"
--
-- Parameterise with your own catalog/schema before running:
--   databricks sql -f sql/ddl.sql --param catalog=main --param db=canonpulse

CREATE CATALOG IF NOT EXISTS ${catalog};
CREATE SCHEMA IF NOT EXISTS ${catalog}.${db};
USE ${catalog}.${db};

-- ---------------------------------------------------------------------------
-- Ingest: the writer's submission
-- ---------------------------------------------------------------------------

-- One row per episode. A 300-episode submission is ~300 rows / ~500k words, so
-- extraction runs as one batched ai_query over this table rather than 300
-- sequential calls. That is the whole reason series-scale analysis is tractable.
CREATE TABLE IF NOT EXISTS episodes (
    series_id       STRING  NOT NULL,
    episode         INT     NOT NULL,
    title           STRING,
    body            STRING,          -- full script text, when supplied
    synopsis        STRING,          -- beat-level summary; always present
    has_full_text   BOOLEAN NOT NULL DEFAULT false,
    word_count      INT,
    writer_id       STRING,          -- drives the multi-writer handoff sheet
    ingested_at     TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id)
COMMENT 'Raw writer submission. Two-speed ingest: synopsis first, body backfilled.';

CREATE TABLE IF NOT EXISTS canonpulse_submission (
    series_id       STRING NOT NULL,
    version_id      STRING NOT NULL,
    source_hash     STRING NOT NULL,
    title           STRING NOT NULL,
    genre           STRING NOT NULL,
    ongoing         BOOLEAN NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id)
COMMENT 'Immutable uploaded submission versions keyed by source hash.';

CREATE TABLE IF NOT EXISTS canonpulse_ingestion_job (
    job_id              STRING NOT NULL,
    series_id           STRING NOT NULL,
    version_id          STRING NOT NULL,
    source_hash         STRING NOT NULL,
    status              STRING NOT NULL,
    completed_episodes  INT NOT NULL DEFAULT 0,
    failed_episodes     ARRAY<INT>,
    created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp(),
    finished_at         TIMESTAMP
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS canonpulse_episode_work_item (
    job_id          STRING NOT NULL,
    episode         INT NOT NULL,
    stage           STRING NOT NULL,
    status          STRING NOT NULL,
    attempt_count   INT NOT NULL DEFAULT 0,
    error           STRING,
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP
)
USING DELTA
PARTITIONED BY (job_id);

-- ---------------------------------------------------------------------------
-- Governed document parsing
-- ---------------------------------------------------------------------------

-- Binary source files are retained by hash so the parsed result can always be
-- tied back to the exact upload without putting document bytes in the app.
CREATE TABLE IF NOT EXISTS canonpulse_raw_document (
    document_id     STRING NOT NULL,
    series_id       STRING NOT NULL,
    source_path     STRING NOT NULL,
    source_hash     STRING NOT NULL,
    content         BINARY NOT NULL,
    file_size       BIGINT,
    ingested_at     TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

-- Databricks Document Parsing output is versioned VARIANT. Persist it once so
-- retries and downstream normalization do not pay to parse the same upload.
CREATE TABLE IF NOT EXISTS canonpulse_parsed_document (
    document_id     STRING NOT NULL,
    series_id       STRING NOT NULL,
    source_path     STRING NOT NULL,
    source_hash     STRING NOT NULL,
    parser          STRING NOT NULL,
    parser_version  STRING NOT NULL,
    parsed_document VARIANT NOT NULL,
    parsed_at       TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS series (
    series_id       STRING  NOT NULL,
    title           STRING  NOT NULL,
    genre           STRING,
    total_episodes  INT     NOT NULL,
    ongoing         BOOLEAN NOT NULL DEFAULT true,
    source          STRING,          -- 'submission' | 'demo'
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA;

-- ---------------------------------------------------------------------------
-- Extraction output: the dual-layer graph
-- ---------------------------------------------------------------------------

-- Nodes carry both coordinates. `perceived_index` is when the audience hears it;
-- `true_time` is when it happens in story-time. Their divergence is what makes
-- twist-vs-hole discrimination possible, so a null true_time degrades the
-- verdict rather than breaking it.
CREATE TABLE IF NOT EXISTS narrative_nodes (
    series_id       STRING  NOT NULL,
    node_id         STRING  NOT NULL,
    episode         INT     NOT NULL,
    perceived_index INT     NOT NULL,
    true_time       DOUBLE,          -- normalised [0,1]; NULL when unplaceable
    summary         STRING,
    entities        ARRAY<STRING>,
    valence         DOUBLE,
    excerpt_id      STRING
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS excerpts (
    series_id       STRING  NOT NULL,
    excerpt_id      STRING  NOT NULL,
    episode         INT     NOT NULL,
    text            STRING  NOT NULL
)
USING DELTA
PARTITIONED BY (series_id)
COMMENT 'Citation anchors. No ledger claim may surface without one.';

CREATE TABLE IF NOT EXISTS canonpulse_extraction_run (
    run_id          STRING NOT NULL,
    series_id       STRING NOT NULL,
    version_id      STRING NOT NULL,
    source_hash     STRING NOT NULL,
    model_name      STRING NOT NULL,
    prompt_version  STRING NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP NOT NULL,
    latency_ms      DOUBLE NOT NULL,
    attempt         INT NOT NULL,
    status          STRING NOT NULL
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS canonpulse_extraction_row (
    run_id          STRING NOT NULL,
    series_id       STRING NOT NULL,
    version_id      STRING NOT NULL,
    episode         INT NOT NULL,
    status          STRING NOT NULL,
    failure_code    STRING,
    failure_message STRING,
    retryable       BOOLEAN,
    citation_ids    ARRAY<STRING>
)
USING DELTA
PARTITIONED BY (run_id);

CREATE TABLE IF NOT EXISTS canonpulse_retrieval_source (
    source_id       STRING NOT NULL,
    series_id       STRING NOT NULL,
    version_id      STRING NOT NULL,
    language        STRING NOT NULL,
    text            STRING NOT NULL,
    permission_key  STRING NOT NULL,
    obligation_ids  ARRAY<STRING>,
    source_hash     STRING NOT NULL,
    updated_at      TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS canonpulse_operational_events (
    event_name      STRING NOT NULL,
    request_id      STRING NOT NULL,
    run_id          STRING NOT NULL,
    series_id       STRING NOT NULL,
    version_id      STRING NOT NULL,
    source_version  STRING NOT NULL,
    model_version   STRING NOT NULL,
    latency_ms      DOUBLE NOT NULL,
    status          STRING NOT NULL,
    cost_usd        DOUBLE NOT NULL,
    metadata        MAP<STRING, STRING>,
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

-- Contradictions and promises, pre-resolution.
CREATE TABLE IF NOT EXISTS ledger_entries (
    series_id       STRING  NOT NULL,
    entry_id        STRING  NOT NULL,
    kind            STRING  NOT NULL,   -- 'contradiction' | 'promise'
    description     STRING,
    episodes        ARRAY<INT> NOT NULL,
    excerpt_ids     ARRAY<STRING>,
    urgency         INT,
    promise_kind    STRING,
    entities        ARRAY<STRING>
)
USING DELTA
PARTITIONED BY (series_id);

-- The extractor's claim that a node discharges an entry. `verified` gates
-- protection: an unverified link must never suppress a contradiction, because a
-- hallucinated payoff hides a real defect.
CREATE TABLE IF NOT EXISTS payoff_links (
    series_id       STRING  NOT NULL,
    node_id         STRING  NOT NULL,
    target_id       STRING  NOT NULL,
    episode         INT     NOT NULL,
    rationale       STRING,
    verified        BOOLEAN NOT NULL DEFAULT false
)
USING DELTA
PARTITIONED BY (series_id);

-- ---------------------------------------------------------------------------
-- Resolution and prediction
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS resolved_entries (
    series_id       STRING  NOT NULL,
    entry_id        STRING  NOT NULL,
    as_of_episode   INT     NOT NULL,
    state           STRING  NOT NULL,   -- suspended | broken | paid | outstanding
    overdue         BOOLEAN NOT NULL DEFAULT false,
    payoff_episode  INT,
    reason          STRING,
    resolved_at     TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

-- Structural features only -- no text-derived columns belong here. Adding one
-- would let a prettier rewrite move the prediction, which defeats the point.
CREATE TABLE IF NOT EXISTS boundary_features (
    series_id             STRING NOT NULL,
    episode               INT    NOT NULL,
    open_obligation_count INT,
    mean_urgency          DOUBLE,
    min_payoff_distance   DOUBLE,
    mean_payoff_distance  DOUBLE,
    planting_recency      INT,
    suspended_edge_density DOUBLE,
    broken_edge_count     INT,
    fair_clue_density     DOUBLE,
    sentiment_velocity    DOUBLE,
    perceived_time_jump   DOUBLE,
    character_thread_count INT
)
USING DELTA
PARTITIONED BY (series_id);

CREATE TABLE IF NOT EXISTS continuation_predictions (
    series_id       STRING  NOT NULL,
    episode         INT     NOT NULL,
    predicted       DOUBLE  NOT NULL,   -- P(listener starts the next episode)
    lower_ci        DOUBLE,
    upper_ci        DOUBLE,
    model_version   STRING  NOT NULL,
    variant         STRING  NOT NULL DEFAULT 'original',  -- 'original' | 'rewrite'
    predicted_at    TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA
PARTITIONED BY (series_id);

-- ---------------------------------------------------------------------------
-- Training corpus (never surfaced to users -- fits the regressor only)
-- ---------------------------------------------------------------------------

-- Three sources with incompatible label scales, so the target is z-scored within
-- each book and `platform` absorbs the residual offset. Split grouped by book_id,
-- never by chapter: chapters from one book on both sides of the split leak.
CREATE TABLE IF NOT EXISTS training_chapters (
    platform        STRING  NOT NULL,   -- 'arxiv' | 'qidian' | 'royalroad'
    book_id         STRING  NOT NULL,
    chapter         INT     NOT NULL,
    text            STRING,
    continue_rate   DOUBLE,             -- native label
    continue_z      DOUBLE,             -- z-scored within book; the target
    split           STRING              -- 'train' | 'test', assigned by book_id
)
USING DELTA
PARTITIONED BY (platform);

-- ---------------------------------------------------------------------------
-- Evaluation: the credibility artifact
-- ---------------------------------------------------------------------------

-- Human-authored before the demo series is generated, and withheld from the
-- analyzer. If a model both plants the defects and grades the detection, the
-- resulting precision/recall measures nothing.
CREATE TABLE IF NOT EXISTS defect_manifest (
    series_id       STRING  NOT NULL,
    defect_id       STRING  NOT NULL,
    defect_class    STRING  NOT NULL,   -- accidental_hole | intentional_twist
                                        -- | outstanding_obligation | clean_control
    planted_episode INT,
    payoff_episode  INT,                -- NULL for holes and open obligations
    expected_state  STRING  NOT NULL,
    notes           STRING,
    authored_by     STRING  NOT NULL
)
USING DELTA
PARTITIONED BY (series_id)
COMMENT 'Ground truth. Hand-written by the team, never model-generated.';

CREATE TABLE IF NOT EXISTS eval_runs (
    run_id              STRING  NOT NULL,
    series_id           STRING  NOT NULL,
    mlflow_run_id       STRING,
    precision_score     DOUBLE,
    recall_score        DOUBLE,
    false_positive_rate DOUBLE,   -- measured on clean controls
    twists_protected    INT,
    holes_caught        INT,
    baseline_flags      INT,      -- what a checker without the payoff test reports
    ran_at              TIMESTAMP NOT NULL DEFAULT current_timestamp()
)
USING DELTA;

-- The five listener cohorts, mirroring app/cohorts.py::COHORTS.
--
-- `weights` is what actually separates them. Cohorts that differ only by an
-- adjective in a prompt are decoration -- five personas that all sound like the
-- same model. Carrying the weight vector here keeps the batch query honest
-- about why two cohorts disagree on the same episode.
CREATE TABLE IF NOT EXISTS listener_cohorts (
    cohort_id       STRING  NOT NULL,
    name            STRING  NOT NULL,
    weights         MAP<STRING, DOUBLE> NOT NULL,
    profile         STRING              -- prose rendering of `weights`, for the prompt
)
USING DELTA;

-- Cohort reactions. Populated by a single ai_query over the (cohort x episode)
-- cross join -- 5 x 220 rows in one statement, not 1,100 API calls.
-- `variant_blinded` records that the cohort could not see whether it was reading
-- the original or the rewrite; unblinded rows must not be reported as evidence.
CREATE TABLE IF NOT EXISTS cohort_reactions (
    series_id       STRING  NOT NULL,
    cohort_id       STRING  NOT NULL,
    episode         INT     NOT NULL,
    engagement      DOUBLE,
    vote            STRING,             -- continue | hesitate | stop
    reaction        STRING,
    citation_ids    ARRAY<STRING>,
    variant         STRING  NOT NULL DEFAULT 'original',
    variant_blinded BOOLEAN NOT NULL DEFAULT true
)
USING DELTA
PARTITIONED BY (series_id);
