-- sql/extract_graph.sql
-- One statement extracts the graph for an entire series. At 300 episodes this
-- replaces 300 sequential API calls with a single governed, parallel job.
--
-- Substitute ${catalog}, ${db}, ${model} before execution; :series_id is a bind
-- parameter, not a literal, so no series identifier is ever hardcoded here. The
-- SQL warehouse this runs against is a property of the caller's connection, not
-- of this statement.
SELECT
  episode,
  ai_query(
    '${model}',
    concat(
      'Extract narrative structure as JSON. Return keys: nodes, entries, payoffs, excerpts. ',
      'A node has id, episode, perceived_index, true_time (0-1 chronological position or null), ',
      'summary, entities, valence (-1..1), excerpt_id. ',
      'An entry has id, kind (contradiction|promise), description, episodes, excerpt_ids, urgency (1-5), entities. ',
      'A payoff has node_id, target_id, episode, rationale. ',
      'Episode ', CAST(episode AS STRING), ': ', coalesce(body, synopsis)
    ),
    -- responseFormat is required, not optional polish. Without it the model
    -- wraps its answer in ```json fences, `parse_extraction_row` rejects every
    -- row, and the extraction silently yields an empty graph with
    -- rejected == row count. Verified against a live workspace.
    --
    -- Must be the json_schema form: the DDL-string form
    -- (`'STRUCT<a:...,b:...>'`) permits exactly one top-level field and fails
    -- with AI_FUNCTION_UNSUPPORTED_RESPONSE_FORMAT.DDL_STRING for four.
    responseFormat => '{
      "type": "json_schema",
      "json_schema": {
        "name": "narrative_graph",
        "schema": {
          "type": "object",
          "properties": {
            "nodes": {"type": "array", "items": {"type": "object", "properties": {
              "id": {"type": "string"}, "episode": {"type": "integer"},
              "perceived_index": {"type": "integer"},
              "true_time": {"type": ["number", "null"]},
              "summary": {"type": "string"},
              "entities": {"type": "array", "items": {"type": "string"}},
              "valence": {"type": "number"}, "excerpt_id": {"type": ["string", "null"]}}}},
            "entries": {"type": "array", "items": {"type": "object", "properties": {
              "id": {"type": "string"}, "kind": {"type": "string"},
              "description": {"type": "string"},
              "episodes": {"type": "array", "items": {"type": "integer"}},
              "excerpt_ids": {"type": "array", "items": {"type": "string"}},
              "urgency": {"type": "integer"},
              "entities": {"type": "array", "items": {"type": "string"}}}}},
            "payoffs": {"type": "array", "items": {"type": "object", "properties": {
              "node_id": {"type": "string"}, "target_id": {"type": "string"},
              "episode": {"type": "integer"}, "rationale": {"type": "string"}}}},
            "excerpts": {"type": "array", "items": {"type": "object", "properties": {
              "id": {"type": "string"}, "episode": {"type": "integer"},
              "text": {"type": "string"}}}}
          },
          "required": ["nodes", "entries", "payoffs", "excerpts"]
        },
        "strict": true
      }
    }'
  ) AS extraction
FROM ${catalog}.${db}.episodes
WHERE series_id = :series_id
ORDER BY episode;
