CREATE TABLE content_blobs (
    content_sha256 TEXT PRIMARY KEY CHECK (
        length(content_sha256) = 64
        AND content_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    relative_path TEXT NOT NULL UNIQUE CHECK (
        relative_path GLOB 'evidence/raw/sha256/[0-9a-f][0-9a-f]/*.bin'
        AND substr(relative_path, 1, 1) <> '/'
        AND instr(relative_path, '..') = 0
        AND instr(relative_path, '\') = 0
    ),
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    media_type TEXT NOT NULL CHECK (length(trim(media_type)) > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE source_date_assertions (
    assertion_id TEXT PRIMARY KEY,
    source_version_id TEXT NOT NULL REFERENCES source_versions (source_version_id),
    date_role TEXT NOT NULL CHECK (date_role IN (
        'acquired_at', 'published_at', 'effective_at', 'first_disclosed_at'
    )),
    disclosure_state TEXT NOT NULL CHECK (disclosure_state IN (
        'reported', 'not_publicly_disclosed', 'not_applicable'
    )),
    observed_at TEXT,
    timezone TEXT NOT NULL CHECK (length(trim(timezone)) > 0),
    locator_json TEXT NOT NULL CHECK (json_valid(locator_json)),
    created_at TEXT NOT NULL,
    CHECK (
        (disclosure_state = 'reported' AND observed_at IS NOT NULL)
        OR (disclosure_state <> 'reported' AND observed_at IS NULL)
    ),
    UNIQUE (source_version_id, date_role)
);

CREATE TRIGGER content_blobs_no_update BEFORE UPDATE ON content_blobs
BEGIN SELECT RAISE(ABORT, 'append-only: content_blobs'); END;
CREATE TRIGGER content_blobs_no_delete BEFORE DELETE ON content_blobs
BEGIN SELECT RAISE(ABORT, 'append-only: content_blobs'); END;

CREATE TRIGGER source_date_assertions_no_update BEFORE UPDATE ON source_date_assertions
BEGIN SELECT RAISE(ABORT, 'append-only: source_date_assertions'); END;
CREATE TRIGGER source_date_assertions_no_delete BEFORE DELETE ON source_date_assertions
BEGIN SELECT RAISE(ABORT, 'append-only: source_date_assertions'); END;

CREATE TRIGGER evidence_fragments_require_original_text
BEFORE INSERT ON evidence_fragments
WHEN length(trim(NEW.content_text)) = 0
BEGIN SELECT RAISE(ABORT, '证据片段必须保留原文'); END;

CREATE INDEX idx_source_dates_version
ON source_date_assertions (source_version_id, date_role);
