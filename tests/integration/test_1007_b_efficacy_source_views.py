"""B efficacy source views project exact A-verified atoms, never new science.

The bridge is read-only: it proves every requested atom against the locked
evidence closure, the persisted fact/fragment rows and the append-only A
consumer registration, then returns the existing B view fields filled from the
row identity plus the verbatim source context. Unknown estimand/direction/scale
and analysis-set semantics stay unknown; no count, rate or ratio is derived.
"""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.b_efficacy_source_views import (
    BEfficacySourceViewError,
    project_b_efficacy_source_views,
)
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.portal_consumer_registry import register_a_source_consumers
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    bind_ctgov_outcome_to_a_row,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import EfficacyRow, ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.storage.snapshot_store import LockedSnapshot
from tests.integration.test_research_package_submission import _project
from tests.integration.test_w04_source_consumer_registry import AT, CONTENT, _candidate
from tests.integration.test_w07_ctgov_capture_bridge import _reported_count_source

REPO = Path(__file__).resolve().parents[2]
FIXED_ROOT = REPO / ".artifacts/1007-pn-joint-abc-source-v1/source-values-v2/working/project"
FIXED_RECEIPT = FIXED_ROOT / "evidence/library/combined-source-receipt-v5.json"
FIXED_A_REPORT = FIXED_ROOT / "evidence/library/a-candidate-v5.json"
QA_ROOT = REPO / ".artifacts/1007-baseline-number-current-v1/project"
QA_RECEIPT = REPO / ".artifacts/1007-baseline-number-current-v1/source-receipt.json"

FIXED_RECEIPT_SHA256 = "8c72878db97b66dfd1fc411a236e37269d272ccb85c20cad6e5da16880e2d555"
FIXED_A_REPORT_SHA256 = "cedd505751b9b37f0f84070712eec2eef52b2e9b2c0524796b7d566622d911c4"
QA_RECEIPT_SHA256 = "10b8b6b3132d3862ee02124a1351d4486b9fe503928061003a08614eebed49c7"

# Fields that only an existing semantic builder may fill. A source-bound
# subset must not claim compatibility, equivalence or derived effect values.
_FORBIDDEN_INVENTED_KEYS = frozenset({
    "direction", "analysis_form", "effect_measure", "effect_value", "effect_unit",
    "compatibility_key", "endpoint_family_id", "endpoint_family_label_zh",
    "actual_timepoint", "actual_timepoint_unit", "statistical_form", "measure_object",
    "rate", "percent", "proportion", "ratio", "crude_rate", "derived_rate",
})


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _locked_snapshot(project_root: Path, receipt: dict[str, Any]) -> LockedSnapshot:
    manifest = project_root / str(receipt["snapshot_relative_path"])
    return LockedSnapshot(
        snapshot_id=str(receipt["snapshot_id"]),
        kind="evidence",
        report=None,
        sha256=str(receipt["snapshot_sha256"]),
        relative_path=str(receipt["snapshot_relative_path"]),
        byte_size=manifest.stat().st_size,
    )


def _selected_efficacy_versions(receipt: dict[str, Any]) -> dict[str, str]:
    versions = {
        str(item["row_ref"]): str(item["fact_version_id"])
        for item in receipt["fact_bindings"]
    }
    return {
        f"efficacy:{row_id}": versions[f"efficacy:{row_id}"]
        for row_id in receipt["registered_a_efficacy_consumers"]
    }


def _fixed_fixture() -> tuple[Path, LockedSnapshot, ReportAPortalData, dict[str, str]]:
    required = (FIXED_RECEIPT, FIXED_A_REPORT, FIXED_ROOT / "state/project.sqlite")
    if not all(path.exists() for path in required):
        pytest.skip("fixed four-study source project is not in this checkout")
    assert _sha256_file(FIXED_RECEIPT) == FIXED_RECEIPT_SHA256
    assert _sha256_file(FIXED_A_REPORT) == FIXED_A_REPORT_SHA256
    receipt = json.loads(FIXED_RECEIPT.read_bytes())
    report = ReportAPortalData.model_validate_json(FIXED_A_REPORT.read_bytes())
    return (
        FIXED_ROOT,
        _locked_snapshot(FIXED_ROOT, receipt),
        report,
        _selected_efficacy_versions(receipt),
    )


def _altered_report(
    report: ReportAPortalData, row_id: str, changes: dict[str, Any],
) -> ReportAPortalData:
    payload = report.model_dump(mode="json")
    row = next(item for item in payload["efficacy"] if item["row_id"] == row_id)
    row.update(changes)
    return ReportAPortalData.model_validate(payload)


def _view_by_role(views: tuple[dict[str, object], ...], role: str) -> dict[str, object]:
    return next(view for view in views if view["source_value_role"] == role)


