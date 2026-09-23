DROP TRIGGER fact_versions_no_update;
DROP TRIGGER fact_versions_no_delete;
DROP TRIGGER fact_evidence_no_update;
DROP TRIGGER fact_evidence_no_delete;
DROP TRIGGER claim_facts_no_update;
DROP TRIGGER claim_facts_no_delete;
DROP INDEX idx_fact_versions_fact;
DROP INDEX idx_fact_versions_logical_id;

ALTER TABLE fact_versions RENAME TO fact_versions_legacy_0012;
ALTER TABLE fact_evidence RENAME TO fact_evidence_legacy_0012;
ALTER TABLE claim_facts RENAME TO claim_facts_legacy_0012;

CREATE TABLE fact_versions (
    fact_version_id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL,
    entity_id TEXT NOT NULL REFERENCES entities (entity_id),
    field_id TEXT NOT NULL,
    raw_value TEXT,
    normalized_value TEXT,
    disclosure_state TEXT NOT NULL CHECK (disclosure_state IN (
        'reported_value', 'reported_zero', 'not_reported',
        'below_reporting_threshold', 'not_publicly_disclosed',
        'not_applicable', 'conflicting', 'unresolved_due_to_route'
    )),
    review_state TEXT NOT NULL CHECK (review_state IN (
        'candidate', 'accepted', 'user_modified', 'rejected', 'superseded'
    )),
    primary_fragment_id TEXT NOT NULL REFERENCES evidence_fragments (fragment_id),
    supersedes_fact_version_id TEXT REFERENCES fact_versions (fact_version_id),
    created_at TEXT NOT NULL,
    content_sha256 TEXT,
    scientific_context_json TEXT
);

INSERT INTO fact_versions SELECT * FROM fact_versions_legacy_0012;

CREATE TABLE fact_evidence (
    fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    fragment_id TEXT NOT NULL REFERENCES evidence_fragments (fragment_id),
    evidence_role TEXT NOT NULL CHECK (evidence_role IN ('primary', 'supporting', 'conflicting')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (fact_version_id, fragment_id, evidence_role)
);
INSERT INTO fact_evidence SELECT * FROM fact_evidence_legacy_0012;

CREATE TABLE claim_facts (
    claim_version_id TEXT NOT NULL REFERENCES claim_versions (claim_version_id),
    fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    support_role TEXT NOT NULL CHECK (support_role IN ('supports', 'limits', 'contradicts')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (claim_version_id, fact_version_id, support_role)
);
INSERT INTO claim_facts SELECT * FROM claim_facts_legacy_0012;

DROP TABLE fact_evidence_legacy_0012;
DROP TABLE claim_facts_legacy_0012;
DROP TABLE fact_versions_legacy_0012;

CREATE TRIGGER fact_versions_no_update BEFORE UPDATE ON fact_versions
BEGIN SELECT RAISE(ABORT, 'append-only: fact_versions'); END;
CREATE TRIGGER fact_versions_no_delete BEFORE DELETE ON fact_versions
BEGIN SELECT RAISE(ABORT, 'append-only: fact_versions'); END;
CREATE TRIGGER fact_evidence_no_update BEFORE UPDATE ON fact_evidence
BEGIN SELECT RAISE(ABORT, 'append-only: fact_evidence'); END;
CREATE TRIGGER fact_evidence_no_delete BEFORE DELETE ON fact_evidence
BEGIN SELECT RAISE(ABORT, 'append-only: fact_evidence'); END;
CREATE TRIGGER claim_facts_no_update BEFORE UPDATE ON claim_facts
BEGIN SELECT RAISE(ABORT, 'append-only: claim_facts'); END;
CREATE TRIGGER claim_facts_no_delete BEFORE DELETE ON claim_facts
BEGIN SELECT RAISE(ABORT, 'append-only: claim_facts'); END;
CREATE INDEX idx_fact_versions_fact ON fact_versions (fact_id, created_at);
CREATE INDEX idx_fact_versions_logical_id ON fact_versions (fact_id, created_at);

CREATE TABLE user_fact_edit_requests (
    request_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    expected_revision INTEGER NOT NULL CHECK (expected_revision >= 0),
    target_fact_id TEXT NOT NULL,
    target_fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    result_fact_version_id TEXT REFERENCES fact_versions (fact_version_id),
    result_revision INTEGER,
    status TEXT NOT NULL CHECK (status IN ('staging', 'complete')),
    command_json TEXT NOT NULL CHECK (json_valid(command_json)),
    result_json TEXT CHECK (result_json IS NULL OR json_valid(result_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE user_fact_derivations (
    derivation_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    derivation_kind TEXT NOT NULL CHECK (derivation_kind IN (
        'crude_rate', 'medical_semantic', 'facet', 'narrative'
    )),
    input_fact_version_ids_json TEXT NOT NULL CHECK (json_valid(input_fact_version_ids_json)),
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    parameters_json TEXT NOT NULL CHECK (json_valid(parameters_json)),
    output_json TEXT NOT NULL CHECK (json_valid(output_json)),
    unit TEXT,
    formula TEXT,
    applicability TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE user_refresh_conflicts (
    conflict_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    base_fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    user_fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    source_fields_json TEXT NOT NULL CHECK (json_valid(source_fields_json)),
    field_states_json TEXT NOT NULL CHECK (json_valid(field_states_json)),
    requires_explicit_resolution INTEGER NOT NULL CHECK (requires_explicit_resolution IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TRIGGER user_fact_edit_requests_no_update
BEFORE UPDATE ON user_fact_edit_requests
WHEN OLD.status = 'complete' OR NEW.status != 'complete'
BEGIN SELECT RAISE(ABORT, 'append-only after completion: user_fact_edit_requests'); END;
CREATE TRIGGER user_fact_edit_requests_no_delete BEFORE DELETE ON user_fact_edit_requests
BEGIN SELECT RAISE(ABORT, 'append-only: user_fact_edit_requests'); END;
CREATE TRIGGER user_fact_derivations_no_update BEFORE UPDATE ON user_fact_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: user_fact_derivations'); END;
CREATE TRIGGER user_fact_derivations_no_delete BEFORE DELETE ON user_fact_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: user_fact_derivations'); END;
CREATE TRIGGER user_refresh_conflicts_no_update BEFORE UPDATE ON user_refresh_conflicts
BEGIN SELECT RAISE(ABORT, 'append-only: user_refresh_conflicts'); END;
CREATE TRIGGER user_refresh_conflicts_no_delete BEFORE DELETE ON user_refresh_conflicts
BEGIN SELECT RAISE(ABORT, 'append-only: user_refresh_conflicts'); END;
