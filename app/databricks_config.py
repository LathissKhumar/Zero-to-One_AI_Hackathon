"""Reads DATABRICKS_HOST / SERVING_MODEL_ENDPOINT -- nothing else does.

The governed, on-platform inference path: same OpenAI-compatible chat-
completions shape app.llm_extractor already speaks, just pointed at a
Databricks Foundation Model API serving endpoint instead of OpenAI's own
endpoint, with a token minted from the caller's Databricks auth rather than
a static key. Opt-in the same way app.llm_config.openai_config is: absent
config means the deterministic/heuristic path stays the default everywhere
that consumes this.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DatabricksModelConfig:
    endpoint: str
    token: str
    model: str


def _sdk_auth_token() -> str:
    from databricks.sdk.core import Config

    headers = Config().authenticate()
    authorization = headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise RuntimeError("Databricks authentication did not return a bearer token")
    return authorization.removeprefix("Bearer ")


def databricks_model_config(token_provider: Callable[[], str] = _sdk_auth_token) -> DatabricksModelConfig | None:
    host = os.environ.get("DATABRICKS_HOST")
    model = os.environ.get("SERVING_MODEL_ENDPOINT")
    if not host or not model:
        return None
    try:
        token = token_provider()
    except Exception:
        # Auth can fail for reasons that have nothing to do with whether the
        # feature is configured (expired CLI session, no SDK, no workspace
        # network route) -- absent config and unusable config both mean
        # "fall back", so callers don't need to distinguish them.
        return None
    return DatabricksModelConfig(
        endpoint=f"{host.rstrip('/')}/serving-endpoints/{model}/invocations",
        token=token,
        model=model,
    )
