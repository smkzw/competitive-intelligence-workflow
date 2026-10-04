"""Native clause context survives ingestion, consumers and ordinary evidence views."""

import json

import pytest

from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_groups,
    _chart_row,
    _evidence_view,
    _external_source_entries,
    _table_rows,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tests.integration.test_r24_c_pdf_extension import _arguments, _builder


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    return build_candidate(tmp_path_factory.mktemp("native-context"))


def build_candidate(root):
    args = _arguments(root)
    result = _builder()(**args)
    data = ReportCPortalData.model_validate_json(
        (args["output"] / "review-portal-data.json").read_bytes()
    )
    return args["output"], result, data


def test_cross_page_fragment_keeps_separate_native_context(candidate):
    _, _, data = candidate
    row = next(r for r in data.observations if r.source_row_id.endswith(
        "sap-p24-concomitant-conservative-lead-in"
    ))
    context = row.model_dump(mode="json").get("source_clause_context")
    assert context is not None, "Cross-page continuation was lost"
    refs = context["continuations"]
    assert len(refs) == 1 and refs[0]["locator"]["page"] == 25
    assert refs[0]["original_text"].startswith("case will be considered")
    view = _evidence_view(data, row, page_id="sample-analysis-statistics")
    assert view.original_text == row.source_text
    assert view.locator.page == 24
    assert view.model_dump(mode="json")["source_clause_context"] == context


def test_local_missing_rule_keeps_deferred_lead_in_and_scope(candidate):
    output, result, data = candidate
    row = next(r for r in data.observations if r.source_row_id.endswith(
        "prot-p62-efficacy-analysis-part2"
    ))
    context = row.model_dump(mode="json").get("source_clause_context")
    assert context is not None, "FACIT/PD scope disappeared from the consumer"
    assert "not safety 12.5" in context["scientific_scope"]["imputation_scope"]
    assert context["continuations"][0]["locator"]["page"] == 61
    assert context["continuations"][0]["original_text"].startswith("12.4")
    assert "不适用于" in context["scope_note_zh"]
    snapshot = SnapshotStore(output / "project").read(
        LockedSnapshot.model_validate(result["snapshot"])
    )
    fact = next(f for f in snapshot["closure"]["facts"]
                if f["fact"]["fact_id"] == row.row_id)
    assert fact["fact"]["source_clause_context"] == context
    assert "source_clause_context" not in data.observations[0].model_dump(mode="json")
    assert "row_id" not in json.dumps(context)


def test_real_conflicts_not_generic_banner_or_automatic_winner(candidate):
    _, _, data = candidate
    row = next(r for r in data.observations if r.source_row_id.endswith(
        "sap-p26-facit-cohort4-ttest"
    ))
    view = _evidence_view(data, row, page_id="sample-analysis-statistics")
    assert view.conflicts, "Source-linked unresolved tension was hidden"
    assert any(c.locator.page == 60 and "no formal statistical testing" in
               c.conflicting_value_zh for c in view.conflicts)
    assert all("未自动" in c.conflict_note_zh for c in view.conflicts)
    assert all(c.conflicting_source_version_id and c.locator.url for c in view.conflicts)


def test_document_links_deduplicate_without_collapsing_source_versions(candidate):
    _, _, data = candidate
    links = _external_source_entries(data, data.observations)
    urls = [item["url"] for item in links]
    assert len(urls) == len(set(urls)) == 6
    assert len({r.source_version_id for r in data.observations}) > len(urls)


def test_native_clause_has_source_topic_and_separate_cross_page_cue(candidate):
    _, _, data = candidate
    observation = next(r for r in data.observations if r.source_row_id.endswith(
        "sap-p24-concomitant-conservative-lead-in"
    ))
    row = _chart_row(data, observation, chart_type="sample-size-bar")
    assert row.get("source_topic_zh") == observation.source_clause_context.label_zh
    assert row.get("source_context_note_zh") == "跨页条款，前后文各页分别定位"
    assert row["source_text"] == observation.source_text
    assert row["value"] == observation.source_text
    baseline = _chart_row(data, data.observations[0], chart_type="status_matrix")
    assert "source_topic_zh" not in baseline


def test_statistics_query_keeps_every_relevant_clause_in_search_and_table(candidate):
    from ci_workflow.renderers.portal.report_c import _page_observations

    _, _, data = candidate
    observations = _page_observations(data, "sample-analysis-statistics")
    groups = _chart_groups(data, observations, page_id="sample-analysis-statistics", title="统计")
    assert {row["row_id"] for group in groups for row in group["rows"]} == {
        row.row_id for row in observations
    }


def test_pdf_native_text_is_not_mislabeled_registry_text(candidate):
    _, _, data = candidate
    observation = data.observations[-1]
    row = _table_rows(data, (observation,), page_id="sample-analysis-statistics")[0]
    assert row["value"].endswith("（研究方案与统计分析计划原文，未译）")
    assert "（登记原文，未译）" not in row["value"]
    assert observation.source_text in row["value"]


