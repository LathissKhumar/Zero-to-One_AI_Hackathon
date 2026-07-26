from __future__ import annotations

import pytest

from app.auth_context import ActorContext, authorize_series


def test_series_route_rejects_actor_without_series_access():
    with pytest.raises(PermissionError, match="series access"):
        authorize_series(ActorContext(actor_id="writer-1", roles=frozenset(), series_ids=frozenset()), "secret", "v1")


def test_showrunner_role_can_access_authorized_version():
    authorize_series(
        ActorContext(actor_id="showrunner", roles=frozenset({"showrunner"}), series_ids=frozenset()),
        "s1",
        "v1",
    )
