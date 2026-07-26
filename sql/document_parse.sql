-- Silver: Databricks-native document parsing. The result preserves document
-- elements, page identifiers, bounding boxes, and parser confidence.
CREATE OR REPLACE TABLE ${catalog}.${db}.canonpulse_parsed_document AS
SELECT
    document_id,
    series_id,
    source_path,
    source_hash,
    'databricks-ai-parse-document' AS parser,
    '2.0' AS parser_version,
    ai_parse_document(
        content,
        map('version', '2.0', 'descriptionElementTypes', '')
    ) AS parsed_document,
    current_timestamp() AS parsed_at
FROM ${catalog}.${db}.canonpulse_raw_document;
