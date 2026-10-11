"""Declared composite cells use existing append-only A/B source consumers.

Synthetic captured record and explicit fixture product relations, not clinical
acceptance of a real paper's product/arm association.
"""
import json
from hashlib import sha256

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.portal_consumer_registry import (
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim, ResearchFact
from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, numeric_value
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import _project
from tests.integration.test_w04_source_consumer_registry import AT, CONTENT, _b_direct_source_view
from tests.integration.test_w07_ctgov_capture_bridge import _reported_count_source
from tests.unit.test_source_publication_view import _result_context


def _candidate(tmp_path):
    root = _project(tmp_path)
    path = ("$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0]."
            "categories[0].measurements[0].value")
    source = _reported_count_source(root, unit="n (%)", denominator=None,
        classes=[{"categories": [{"measurements": [{"groupId": "OG1", "value": "14 (18.4)"}]}]}])
    context = _result_context(trial_id="NCT02277743", group_id="OG1",
        group_title="Drug 200 mg", arm="Drug 200 mg", term="Participants With Response",
        endpoint="Participants With Response", timepoint="Week 26", source_measure_path=path,
        analysis_population="Source population")
    fact = ResearchFact(fact_id="synthetic-composite-cell", row_ref="efficacy:composite-row",
        entity_id="nct02277743", entity_type="clinical_trial", canonical_name="Synthetic study",
        field_id="efficacy.source_cell", raw_value="14 (18.4)", normalized_value=None,
        disclosure_state="reported_value", source_id=source.source_id,
        locator={"document_role": "clinical_trial_registry", "field_path": path,
                 "url": source.url}, original_text="14 (18.4)", result_context=context)
    contract = verify_project_workspace(root).contract
    lineage = ingest_research_evidence(project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="A",
        data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"composite").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(), facts=(fact,),
        claims=(ResearchClaim(claim_id="synthetic-claim", claim_kind="direct_evidence",
                             claim_text=fact.original_text, fact_ids=(fact.fact_id,)),))
    baseline = json.loads(CONTENT.read_text())["report_data"]
    original = next(row for row in baseline["efficacy"] if row["trial_id"] == "nct02277743")
    row = {**original, "row_id": "composite-row", "value_basis": "reported_percent",
        "endpoint": context.endpoint, "timepoint": context.timepoint,
        "arm": original["arm"], "group_id": "OG1", "group_assignment_state": "declared",
        "population": "Source population", "value": 18.4, "unit": "%",
        "numerator": None, "denominator": None, "source_field_path": path,
        "source_version_id": lineage.source_version_ids[0], "source_text": fact.original_text}
    baseline.update(data_cutoff=contract.data_cutoff.isoformat(), efficacy=[
        row if item["row_id"] == original["row_id"] else item
        for item in baseline["efficacy"]
    ])
    trial = next(trial for trial in baseline["trials"] if trial["id"] == "nct02277743")
    trial["product_links"] = [{"product_id": row["product_id"], "arm_role": "experimental",
                                "arm_labels": [context.group_title]}]
    return root, lineage.evidence_snapshot, ReportAPortalData.model_validate(baseline), (
        lineage.fact_version_by_ref[fact.row_ref])


def _b_report(root, data, version):
    with open_database(root / "state/project.sqlite") as db:
        locator, quote = db.execute("SELECT f.locator,f.content_text FROM fact_versions v "
            "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
            "WHERE v.fact_version_id=?", (version,)).fetchone()
    data_b = _b_direct_source_view(data, locator, source_text=quote)
    raw = data_b.model_dump(mode="json")
    raw["efficacy_views"]["facts"][0].update(reported_count=14, value_basis="reported_percent")
    return type(data_b).model_validate(raw)


def test_composite_source_has_legal_a_b_consumers_without_normalizing_or_deriving(tmp_path):
    root, snapshot, data, version = _candidate(tmp_path)
    with open_database(root / "state/project.sqlite") as db:
        before = db.execute("SELECT * FROM fact_versions").fetchall()
    a = register_a_source_consumers(root, snapshot, data,
        {"efficacy:composite-row": version}, registered_at=AT)[0]
    b_data = _b_report(root, data, version)
    b = register_b_shared_source_consumers(root, snapshot, b_data,
        {"efficacy:composite-row": version}, registered_at=AT)[0]
    assert a.statistical_form == b.statistical_form == "reported_proportion"
    assert a.measure_object == b.measure_object == "participants"
    service = UserFactEditService(root)
    fact = service._public_fact(service._fact_row(version))
    assert {binding["report"] for binding in fact["consumer_bindings"]} == {"A", "B"}
    assert fact["raw_value"] == "14 (18.4)" and fact["normalized_value"] is None
    assert numeric_value(ActiveFact.model_validate(fact)) == 18.4
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT * FROM fact_versions").fetchall() == before


@pytest.mark.parametrize("fault", ["value", "count", "denominator", "basis", "group"])
def test_wrong_shared_component_never_writes_b_binding(tmp_path, fault):
    root, snapshot, data, version = _candidate(tmp_path)
    register_a_source_consumers(root, snapshot, data,
        {"efficacy:composite-row": version}, registered_at=AT)
    b = _b_report(root, data, version)
    raw = b.model_dump(mode="json")
    domain_row = next(row for row in raw["efficacy"] if row["row_id"] == "composite-row")
    if fault == "value":
        domain_row["value"] = raw["efficacy_views"]["facts"][0]["value"] = 19
    elif fault == "count":
        raw["efficacy_views"]["facts"][0]["reported_count"] = 15
    elif fault == "denominator":
        raw["efficacy_views"]["facts"][0]["denominator"] = 76
    elif fault == "basis":
        domain_row["value_basis"] = None
    else:
        raw["efficacy_views"]["facts"][0]["arm_id"] = "foreign-group"
    with pytest.raises(ValueError):
        register_b_shared_source_consumers(root, snapshot, type(b).model_validate(raw),
            {"efficacy:composite-row": version}, registered_at=AT)
    with open_database(root / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings "
                          "WHERE report='B'").fetchone()[0] == 0
