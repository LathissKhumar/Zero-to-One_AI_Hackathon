"""Load and validate the demo series.

Validation is not ceremony: a dangling excerpt reference means a warning would
surface to a writer with no evidence behind it, which is the one thing this
product must never do.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.narrative_models import Series


def load_series(path: Path) -> Series:
    with path.open(encoding="utf-8") as handle:
        return Series.model_validate(json.load(handle))
