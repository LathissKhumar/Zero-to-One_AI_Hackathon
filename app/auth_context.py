"""Minimal request-scoped actor and series authorization boundary."""

from __future__ import annotations

import uuid

from fastapi import Request
from pydantic import BaseModel, Field


class ActorContext(BaseModel):
    actor_id: str = Field(min_length=1)
    roles: frozenset[str] = frozenset()
    series_ids: frozenset[str] = frozenset()


def actor_from_request(request: Request) -> ActorContext:
    actor_id = request.headers.get("x-actor-id", "anonymous")
    roles = frozenset(filter(None, request.headers.get("x-roles", "").split(",")))
    series_ids = frozenset(filter(None, request.headers.get("x-series-ids", "").split(",")))
    return ActorContext(actor_id=actor_id, roles=roles, series_ids=series_ids)


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def authorize_series(actor: ActorContext, series_id: str, version_id: str) -> None:
    if not version_id:
        raise PermissionError("version access is required")
    if "showrunner" not in actor.roles and series_id not in actor.series_ids:
        raise PermissionError("actor lacks series access")
