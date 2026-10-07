-- Forward-only expansion of consumer scope. Scientific facts, hashes, old
-- snapshots and the already-applied 0016 bytes are not changed.
CREATE TABLE source_portal_consumer_bindings_v17 (
    binding_id TEXT PRIMARY KEY,
    source_fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    evidence_snapshot_id TEXT NOT NULL,
    report TEXT NOT NULL CHECK (report IN ('A', 'B', 'C')),
    collection TEXT NOT NULL CHECK (
        collection IN ('efficacy', 'safety', 'observations')
        OR (collection = 'baseline' AND report = 'B')
    ),
    row_id TEXT NOT NULL,
    binding_json TEXT NOT NULL CHECK (json_valid(binding_json)),
    binding_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source_fact_version_id, report, collection, row_id)
);
INSERT INTO source_portal_consumer_bindings_v17
SELECT * FROM source_portal_consumer_bindings;
DROP TABLE source_portal_consumer_bindings;
ALTER TABLE source_portal_consumer_bindings_v17 RENAME TO source_portal_consumer_bindings;
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
