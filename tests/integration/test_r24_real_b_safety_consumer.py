"""B may share a verified original safety count, not invent a new source fact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.portal_consumer_registry import (
    PortalConsumerRegistrationError,
    project_b_safety_source_views,
    register_b_shared_source_consumers,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.storage.snapshot_store import LockedSnapshot
from ci_workflow.storage.sqlite import open_database
from tools.materialize_ctgov_a_candidate import materialize


def test_two_real_safety_counts_share_exact_a_b_source_and_reject_drift(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    cas = repo / ".artifacts/r24-pnh-current-ctgov-20260926"
    payload = cas / "report-a-ctgov-20260926-sponsor-separate-v5.json"
    sidecar = cas / "report-a-ctgov-20260926-sponsor-separate-v5.derivation.json"
    previous = repo / ".artifacts/r24-pnh-refresh-slice-20260926"
    if not all(path.exists() for path in (cas, payload, sidecar, previous)):
        pytest.skip("fixed 2026-09-26 CT.gov source corpus is not in this checkout")
    assert sha256(payload.read_bytes()).hexdigest() == (
        "3ae2a238733eb06269c2fd58c171e4f6a1a3b8c97bc3a7069beec88ca08c952a"
    )
    assert sha256(sidecar.read_bytes()).hexdigest() == (
        "0ef8a7275bab87eccc4e0a296744b8ae624a0771ca1d082300a1fa081b78d655"
    )
    root = tmp_path / "safety-a-b-candidate"
    create_project_workspace(root, verify_project_workspace(previous).contract)
    bound_input = root / "inputs/a-bound.json"
    at = datetime(2026, 9, 26, 10, 5, tzinfo=UTC)
    receipt = materialize(
        project_root=root, cas_dir=cas, payload_path=payload, sidecar_path=sidecar,
        observed_at=at, selected_trials={"nct02264639", "nct03829449"},
        bound_report_output=bound_input,
    )
    a_report = ReportAPortalData.model_validate_json(bound_input.read_bytes())
    versions = {
        item["row_ref"]: item["fact_version_id"] for item in receipt["fact_bindings"]
    }
    row_ids = set(receipt["registered_a_safety_consumers"])
    assert row_ids == {"safe-7727c2ce1c1803f54bb0", "safe-9fe1ea2f8b52dd3ec294"}
    rows = [row for row in a_report.safety if row.row_id in row_ids]
    manifest_path = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"],
        byte_size=manifest_path.stat().st_size,
    )
    safety_versions = {
        ref: version_id for ref, version_id in versions.items()
        if ref.startswith("safety:") and not ref.endswith(":denominator")
    }
    source_views = project_b_safety_source_views(
        root, snapshot, a_report, safety_versions,
    )
    assert len(source_views) == 92
    assert sum(view["group_assignment_state"] == "unknown" for view in source_views) == 90
    b_report = ReportBPortalData.model_validate({
        **a_report.model_dump(mode="json"),
        "safety_views": {"coverage_mode": "partial", "facts": source_views},
    })
    selected = {f"safety:{row_id}": versions[f"safety:{row_id}"] for row_id in row_ids}
    bindings = register_b_shared_source_consumers(
        root, snapshot, b_report, selected, registered_at=at,
    )
    assert {binding.row_id for binding in bindings} == row_ids
    assert {binding.statistical_form for binding in bindings} == {"count"}
    assert {binding.measure_object for binding in bindings} == {"participants"}
    assert register_b_shared_source_consumers(
        root, snapshot, b_report, selected, registered_at=at,
    ) == bindings
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings "
            "WHERE report='B' AND collection='safety'"
        ).fetchone()[0] == 2

    b_input = root / "inputs/b-partial-safety.json"
    b_input.write_text(b_report.model_dump_json(), encoding="utf-8")
    sites = {
        "A": root / "reports/A/development/html",
        "B": root / "reports/B/development/html",
    }
    render_report_a_site(a_report, sites["A"])
    render_report_b_site(b_report, sites["B"])
    unknown = next(
        row for row in a_report.safety
        if row.trial_id == "nct02264639" and row.group_assignment_state == "unknown"
    )
    initial_b_html = (sites["B"] / "safety.html").read_text(encoding="utf-8")
    initial_groups, _ = json.JSONDecoder().raw_decode(
        initial_b_html.split("window.__CHART_GROUPS__ = ", 1)[1].lstrip()
    )
    unknown_chart_row = next(
        row for group in initial_groups for row in group.get("rows", [])
        if row.get("row_id") == unknown.row_id
    )
    assert unknown_chart_row["value"] == unknown.value
    assert unknown_chart_row["group_assignment_state"] == "unknown"
    assert unknown_chart_row["renderable"] is False
    assert unknown_chart_row["product_zh"] == "结果组别产品归属待核"
    assert unknown_chart_row["disclosure_state"] in {"reported_value", "reported_zero"}
    initial_views, _ = json.JSONDecoder().raw_decode(
        initial_b_html.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].lstrip()
    )
    unknown_view = next(
        view for view in initial_views if view["row"]["row_id"] == unknown.row_id
    )
    located_ids = {view["row"]["row_id"] for view in initial_views
                   if view["source_trace_state"] == "located"}
    assert {view["row_id"] for view in source_views} <= located_ids
    assert len({view["row_id"] for view in source_views}) == 92
    assert float(unknown_view["value"]["value"]) == unknown.value
    assert unknown_view["product_zh"] == "结果组别产品归属待核"
    assert unknown_view["row"]["product_id"] is None
    assert unknown_view["source_trace_state"] == "located"
    assert unknown_view["original_text"] == unknown.source_text
    service = UserFactEditService(root)
    contract = verify_project_workspace(root).contract
    service.initialize_current_delivery(
        project_id=contract.project_id,
        report_sites=sites,
        report_data_paths={"A": bound_input, "B": b_input},
        fact_version_ids=tuple(
            versions[f"efficacy:{row_id}"]
            for row_id in receipt["registered_a_efficacy_consumers"]
        ) + tuple(selected.values()),
        created_at=at,
    )
    zero_row_id = "safe-7727c2ce1c1803f54bb0"
    zero_version = versions[f"safety:{zero_row_id}"]
    source = service._fact_row(zero_version)
    target = FactTargetIdentity(
        fact_id=source["fact_id"], fact_version_id=zero_version,
        entity_id=source["entity_id"], field_id=source["field_id"],
    )
    old_current = service.read_current_delivery()
    with pytest.raises(UserFactSaveError, match="分母矛盾"):
        service.save(UserFactSaveCommand(
            request_id="safety-over-denominator-development", project_id=contract.project_id,
            expected_revision=0, target=target,
            edits=FactEdit(raw_value="16", normalized_value=16),
            user_basis="开发负例，不是医学修订", saved_by="test", saved_at=at,
        ))
    assert service.read_current_delivery() == old_current
    saved = service.save(UserFactSaveCommand(
        request_id="safety-zero-to-one-development", project_id=contract.project_id,
        expected_revision=0, target=target,
        edits=FactEdit(raw_value="1", normalized_value=1),
        user_basis="开发演练假设值，非医学订正", saved_by="test", saved_at=at,
    ))
    assert saved.rebuilt_reports == ("A", "B")
    current = service.read_current_delivery()
    assert current.revision == 1
    for delivery in current.reports:
        site = root / delivery.site_relative_path
        payload = json.loads(
            (site / "data/report.js").read_text(encoding="utf-8")
            .split("=", 1)[1].rstrip(" ;\n")
        )
        row = next(item for item in payload["safety"] if item["row_id"] == zero_row_id)
        assert (row["value"], row["numerator"], row["denominator"]) == (1, 1, 15)
        assert row["source_text"] == "0"
        assert any(item["row_id"] == zero_row_id for item in json.loads(
            (site / "data/consumer-receipt.json").read_text(encoding="utf-8")
        )["consumers"])
        if delivery.report == "B":
            search_js = (site / "data/search-index.js").read_text(encoding="utf-8")
            search = json.loads(search_js.split("=", 1)[1].rstrip(" ;\n"))
            indexed = next(item for item in search if item.get("row_id") == zero_row_id)
            assert indexed["slug"] == "safety"
            assert zero_row_id in indexed["keywords"]
            assert "1" in indexed["keywords"]
            html = (site / "safety.html").read_text(encoding="utf-8")
            embedded = html.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0]
            view = next(
                item for item in json.loads(embedded)
                if item["row"]["row_id"] == zero_row_id
            )
            assert view["source_trace_state"] == "located"
            assert view["original_text"] == "0"
            assert view["value"]["value"] == "1"
            all_views = json.loads(embedded)
            after_unknown = next(
                item for item in all_views if item["row"]["row_id"] == unknown.row_id
            )
            assert after_unknown["source_trace_state"] == "located"
            assert after_unknown["row"]["product_id"] is None
            assert after_unknown["original_text"] == unknown.source_text
            assert view["explanation"]["value"] == (
                "当前数值由用户修订，尚未独立复核；原始来源值和定位仍可查。"
            )
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (source["primary_fragment_id"],),
        ).fetchone() == ("0",)
        assert database.execute(
            "SELECT COUNT(DISTINCT source_fact_version_id) "
            "FROM source_portal_consumer_bindings WHERE collection='safety'"
        ).fetchone()[0] == 2

    selected_source_view = next(
        item for item in source_views if item["row_id"] == rows[0].row_id
    )
    for change in (
        {"denominator": 16},
        {"source_text": "missing"},
        {"term": "different clinical event"},
        {"source_locator": {
            **selected_source_view["source_locator"], "field_path": "$.wrong",
        }},
    ):
        altered = b_report.model_dump(mode="json")
        selected_view = next(
            item for item in altered["safety_views"]["facts"]
            if item["row_id"] == rows[0].row_id
        )
        selected_view.update(change)
        with pytest.raises(PortalConsumerRegistrationError):
            register_b_shared_source_consumers(
                root, snapshot, ReportBPortalData.model_validate(altered),
                selected, registered_at=at,
            )
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings "
            "WHERE report='B' AND collection='safety'"
        ).fetchone()[0] == 2
