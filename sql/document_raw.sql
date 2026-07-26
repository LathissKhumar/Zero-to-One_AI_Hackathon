-- Bronze: read arbitrary supported document files from a Unity Catalog Volume.
-- The runner replaces __SOURCE_PATH__ with a validated /Volumes/... path.
CREATE OR REPLACE TABLE ${catalog}.${db}.canonpulse_raw_document AS
SELECT
    sha2(content, 256) AS document_id,
    '__SERIES_ID__' AS series_id,
    path AS source_path,
    sha2(content, 256) AS source_hash,
    content,
    length(content) AS file_size,
    current_timestamp() AS ingested_at
FROM read_files('__SOURCE_PATH__', format => 'binaryFile');
