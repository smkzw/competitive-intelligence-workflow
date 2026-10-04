"""Registration and B projection must accept source-proven direct safety measures."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.portal_consumer_registry import (
    PortalConsumerRegistrationError,
    project_b_safety_source_views,
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    bind_ctgov_direct_safety_to_a_row,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, SafetyRow
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from ci_workflow.reports.b.safety_concepts import describe_safety_concept, safety_category_zh
from tests.integration.test_research_package_submission import _project
from tests.integration.test_w07_ctgov_capture_bridge import _reported_count_source


@pytest.mark.parametrize(
    "raw_unit,display_unit,measure,value",
    [
        ("Participants", "人", "participant_count", 8),
        ("Events", "次", "event_count", 12),
        ("Percentage of Participants", "%", "participant_proportion", 28),
    ],
)
def test_direct_safety_registers_and_projects_without_weakening_source_checks(
    tmp_path: Path,
    raw_unit: str,
    display_unit: str,
    measure: str,
    value: int,
) -> None:
    root = _project(tmp_path)
    title = "Number of Participants With Treatment-emergent Adverse Events (TEAEs)"
    source = _reported_count_source(
        root,
        title=title,
        unit=raw_unit,
        timeframe="Baseline to Week 26",
        classes=[
            {
                "title": "Week 26",
                "categories": [
                    {
                        "title": "Any",
                        "measurements": [
                            {"groupId": "OG1", "value": str(value)},
                        ],
                    }
                ],
            }
        ],
    )
    atom = extract_ctgov_atomic_results(source)[0][0]
    semantic = describe_safety_concept(title)
    row = SafetyRow(
        row_id="direct-safety",
        product_id="dupilumab",
        trial_id="nct02277743",
        arm="Drug 200 mg",
        group_id="OG1",
        group_assignment_state="declared",
        category=safety_category_zh(semantic.key),
        term=title,
        term_key=semantic.key,
        count_basis="events" if measure == "event_count" else semantic.count_basis,
        source_class_title="Week 26",
        source_category_title="Any",
        time_window="Week 26",
        value=value,
        unit=display_unit,
        measure_object=measure,
        numerator=value if measure == "participant_count" else None,
        denominator=35 if measure == "participant_count" else None,
    )
    bound, facts, claim = bind_ctgov_direct_safety_to_a_row(source, atom, row)
    baseline = ReportAPortalData.model_validate(
        json.loads(Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text())[
            "report_data"
        ]
    )
    report = baseline.model_copy(update={"safety": (bound,)})
    contract = verify_project_workspace(root).contract
    report = report.model_copy(update={"data_cutoff": contract.data_cutoff})
    lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(raw_unit.encode()).hexdigest(),
        created_at=source.acquired_at,
        sources=(source,),
        route_attempts=(),
        facts=facts,
        claims=(claim,),
    )
    versions = {f"safety:{bound.row_id}": lineage.fact_version_by_ref[facts[0].fact_id]}
    register_a_source_consumers(
        root,
        lineage.evidence_snapshot,
        report,
        versions,
        registered_at=source.acquired_at,
    )
    views = project_b_safety_source_views(root, lineage.evidence_snapshot, report, versions)
    assert len(views) == 1 and views[0]["value"] == value
    assert views[0]["source_text"] == str(value)
    assert views[0]["measure_object"] == measure
    assert (views[0]["numerator"], views[0]["denominator"]) == (
        (value, 35) if measure == "participant_count" else (None, None)
    )
    for changes in (
        {"time_window": "Baseline to Week 26"},
        {"unit": "wrong unit"},
        {"term_key": "death"},
        {"source_class_title": "Baseline"},
    ):
        broken = report.model_copy(update={"safety": (bound.model_copy(update=changes),)})
        with pytest.raises(PortalConsumerRegistrationError):
            project_b_safety_source_views(root, lineage.evidence_snapshot, broken, versions)
    b_report = ReportBPortalData.model_validate(
        {
            **report.model_dump(mode="json"),
            "safety_views": {"coverage_mode": "partial", "facts": views},
        }
    )
    bindings = register_b_shared_source_consumers(
        root,
        lineage.evidence_snapshot,
        b_report,
        versions,
        registered_at=source.acquired_at,
    )
    assert len(bindings) == 1 and bindings[0].report == "B"
    assert bindings[0].measure_object == ("events" if measure == "event_count" else "participants")
    assert (
        register_b_shared_source_consumers(
            root,
            lineage.evidence_snapshot,
            b_report,
            versions,
            registered_at=source.acquired_at,
        )
        == bindings
    )
    bad = b_report.model_copy(update={"safety": (bound.model_copy(update={"term_key": "death"}),)})
    with pytest.raises(PortalConsumerRegistrationError):
        register_b_shared_source_consumers(
            root,
            lineage.evidence_snapshot,
            bad,
            versions,
            registered_at=source.acquired_at,
        )
