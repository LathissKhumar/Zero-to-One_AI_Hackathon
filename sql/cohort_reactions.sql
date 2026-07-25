-- sql/cohort_reactions.sql
-- The entire audience simulation as one statement: 5 cohorts x N episodes in a
-- single governed, parallel job. Say this out loud during the demo.
--
-- Substitute ${catalog}, ${db}, ${model} before execution; :series_id is a bind
-- parameter, not a literal, so no series identifier is ever hardcoded here. The
-- SQL warehouse this runs against is a property of the caller's connection, not
-- of this statement.
SELECT
  c.cohort_id,
  e.episode,
  ai_query(
    '${model}',
    concat(
      'You are a listener of this type: ', c.profile, '. ',
      'Rate engagement 0-1 for this episode and vote continue, hesitate, or stop. ',
      'Return JSON with keys engagement, vote, reaction, citation_ids. ',
      'Episode ', CAST(e.episode AS STRING), ': ', coalesce(e.body, e.synopsis)
    ),
    responseFormat => 'STRUCT<engagement:DOUBLE,vote:STRING,reaction:STRING,citation_ids:ARRAY<STRING>>'
  ) AS reaction
FROM ${catalog}.${db}.episodes e
CROSS JOIN ${catalog}.${db}.audience_cohorts c
WHERE e.series_id = :series_id;
