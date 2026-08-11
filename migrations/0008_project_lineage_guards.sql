CREATE TRIGGER gate_evaluations_require_project
BEFORE INSERT ON gate_evaluations
WHEN NOT EXISTS (
    SELECT 1 FROM project_contract_versions WHERE project_id = NEW.project_id
)
BEGIN
    SELECT RAISE(ABORT, 'project lineage: gate_evaluations');
END;

CREATE TRIGGER report_snapshots_require_project
BEFORE INSERT ON report_snapshots
WHEN NOT EXISTS (
    SELECT 1 FROM project_contract_versions WHERE project_id = NEW.project_id
)
BEGIN
    SELECT RAISE(ABORT, 'project lineage: report_snapshots');
END;

CREATE TRIGGER correction_proposals_require_project
BEFORE INSERT ON correction_proposals
WHEN NOT EXISTS (
    SELECT 1 FROM project_contract_versions WHERE project_id = NEW.project_id
)
BEGIN
    SELECT RAISE(ABORT, 'project lineage: correction_proposals');
END;
