ALTER TABLE fact_versions ADD COLUMN content_sha256 TEXT;
ALTER TABLE fact_versions ADD COLUMN scientific_context_json TEXT;

CREATE TABLE source_acquisition_attempts (
    attempt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_version_id TEXT NOT NULL REFERENCES source_versions (source_version_id),
    receipt_id TEXT NOT NULL UNIQUE,
    attempt_index INTEGER NOT NULL CHECK (attempt_index >= 1),
    acquired_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (request_id, source_id)
);

CREATE TABLE evidence_derivations (
    derivation_id TEXT PRIMARY KEY,
    derivation_kind TEXT NOT NULL CHECK (derivation_kind IN (
        'source_text', 'normalization', 'translation'
    )),
    input_fragment_ids_json TEXT NOT NULL CHECK (json_valid(input_fragment_ids_json)),
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    output_json TEXT NOT NULL CHECK (json_valid(output_json)),
    created_at TEXT NOT NULL
);

CREATE TRIGGER source_acquisition_attempts_no_update
BEFORE UPDATE ON source_acquisition_attempts
BEGIN SELECT RAISE(ABORT, 'append-only: source_acquisition_attempts'); END;

CREATE TRIGGER source_acquisition_attempts_no_delete
BEFORE DELETE ON source_acquisition_attempts
BEGIN SELECT RAISE(ABORT, 'append-only: source_acquisition_attempts'); END;

CREATE TRIGGER evidence_derivations_no_update
BEFORE UPDATE ON evidence_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_derivations'); END;

CREATE TRIGGER evidence_derivations_no_delete
BEFORE DELETE ON evidence_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_derivations'); END;

CREATE INDEX idx_acquisition_attempt_source
ON source_acquisition_attempts (source_id, attempt_index);

CREATE INDEX idx_fact_versions_logical_id
ON fact_versions (fact_id, created_at);
