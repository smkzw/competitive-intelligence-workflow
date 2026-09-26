-- Portal row identities are not part of a source fact's scientific content hash.
-- An accepted report can later select these append-only candidate bindings;
-- registration alone does not publish or accept the source fact.
CREATE TABLE source_portal_consumer_bindings (
    binding_id TEXT PRIMARY KEY,
    source_fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    evidence_snapshot_id TEXT NOT NULL,
    report TEXT NOT NULL CHECK (report IN ('A', 'B', 'C')),
    collection TEXT NOT NULL CHECK (collection IN ('efficacy', 'safety', 'observations')),
    row_id TEXT NOT NULL,
    binding_json TEXT NOT NULL CHECK (json_valid(binding_json)),
    binding_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_fact_version_id, report, collection, row_id)
);
CREATE INDEX idx_source_portal_bindings_fact
ON source_portal_consumer_bindings (source_fact_version_id, report);
CREATE UNIQUE INDEX idx_source_portal_one_row_per_fact_report
ON source_portal_consumer_bindings (source_fact_version_id, report);
CREATE TRIGGER source_portal_consumer_bindings_no_update
BEFORE UPDATE ON source_portal_consumer_bindings
BEGIN SELECT RAISE(ABORT, 'append-only: source_portal_consumer_bindings'); END;
CREATE TRIGGER source_portal_consumer_bindings_no_delete
BEFORE DELETE ON source_portal_consumer_bindings
BEGIN SELECT RAISE(ABORT, 'append-only: source_portal_consumer_bindings'); END;
