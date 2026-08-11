CREATE TABLE correction_proposals (
    proposal_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'submitted', 'needs_evidence', 'rejected',
        'validated_pending_user_approval', 'approved', 'published'
    )),
    proposal_json TEXT NOT NULL CHECK (json_valid(proposal_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    result_digest TEXT,
    created_at TEXT NOT NULL
);
