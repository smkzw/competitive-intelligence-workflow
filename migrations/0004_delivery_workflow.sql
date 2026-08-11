CREATE TABLE format_jobs (
    format_job_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES report_snapshots (snapshot_id),
    output_format TEXT NOT NULL CHECK (output_format IN ('html', 'pdf', 'html-ppt', 'pptx')),
    state TEXT NOT NULL CHECK (state IN (
        'queued', 'generating', 'quality_check', 'passed',
        'delivery_ready', 'blocked', 'superseded'
    )),
    created_at TEXT NOT NULL
);

CREATE TABLE render_queue (
    queue_item_id TEXT PRIMARY KEY,
    format_job_id TEXT NOT NULL REFERENCES format_jobs (format_job_id),
    state TEXT NOT NULL CHECK (state IN (
        'queued', 'generating', 'quality_check', 'passed',
        'delivery_ready', 'blocked', 'superseded'
    )),
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    created_at TEXT NOT NULL
);

CREATE TABLE artifact_records (
    artifact_id TEXT PRIMARY KEY,
    format_job_id TEXT NOT NULL REFERENCES format_jobs (format_job_id),
    artifact_path TEXT NOT NULL CHECK (
        artifact_path GLOB 'reports/[ABC]/v[0-9]*/*'
        AND substr(artifact_path, 1, 1) <> '/'
        AND instr(artifact_path, '..') = 0
        AND instr(artifact_path, '\\') = 0
    ),
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    mtime REAL NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'queued', 'generating', 'quality_check', 'passed',
        'delivery_ready', 'blocked', 'superseded'
    )),
    supersedes_artifact_id TEXT REFERENCES artifact_records (artifact_id),
    created_at TEXT NOT NULL
);

CREATE TABLE download_requests (
    download_request_id TEXT PRIMARY KEY,
    source_id TEXT,
    state TEXT NOT NULL CHECK (state IN (
        'awaiting_user', 'file_detected', 'matched', 'accepted',
        'needs_re_download', 'not_required'
    )),
    expected_relative_path TEXT CHECK (
        expected_relative_path IS NULL OR (
            substr(expected_relative_path, 1, 1) <> '/'
            AND instr(expected_relative_path, '..') = 0
            AND instr(expected_relative_path, '\\') = 0
        )
    ),
    created_at TEXT NOT NULL
);
