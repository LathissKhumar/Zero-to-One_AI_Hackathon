from scripts.promote_document_series import extraction_object, response_rows


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