def _zero_count_candidate(tmp_path: Path) -> tuple[Path, LockedSnapshot, ReportAPortalData, str]:
    """Deterministic captured source whose direct participant count is exactly 0."""
    root = _project(tmp_path)
    source = _reported_count_source(
        root,
        classes=[{"categories": [{"measurements": [{"groupId": "OG1", "value": "0"}]}]}],
    )
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
        "value": 0,
        "unit": "Participants",
        "numerator": None,
        "denominator": None,
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
        claim_id="b-efficacy-zero-claim",
        claim_text="登记报告直接计数0",
        claim_kind="direct_evidence",
        fact_ids=tuple(fact.fact_id for fact in facts),
    )
    lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        report_kind="A",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"b-efficacy-zero").hexdigest(),
        created_at=source.acquired_at,
        sources=(source,),
        route_attempts=(),
        facts=facts,
        claims=(claim,),
    )
    return root, lineage.evidence_snapshot, report, lineage.fact_version_by_ref[
        f"efficacy:{bound.row_id}"
    ]


def test_real_a_verified_efficacy_atoms_project_exactly_into_partial_b_views() -> None:
    project, snapshot, a_report, selected = _fixed_fixture()
    assert len(selected) == len(set(selected.values())) == 91
    database = project / "state/project.sqlite"
    snapshot_path = project / snapshot.relative_path
    database_before = _sha256_file(database)
    snapshot_before = _sha256_file(snapshot_path)
    receipt_before = _sha256_file(FIXED_RECEIPT)

    views = project_b_efficacy_source_views(project, snapshot, a_report, selected)

    assert len(views) == 91
    assert len({view["row_id"] for view in views}) == 91
    rows = {row.row_id: row for row in a_report.efficacy}
    roles = [view["source_value_role"] for view in views]
    assert roles.count("participant_count") == 14
    assert roles.count("reported_measure") == 77
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        for view in views:
            row = rows[str(view["row_id"])]
            version_id = selected[f"efficacy:{row.row_id}"]
            raw_value, context_json, locator_json, quote = connection.execute(
                "SELECT v.raw_value,v.scientific_context_json,f.locator,f.content_text "
                "FROM fact_versions v JOIN evidence_fragments f "
                "ON f.fragment_id=v.primary_fragment_id WHERE v.fact_version_id=?",
                (version_id,),
            ).fetchone()
            context = json.loads(context_json)["result_context"]
            # Existing view fields come only from the row identity.
            assert view["product_id"] == row.product_id
            assert view["trial_id"] == row.trial_id
            assert view["original_definition"] == row.endpoint
            assert view["arm_label"] == row.arm == context["group_title"]
            assert view["arm_id"] == view["group_id"] == row.group_id
            assert view["analysis_population"] == row.population
            assert view["unit"] == row.unit
            assert view["value"] == row.value
            assert view["numerator"] == row.numerator
            assert view["denominator"] == row.denominator
            assert view["disclosure_state"] == row.disclosure_state.value
            # Exact source trace and verbatim source context are data.
            assert view["source_locator"] == json.loads(locator_json)
            assert view["source_locator"]["field_path"] == row.source_field_path
            assert view["source_text"] == quote == row.source_text
            assert view["source_version_id"] == row.source_version_id
            assert view["source_raw_value"] == raw_value
            assert view["source_endpoint"] == context["endpoint"] == row.endpoint
            assert view["source_timepoint"] == context["timepoint"]
            assert view["source_observation_timepoint"] == context.get("observation_timepoint")
            assert view["source_param_type"] == context.get("source_param_type")
            assert view["source_dispersion_type"] == context.get("source_dispersion_type")
            assert view["source_class_title"] == context.get("class_title")
            assert view["source_category_title"] == context.get("category_title")
            assert view["source_analysis_population"] == context.get("analysis_population")
            assert view["source_group_id"] == context["group_id"] == row.group_id
            assert view["source_group_title"] == context["group_title"]
            assert view["source_unit"] == context["source_unit"]
            assert view["source_value_role"] == context["value_role"]
            if view["source_value_role"] == "participant_count":
                assert view["numerator"] == int(raw_value)
                assert view["value"] == view["numerator"]
            else:
                assert view["numerator"] is None
            # No invented estimand/direction/scale semantics or derived ratios.
            assert _FORBIDDEN_INVENTED_KEYS.isdisjoint(view)

    # The source-bound subset is partial: the full 3544-row B pool is retained.
    b_report = ReportBPortalData.model_validate({
        **a_report.model_dump(mode="json"),
        "efficacy_views": {"coverage_mode": "partial", "facts": views},
    })
    assert len(b_report.efficacy) == 3544
    assert len(views) < len(b_report.efficacy)
    assert {view["row_id"] for view in views} < {row.row_id for row in b_report.efficacy}
    assert b_report.efficacy_views is not None
    assert b_report.efficacy_views["coverage_mode"] == "partial"
    assert tuple(b_report.efficacy_views["facts"]) == tuple(views)

    # Read-only: no database, snapshot or receipt byte changed.
    assert _sha256_file(database) == database_before
    assert _sha256_file(snapshot_path) == snapshot_before
    assert _sha256_file(FIXED_RECEIPT) == receipt_before


