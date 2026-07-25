-- Audience Court batch template. Substitute DAB variables before running on a serverless SQL warehouse.
WITH candidate_context AS (
  SELECT
    '${draft_context}' AS draft_context
)
SELECT
  cohort.cohort_id,
  cohort.cohort_name,
  ai_query(
    '${var.court_model}',
    concat(
      context.draft_context,
      '\n\nListener cohort: ', cohort.preference_profile,
      '\nReturn a verdict grounded only in the provided cited story evidence.'
    ),
    responseFormat => 'STRUCT<vote:STRING,debt_status:STRING,fairness:DOUBLE,urgency:DOUBLE,reason:STRING,citation_ids:ARRAY<STRING>>',
    failOnError => false
  ) AS verdict
FROM ${var.catalog}.${var.schema}.audience_cohorts AS cohort
CROSS JOIN candidate_context AS context;
