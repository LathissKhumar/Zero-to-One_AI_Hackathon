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
    )
  ) AS extraction
FROM ${catalog}.${db}.episodes
WHERE series_id = :series_id
ORDER BY episode;
