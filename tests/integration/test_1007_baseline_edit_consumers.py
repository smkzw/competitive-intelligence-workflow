"""Source baseline scalar registration and the existing current/save transaction."""

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from ci_workflow.application import portal_consumer_registry as registry
from ci_workflow.application.ctgov_baseline_atoms import extract_ctgov_baseline_atoms
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.b.source_baseline import build_source_baseline_view
from ci_workflow.storage import migrations
from ci_workflow.storage.sqlite import open_database
from tests.integration.reports.test_b_report_portal import _page_json_assignment
from tests.reports.b.test_baseline_active_projection import _data
from tests.unit.test_ctgov_baseline_atoms import _capture, _record

AT = datetime(2026, 10, 7, tzinfo=UTC)


def _candidate(tmp_path):
    root = tmp_path / "baseline-project"
    data = _data()
    contract = create_project_contract(indication=data.indication, reports=["B"],
        outputs=["html"], cutoff="2026-10-07", created_at=AT)
    create_project_workspace(root, contract)
    capture = _capture(_record())
    facts = extract_ctgov_baseline_atoms(capture).facts
    lineage = ingest_research_evidence(project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="B",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"baseline-test").hexdigest(),
        created_at=AT, sources=(capture,), route_attempts=(), facts=facts,
        claims=tuple(ResearchClaim(claim_id="claim-" + f.fact_id, claim_kind="direct_evidence",
            claim_text=f.original_text, fact_ids=(f.fact_id,)) for f in facts))
    view = build_source_baseline_view(facts,
        source_versions={capture.source_id: lineage.source_version_ids[0]},
        fact_versions=lineage.fact_version_by_ref)
    report = ReportBPortalData.model_validate({**data.model_dump(mode="json"),
        "baseline_views": view, "data_cutoff": contract.data_cutoff})
    mapping = {r["row_id"]: r["source_fact_version_id"] for r in view["facts"]
               if r["statistic_form"] in {"MEAN", "STANDARD_DEVIATION"}}
    return root, contract, lineage.evidence_snapshot, report, mapping


def test_scalar_bindings_are_source_proven_idempotent_without_science_rewrite(tmp_path):
    root, _, snapshot, data, mapping = _candidate(tmp_path)
    with open_database(root / "state/project.sqlite") as db:
        before = db.execute("SELECT fact_version_id,content_sha256,scientific_context_json "
                            "FROM fact_versions ORDER BY fact_version_id").fetchall()
    register = registry.register_b_baseline_source_consumers
    bindings = register(root, snapshot, data, mapping, registered_at=AT)
    assert len(bindings) == 4 and all(b.product_id is None for b in bindings)
    assert register(root, snapshot, data, mapping, registered_at=AT) == bindings
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings").fetchone()[0] == 4
        assert db.execute("SELECT fact_version_id,content_sha256,scientific_context_json "
                          "FROM fact_versions ORDER BY fact_version_id").fetchall() == before
    assert read_current_delivery(root) is None


@pytest.mark.parametrize("damage", ["quote", "value", "locator", "population", "group", "version"])
def test_whole_registration_rejects_forged_source_without_partial_bindings(tmp_path, damage):
    root, _, snapshot, data, mapping = _candidate(tmp_path)
    payload = data.model_dump(mode="json")
    row = next(r for r in payload["baseline_views"]["facts"] if r["row_id"] in mapping)
    if damage == "quote":
        row["source_text"] = "unrelated source text"
    elif damage == "value":
        row["value"] = 1000
    elif damage == "locator":
        row["source_locator"]["field_path"] = "$.wrong"
    elif damage == "population":
        row["analysis_population"] = "Different subset"
    elif damage == "group":
        row["group_id"] = "unrelated-group"
    else:
        mapping[row["row_id"]] = "missing-fact-version"
    with pytest.raises(ValueError):
        registry.register_b_baseline_source_consumers(root, snapshot,
            ReportBPortalData.model_validate(payload), mapping, registered_at=AT)
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings").fetchone()[0] == 0


