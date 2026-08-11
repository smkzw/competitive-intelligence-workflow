CREATE TABLE gate_evaluations (
    gate_evaluation_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    report_kind TEXT NOT NULL CHECK (report_kind IN ('A', 'B', 'C')),
    gate_id TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('passed', 'failed', 'not_applicable', 'blocked')),
    details_json TEXT NOT NULL CHECK (json_valid(details_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE report_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    report_kind TEXT NOT NULL CHECK (report_kind IN ('A', 'B', 'C')),
    report_version TEXT NOT NULL,
    evidence_state TEXT NOT NULL CHECK (evidence_state IN (
        'queued', 'collecting', 'recovering', 'awaiting_user',
        'scientific_qc', 'snapshot_locked', 'evidence_blocked', 'superseded'
    )),
    manifest_json TEXT NOT NULL CHECK (json_valid(manifest_json)),
    created_at TEXT NOT NULL,
    UNIQUE (project_id, report_kind, report_version)
);

CREATE TABLE coverage_sets (
    coverage_set_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES report_snapshots (snapshot_id),
    report_kind TEXT NOT NULL CHECK (report_kind IN ('A', 'B', 'C')),
    coverage_json TEXT NOT NULL CHECK (json_valid(coverage_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE coverage_projections (
    projection_id TEXT PRIMARY KEY,
    coverage_set_id TEXT NOT NULL REFERENCES coverage_sets (coverage_set_id),
    output_format TEXT NOT NULL CHECK (output_format IN ('html', 'pdf', 'html-ppt', 'pptx')),
    projection_json TEXT NOT NULL CHECK (json_valid(projection_json)),
    exception_json TEXT NOT NULL CHECK (json_valid(exception_json)),
    created_at TEXT NOT NULL,
    UNIQUE (coverage_set_id, output_format)
);
