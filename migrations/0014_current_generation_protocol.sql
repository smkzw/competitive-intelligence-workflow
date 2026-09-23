CREATE TABLE current_delivery_generations (
    generation_sha256 TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    request_id TEXT,
    generation_relative_path TEXT NOT NULL UNIQUE,
    bundle_json TEXT NOT NULL CHECK (json_valid(bundle_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE current_delivery_state (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    request_id TEXT,
    generation_sha256 TEXT NOT NULL REFERENCES current_delivery_generations (generation_sha256),
    generation_relative_path TEXT NOT NULL,
    committed_at TEXT NOT NULL
);

CREATE TRIGGER current_delivery_generations_no_update
BEFORE UPDATE ON current_delivery_generations
BEGIN SELECT RAISE(ABORT, 'append-only: current_delivery_generations'); END;

CREATE TRIGGER current_delivery_generations_no_delete
BEFORE DELETE ON current_delivery_generations
BEGIN SELECT RAISE(ABORT, 'append-only: current_delivery_generations'); END;