def test_real_projection_is_mapping_order_independent_and_read_only() -> None:
    project, snapshot, a_report, selected = _fixed_fixture()
    database_before = _sha256_file(project / "state/project.sqlite")
    forward = project_b_efficacy_source_views(project, snapshot, a_report, dict(selected))
    reversed_mapping = dict(reversed(list(selected.items())))
    backward = project_b_efficacy_source_views(project, snapshot, a_report, reversed_mapping)
    assert forward == backward
    assert [view["row_id"] for view in forward] == [
        row.row_id for row in a_report.efficacy if f"efficacy:{row.row_id}" in selected
    ]
    assert _sha256_file(project / "state/project.sqlite") == database_before


def test_real_whole_batch_rejects_wrong_value_quote_locator_group_population_domain() -> None:
    project, snapshot, a_report, selected = _fixed_fixture()
    database_before = _sha256_file(project / "state/project.sqlite")
    snapshot_before = _sha256_file(project / snapshot.relative_path)
    views = project_b_efficacy_source_views(project, snapshot, a_report, selected)
    count_id = str(_view_by_role(views, "participant_count")["row_id"])
    measure_id = str(_view_by_role(views, "reported_measure")["row_id"])
    batch = {
        f"efficacy:{count_id}": selected[f"efficacy:{count_id}"],
        f"efficacy:{measure_id}": selected[f"efficacy:{measure_id}"],
    }
    count_row = next(row for row in a_report.efficacy if row.row_id == count_id)
    measure_row = next(row for row in a_report.efficacy if row.row_id == measure_id)

    for row_id, changes in (
        (count_id, {"value": (count_row.value or 0) + 1}),
        (count_id, {"numerator": (count_row.numerator or 0) + 1}),
        (count_id, {"denominator": (count_row.denominator or 1) + 1}),
        (count_id, {"group_id": "OG999"}),
        (count_id, {"population": "另一分析人群"}),
        (measure_id, {"source_text": "not the locked quote"}),
        (measure_id, {"source_field_path": "$.resultsSection.wrong.value"}),
        (measure_id, {"endpoint": f"{measure_row.endpoint} (edited)"}),
        (measure_id, {"value": (measure_row.value or 0) + 0.1}),
    ):
        with pytest.raises(BEfficacySourceViewError):
            project_b_efficacy_source_views(
                project, snapshot, _altered_report(a_report, row_id, changes), batch,
            )

    count_version = selected[f"efficacy:{count_id}"]
    with pytest.raises(BEfficacySourceViewError):
        project_b_efficacy_source_views(
            project, snapshot, a_report,
            {f"efficacy:{count_id}": count_version, f"efficacy:{measure_id}": count_version},
        )
    with pytest.raises(BEfficacySourceViewError):
        project_b_efficacy_source_views(
            project, snapshot, a_report,
            {f"efficacy:{count_id}": count_version, "efficacy:unknown-row": count_version},
        )
    with pytest.raises(BEfficacySourceViewError):
        project_b_efficacy_source_views(
            project, snapshot, a_report,
            {f"safety:{count_id}": count_version},
        )
    with pytest.raises(BEfficacySourceViewError):
        project_b_efficacy_source_views(
            project, snapshot, a_report,
            {f"efficacy:{count_id}": "fact-version_missing"},
        )
    receipt = json.loads(FIXED_RECEIPT.read_bytes())
    versions = {
        str(item["row_ref"]): str(item["fact_version_id"])
        for item in receipt["fact_bindings"]
    }
    safety_row_id = str(receipt["registered_a_safety_consumers"][0])
    with pytest.raises(BEfficacySourceViewError):
        project_b_efficacy_source_views(
            project, snapshot, a_report,
            {f"efficacy:{count_id}": versions[f"safety:{safety_row_id}"]},
        )

    assert _sha256_file(project / "state/project.sqlite") == database_before
    assert _sha256_file(project / snapshot.relative_path) == snapshot_before