def test_scalar_save_clear_restore_undo_and_failed_save_keep_source_layer(tmp_path):
    root, contract, snapshot, data, mapping = _candidate(tmp_path)
    registry.register_b_baseline_source_consumers(
        root, snapshot, data, mapping, registered_at=AT)
    site = root / "reports/B/source/html"
    render_report_b_site(data, site)
    inputs = root / "inputs/baseline.json"
    inputs.parent.mkdir()
    inputs.write_text(data.model_dump_json())
    service = UserFactEditService(root)
    service.initialize_current_delivery(project_id=contract.project_id,
        report_sites={"B": site}, report_data_paths={"B": inputs},
        fact_version_ids=tuple(mapping.values()), created_at=AT)
    row = next(r for r in data.baseline_views["facts"]
               if r["statistic_form"] == "STANDARD_DEVIATION")
    fact = service._fact_row(mapping[row["row_id"]])
    source_digest = fact["content_sha256"]

    def command(request, edits, operation="save"):
        current = service.read_current_delivery()
        version = service.current_facts()[fact["fact_id"]]["fact_version_id"]
        return UserFactSaveCommand(request_id=request, project_id=contract.project_id,
            expected_revision=current.revision, target=FactTargetIdentity(fact_id=fact["fact_id"],
                fact_version_id=version, entity_id=fact["entity_id"], field_id=fact["field_id"]),
            edits=edits, operation=operation, user_basis="合成事务测试",
            saved_by="test", saved_at=AT)

    original_current = service.read_current_delivery()
    with pytest.raises(UserFactSaveError):
        service.save(command("invalid-negative-spread",
                             FactEdit(raw_value="-1", normalized_value=-1)))
    assert service.read_current_delivery() == original_current
    for request, edits, operation, expected in (
        ("edit-spread", FactEdit(raw_value="14.5", normalized_value=14.5), "save", 14.5),
        ("clear-spread", FactEdit(raw_value=None), "save", None),
        ("restore-spread", FactEdit(raw_value="15", normalized_value=15), "save", 15),
        ("undo-restore", FactEdit(), "undo", None),
    ):
        cmd = command(request, edits, operation)
        saved = service.save(cmd)
        assert saved.rebuilt_reports == ("B",)
        assert service.save(cmd) == saved
        current = service.read_current_delivery()
        text = (root / current.reports[0].site_relative_path / "data/report.js").read_text()
        payload = json.loads(text.split("=", 1)[1].rstrip(" ;\n"))
        site = root / current.reports[0].site_relative_path
        evidence = next(e for e in _page_json_assignment(
            site, "baseline-overview.html", "__EVIDENCE_VIEWS__")
            if e["row"]["row_id"] == row["row_id"])
        result = evidence["row"]
        assert evidence["original_text"] == row["source_text"]
        if expected is not None:
            assert float(evidence["value"]["value"]) == expected
        else:
            assert evidence["value"]["value"] is None
            assert evidence["value"]["state"] == "user_cleared"
        if expected is None:
            assert result["disclosure_state"] == "user_cleared"
            assert payload["user_edits"][row["row_id"]]["current_value"] == "用户清除，待重新核实"
    assert service._fact_row(mapping[row["row_id"]])["content_sha256"] == source_digest


def test_forward_migration_preserves_old_bindings_and_append_only_guards(tmp_path, monkeypatch):
    original = migrations.migration_directory()
    old = tmp_path / "old-migrations"
    old.mkdir()
    for path in original.glob("*.sql"):
        if int(path.name[:4]) <= 16:
            shutil.copyfile(path, old / path.name)
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "migration_directory", lambda: old)
        root, _, snapshot, data, mapping = _candidate(tmp_path)
    version = next(iter(mapping.values()))
    old_record = ("historical-synthetic-binding", version, snapshot.snapshot_id, "C",
                  "observations", "old-row", "{}", "a" * 64, AT.isoformat())
    with open_database(root / "state/project.sqlite") as db:
        db.execute("INSERT INTO source_portal_consumer_bindings VALUES (?,?,?,?,?,?,?,?,?)",
                   old_record)
        facts_before = db.execute("SELECT fact_version_id,content_sha256 FROM fact_versions "
                                  "ORDER BY fact_version_id").fetchall()
    assert [m.version for m in migrations.apply_migrations(root / "state/project.sqlite")] == [17]
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT * FROM source_portal_consumer_bindings").fetchall() == (
            [old_record])
        assert db.execute("SELECT fact_version_id,content_sha256 FROM fact_versions "
                          "ORDER BY fact_version_id").fetchall() == facts_before
        for query in ("UPDATE source_portal_consumer_bindings SET row_id='changed'",
                      "DELETE FROM source_portal_consumer_bindings"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                db.execute(query)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    bindings = registry.register_b_baseline_source_consumers(
        root, snapshot, data, mapping, registered_at=AT)
    assert len(bindings) == 4