def test_source_topic_is_not_a_replacement_for_user_current_value(candidate):
    from ci_workflow.domain.facts import FactReviewState

    _, _, data = candidate
    observation = data.observations[-1].model_copy(update={
        "review_state": FactReviewState.USER_MODIFIED,
        "display_text": "User changed this analysis",
    })
    row = _chart_row(data, observation, chart_type="sample-size-bar")
    assert row.get("source_topic_zh") == observation.source_clause_context.label_zh
    assert row["value"] == "User changed this analysis"
    table = _table_rows(data, (observation,), page_id="sample-analysis-statistics")[0]
    assert table["value"] == "User changed this analysis（用户修订，未独立复核）"


def test_context_observations_match_public_schema(candidate):
    from jsonschema import Draft202012Validator

    from ci_workflow.reports.c.contracts import SCHEMA_PATH

    _, _, data = candidate
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_bytes()))
    for row in data.observations[85:]:
        validator.validate(row.model_dump(mode="json"))


def test_readable_review_keeps_complete_native_pages_and_raw_quotes(candidate):
    import hashlib

    output, manifest, data = candidate
    index = json.loads((output / "readable-review/index.json").read_bytes())
    assert len(index["pages"]) == 31 and len(index["clauses"]) == 42
    assert "not_independent_extraction" in index["status"]
    for page in index["pages"]:
        raw = (output / "readable-review" / page["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == page["native_page_sha256"]
        assert len(page["raw_pdf_sha256"]) == 64 and page["physical_page"] > 0
    for row in data.observations[85:]:
        raw = (output / "readable-review/clauses" / (row.source_row_id + ".md")).read_text()
        assert row.source_text in raw and "NOT_ACCEPTED" in raw
    for path, expected in manifest["readable_review_sha256"].items():
        assert hashlib.sha256((output / path).read_bytes()).hexdigest() == expected


def test_changed_scope_cannot_reuse_frozen_consumer_binding(candidate):
    from datetime import UTC, datetime

    from ci_workflow.application.c_portal_consumer_registry import (
        CPortalConsumerRegistrationError,
        register_c_source_consumers,
    )
    from ci_workflow.application.source_research_service import SourceCapture

    output, result, data = candidate
    snapshot = SnapshotStore(output / "project").read(
        LockedSnapshot.model_validate(result["snapshot"])
    )
    sources = {
        source["capture"]["source_id"]: SourceCapture.model_validate(source["capture"])
        for source in snapshot["closure"]["sources"]
    }
    rows = list(data.observations)
    context = rows[-1].source_clause_context.model_copy(update={
        "scientific_scope": {"domain": "invented_global_rule"},
    })
    rows[-1] = rows[-1].model_copy(update={"source_clause_context": context})
    with pytest.raises(CPortalConsumerRegistrationError, match="scientific_context"):
        register_c_source_consumers(
            output / "project", LockedSnapshot.model_validate(result["snapshot"]),
            data.model_copy(update={"observations": tuple(rows)}),
            result["fact_version_by_ref"], sources, registered_at=datetime.now(UTC),
        )


@pytest.mark.parametrize("damage", ["quote", "page", "source"])
def test_context_reference_cannot_forge_independent_page_proof(candidate, damage):
    from datetime import UTC, datetime

    from ci_workflow.application.fresh_c_research_package import research_facts_from_c_observations
    from ci_workflow.application.fresh_research_ingestion import (
        ResearchIngestionError,
        ingest_research_evidence,
    )
    from ci_workflow.application.source_research_service import ResearchClaim, SourceCapture
    from ci_workflow.storage.sqlite import open_database

    output, result, data = candidate
    snapshot = SnapshotStore(output / "project").read(
        LockedSnapshot.model_validate(result["snapshot"])
    )
    sources = tuple(SourceCapture.model_validate(item["capture"])
                    for item in snapshot["closure"]["sources"])
    row = next(r for r in data.observations if r.source_row_id.endswith(
        "sap-p24-concomitant-conservative-lead-in"
    ))
    fact = research_facts_from_c_observations(
        (row,), sources=sources, trial_names={t.id: t.name for t in data.trials},
    )[0]
    context = fact.source_clause_context
    ref = context.continuations[0]
    if damage == "quote":
        ref = ref.model_copy(update={"original_text": "Invented universal imputation"})
    elif damage == "page":
        ref = ref.model_copy(update={"locator": ref.locator.model_copy(update={"page": 24})})
    else:
        ref = ref.model_copy(update={"source_id": "not-in-this-source-set"})
    bad = fact.model_copy(update={
        "source_clause_context": context.model_copy(update={"continuations": (ref,)}),
    })
    with open_database(output / "project/state/project.sqlite") as db:
        before = db.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0]
    with pytest.raises(ResearchIngestionError, match="上下文"):
        ingest_research_evidence(
            project_root=output / "project", project_id=snapshot["project_id"],
            contract_version=snapshot["contract_version"], report_kind="C",
            data_cutoff=data.data_cutoff, scientific_content_digest="0" * 64,
            created_at=datetime.now(UTC), sources=sources, route_attempts=(), facts=(bad,),
            claims=(ResearchClaim(claim_id="rejected-context-claim",
                                  claim_text=bad.original_text, claim_kind="direct_evidence",
                                  fact_ids=(bad.fact_id,)),),
        )
    with open_database(output / "project/state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM fact_versions").fetchone()[0] == before