def test_new_qa_project_snapshot_projects_the_same_exact_views() -> None:
    if not (QA_RECEIPT.exists() and QA_ROOT.is_dir()):
        pytest.skip("new real QA project is not in this checkout")
    assert _sha256_file(QA_RECEIPT) == QA_RECEIPT_SHA256
    _, fixed_snapshot, a_report, _ = _fixed_fixture()
    receipt = json.loads(QA_RECEIPT.read_bytes())
    assert receipt["snapshot_id"] != fixed_snapshot.snapshot_id
    database_before = _sha256_file(QA_ROOT / "state/project.sqlite")
    snapshot_before = _sha256_file(QA_ROOT / str(receipt["snapshot_relative_path"]))
    selected = _selected_efficacy_versions(receipt)
    assert selected == _selected_efficacy_versions(json.loads(FIXED_RECEIPT.read_bytes()))
    views = project_b_efficacy_source_views(
        QA_ROOT, _locked_snapshot(QA_ROOT, receipt), a_report, selected,
    )
    assert len(views) == 91
    assert _sha256_file(QA_ROOT / "state/project.sqlite") == database_before
    assert _sha256_file(QA_ROOT / str(receipt["snapshot_relative_path"])) == snapshot_before


def test_deterministic_capture_requires_a_consumer_proof_and_keeps_count_unconverted(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    database_before = _sha256_file(root / "state/project.sqlite")
    with pytest.raises(BEfficacySourceViewError, match="A"):
        project_b_efficacy_source_views(root, snapshot, a_report, selected)
    assert _sha256_file(root / "state/project.sqlite") == database_before

    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)
    views = project_b_efficacy_source_views(root, snapshot, a_report, selected)

    assert len(views) == 1
    view = views[0]
    row = next(item for item in a_report.efficacy if item.row_id == row_id)
    assert view["source_value_role"] == "participant_count"
    assert (view["value"], view["numerator"], view["denominator"]) == (30.0, 30, 35)
    assert view["value"] == view["numerator"]  # 登记人数原值，而不是派生比例
    assert view["unit"] == row.unit == "Participants"
    assert view["original_definition"] == row.endpoint
    assert view["analysis_population"] == row.population
    assert view["arm_id"] == view["group_id"] == row.group_id
    assert view["arm_label"] == row.arm
    assert view["source_locator"]["field_path"] == row.source_field_path
    assert view["source_text"] == row.source_text == "30"
    assert view["source_group_title"] == row.arm
    assert _FORBIDDEN_INVENTED_KEYS.isdisjoint(view)


def test_deterministic_reported_measure_stays_estimate_without_count_or_rate(
    tmp_path: Path,
) -> None:
    root, snapshot, a_report, version_id = _candidate(
        tmp_path, source_unit="Percentage of responders",
    )
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)

    view = project_b_efficacy_source_views(root, snapshot, a_report, selected)[0]

    row = next(item for item in a_report.efficacy if item.row_id == row_id)
    assert view["source_value_role"] == "reported_measure"
    assert view["numerator"] is None
    assert view["value"] == row.value == 30.0
    assert view["source_unit"] == "Percentage of responders"
    assert view["denominator"] == row.denominator == 35
    assert _FORBIDDEN_INVENTED_KEYS.isdisjoint(view)


def test_deterministic_zero_count_is_preserved_without_a_derived_rate(tmp_path: Path) -> None:
    root, snapshot, a_report, version_id = _zero_count_candidate(tmp_path)
    row_id = next(row.row_id for row in a_report.efficacy if row.source_version_id)
    selected = {f"efficacy:{row_id}": version_id}
    register_a_source_consumers(root, snapshot, a_report, selected, registered_at=AT)

    view = project_b_efficacy_source_views(root, snapshot, a_report, selected)[0]

    assert view["source_value_role"] == "participant_count"
    assert (view["value"], view["numerator"], view["denominator"]) == (0.0, 0, 35)
    assert view["source_raw_value"] == "0"
    assert view["source_text"] == "0"
    assert view["disclosure_state"] == "reported_value"
    assert _FORBIDDEN_INVENTED_KEYS.isdisjoint(view)


def test_real_projection_rejects_a_report_row_that_drifts_from_its_a_consumer() -> None:
    """A/B scientific identity is matched through the append-only A proof."""
    project, snapshot, a_report, selected = _fixed_fixture()
    row_id = str(_view_by_role(
        project_b_efficacy_source_views(project, snapshot, a_report, selected),
        "reported_measure",
    )["row_id"])
    database_before = _sha256_file(project / "state/project.sqlite")
    for changes in (
        {"cohort_id": "another-cohort"},
        {"arm_detail": "another arm detail"},
        {"timepoint": "另一次访视"},
    ):
        with pytest.raises(BEfficacySourceViewError):
            project_b_efficacy_source_views(
                project, snapshot, _altered_report(a_report, row_id, changes), selected,
            )
    assert _sha256_file(project / "state/project.sqlite") == database_before
