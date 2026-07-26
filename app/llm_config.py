"""Single place that reads OPENAI_API_KEY -- nothing else reads it directly.

Every LLM-backed feature in this app (personas, repair text, deep ingestion
extraction) is opt-in: present when this returns a config, silently absent
(falling back to the deterministic/heuristic path) or explicitly refused
(422, never faked) when it returns None. See docs/superpowers/specs/
2026-07-26-canonpulse-gap-closure-design.md for which behaviour applies where.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class OpenAIConfig:
    endpoint: str
    token: str
    model: str


def openai_config() -> OpenAIConfig | None:
    token = os.environ.get("OPENAI_API_KEY")
    if not token:
        return None
    return OpenAIConfig(
        endpoint=os.environ.get("OPENAI_BASE_URL", _DEFAULT_ENDPOINT),
        token=token,
        model=os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL),
    )
