"""A source atom may acquire a portal consumer without changing its science version."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.portal_consumer_registry import (
    PortalConsumerRegistrationError,
    SourceRowContext,
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    bind_ctgov_outcome_to_a_row,
    extract_ctgov_atomic_results,
)
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFact,
    validate_active_fact_binding,
)
from ci_workflow.renderers.portal.report_a import (
    EfficacyRow,
    ReportAPortalData,
    render_report_a_site,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    active_fact_binding_for_b,
    render_report_b_site,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import _project
from tests.integration.test_w07_ctgov_capture_bridge import _reported_count_source
from tools.materialize_ctgov_a_candidate import materialize

CONTENT = Path("fixtures/positive/a-atopic-dermatitis/research-content.json")
AT = datetime(2026, 9, 26, tzinfo=UTC)


def _candidate(
    tmp_path: Path, *, source_unit: str = "Participants",
) -> tuple[Path, LockedSnapshot, ReportAPortalData, str]:
    root = _project(tmp_path)
    source = _reported_count_source(root, unit=source_unit)
    atom = extract_ctgov_atomic_results(source)[0][0]
    baseline = ReportAPortalData.model_validate(
        json.loads(CONTENT.read_text(encoding="utf-8"))["report_data"]
    )
    original = next(row for row in baseline.efficacy if row.trial_id == "nct02277743")
    requested = EfficacyRow.model_validate({
        **original.model_dump(mode="json"),
        "endpoint": atom.endpoint,
        "timepoint": atom.timepoint,
        "arm": atom.group_title,
        "arm_detail": atom.group_title,
        "group_id": atom.group_id,
        "group_assignment_state": "declared",
        "value": 30,
        "unit": source_unit,
        "numerator": None,
        "denominator": 35 if source_unit != "Participants" else None,
        "source_field_path": None,
        "source_version_id": None,
        "source_text": None,
    })
    bound, facts = bind_ctgov_outcome_to_a_row(source, atom, requested)
    contract = verify_project_workspace(root).contract
    report = ReportAPortalData.model_validate({
        **baseline.model_dump(mode="json"),
        "data_cutoff": contract.data_cutoff.isoformat(),
        "trials": [
            {
                **trial.model_dump(mode="json"),
                "product_links": [{
                    "product_id": original.product_id,
                    "arm_role": "experimental",
                    "arm_labels": [atom.group_title.upper()],
                }],
            } if trial.id == original.trial_id else trial.model_dump(mode="json")
            for trial in baseline.trials
        ],
        "efficacy": [
            bound.model_dump(mode="json") if row.row_id == original.row_id
            else row.model_dump(mode="json") for row in baseline.efficacy
        ],
    })
    claim = ResearchClaim(
        claim_id="source-consumer-test-claim", claim_text="登记报告直接数值30",
        claim_kind="direct_evidence", fact_ids=tuple(fact.fact_id for fact in facts),
    )
    lineage = ingest_research_evidence(
        project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="A",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"source-consumer-test").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(),
        facts=facts, claims=(claim,),
    )
    return root, lineage.evidence_snapshot, report, lineage.fact_version_by_ref[
        f"efficacy:{bound.row_id}"
    ]


def _b_direct_source_view(
    report: ReportAPortalData, locator: str, *, source_text: str,
) -> ReportBPortalData:
    row = next(item for item in report.efficacy if item.source_version_id)
    return ReportBPortalData.model_validate({
        **report.model_dump(mode="json"),
        "efficacy_views": {"facts": [{
            "row_id": row.row_id,
            "product_id": row.product_id,
            "trial_id": row.trial_id,
            "original_definition": row.endpoint,
            "arm_id": row.group_id,
            "arm_label": row.arm,
            "analysis_population": row.population,
            "value": row.value,
            "unit": row.unit,
            "numerator": row.numerator,
            "denominator": row.denominator,
            "source_version_id": row.source_version_id,
            "source_locator": json.loads(locator),
            "source_text": source_text,
            "disclosure_state": "reported_value",
        }]},
    })


def test_captured_synthetic_direct_count_has_a_and_b_consumers(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    a_binding = register_a_source_consumers(
        root, snapshot, a_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )[0]
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
        before = database.execute(
            "SELECT content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?", (version_id,),
        ).fetchone()
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    b_binding = register_b_shared_source_consumers(
        root, snapshot, b_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )[0]
    assert (a_binding.statistical_form, b_binding.statistical_form) == ("count", "count")
    assert (a_binding.measure_object, b_binding.measure_object) == (
        "participants", "participants",
    )
    assert b_binding == active_fact_binding_for_b(b_report, "efficacy", row_id)
    assert register_b_shared_source_consumers(
        root, snapshot, b_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    ) == (b_binding,)
    public = UserFactEditService(root)._public_fact(UserFactEditService(root)._fact_row(version_id))
    assert {item["report"] for item in public["consumer_bindings"]} == {"A", "B"}
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?", (version_id,),
        ).fetchone() == before


def test_reported_measure_is_shared_as_estimate_not_a_crude_rate(tmp_path: Path) -> None:
    root, snapshot, a_report, version_id = _candidate(
        tmp_path, source_unit="Percentage of responders",
    )
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    a_binding = register_a_source_consumers(
        root, snapshot, a_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )[0]
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    b_binding = register_b_shared_source_consumers(
        root, snapshot, b_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )[0]
    assert (a_binding.statistical_form, a_binding.measure_object) == ("estimate", "estimate")
    assert (b_binding.statistical_form, b_binding.measure_object) == ("estimate", "estimate")
    assert b_report.efficacy_views["facts"][0]["numerator"] is None


def test_b_shared_source_registration_rejects_wrong_view_without_partial_write(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    register_a_source_consumers(
        root, snapshot, a_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    for changed in (
        {"source_locator": {**json.loads(locator), "field_path": "$.wrong.value"}},
        {"source_text": "30 from an unrelated source"},
        {"analysis_population_zh": "another analysis set"},
        {"numerator": 31},
    ):
        payload = b_report.model_dump(mode="json")
        payload["efficacy_views"]["facts"][0].update(changed)
        with pytest.raises(PortalConsumerRegistrationError):
            register_b_shared_source_consumers(
                root, snapshot, ReportBPortalData.model_validate(payload),
                {f"efficacy:{row_id}": version_id}, registered_at=AT,
            )
    wrong_denominator = b_report.model_dump(mode="json")
    domain = next(item for item in wrong_denominator["efficacy"] if item["row_id"] == row_id)
    domain["denominator"] = 36
    wrong_denominator["efficacy_views"]["facts"][0]["denominator"] = 36
    with pytest.raises(PortalConsumerRegistrationError, match="来源|科学"):
        register_b_shared_source_consumers(
            root, snapshot, ReportBPortalData.model_validate(wrong_denominator),
            {f"efficacy:{row_id}": version_id}, registered_at=AT,
        )
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings WHERE report='B'"
        ).fetchone()[0] == 0


def test_captured_synthetic_count_save_fans_out_to_a_and_b_atomically(tmp_path: Path) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    register_a_source_consumers(
        root, snapshot, a_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    register_b_shared_source_consumers(
        root, snapshot, b_report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    sites = {"A": root / "reports/A/v1/html", "B": root / "reports/B/v1/html"}
    render_report_a_site(a_report, sites["A"])
    render_report_b_site(b_report, sites["B"])
    b_html = (sites["B"] / "efficacy.html").read_text(encoding="utf-8")
    embedded = b_html.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0]
    evidence = next(item for item in json.loads(embedded) if item["row"]["row_id"] == row_id)
    assert evidence["original_text"] == quote
    inputs = {"A": root / "inputs/a-source.json", "B": root / "inputs/b-source.json"}
    inputs["A"].parent.mkdir(parents=True)
    inputs["A"].write_text(a_report.model_dump_json(), encoding="utf-8")
    inputs["B"].write_text(b_report.model_dump_json(), encoding="utf-8")
    service = UserFactEditService(root)
    contract = verify_project_workspace(root).contract
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites=sites, report_data_paths=inputs,
        fact_version_ids=(version_id,), created_at=AT,
    )
    source = service._fact_row(version_id)
    target = FactTargetIdentity(
        fact_id=source["fact_id"], fact_version_id=version_id,
        entity_id=source["entity_id"], field_id=source["field_id"],
    )
    old_current = service.read_current_delivery()
    with pytest.raises(UserFactSaveError, match="数值文本和规范值"):
        service.save(UserFactSaveCommand(
            request_id="source-ab-invalid", project_id=contract.project_id,
            expected_revision=0, target=target, edits=FactEdit(raw_value="25"),
            user_basis="开发候选负例", saved_by="test", saved_at=AT,
        ))
    assert service.read_current_delivery() == old_current
    saved = service.save(UserFactSaveCommand(
        request_id="source-ab-save", project_id=contract.project_id,
        expected_revision=0, target=target,
        edits=FactEdit(raw_value="25", normalized_value=25),
        user_basis="开发候选演练，不是医学修订", saved_by="test", saved_at=AT,
    ))
    assert saved.rebuilt_reports == ("A", "B")
    current = service.read_current_delivery()
    assert current.revision == 1
    for report in current.reports:
        content = (root / report.site_relative_path / "data/report.js").read_text()
        payload = json.loads(content.split("=", 1)[1].rstrip(" ;\n"))
        row = next(item for item in payload["efficacy"] if item["row_id"] == row_id)
        assert (row["value"], row["numerator"], row["denominator"]) == (25, 25, 35)
        assert "25" in (root / report.site_relative_path / "data/search-index.js").read_text()
        assert any(item["row_id"] == row_id for item in json.loads(
            (root / report.site_relative_path / "data/consumer-receipt.json").read_text()
        )["consumers"])


def test_fixed_real_ctgov_pnh_atom_rebuilds_a_and_b_from_one_user_save(
    tmp_path: Path,
) -> None:
    """Local fixed-CAS probe; an absent raw corpus is SKIP, not a scientific PASS."""
    repo = Path(__file__).resolve().parents[2]
    cas = repo / ".artifacts/source-cas/ctgov-live-20260906"
    payload = repo / ".artifacts/r24-pnh-candidate-20260926/report-a-r24-14-final.json"
    sidecar = repo / ".artifacts/r24-pnh-candidate-20260926/report-a-r24-14-final.derivation.json"
    previous = repo / ".artifacts/r24-pnh-auto-binding-slice-20260926"
    if not all(path.exists() for path in (cas, payload, sidecar, previous)):
        pytest.skip("fixed 2026-09-06 CT.gov CAS not present in this checkout")
    assert sha256(payload.read_bytes()).hexdigest() == (
        "2cd32ccbb17ab044360a2ec10c7b41071e44f569c3b853421f95c24040d52d74"
    )
    assert sha256(sidecar.read_bytes()).hexdigest() == (
        "2cbba015597af4cefbd1fb8104fc7c00e33563fdf515350d4e9046b955d0ad09"
    )
    root = tmp_path / "real-pnh-a-b-development"
    contract = verify_project_workspace(previous).contract
    create_project_workspace(root, contract)
    a_input = root / "inputs/a-bound.json"
    receipt = materialize(
        project_root=root, cas_dir=cas, payload_path=payload, sidecar_path=sidecar,
        observed_at=datetime(2026, 9, 26, 5, 54, 30, tzinfo=UTC),
        selected_trials={"nct04820530"}, bound_report_output=a_input,
    )
    manifest = root / receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=receipt["snapshot_id"], kind="evidence", report=None,
        sha256=receipt["snapshot_sha256"],
        relative_path=receipt["snapshot_relative_path"], byte_size=manifest.stat().st_size,
    )
    a_report = ReportAPortalData.model_validate_json(a_input.read_bytes())
    source_row = next(row for row in a_report.efficacy if row.row_id == "eff-1")
    assert (source_row.value, source_row.source_text) == (92.2, "92.2")
    versions = {item["row_ref"]: item["fact_version_id"] for item in receipt["fact_bindings"]}
    version_id = versions["efficacy:eff-1"]
    with open_database(root / "state/project.sqlite") as database:
        locator, quote = database.execute(
            "SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version_id,),
        ).fetchone()
    b_report = _b_direct_source_view(a_report, locator, source_text=quote)
    b_binding = register_b_shared_source_consumers(
        root, snapshot, b_report, {"efficacy:eff-1": version_id}, registered_at=AT,
    )[0]
    assert (b_binding.statistical_form, b_binding.measure_object) == ("estimate", "estimate")
    b_input = root / "inputs/b-direct-source-development.json"
    b_input.write_text(b_report.model_dump_json(), encoding="utf-8")
    sites = {"A": root / "reports/A/development/html", "B": root / "reports/B/development/html"}
    render_report_a_site(a_report, sites["A"])
    render_report_b_site(b_report, sites["B"])
    service = UserFactEditService(root)
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites=sites,
        report_data_paths={"A": a_input, "B": b_input},
        fact_version_ids=tuple(
            versions[f"efficacy:{row_id}"]
            for row_id in receipt["registered_a_efficacy_consumers"]
        ),
        created_at=AT,
    )
    source = service._fact_row(version_id)
    saved = service.save(UserFactSaveCommand(
        request_id="real-cas-pnh-ab-development-only", project_id=contract.project_id,
        expected_revision=0,
        target=FactTargetIdentity(
            fact_id=source["fact_id"], fact_version_id=version_id,
            entity_id=source["entity_id"], field_id=source["field_id"],
        ),
        edits=FactEdit(raw_value="90.1", normalized_value=90.1),
        user_basis="开发演练假设值，非医学订正", saved_by="test", saved_at=AT,
    ))
    assert saved.rebuilt_reports == ("A", "B")
    for item in service.read_current_delivery().reports:
        site = root / item.site_relative_path
        projection = json.loads(
            (site / "data/report.js").read_text(encoding="utf-8").split("=", 1)[1].rstrip(" ;\n")
        )
        row = next(entry for entry in projection["efficacy"] if entry["row_id"] == "eff-1")
        assert row["value"] == 90.1 and row["source_text"] == "92.2"
        if item.report == "B":
            evidence = (site / "efficacy.html").read_text(encoding="utf-8")
            embedded = evidence.split("window.__EVIDENCE_VIEWS__ = ", 1)[1].split(";\n", 1)[0]
            view = next(
                entry for entry in json.loads(embedded) if entry["row"]["row_id"] == "eff-1"
            )
            assert view["value"]["value"] == "90.1"
            assert view["original_text"] == "92.2"
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (source["primary_fragment_id"],),
        ).fetchone() == ("92.2",)


def test_real_ingested_source_fact_gets_external_a_binding_without_science_rewrite(
    tmp_path: Path,
) -> None:
    root, snapshot, report, version_id = _candidate(tmp_path)
    with open_database(root / "state/project.sqlite") as database:
        before = database.execute(
            "SELECT content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?", (version_id,),
        ).fetchone()
    assert before is not None and '"consumer_bindings"' not in before[1]
    row_id = next(row.row_id for row in report.efficacy if row.source_version_id)
    binding = register_a_source_consumers(
        root, snapshot, report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )[0]
    assert binding.report == "A" and binding.row_id == row_id
    assert (binding.statistical_form, binding.measure_object) == ("count", "participants")
    assert register_a_source_consumers(
        root, snapshot, report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    ) == (binding,)
    with open_database(root / "state/project.sqlite") as database:
        after = database.execute(
            "SELECT content_sha256,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?", (version_id,),
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "UPDATE source_portal_consumer_bindings SET row_id='other' "
                "WHERE source_fact_version_id=?", (version_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "DELETE FROM source_portal_consumer_bindings WHERE source_fact_version_id=?",
                (version_id,),
            )
    assert after == before
    public = UserFactEditService(root)._public_fact(
        UserFactEditService(root)._fact_row(version_id)
    )
    assert public["consumer_bindings"] == [binding.model_dump(mode="json")]
    assert public["source_locator"] != binding.source_pointer  # full JSON locator retained
    assert validate_active_fact_binding(ActiveFact.model_validate(public), binding, binding)


def test_external_a_binding_rejects_mismatched_row_and_keeps_registry_empty(
    tmp_path: Path,
) -> None:
    root, snapshot, report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in report.efficacy if row.source_version_id)
    with pytest.raises(PortalConsumerRegistrationError, match="复制"):
        register_a_source_consumers(
            root, snapshot, report,
            {f"efficacy:{row_id}": version_id, "efficacy:second-row": version_id},
            registered_at=AT,
        )
    for changed in (
        {"value": 31},
        {"source_field_path": "$.resultsSection.unrelated.value"},
        {"group_assignment_state": "unknown"},
    ):
        altered = report.model_dump(mode="json")
        row = next(item for item in altered["efficacy"] if item["row_id"] == row_id)
        row.update(changed)
        modified = ReportAPortalData.model_validate(altered)
        with pytest.raises(PortalConsumerRegistrationError):
            register_a_source_consumers(
                root, snapshot, modified,
                {f"efficacy:{row_id}": version_id}, registered_at=AT,
            )
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings"
        ).fetchone()[0] == 0


def test_translated_a_row_requires_exact_original_context(tmp_path: Path) -> None:
    root, snapshot, report, version_id = _candidate(tmp_path)
    row = next(item for item in report.efficacy if item.source_version_id)
    translated = EfficacyRow.model_validate({
        **row.model_dump(mode="json"),
        "endpoint": "中文显示终点",
        "timepoint": "第26周", "arm": "中文治疗组",
    })
    report = ReportAPortalData.model_validate({
        **report.model_dump(mode="json"),
        "efficacy": [
            translated.model_dump(mode="json") if item.row_id == row.row_id
            else item.model_dump(mode="json") for item in report.efficacy
        ],
    })
    row_versions = {f"efficacy:{row.row_id}": version_id}
    with pytest.raises(PortalConsumerRegistrationError, match="原文对照"):
        register_a_source_consumers(
            root, snapshot, report, row_versions, registered_at=AT,
        )
    original = SourceRowContext(
        endpoint=row.endpoint, timepoint=row.timepoint,
        group_title=row.arm, value_path=row.source_field_path or "",
    )
    with pytest.raises(PortalConsumerRegistrationError, match="原文对照"):
        register_a_source_consumers(
            root, snapshot, report, row_versions, registered_at=AT,
            source_row_contexts={f"efficacy:{row.row_id}": SourceRowContext(
                endpoint=original.endpoint, timepoint="另一访视",
                group_title=original.group_title, value_path=original.value_path,
            )},
        )
    bound = register_a_source_consumers(
        root, snapshot, report, row_versions, registered_at=AT,
        source_row_contexts={f"efficacy:{row.row_id}": original},
    )
    assert bound[0].row_id == row.row_id


def test_direct_source_count_edit_updates_a_value_and_count_without_changing_source(
    tmp_path: Path,
) -> None:
    root, snapshot, report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in report.efficacy if row.source_version_id)
    register_a_source_consumers(
        root, snapshot, report, {f"efficacy:{row_id}": version_id}, registered_at=AT,
    )
    site = root / "reports/A/v1/html"
    render_report_a_site(report, site)
    builder_input = root / "inputs/a-source-data.json"
    builder_input.parent.mkdir(parents=True)
    builder_input.write_text(report.model_dump_json(), encoding="utf-8")
    service = UserFactEditService(root)
    contract = verify_project_workspace(root).contract
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites={"A": site},
        report_data_paths={"A": builder_input}, fact_version_ids=(version_id,),
        created_at=AT,
    )
    source = service._fact_row(version_id)
    target = FactTargetIdentity(
        fact_id=source["fact_id"], fact_version_id=version_id,
        entity_id=source["entity_id"], field_id=source["field_id"],
    )
    rejected = UserFactSaveCommand(
        request_id="source-count-incomplete", project_id=contract.project_id,
        expected_revision=0, target=target, edits=FactEdit(raw_value="25"),
        user_basis="核对登记原始人数", saved_by="medical-user", saved_at=AT,
    )
    with pytest.raises(UserFactSaveError, match="数值文本和规范值"):
        service.save(rejected)
    assert service.read_current_delivery().revision == 0
    saved = service.save(rejected.model_copy(update={
        "request_id": "source-count-corrected",
        "edits": FactEdit(raw_value="25", normalized_value=25),
    }))
    assert saved.rebuilt_reports == ("A",)
    current = service.read_current_delivery()
    assert current.revision == 1
    current_site = root / current.reports[0].site_relative_path
    raw = (current_site / "data/report.js").read_text(encoding="utf-8")
    payload = json.loads(raw.removeprefix("window.REPORT_A=").rstrip(" ;\n"))
    current_row = next(item for item in payload["efficacy"] if item["row_id"] == row_id)
    assert (current_row["value"], current_row["numerator"], current_row["denominator"]) == (
        25, 25, 35,
    )
    with open_database(root / "state/project.sqlite") as database:
        original = database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (source["primary_fragment_id"],),
        ).fetchone()
    assert original == ("30",)
    cleared = service.save(UserFactSaveCommand(
        request_id="source-count-cleared", project_id=contract.project_id,
        expected_revision=1,
        target=target.model_copy(update={"fact_version_id": saved.fact_version_id}),
        edits=FactEdit(raw_value=None), user_basis="人数待重新核实",
        saved_by="medical-user", saved_at=AT,
    ))
    assert cleared.rebuilt_reports == ("A",)
    current = service.read_current_delivery()
    assert current.revision == 2
    current_site = root / current.reports[0].site_relative_path
    raw = (current_site / "data/report.js").read_text(encoding="utf-8")
    payload = json.loads(raw.removeprefix("window.REPORT_A=").rstrip(" ;\n"))
    current_row = next(item for item in payload["efficacy"] if item["row_id"] == row_id)
    assert current_row["value"] is None
    assert current_row["numerator"] is None and current_row["denominator"] is None
    assert current_row["disclosure_state"] == "user_cleared"
    service.save(UserFactSaveCommand(
        request_id="source-count-undo", project_id=contract.project_id,
        expected_revision=2, operation="undo",
        target=target.model_copy(update={"fact_version_id": cleared.fact_version_id}),
        edits=FactEdit(), user_basis="撤销待核清除",
        saved_by="medical-user", saved_at=AT,
    ))
    assert service.read_current_delivery().revision == 3
    assert service.current_facts()[source["fact_id"]]["normalized_value"] == "25"
