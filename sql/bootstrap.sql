-- CanonPulse bootstrap template. Replace ${catalog} and ${schema} before execution.
CREATE SCHEMA IF NOT EXISTS ${catalog}.${schema};

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.episodes (
  story_id STRING,
  episode_number INT,
  title STRING,
  summary STRING,
  content STRING,
  PRIMARY KEY (story_id, episode_number) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.story_claims (
  claim_id STRING,
  story_id STRING,
  episode_number INT,
  claim_type STRING,
  claim_text STRING,
  evidence_excerpt STRING,
  PRIMARY KEY (claim_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.narrative_debts (
  debt_id STRING,
  story_id STRING,
  debt_type STRING,
  label STRING,
  status STRING,
  opened_episode INT,
  urgency INT,
  evidence_claim_ids ARRAY<STRING>,
  PRIMARY KEY (debt_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.audience_cohorts (
  cohort_id STRING,
  cohort_name STRING,
  preference_profile STRING,
  PRIMARY KEY (cohort_id) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.court_verdicts (
  audit_id STRING,
  cohort_id STRING,
  verdict STRUCT<vote:STRING,debt_status:STRING,fairness:DOUBLE,urgency:DOUBLE,reason:STRING,citation_ids:ARRAY<STRING>>,
  created_at TIMESTAMP
);

-- Create an AI Search Delta Sync index over episode content after inserting story rows.
-- Source table: ${catalog}.${schema}.episodes
-- Primary key: story_id + episode_number materialized as a single segment_id column.
-- Sync metadata: story_id, episode_number, title.
