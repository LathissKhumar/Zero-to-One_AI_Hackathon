"""Two separable numbers, not one hollow one.

`data/series/last_monsoon.json` ships with its `entries` and `payoffs`
pre-populated by the same script that was conditioned on the manifest answer
key. Resolving *those* against the manifest measures nothing but that graph
traversal is exact -- it never exercises extraction, because extraction never
ran. This module reports that number honestly (as ``ledger``) and, when an
extractor is supplied, a second number (``extracted``) that rebuilds the graph
from episode text first and only then resolves and scores it. ``extracted`` is
the number that can fall, which is what makes it evidence.

THE MATCHING RULE (the one load-bearing judgement here -- argue with this, not
with the code):

Extracted `LedgerEntry` ids are synthetic (``contradiction-12-88``,
``promise-30-obligation``, ...); they never equal a manifest `defect_id`, so
`score_discrimination` cannot join the two by id. Instead we match by
position: an extracted entry is credited with recovering manifest item ``X``
when

  1. the entry's *kind* is compatible with ``X``'s `defect_class`
     (``contradiction`` entries may only match ``accidental_hole`` or
     ``intentional_twist`` items; ``promise`` entries may only match
     ``outstanding_obligation`` or ``clean_control`` items) -- a promise can
     never "recover" a plot hole no matter where it falls, and

  2. ``X.planted_episode`` falls inside the entry's own detected span,
     inclusive: ``entry.origin_episode <= X.planted_episode <=
     entry.latest_episode``.

Tolerance chosen: exact containment, zero fuzzy widening. We deliberately did
not add a "within N episodes of the plant" proximity rule. A window wide
enough to forgive the extractor's imprecision (N=5, say) is also wide enough
to let two *unrelated* contradictions -- different characters, different
threads, whose planted episodes merely happen to fall a few episodes apart --
match each other. That would manufacture recall out of coincidence rather than
detection. Containment ties the match to a span the extractor actually
computed from the text (the two episodes its own rules found in conflict),
so a match means the extractor's detected span really does bracket the
planted claim, not merely that it landed nearby.

Each manifest item can be claimed by at most one extracted entry (first
encountered, in the extractor's own deterministic output order), and each
extracted entry claims at most one manifest item (the one with the smallest
`planted_episode` among candidates, for determinism) -- so one lucky wide
span cannot "recover" several manifest items at once, and matching is a
one-to-one assignment, not a many-to-many fan-out.

A matched entry is not automatically scored as a hit: it is only *renamed* to
the manifest's `defect_id` before scoring, so `score_discrimination`'s
existing precision/recall/false-positive logic runs unchanged on top of it.
Whether it then counts as recovered still depends on the state the resolver
assigned it -- and extracted `PayoffLink`s are always `verified=False`
(see `app/heuristic_extractor.py`), so `LedgerResolver` will not let an
unverified link protect a contradiction. An extracted, correctly-matched
twist therefore still resolves `broken`, not `suspended`, and counts against
precision as a false positive rather than for recall as a protected twist.
That is the system working as designed, not a bug in the matching rule.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.extraction import Extractor
from app.ledger import LedgerResolver
from app.manifest import DiscriminationReport, Manifest, score_discrimination
from app.narrative_models import LedgerEntry, ResolvedEntry, Series

_KIND_TO_MANIFEST_CLASSES: dict[str, set[str]] = {
    "contradiction": {"accidental_hole", "intentional_twist"},
    "promise": {"outstanding_obligation", "clean_control"},
}


class EndToEndReport(BaseModel):
    """Both numbers side by side. ``extracted`` is ``None`` iff no extractor
    was supplied -- callers must not accidentally compare a real end-to-end
    number against a stand-in."""

    ledger: DiscriminationReport
    extracted: DiscriminationReport | None = None
    extraction_rejected: int = 0


def _episode_rows(series: Series) -> list[dict]:
    """Build the extractor's input from the series' own authored text.

    Nodes carry a short authored ``summary``; excerpts carry the fuller scene
    text for the same episode. Concatenating both gives the extractor
    everything a reader would see for that episode, without introducing a new
    data file -- the episode text already lives on the series.
    """
    excerpt_text_by_episode = {excerpt.episode: excerpt.text for excerpt in series.excerpts}
    rows: list[dict] = []
    for node in series.nodes:
        excerpt_text = excerpt_text_by_episode.get(node.episode, "")
        text = f"{node.summary} {excerpt_text}".strip()
        rows.append({"episode": node.episode, "synopsis": text})
    return rows


def _match_extracted_ids(entries: list[LedgerEntry], manifest: Manifest) -> dict[str, str]:
    """Positional match from extracted entry id -> manifest defect_id.

    See the module docstring for the exact rule and the tolerance rationale.
    """
    matched_defect_ids: set[str] = set()
    mapping: dict[str, str] = {}
    for entry in entries:
        allowed_classes = _KIND_TO_MANIFEST_CLASSES.get(entry.kind, set())
        candidates = [
            item
            for item in manifest.items
            if item.defect_class in allowed_classes
            and item.defect_id not in matched_defect_ids
            and item.planted_episode is not None
            and entry.origin_episode <= item.planted_episode <= entry.latest_episode
        ]
        if not candidates:
            continue
        chosen = min(candidates, key=lambda item: item.planted_episode)
        mapping[entry.id] = chosen.defect_id
        matched_defect_ids.add(chosen.defect_id)
    return mapping


def _rescored(resolved: list[ResolvedEntry], mapping: dict[str, str]) -> list[ResolvedEntry]:
    """Rename matched entries' ids to the manifest defect_id they recovered.

    Unmatched entries keep their synthetic id, so they remain outside
    ``manifest_ids`` in ``score_discrimination`` and are counted as spurious
    false positives, exactly as an unmatched extractor invention should be.
    """
    rescored: list[ResolvedEntry] = []
    for resolved_entry in resolved:
        new_id = mapping.get(resolved_entry.entry.id)
        if new_id is None:
            rescored.append(resolved_entry)
            continue
        renamed_entry = resolved_entry.entry.model_copy(update={"id": new_id})
        rescored.append(resolved_entry.model_copy(update={"entry": renamed_entry}))
    return rescored


def evaluate_series(
    series: Series, manifest: Manifest, extractor: Extractor | None = None
) -> EndToEndReport:
    """Score the series twice: ledger correctness, then (optionally) end-to-end.

    1. Ledger: resolve the series' authored ``entries``/``payoffs`` as-is and
       score against ``manifest``. This is graph traversal only; it never
       touches extraction and should stay near-perfect.
    2. Extracted: when ``extractor`` is supplied, rebuild ``entries``,
       ``payoffs``, ``nodes`` and ``excerpts`` from the series' episode text
       via the extractor, resolve *that* graph, and score it against the same
       manifest using the positional match described in the module docstring.
       Omitting ``extractor`` omits this number entirely (``None``) rather
       than faking one.
    """
    resolver = LedgerResolver()
    ledger_report = score_discrimination(manifest, resolver.resolve_series(series))

    if extractor is None:
        return EndToEndReport(ledger=ledger_report, extracted=None, extraction_rejected=0)

    extraction = extractor.extract(_episode_rows(series))
    extracted_series = series.model_copy(
        update={
            "nodes": extraction.nodes,
            "entries": extraction.entries,
            "payoffs": extraction.payoffs,
            "excerpts": extraction.excerpts,
        }
    )
    resolved = resolver.resolve_series(extracted_series)
    mapping = _match_extracted_ids(extraction.entries, manifest)
    extracted_report = score_discrimination(manifest, _rescored(resolved, mapping))

    return EndToEndReport(
        ledger=ledger_report,
        extracted=extracted_report,
        extraction_rejected=extraction.rejected,
    )
