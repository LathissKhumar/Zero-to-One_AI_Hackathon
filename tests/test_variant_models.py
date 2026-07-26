from __future__ import annotations

from app.variant_models import VariantOperation, ValidationResult
from app.variants import Variant
from tests.test_variants import _series


def test_variant_operation_accepts_only_typed_kinds():
    operation = VariantOperation(kind="swap_order", node_ids=("n1", "n2"), seed=3)
    assert operation.kind == "swap_order"


def test_variant_validation_rejects_changed_true_graph():
    source = _series()
    changed = source.model_copy(deep=True)
    changed.nodes[0].summary = "changed chronology"
    variant = Variant(
        variant_id="v1", series=changed, base_version=source.source_version,
        operation=VariantOperation(kind="repair", node_ids=("n1",), seed=1),
        changed_node_ids=("n1",),
    )
    result = ValidationResult(valid=False, errors=["G_true nodes or edges changed"])
    assert result.valid is False
    assert variant.changed_node_ids == ("n1",)
