"""Count/N save and clear use the real source registry and atomic current chain."""

import json

import pytest

from ci_workflow.application.portal_consumer_registry import register_b_baseline_source_consumers
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.renderers.portal.report_b import render_report_b_site
from ci_workflow.storage.sqlite import open_database
from tests.integration.reports.test_b_report_portal import _page_json_assignment
from tests.integration.test_1007_baseline_edit_consumers import AT, _candidate


@pytest.mark.parametrize("role", ["participant_count", "denominator"])
def test_counts_and_N_save_clear_restore_undo_with_no_implicit_rate(tmp_path, role):
    root, contract, snapshot, data, _ = _candidate(tmp_path)
    mapping = {r["row_id"]: r["source_fact_version_id"] for r in data.baseline_views["facts"]}
    bindings = register_b_baseline_source_consumers(root, snapshot, data, mapping, registered_at=AT)
    assert len(bindings) == 9
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
               if r["source_value_role"] == role and r["group_id"] == "BG7")
    source = service._fact_row(mapping[row["row_id"]])
    before_digest = source["content_sha256"]

    def command(request, edits, operation="save"):
        current = service.read_current_delivery()
        version = service.current_facts()[source["fact_id"]]["fact_version_id"]
        return UserFactSaveCommand(request_id=request, project_id=contract.project_id,
            expected_revision=current.revision,
            target=FactTargetIdentity(fact_id=source["fact_id"], fact_version_id=version,
                entity_id=source["entity_id"], field_id=source["field_id"]),
            edits=edits, operation=operation, user_basis="源原子事务测试，不派生比例",
            saved_by="test", saved_at=AT)

    before = service.read_current_delivery()
    with pytest.raises(UserFactSaveError):
        service.save(command("bad-count", FactEdit(raw_value="1.5", normalized_value=1.5)))
    assert service.read_current_delivery() == before
    for request, edit, operation, expected in (
        ("set", FactEdit(raw_value="3", normalized_value=3), "save", 3),
        ("clear", FactEdit(raw_value=None), "save", None),
        ("restore", FactEdit(raw_value="0", normalized_value=0), "save", 0),
        ("undo", FactEdit(), "undo", None),
    ):
        cmd = command(request, edit, operation)
        saved = service.save(cmd)
        assert saved.rebuilt_reports == ("B",) and service.save(cmd) == saved
        current = service.read_current_delivery()
        text = (root / current.reports[0].site_relative_path / "data/report.js").read_text()
        payload = json.loads(text.split("=", 1)[1].rstrip(" ;\n"))
        site = root / current.reports[0].site_relative_path
        evidence = next(e for e in _page_json_assignment(
            site, "baseline-overview.html", "__EVIDENCE_VIEWS__"
        ) if e["row"]["row_id"] == row["row_id"])
        value = evidence["value"]["value"]
        assert (None if value is None else float(value)) == expected
        assert evidence["original_text"] == row["source_text"]
        public = service.current_facts()[source["fact_id"]]
        assert public.get("numerator") is None and public.get("denominator") is None
        if expected is None:
            assert evidence["value"]["state"] == "user_cleared"
            assert payload["user_edits"][row["row_id"]]["current_value"] == "用户清除，待重新核实"
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM user_fact_derivations").fetchone()[0] == 0
    assert service._fact_row(mapping[row["row_id"]])["content_sha256"] == before_digest
