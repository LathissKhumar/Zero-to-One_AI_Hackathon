# CanonPulse Ingestion and Extraction Specification

## Purpose

Accept a writer's series at up to roughly 300 episodes / 500k words and make a
usable ledger available quickly while deeper extraction continues. The
extraction seam supports deterministic local tests, governed Databricks
batching, and a configured model adapter without changing downstream graph
logic.

## Submission lifecycle

`received → validated → synopsis_ready → deep_extraction_running →
complete` is the normal lifecycle. `partial`, `failed`, and `cancelled` are
terminal or resumable states with an error record. Each episode has its own
processing status, so one malformed or slow episode does not discard the
series.

The synopsis pass creates episode nodes, coarse obligations, citations, and
confidence labels using only synopsis text. The deep pass replaces or enriches
those records with full-text claims, entities, temporal placement, emotional
beats, and payoff candidates. The ledger is queryable after the synopsis pass
and marks low-confidence entries until deep extraction verifies them.

## Extraction contract

```text
ExtractionAdapter.extract(batch: EpisodeBatch) -> ExtractionResult
```

`ExtractionResult` contains nodes, entries, candidate payoffs, excerpts,
rejected rows, backend/model metadata, prompt version, source hashes, and
usage/latency measurements. Every emitted ID is scoped to the extraction run.

Adapters:

- `SynopsisExtractor` — deterministic, fast, bounded output.
- `DatabricksAiQueryExtractor` — one governed `ai_query` over Delta rows,
  structured JSON response format, row-level rejection and retry accounting.
- `LocalModelExtractor` — development adapter with the same schema and no
  production authority.
- `HeuristicExtractor` — offline evaluation floor, never presented as the
  production extractor.

## Input validation and reliability

Validate series identity, episode uniqueness, ordering, language, text limits,
encoding, and content hashes before extraction. Validate every model response
against the canonical schema. Reject malformed rows, preserve the rejection
reason, and continue the batch. Retry transient model or warehouse failures
with bounded exponential backoff; never retry schema-invalid output forever.

The system records `accepted`, `rejected`, `retried`, `timed_out`, and
`unsupported` counts. A partial result is visibly partial in every API response
and cannot be presented as a complete audit.

## Evidence rules

The extractor may propose excerpt IDs, but the graph builder rebinds them to
the source episode and source hash. A finding is publishable only when the
excerpt exists in the same source version. Citation text is stored separately
from model summaries so a summary conditioned on a defect cannot masquerade as
blind evidence.

## Two-speed operation

The fast pass must return a series job ID and usable synopsis ledger within the
product's configured latency target. Deep extraction runs per episode in a
queue, updates the extraction run progressively, and leaves prior results
available until the replacement run is complete. A new run is promoted
atomically after graph and citation validation.

## Acceptance criteria

- A 220-episode synthetic series can be loaded without a sequential model-call
  loop in Databricks mode.
- The fast pass produces a queryable partial ledger before deep extraction
  finishes.
- A malformed model response affects only its row and is visible in run
  diagnostics.
- Local and Databricks adapters produce the same validated domain schema.
- No extraction result can claim a contradiction payoff is verified.
- Cancellation, retry, resume, and duplicate-submission behavior are
  deterministic and idempotent.

## Tests

Test the adapter seam with fakes: schema validation, row isolation, retry
limits, cache replay, source-hash citation binding, job state transitions,
two-speed promotion, and no-network local mode. Databricks tests inspect SQL
parameterization and `ai_query` structure; workspace execution is covered by
an integration checklist, not a network-dependent unit test.
