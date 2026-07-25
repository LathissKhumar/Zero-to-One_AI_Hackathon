"""Episode text -> dual-layer graph, via a real model call instead of rules.

`HeuristicExtractor` is a deliberate floor: it has never seen a language
model. `LLMExtractor` is the extractor the product actually claims to
use -- Databricks Foundation Model APIs and OpenAI both speak
OpenAI-compatible chat completions, so one client, differing only by base
URL / token / model name, serves both:

* Databricks Foundation Model API endpoint -> the governed, on-platform path.
* OpenAI's own endpoint -> exists only so the number can be measured before a
  Databricks workspace is authenticated. It must never be presented as the
  governed path, so every result and every printed line carries a
  ``backend`` label ("databricks" or "openai") derived from the endpoint URL,
  never asserted by the caller.

The prompt below requests exactly the JSON shape `sql/extract_graph.sql`
asks the Databricks path for (same keys, same field lists), so the two paths
stay one schema instead of drifting apart. It is written against the episode
text and that schema only -- it has never seen, and must never be tuned
against, `data/manifest/last_monsoon.yaml`. A prompt iterated until it
recovers known defects would reproduce the exact circularity this evaluation
plan exists to remove; if the model does poorly, that is the finding, not a
bug to prompt-engineer away.

Cost discipline: responses are cached to disk keyed by a hash of
(model, prompt), so re-running against a warm cache is free and makes no
network call -- this is also what lets the test suite run with no network and
no credentials. The cache file holds only model output text; it never
contains a token, endpoint, or any other credential.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.extraction import ExtractionResult, parse_extraction_row
from app.narrative_models import Excerpt, LedgerEntry, NarrativeNode, PayoffLink

# Same keys and field lists as sql/extract_graph.sql's ai_query prompt, so the
# local (OpenAI/Databricks-direct) and on-platform (batched ai_query) paths
# request one schema rather than two that can silently drift apart.
_PROMPT_TEMPLATE = (
    "Extract narrative structure as JSON. Return keys: nodes, entries, payoffs, excerpts. "
    "A node has id, episode, perceived_index, true_time (0-1 chronological position or null), "
    "summary, entities, valence (-1..1), excerpt_id. "
    "An entry has id, kind (contradiction|promise), description, episodes, excerpt_ids, urgency (1-5), entities. "
    "A payoff has node_id, target_id, episode, rationale. "
    "Respond with JSON only, no prose, no markdown fences. "
    "Episode {episode}: {text}"
)


class Transport(Protocol):
    """Sends one chat-completion request, returns the raw message content.

    Tests inject a fake implementation so the suite never touches the
    network; `_http_transport` is the only implementation that does.
    """

    def __call__(self, *, endpoint: str, token: str, model: str, prompt: str) -> str: ...


def _http_transport(*, endpoint: str, token: str, model: str, prompt: str) -> str:
    """OpenAI-compatible chat-completions POST. Used by both backends -- they
    differ only in endpoint URL, token, and model name, never in shape."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def cache_key(model: str, prompt: str) -> str:
    """Hash of (model, prompt) -- changing either invalidates the cache entry
    cleanly rather than silently serving a stale answer for a new question."""
    return hashlib.sha256(f"{model}\n{prompt}".encode("utf-8")).hexdigest()


def backend_for(endpoint: str) -> str:
    """Which backend an endpoint URL names. A Databricks Foundation Model API
    URL is the governed, on-platform path; anything else (principally
    OpenAI's own endpoint) is the off-platform measurement path. This is a
    property of the URL, never a caller-supplied label, so a result cannot
    claim to be the governed path just because the caller says so."""
    return "databricks" if "databricks" in endpoint.lower() else "openai"


class LLMExtractor:
    """Extractor backed by one OpenAI-compatible chat-completions endpoint.

    Conforms to `app.extraction.Extractor`. ``backend`` (derived from
    ``endpoint``) is set on every returned `ExtractionResult` and is the
    single source of truth for whether a number came from the governed
    Databricks path or the off-platform OpenAI path.
    """

    def __init__(
        self,
        endpoint: str,
        token: str,
        model: str,
        cache_path: str | Path | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._token = token
        self._model = model
        self._cache_path = Path(cache_path) if cache_path else None
        self._transport = transport or _http_transport
        self.backend = backend_for(endpoint)
        self._cache: dict[str, str] = {}
        if self._cache_path and self._cache_path.exists():
            self._cache = json.loads(self._cache_path.read_text(encoding="utf-8"))

    def extract(self, episodes: list[dict]) -> ExtractionResult:
        result = ExtractionResult(backend=self.backend)
        cache_dirty = False

        for row in episodes:
            validated = self._validate_row(row)
            if validated is None:
                result.rejected += 1
                continue
            episode, text = validated

            prompt = _PROMPT_TEMPLATE.format(episode=episode, text=text)
            key = cache_key(self._model, prompt)
            if key in self._cache:
                raw = self._cache[key]
            else:
                raw = self._transport(
                    endpoint=self._endpoint, token=self._token, model=self._model, prompt=prompt
                )
                self._cache[key] = raw
                cache_dirty = True

            parsed = parse_extraction_row(raw)
            if parsed is None:
                result.rejected += 1
                continue

            # As with DatabricksExtractor: one malformed item makes the whole
            # row's contribution suspect, so it is rejected wholesale rather
            # than item-by-item. The batch itself continues.
            try:
                nodes = [NarrativeNode.model_validate(item) for item in parsed.get("nodes", [])]
                entries = [LedgerEntry.model_validate(item) for item in parsed.get("entries", [])]
                # verified is forced False regardless of what the model
                # claims -- an extracted payoff is a claim, not a fact, and
                # trusting the model's own "verified" field would let a
                # hallucinated payoff suppress a real defect.
                payoffs = [
                    PayoffLink.model_validate({**item, "verified": False})
                    for item in parsed.get("payoffs", [])
                ]
                excerpts = [Excerpt.model_validate(item) for item in parsed.get("excerpts", [])]
            except ValidationError:
                result.rejected += 1
                continue

            result.nodes.extend(nodes)
            result.entries.extend(entries)
            result.payoffs.extend(payoffs)
            result.excerpts.extend(excerpts)

        if cache_dirty and self._cache_path is not None:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(self._cache, indent=2, sort_keys=True), encoding="utf-8"
            )

        return result

    @staticmethod
    def _validate_row(row: object) -> tuple[int, str] | None:
        if not isinstance(row, dict):
            return None
        try:
            episode = int(row.get("episode"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        text = row.get("synopsis") or row.get("body") or ""
        if not isinstance(text, str) or not text.strip():
            return None
        return episode, text
