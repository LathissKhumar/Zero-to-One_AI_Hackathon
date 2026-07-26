from __future__ import annotations

import json

import pytest

from app.corpus_adapters import ArxivAdapter, CorpusSourceConfig, source_checksum


def test_real_source_adapter_requires_explicit_local_licensed_export(tmp_path):
    config = CorpusSourceConfig(platform="arxiv", path=tmp_path / "missing.json", license_reference="paper", source_version="v1")
    with pytest.raises(FileNotFoundError, match="licensed"):
        ArxivAdapter(config).load()


def test_adapter_preserves_platform_license_version_and_checksum(tmp_path):
    path = tmp_path / "arxiv.json"
    path.write_text(json.dumps([{"book_id": "b1", "chapter": 3, "continue_rate": 0.6, "text_reference": "paper#3"}]))
    rows = ArxivAdapter(CorpusSourceConfig(platform="arxiv", path=path, license_reference="paper", source_version="v1")).load()
    assert rows[0]["platform"] == "arxiv"
    assert rows[0]["license_reference"] == "paper"
    assert rows[0]["source_version"] == "v1"
    assert source_checksum(rows) == source_checksum(rows)
