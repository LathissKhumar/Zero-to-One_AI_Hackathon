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


def load_manifest(path: Path) -> Manifest:
    with path.open(encoding="utf-8") as handle:
        return Manifest.model_validate(yaml.safe_load(handle))


def score_discrimination(
    manifest: Manifest, resolved: list[ResolvedEntry]
) -> DiscriminationReport:
    """Compare the resolver's verdicts against hand-authored ground truth.

    Precision is measured over everything the resolver called broken: a protected
    twist wrongly flagged is a false positive, because that is precisely the
    error that makes writers stop trusting continuity tools.
    """
    states = {item.entry.id: item.state for item in resolved}

    holes = manifest.by_class("accidental_hole")
    twists = manifest.by_class("intentional_twist")
    cleans = manifest.by_class("clean_control")

    holes_caught = sum(1 for item in holes if states.get(item.defect_id) == "broken")
    twists_protected = sum(1 for item in twists if states.get(item.defect_id) == "suspended")
    twists_flagged = sum(1 for item in twists if states.get(item.defect_id) == "broken")
    cleans_flagged = sum(1 for item in cleans if states.get(item.defect_id) == "broken")

    false_positives = twists_flagged + cleans_flagged
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
        # What a checker without the payoff test reports: every contradiction.
        baseline_flags=len(holes) + len(twists),
    )
