-- Forward-only expansion of consumer scope: the same immutable scientific fact
-- may be consumed by the same report row under more than one evidence snapshot
-- (a new candidate snapshot may reuse facts unchanged). Existing rows keep their
-- exact binding ids, payloads, hashes and times; only the uniqueness scope
-- changes from (fact, report) to (fact, report, evidence_snapshot_id). New
-- registrations carry snapshot-qualified ids; recovery still accepts original
-- legacy ids under their exact original scope. Scientific facts, hashes, old
-- snapshots and the already-applied 0016/0017 bytes are not changed.
CREATE TABLE source_portal_consumer_bindings_v18 (
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
    UNIQUE (source_fact_version_id, report, evidence_snapshot_id)
);
INSERT INTO source_portal_consumer_bindings_v18
SELECT * FROM source_portal_consumer_bindings;
DROP TABLE source_portal_consumer_bindings;
ALTER TABLE source_portal_consumer_bindings_v18 RENAME TO source_portal_consumer_bindings;
CREATE INDEX idx_source_portal_bindings_fact
ON source_portal_consumer_bindings (source_fact_version_id, report);
CREATE INDEX idx_source_portal_bindings_snapshot
ON source_portal_consumer_bindings (evidence_snapshot_id, report);
CREATE TRIGGER source_portal_consumer_bindings_no_update
BEFORE UPDATE ON source_portal_consumer_bindings
BEGIN SELECT RAISE(ABORT, 'append-only: source_portal_consumer_bindings'); END;
CREATE TRIGGER source_portal_consumer_bindings_no_delete
BEFORE DELETE ON source_portal_consumer_bindings
BEGIN SELECT RAISE(ABORT, 'append-only: source_portal_consumer_bindings'); END;
