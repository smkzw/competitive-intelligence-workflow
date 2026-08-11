CREATE TRIGGER schema_migrations_no_update BEFORE UPDATE ON schema_migrations
BEGIN SELECT RAISE(ABORT, 'append-only: schema_migrations'); END;
CREATE TRIGGER schema_migrations_no_delete BEFORE DELETE ON schema_migrations
BEGIN SELECT RAISE(ABORT, 'append-only: schema_migrations'); END;

CREATE TRIGGER project_contract_versions_no_update BEFORE UPDATE ON project_contract_versions
BEGIN SELECT RAISE(ABORT, 'append-only: project_contract_versions'); END;
CREATE TRIGGER project_contract_versions_no_delete BEFORE DELETE ON project_contract_versions
BEGIN SELECT RAISE(ABORT, 'append-only: project_contract_versions'); END;

CREATE TRIGGER source_versions_no_update BEFORE UPDATE ON source_versions
BEGIN SELECT RAISE(ABORT, 'append-only: source_versions'); END;
CREATE TRIGGER source_versions_no_delete BEFORE DELETE ON source_versions
BEGIN SELECT RAISE(ABORT, 'append-only: source_versions'); END;

CREATE TRIGGER source_eligibility_evaluations_no_update BEFORE UPDATE ON source_eligibility_evaluations
BEGIN SELECT RAISE(ABORT, 'append-only: source_eligibility_evaluations'); END;
CREATE TRIGGER source_eligibility_evaluations_no_delete BEFORE DELETE ON source_eligibility_evaluations
BEGIN SELECT RAISE(ABORT, 'append-only: source_eligibility_evaluations'); END;

CREATE TRIGGER refresh_candidates_no_update BEFORE UPDATE ON refresh_candidates
BEGIN SELECT RAISE(ABORT, 'append-only: refresh_candidates'); END;
CREATE TRIGGER refresh_candidates_no_delete BEFORE DELETE ON refresh_candidates
BEGIN SELECT RAISE(ABORT, 'append-only: refresh_candidates'); END;

CREATE TRIGGER evidence_fragments_no_update BEFORE UPDATE ON evidence_fragments
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_fragments'); END;
CREATE TRIGGER evidence_fragments_no_delete BEFORE DELETE ON evidence_fragments
BEGIN SELECT RAISE(ABORT, 'append-only: evidence_fragments'); END;

CREATE TRIGGER fact_versions_no_update BEFORE UPDATE ON fact_versions
BEGIN SELECT RAISE(ABORT, 'append-only: fact_versions'); END;
CREATE TRIGGER fact_versions_no_delete BEFORE DELETE ON fact_versions
BEGIN SELECT RAISE(ABORT, 'append-only: fact_versions'); END;

CREATE TRIGGER fact_evidence_no_update BEFORE UPDATE ON fact_evidence
BEGIN SELECT RAISE(ABORT, 'append-only: fact_evidence'); END;
CREATE TRIGGER fact_evidence_no_delete BEFORE DELETE ON fact_evidence
BEGIN SELECT RAISE(ABORT, 'append-only: fact_evidence'); END;

CREATE TRIGGER claim_versions_no_update BEFORE UPDATE ON claim_versions
BEGIN SELECT RAISE(ABORT, 'append-only: claim_versions'); END;
CREATE TRIGGER claim_versions_no_delete BEFORE DELETE ON claim_versions
BEGIN SELECT RAISE(ABORT, 'append-only: claim_versions'); END;

CREATE TRIGGER claim_facts_no_update BEFORE UPDATE ON claim_facts
BEGIN SELECT RAISE(ABORT, 'append-only: claim_facts'); END;
CREATE TRIGGER claim_facts_no_delete BEFORE DELETE ON claim_facts
BEGIN SELECT RAISE(ABORT, 'append-only: claim_facts'); END;

CREATE TRIGGER conflict_sets_no_update BEFORE UPDATE ON conflict_sets
BEGIN SELECT RAISE(ABORT, 'append-only: conflict_sets'); END;
CREATE TRIGGER conflict_sets_no_delete BEFORE DELETE ON conflict_sets
BEGIN SELECT RAISE(ABORT, 'append-only: conflict_sets'); END;

CREATE TRIGGER gate_evaluations_no_update BEFORE UPDATE ON gate_evaluations
BEGIN SELECT RAISE(ABORT, 'append-only: gate_evaluations'); END;
CREATE TRIGGER gate_evaluations_no_delete BEFORE DELETE ON gate_evaluations
BEGIN SELECT RAISE(ABORT, 'append-only: gate_evaluations'); END;

CREATE TRIGGER report_snapshots_no_update BEFORE UPDATE ON report_snapshots
BEGIN SELECT RAISE(ABORT, 'append-only: report_snapshots'); END;
CREATE TRIGGER report_snapshots_no_delete BEFORE DELETE ON report_snapshots
BEGIN SELECT RAISE(ABORT, 'append-only: report_snapshots'); END;

CREATE TRIGGER coverage_sets_no_update BEFORE UPDATE ON coverage_sets
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_sets'); END;
CREATE TRIGGER coverage_sets_no_delete BEFORE DELETE ON coverage_sets
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_sets'); END;

CREATE TRIGGER coverage_projections_no_update BEFORE UPDATE ON coverage_projections
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_projections'); END;
CREATE TRIGGER coverage_projections_no_delete BEFORE DELETE ON coverage_projections
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_projections'); END;

CREATE TRIGGER artifact_records_no_update BEFORE UPDATE ON artifact_records
BEGIN SELECT RAISE(ABORT, 'append-only: artifact_records'); END;
CREATE TRIGGER artifact_records_no_delete BEFORE DELETE ON artifact_records
BEGIN SELECT RAISE(ABORT, 'append-only: artifact_records'); END;

CREATE TRIGGER idempotency_keys_no_update BEFORE UPDATE ON idempotency_keys
BEGIN SELECT RAISE(ABORT, 'append-only: idempotency_keys'); END;
CREATE TRIGGER idempotency_keys_no_delete BEFORE DELETE ON idempotency_keys
BEGIN SELECT RAISE(ABORT, 'append-only: idempotency_keys'); END;

CREATE INDEX idx_source_versions_source ON source_versions (source_id, acquired_at);
CREATE INDEX idx_fact_versions_fact ON fact_versions (fact_id, created_at);
CREATE INDEX idx_claim_versions_claim ON claim_versions (claim_id, created_at);
CREATE INDEX idx_report_snapshots_report ON report_snapshots (project_id, report_kind, report_version);
CREATE INDEX idx_artifact_records_job ON artifact_records (format_job_id, created_at);
