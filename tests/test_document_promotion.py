from scripts.promote_document_series import chunked_extraction_sql, extraction_object, namespace_extraction, response_rows


def test_statement_api_rows_are_mapped_by_manifest_column_names():
    response = {
        "manifest": {"schema": {"columns": [{"name": "episode"}, {"name": "extraction"}]}},
        "result": {"data_array": [[1, '{"nodes": []}']]},
    }

    assert response_rows(response) == [{"episode": 1, "extraction": '{"nodes": []}'}]


def test_graph_payload_accepts_json_string_or_variant_dict():
    payload = {"nodes": [], "entries": [], "payoffs": [], "excerpts": []}

    assert extraction_object(json_text := '{"nodes": [], "entries": [], "payoffs": [], "excerpts": []}') == payload
    assert extraction_object(payload) == payload


def test_long_episode_extraction_is_chunked_before_ai_query():
    template = "SELECT episode, ai_query('${model}', coalesce(body, synopsis)) AS extraction FROM ${catalog}.${db}.episodes WHERE series_id = :series_id ORDER BY episode;"
    statement = chunked_extraction_sql(template, catalog="writers_room", schema="canonpulse", model="model", chunk_size=1200)

    assert "WITH chunks AS" in statement
    assert "posexplode" in statement
    assert "chunk_index * 1200 + 1" in statement
    assert "FROM chunks" in statement
    assert "chunk_index" in statement
    assert not statement.rstrip().endswith(";")


def test_chunk_ids_are_namespaced_without_breaking_local_references():
    parsed = {
        "nodes": [{"id": "n1", "excerpt_id": "x1"}],
        "entries": [{"id": "e1", "excerpt_ids": ["x1"]}],
        "payoffs": [{"node_id": "n1", "target_id": "n1"}],
        "excerpts": [{"id": "x1"}],
    }

    namespaced = namespace_extraction(parsed, 2)

    assert namespaced["nodes"][0]["id"] == "chunk-2-n1"
    assert namespaced["nodes"][0]["excerpt_id"] == "chunk-2-x1"
    assert namespaced["entries"][0]["excerpt_ids"] == ["chunk-2-x1"]
    assert namespaced["payoffs"][0]["target_id"] == "chunk-2-n1"
