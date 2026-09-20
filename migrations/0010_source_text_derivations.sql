CREATE TABLE source_text_derivations (
    source_version_id TEXT PRIMARY KEY REFERENCES source_versions (source_version_id),
    raw_content_sha256 TEXT NOT NULL REFERENCES content_blobs (content_sha256),
    derivation_json TEXT NOT NULL CHECK (json_valid(derivation_json)),
    CHECK (raw_content_sha256 = json_extract(derivation_json, '$.raw_asset.sha256'))
);

CREATE TRIGGER source_text_derivations_no_update BEFORE UPDATE ON source_text_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: source_text_derivations'); END;
CREATE TRIGGER source_text_derivations_no_delete BEFORE DELETE ON source_text_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: source_text_derivations'); END;
