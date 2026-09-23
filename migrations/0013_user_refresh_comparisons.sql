ALTER TABLE user_refresh_conflicts ADD COLUMN source_version_id TEXT;
ALTER TABLE user_refresh_conflicts ADD COLUMN base_fields_json TEXT
    CHECK (base_fields_json IS NULL OR json_valid(base_fields_json));
ALTER TABLE user_refresh_conflicts ADD COLUMN user_fields_json TEXT
    CHECK (user_fields_json IS NULL OR json_valid(user_fields_json));
ALTER TABLE user_refresh_conflicts ADD COLUMN comparison_json TEXT
    CHECK (comparison_json IS NULL OR json_valid(comparison_json));
ALTER TABLE user_refresh_conflicts ADD COLUMN resolution_json TEXT
    CHECK (resolution_json IS NULL OR json_valid(resolution_json));
