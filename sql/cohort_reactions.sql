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
      'Episode ', CAST(e.episode AS STRING), ': ', coalesce(e.body, e.synopsis)
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
WHERE e.series_id = :series_id;
