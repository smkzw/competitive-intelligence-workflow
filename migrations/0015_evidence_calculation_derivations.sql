-- Preserve existing append-only derivations while admitting version-bound
-- calculations. SQLite cannot widen a CHECK constraint in place.
DROP TRIGGER evidence_derivations_no_update;
DROP TRIGGER evidence_derivations_no_delete;

CREATE TABLE evidence_derivations_next (
    derivation_id TEXT PRIMARY KEY,
    derivation_kind TEXT NOT NULL CHECK (derivation_kind IN (
        'source_text', 'normalization', 'translation', 'calculation'
    )),
    input_fragment_ids_json TEXT NOT NULL CHECK (json_valid(input_fragment_ids_json)),
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    output_json TEXT NOT NULL CHECK (json_valid(output_json)),
    created_at TEXT NOT NULL
);

INSERT INTO evidence_derivations_next (
    derivation_id, derivation_kind, input_fragment_ids_json, rule_id,
    rule_version, output_json, created_at
)
SELECT derivation_id, derivation_kind, input_fragment_ids_json, rule_id,
       rule_version, output_json, created_at
FROM evidence_derivations;

DROP TABLE evidence_derivations;
ALTER TABLE evidence_derivations_next RENAME TO evidence_derivations;

CREATE TRIGGER evidence_derivations_no_update
BEFORE UPDATE ON evidence_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_derivations'); END;

CREATE TRIGGER evidence_derivations_no_delete
BEFORE DELETE ON evidence_derivations
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_derivations'); END;
