from __future__ import annotations

from app.store import ApprovalAuditStore


def test_approval_is_scoped_and_idempotently_audited():
    store = ApprovalAuditStore()
    first = store.approve("s1", "v1", "i1", "writer-1", "request-1")
    second = store.approve("s1", "v1", "i1", "writer-1", "request-1")
    assert first == second
    assert store.events("s1", "v1")[0].issue_id == "i1"
