CREATE TABLE source_versions (
    source_version_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    published_at TEXT,
    effective_at TEXT,
    first_disclosed_at TEXT,
    source_locator TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE source_eligibility_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    source_version_id TEXT NOT NULL REFERENCES source_versions (source_version_id),
    eligible INTEGER NOT NULL CHECK (eligible IN (0, 1)),
    rationale TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE refresh_candidates (
    candidate_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    candidate_locator TEXT NOT NULL,
    first_disclosed_at TEXT,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE evidence_fragments (
    fragment_id TEXT PRIMARY KEY,
    source_version_id TEXT NOT NULL REFERENCES source_versions (source_version_id),
    locator TEXT NOT NULL,
    content_text TEXT NOT NULL,
    content_sha256 TEXT,
    created_at TEXT NOT NULL
);

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
        'candidate', 'accepted', 'rejected', 'superseded'
    )),
    primary_fragment_id TEXT NOT NULL REFERENCES evidence_fragments (fragment_id),
    supersedes_fact_version_id TEXT REFERENCES fact_versions (fact_version_id),
    created_at TEXT NOT NULL
);

CREATE TABLE fact_evidence (
    fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    fragment_id TEXT NOT NULL REFERENCES evidence_fragments (fragment_id),
    evidence_role TEXT NOT NULL CHECK (evidence_role IN ('primary', 'supporting', 'conflicting')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (fact_version_id, fragment_id, evidence_role)
);

CREATE TABLE claim_versions (
    claim_version_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    claim_kind TEXT NOT NULL CHECK (claim_kind IN (
        'direct_evidence', 'deterministic_calculation', 'synthesis'
    )),
    review_state TEXT NOT NULL CHECK (review_state IN (
        'candidate', 'accepted', 'rejected', 'superseded'
    )),
    supersedes_claim_version_id TEXT REFERENCES claim_versions (claim_version_id),
    created_at TEXT NOT NULL
);

CREATE TABLE claim_facts (
    claim_version_id TEXT NOT NULL REFERENCES claim_versions (claim_version_id),
    fact_version_id TEXT NOT NULL REFERENCES fact_versions (fact_version_id),
    support_role TEXT NOT NULL CHECK (support_role IN ('supports', 'limits', 'contradicts')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (claim_version_id, fact_version_id, support_role)
);

CREATE TABLE conflict_sets (
    conflict_set_id TEXT PRIMARY KEY,
    object_type TEXT NOT NULL CHECK (object_type IN ('fact', 'claim')),
    object_id TEXT NOT NULL,
    resolution_state TEXT NOT NULL CHECK (resolution_state IN ('open', 'resolved')),
    resolution_note TEXT,
    created_at TEXT NOT NULL
);
