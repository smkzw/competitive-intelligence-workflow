CREATE TABLE project_contract_versions (
    project_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version >= 1),
    contract_json TEXT NOT NULL CHECK (json_valid(contract_json)),
    timezone TEXT NOT NULL,
    data_cutoff TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, contract_version)
);

CREATE TABLE project_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    contract_version INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'running', 'awaiting_user', 'partially_delivered',
        'partial_delivery_blocked', 'blocked', 'complete'
    )),
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id, contract_version)
        REFERENCES project_contract_versions (project_id, contract_version)
);

CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE entity_identifiers (
    identifier_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities (entity_id),
    namespace TEXT NOT NULL,
    identifier TEXT NOT NULL,
    evidence_fragment_id TEXT REFERENCES evidence_fragments (fragment_id),
    created_at TEXT NOT NULL,
    UNIQUE (namespace, identifier, entity_id)
);

CREATE TABLE entity_relations (
    relation_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL REFERENCES entities (entity_id),
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL REFERENCES entities (entity_id),
    evidence_fragment_id TEXT REFERENCES evidence_fragments (fragment_id),
    created_at TEXT NOT NULL
);
