"""Ground truth and discrimination scoring.

The manifest is authored by hand before the demo series is generated and is
withheld from the analyzer. A model that both plants the defects and grades the
detection measures nothing -- which is exactly the flaw in the superseded
benchmark, whose plan specified a test asserting precision == recall == 1.0.

Nothing here may assert a metric equals 1.0. Bound results; never fix them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from app.narrative_models import LedgerState, ResolvedEntry

DefectClass = Literal[
    "accidental_hole", "intentional_twist", "outstanding_obligation", "clean_control"
]


class ManifestItem(BaseModel):
    defect_id: str
    defect_class: DefectClass
    planted_episode: int | None = None
    payoff_episode: int | None = None
    expected_state: LedgerState
    notes: str = ""


class Manifest(BaseModel):
    series_id: str
    authored_by: str
    items: list[ManifestItem]

    def by_class(self, defect_class: DefectClass) -> list[ManifestItem]:
        return [item for item in self.items if item.defect_class == defect_class]


class DiscriminationReport(BaseModel):
    holes_caught: int
    holes_total: int
    twists_protected: int
    twists_total: int
    false_positives: int
    clean_total: int
    precision: float
    recall: float
    false_positive_rate: float
    baseline_flags: int
    obligations_tracked: int
    obligations_total: int


def load_manifest(path: Path) -> Manifest:
    with path.open(encoding="utf-8") as handle:
        return Manifest.model_validate(yaml.safe_load(handle))


def score_discrimination(
    manifest: Manifest, resolved: list[ResolvedEntry]
) -> DiscriminationReport:
    """Compare the resolver's verdicts against hand-authored ground truth.

    Precision is measured over everything the resolver called broken -- not just
    the subset of ``broken`` verdicts that happen to land on a manifest item. A
    resolver (or an extractor feeding it) that invents contradictions absent from
    the manifest entirely is still a false positive: it is still a spurious flag
    a writer has to triage, so it counts against precision even though there is
    no manifest item to compare it to.

    ``false_positive_rate`` is scored over the three ``clean_control`` items,
    which are ordinary paid promises. It can only detect one failure mode: the
    resolver assigning a clean control something other than its expected
    ``paid`` state (e.g. wrongly calling it ``broken`` or ``suspended``). It
    cannot detect false positives the resolver invents on entries that were
    never part of the manifest at all -- those are folded into ``false_positives``
    and precision instead, via the spurious-broken count above.

    ``outstanding_obligation`` items (a third of the manifest) are scored
    directly: an item expected to still be ``outstanding`` that resolves to
    anything else is a real discrimination error, not merely an unscored entry.
    """
    manifest_ids = {item.defect_id for item in manifest.items}
    states = {item.entry.id: item.state for item in resolved}

    holes = manifest.by_class("accidental_hole")
    twists = manifest.by_class("intentional_twist")
    cleans = manifest.by_class("clean_control")
    obligations = manifest.by_class("outstanding_obligation")

    holes_caught = sum(1 for item in holes if states.get(item.defect_id) == "broken")
    twists_protected = sum(1 for item in twists if states.get(item.defect_id) == "suspended")
    twists_flagged = sum(1 for item in twists if states.get(item.defect_id) == "broken")
    # A clean control is "flagged" if it resolves to anything other than its
    # expected paid state -- not only "broken". Suspending or leaving a clean
    # control outstanding is just as much a false read as breaking it.
    cleans_flagged = sum(
        1 for item in cleans if states.get(item.defect_id) not in (None, item.expected_state)
    )
    obligations_tracked = sum(
        1 for item in obligations if states.get(item.defect_id) == item.expected_state
    )

    # Entries the resolver called "broken" that aren't in the manifest at all --
    # an extractor's spurious contradictions, which precision must not ignore.
    spurious_broken = sum(
        1
        for entry_id, state in states.items()
        if state == "broken" and entry_id not in manifest_ids
    )

    false_positives = twists_flagged + cleans_flagged + spurious_broken
    flagged_total = holes_caught + false_positives

    return DiscriminationReport(
        holes_caught=holes_caught,
        holes_total=len(holes),
        twists_protected=twists_protected,
        twists_total=len(twists),
        false_positives=false_positives,
        clean_total=len(cleans),
        precision=holes_caught / flagged_total if flagged_total else 0.0,
        recall=holes_caught / len(holes) if holes else 0.0,
        false_positive_rate=cleans_flagged / len(cleans) if cleans else 0.0,
        # What this resolved graph actually flags without distinguishing
        # whether the contradiction maps to the held-out manifest. The authored
        # demo graph therefore reports 11, while an extracted graph can report
        # its own candidate count instead of inheriting the answer key's 11.
        baseline_flags=sum(1 for state in states.values() if state in {"broken", "suspended"}),
        obligations_tracked=obligations_tracked,
        obligations_total=len(obligations),
    )
