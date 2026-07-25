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
  b.episode,
  ai_query(
    '${model}',
    concat(
      'Evaluate a serialized-fiction boundary using only these structural signals. ',
      'Do not infer a real audience or use prose style. Cohort weights: ', to_json(c.weights),
      '. Features: open_obligation_count=', CAST(b.open_obligation_count AS STRING),
      ', mean_urgency=', CAST(b.mean_urgency AS STRING),
      ', overdue_count=', CAST(b.overdue_count AS STRING),
      ', broken_count=', CAST(b.broken_count AS STRING),
      ', sentiment_velocity=', CAST(b.sentiment_velocity AS STRING),
      ', perceived_time_jump=', CAST(b.perceived_time_jump AS STRING),
      '. Return engagement 0-1, vote continue/hesitate/stop, a concise structural reaction, and citation ids from episode ', CAST(b.episode AS STRING), '.'
    ),
    -- json_schema, not the DDL-string form. Verified against a live workspace:
    -- `responseFormat => 'STRUCT<a:...,b:...>'` fails with
    -- AI_FUNCTION_UNSUPPORTED_RESPONSE_FORMAT.DDL_STRING because that form
    -- permits exactly one top-level field, and this needs four.
    responseFormat => '{
      "type": "json_schema",
      "json_schema": {
        "name": "cohort_reaction",
        "schema": {
          "type": "object",
          "properties": {
            "engagement": {"type": "number"},
            "vote": {"type": "string"},
            "reaction": {"type": "string"},
            "citation_ids": {"type": "array", "items": {"type": "string"}}
          },
          "required": ["engagement", "vote", "reaction", "citation_ids"]
        },
        "strict": true
      }
    }'
  ) AS reaction
FROM ${catalog}.${db}.episodes e
CROSS JOIN ${catalog}.${db}.listener_cohorts c
JOIN ${catalog}.${db}.boundary_features b
  ON b.series_id = e.series_id AND b.episode = e.episode
WHERE e.series_id = :series_id;
