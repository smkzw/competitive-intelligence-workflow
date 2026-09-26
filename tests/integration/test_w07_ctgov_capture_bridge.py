"""CT.gov 原始分页切片到现有研究来源合同的最小接缝。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    CtgovARowSourceRef,
    FreshAResearchContent,
    ResearchClaim,
    ResearchFact,
    ResearchLineage,
    ResearchPackageError,
    SourceCapture,
    _validate_bound_ctgov_a_results,
    bind_ctgov_ae_count_to_a_row,
    bind_ctgov_ae_to_a_row,
    bind_ctgov_direct_safety_to_a_row,
    bind_ctgov_outcome_to_a_row,
    build_ctgov_a_outcome_candidate_batch,
    build_ctgov_a_safety_candidate_batch,
    extract_ctgov_atomic_results,
    project_a_calculation_evidence,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import CtgovRecordSelector
from ci_workflow.domain.public_provenance import PublicProvenance, PublicSource
from ci_workflow.renderers.portal.report_a import (
    EfficacyRow,
    ReportAPortalData,
    SafetyRow,
    render_report_a_site,
)
from ci_workflow.reports.b.safety_concepts import describe_safety_concept, safety_category_zh
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import SourceDerivationError, capture_source_text
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import _project


def _derived(tmp_path: Path) -> DerivedCtgovStudy:
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT04558918", "briefTitle": "PNH study"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": []}},
    }
    raw = json.dumps({"studies": [record]}, ensure_ascii=False).encode()
    text, receipt = capture_source_text(
        tmp_path,
        raw,
        media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT04558918"),
    )
    return DerivedCtgovStudy(
        nct_id="NCT04558918",
        title="PNH study",
        record_url="https://clinicaltrials.gov/study/NCT04558918",
        registry_posted_version_date="2026-08-01",
        acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text,
        text_derivation=receipt,
    )


def test_saved_ctgov_page_replay_is_exact_and_never_masquerades_as_live_fetch(
    tmp_path: Path,
) -> None:
    from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record

    original = _derived(tmp_path)
    blob = original.text_derivation.raw_asset
    replayed = derive_saved_ctgov_record(
        tmp_path, blob, "NCT04558918",
        replayed_at=datetime(2026, 9, 26, tzinfo=UTC),
    )
    assert replayed.content_text == original.content_text
    assert replayed.text_derivation == original.text_derivation
    capture = source_capture_from_ctgov_study(tmp_path, replayed)
    assert capture.access_method == "offline_cas_replay"
    assert capture.route_id == "ctgov-cas-replay-v1"
    assert capture.date_precisions is not None
    assert capture.date_precisions.first_disclosed_at == "calendar_day"

    record = json.loads(original.content_text)
    duplicate_raw = json.dumps({"studies": [record, record]}).encode()
    duplicate_blob = ContentAddressedStore(tmp_path).put_bytes(
        duplicate_raw, media_type="application/json"
    )
    with pytest.raises(ValueError, match="唯一"):
        derive_saved_ctgov_record(
            tmp_path, duplicate_blob, "NCT04558918",
            replayed_at=datetime(2026, 9, 26, tzinfo=UTC),
        )


def test_saved_ctgov_page_replay_rejects_malformed_record_with_scoped_error(
    tmp_path: Path,
) -> None:
    malformed = {"studies": [{"protocolSection": None}]}
    blob = ContentAddressedStore(tmp_path).put_bytes(
        json.dumps(malformed).encode(), media_type="application/json"
    )
    with pytest.raises(SourceDerivationError, match="保存的登记分页"):
        from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record

        derive_saved_ctgov_record(
            tmp_path, blob, "NCT04558918",
            replayed_at=datetime(2026, 9, 26, tzinfo=UTC),
        )


def test_event_group_sae_and_death_counts_bind_raw_atoms_without_rate_substitution(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT04820530", "briefTitle": "PNH study"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}},
        },
        "resultsSection": {"adverseEventsModule": {
            "timeFrame": "Day 1 through Week 48",
            "eventGroups": [{
                "id": "EG000", "title": "LNP023 200mg b.i.d.",
                "seriousNumAffected": 8, "seriousNumAtRisk": 40,
                "deathsNumAffected": 0, "deathsNumAtRisk": 40,
            }],
        }},
    }
    raw = json.dumps({"studies": [record]}, ensure_ascii=False).encode()
    blob = ContentAddressedStore(project).put_bytes(raw, media_type="application/json")
    from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record

    replayed = derive_saved_ctgov_record(
        project, blob, "NCT04820530", replayed_at=datetime(2026, 9, 26, tzinfo=UTC)
    )
    source = source_capture_from_ctgov_study(project, replayed)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    assert {(atom.category, atom.value_quote, atom.denominator_quote) for atom in atoms} == {
        ("sae", "8", "40"), ("death", "0", "40"),
    }
    specs = (
        ("sae", "严重不良事件（登记）", "严重不良事件组别汇总计数", "any_sae", 8),
        ("death", "死亡病例（登记）", "死亡病例组别汇总计数", "death", 0),
    )
    bound_rows = []
    facts = []
    claims = []
    for category, label, term, concept, count in specs:
        row = SafetyRow(
            row_id=f"r24-{category}", product_id="iptacopan",
            trial_id="nct04820530", arm="LNP023 200mg b.i.d.", group_id="EG000",
            category=label, term=term, term_key=concept,
            value=count, unit="人", measure_object="participant_count",
            numerator=count, denominator=40, time_window="Day 1 through Week 48",
        )
        atom = next(item for item in atoms if item.category == category)
        bound, row_facts, claim = bind_ctgov_ae_count_to_a_row(source, atom, row)
        assert bound.value == count and bound.source_text == str(count)
        assert claim.claim_kind == "direct_evidence" and claim.calculation is None
        assert [fact.original_text for fact in row_facts] == [str(count), "40"]
        bound_rows.append(bound)
        facts.extend(row_facts)
        claims.append(claim)
        with pytest.raises(ResearchPackageError):
            bind_ctgov_ae_count_to_a_row(
                source, atom, row.model_copy(update={"value": count + 1})
            )
    batch = build_ctgov_a_safety_candidate_batch((source,), tuple(bound_rows))
    assert len(batch.bound_rows) == 2 and not batch.gaps
    assert len(batch.facts) == 4 and len(batch.claims) == 2
    baseline = ReportAPortalData.model_validate(json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )["report_data"])
    # This test targets the source-to-row validator, not full indication-universe
    # admission; the fixture's unrelated AD product catalog is left unchanged.
    report = baseline.model_copy(update={"safety": (*baseline.safety, *bound_rows)})
    _validate_bound_ctgov_a_results(report, (source,), tuple(facts), tuple(claims))
    contract = verify_project_workspace(project).contract
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"r24-sae-death-raw-counts").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(),
        facts=tuple(facts), claims=tuple(claims),
    )
    assert len(lineage.fact_version_ids) == 4
    assert len(lineage.claim_version_ids) == 2


def _reported_count_source(
    tmp_path: Path,
    *,
    classes: list[dict[str, object]] | None = None,
    timeframe: str = "Week 26",
    title: str = "Participants With Response",
    unit: str = "Participants",
    denominator: int | None = 35,
) -> SourceCapture:
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT02277743", "briefTitle": "AD count study"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "title": title, "timeFrame": timeframe,
            "unitOfMeasure": unit,
            "paramType": "COUNT_OF_PARTICIPANTS" if unit == "Participants" else "",
            "groups": [{"id": "OG1", "title": "Drug 200 mg"}],
            "denoms": (
                [{"units": "Participants", "counts": [
                    {"groupId": "OG1", "value": str(denominator)},
                ]}]
                if denominator is not None else []
            ),
            "classes": classes if classes is not None else [{"categories": [{"measurements": [
                {"groupId": "OG1", "value": "30"},
            ]}]}],
        }]}},
    }
    raw = json.dumps({"studies": [record]}, ensure_ascii=False).encode()
    text, receipt = capture_source_text(
        tmp_path, raw, media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT02277743"),
    )
    study = DerivedCtgovStudy(
        nct_id="NCT02277743", title="AD count study",
        record_url="https://clinicaltrials.gov/study/NCT02277743",
        registry_posted_version_date="2026-08-01",
        acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text, text_derivation=receipt,
    )
    return source_capture_from_ctgov_study(tmp_path, study)


def test_direct_safety_outcome_binds_exact_category_and_raw_count(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    title = "Number of Participants With Treatment-emergent Adverse Events (TEAEs)"
    source = _reported_count_source(
        project, title=title, timeframe="Baseline to Week 26",
        classes=[{"title": "Week 26", "categories": [
            {"title": "Any", "measurements": [{"groupId": "OG1", "value": "8"}]},
            {"title": "Other", "measurements": [{"groupId": "OG1", "value": "8"}]},
        ]}],
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 2
    semantic = describe_safety_concept(title)
    row = SafetyRow(
        row_id="safe-direct", product_id="dupilumab", trial_id="nct02277743",
        arm="Drug 200 mg", group_id="OG1",
        category=safety_category_zh(semantic.key), term=title,
        term_key=semantic.key, count_basis=semantic.count_basis,
        source_class_title="Week 26", source_category_title="Any",
        measure_context="第26周；Any", value=8, unit="人",
        measure_object="participant_count", numerator=8, denominator=35,
        time_window="Week 26",
    )
    bound, facts, claim = bind_ctgov_direct_safety_to_a_row(source, atoms[0], row)
    assert bound.source_text == "8" and bound.value == 8
    assert bound.source_field_path == atoms[0].value_locator.field_path
    assert [fact.original_text for fact in facts] == ["8", "35"]
    assert claim.claim_kind == "direct_evidence" and claim.calculation is None
    assert facts[0].result_context is not None
    assert facts[0].result_context.value_role == "participant_count"
    baseline = ReportAPortalData.model_validate(json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )["report_data"])
    report = ReportAPortalData.model_validate({
        **baseline.model_dump(mode="json"),
        "safety": [*baseline.model_dump(mode="json")["safety"], bound.model_dump(mode="json")],
    })
    _validate_bound_ctgov_a_results(report, (source,), facts, (claim,))
    contract = verify_project_workspace(project).contract
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"direct-safety-outcome").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(),
        facts=facts, claims=(claim,),
    )
    assert len(lineage.fact_version_ids) == 2
    with open_database(project / "state/project.sqlite") as database:
        fragments = database.execute(
            "SELECT content_text,locator FROM evidence_fragments WHERE fragment_id IN (?,?)",
            tuple(lineage.fragment_by_fact_id[item.fact_id] for item in facts),
        ).fetchall()
    assert {item[0] for item in fragments} == {"8", "35"}
    assert all('"field_path":"$.' in item[1] for item in fragments)
    for changes in (
        {"source_category_title": "Other"}, {"source_class_title": "Baseline"},
        {"time_window": "Baseline"}, {"value": 9}, {"group_id": "OG2"},
        {"unit": "%"}, {"numerator": None, "denominator": None},
        {"source_field_path": "$.wrong"},
    ):
        with pytest.raises(ResearchPackageError):
            bind_ctgov_direct_safety_to_a_row(
                source, atoms[0], row.model_copy(update=changes)
            )
    with pytest.raises(ResearchPackageError, match="唯一"):
        bind_ctgov_direct_safety_to_a_row(source, atoms[1], row)
    with pytest.raises(ResearchPackageError, match="声明"):
        _validate_bound_ctgov_a_results(report, (source,), facts)


def test_immunogenicity_atom_keeps_raw_measure_context_and_rejects_efficacy_binding(
    tmp_path: Path,
) -> None:
    source = _reported_count_source(
        tmp_path, title="Number of Participants With Anti-drug Antibodies (ADA)",
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    atom = atoms[0]
    assert atom.domain == "immunogenicity"
    assert atom.metric == "participant_count"
    assert atom.source_param_type == "COUNT_OF_PARTICIPANTS"
    assert atom.raw_value_type == "str"
    assert atom.source_measure_path.endswith("outcomeMeasures[0]")
    assert atom.denominator_candidates[0].raw_value == "35"
    assert atom.denominator_candidates[0].group_id == "OG1"
    facts = research_facts_from_ctgov_atom(atom)
    assert facts[0].result_context is not None
    assert facts[0].result_context.domain == "immunogenicity"
    assert facts[0].result_context.source_param_type == "COUNT_OF_PARTICIPANTS"
    with pytest.raises(ResearchPackageError, match="领域"):
        research_facts_from_ctgov_atom(atom, report_row_ref="efficacy:eff-130")


@pytest.mark.parametrize(
    ("title", "raw_unit", "display_unit", "measure_object", "value"),
    [
        ("Number of Events With Adverse Events", "Events", "次", "event_count", 41),
        ("Percentage of Participants With Serious Adverse Events (SAEs)",
         "Percentage of participants", "%", "participant_proportion", 20),
    ],
)
def test_direct_safety_event_and_percentage_are_not_derived_rates(
    tmp_path: Path, title: str, raw_unit: str, display_unit: str,
    measure_object: str, value: int,
) -> None:
    source = _reported_count_source(
        tmp_path, title=title, unit=raw_unit,
        classes=[{"categories": [{"measurements": [
            {"groupId": "OG1", "value": str(value)},
        ]}]}],
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    semantic = describe_safety_concept(title)
    row = SafetyRow.model_validate({
        "row_id": "safe-direct", "product_id": "dupilumab", "trial_id": "nct02277743",
        "arm": "Drug 200 mg", "group_id": "OG1",
        "category": safety_category_zh(semantic.key), "term": title,
        "term_key": semantic.key, "count_basis": semantic.count_basis,
        "value": value, "unit": display_unit, "measure_object": measure_object,
        "time_window": "Week 26",
    })
    bound, facts, claim = bind_ctgov_direct_safety_to_a_row(source, atoms[0], row)
    assert bound.value == value and bound.source_text == str(value)
    assert len(facts) == 1 and facts[0].original_text == str(value)
    assert claim.calculation is None and claim.claim_kind == "direct_evidence"


def test_safety_batch_keeps_unique_categories_and_exposes_unmatched_rows(
    tmp_path: Path,
) -> None:
    title = "Number of Participants With Treatment-emergent Adverse Events (TEAEs)"
    source = _reported_count_source(
        tmp_path, title=title,
        classes=[{"title": "Week 26", "categories": [
            {"title": "Any", "measurements": [{"groupId": "OG1", "value": "8"}]},
            {"title": "Other", "measurements": [{"groupId": "OG1", "value": "8"}]},
        ]}],
    )
    semantic = describe_safety_concept(title)
    first = SafetyRow(
        row_id="any", product_id="dupilumab", trial_id="nct02277743",
        arm="Drug 200 mg", group_id="OG1",
        category=safety_category_zh(semantic.key), term=title,
        term_key=semantic.key, count_basis=semantic.count_basis,
        source_class_title="Week 26", source_category_title="Any",
        value=8, unit="人", measure_object="participant_count",
        numerator=8, denominator=35, time_window="Week 26",
    )
    other = first.model_copy(update={"row_id": "other", "source_category_title": "Other"})
    missing = first.model_copy(update={"row_id": "missing", "source_category_title": "Absent"})
    batch = build_ctgov_a_safety_candidate_batch((source,), (first, other, missing))
    assert [row.row_id for row in batch.bound_rows] == ["any", "other"]
    assert [fact.original_text for fact in batch.facts] == ["8", "35", "8", "35"]
    assert len(batch.claims) == 2 and all(
        claim.claim_kind == "direct_evidence" and claim.calculation is None
        for claim in batch.claims
    )
    assert [(gap.row_id, gap.reason) for gap in batch.gaps] == [
        ("missing", "no_exact_match")
    ]
    reused = build_ctgov_a_safety_candidate_batch(
        (source,), (first, first.model_copy(update={"row_id": "copy"}))
    )
    assert not reused.bound_rows and not reused.facts
    assert [gap.reason for gap in reused.gaps] == [
        "source_atom_reused", "source_atom_reused"
    ]
    ambiguous = build_ctgov_a_safety_candidate_batch(
        (source, source.model_copy(update={"source_id": "second-version"})), (first,)
    )
    assert not ambiguous.bound_rows
    assert [(gap.reason, gap.candidate_count) for gap in ambiguous.gaps] == [
        ("ambiguous", 2)
    ]
    with pytest.raises(ResearchPackageError, match="标识重复"):
        build_ctgov_a_safety_candidate_batch((source,), (first, first))


def test_direct_safety_count_without_denominator_keeps_reported_value_only(
    tmp_path: Path,
) -> None:
    title = "Number of Participants With Treatment-emergent Adverse Events (TEAEs)"
    source = _reported_count_source(
        tmp_path, title=title, denominator=None,
        classes=[{"categories": [{"measurements": [
            {"groupId": "OG1", "value": "1"},
        ]}]}],
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert len(atoms) == 1
    assert atoms[0].value_quote == "1" and atoms[0].denominator_locator is None
    assert atoms[0].display_value == 1 and atoms[0].display_unit == "人"
    assert len(issues) == 1 and issues[0].status == "missing"
    assert "风险率未知" in issues[0].reason_zh
    semantic = describe_safety_concept(title)
    row = SafetyRow(
        row_id="direct-no-denom", product_id="dupilumab", trial_id="nct02277743",
        arm="Drug 200 mg", group_id="OG1", term=title,
        category=safety_category_zh(semantic.key), term_key=semantic.key,
        count_basis=semantic.count_basis, value=1, unit="人",
        measure_object="participant_count", time_window="Week 26",
    )
    bound, facts, claim = bind_ctgov_direct_safety_to_a_row(source, atoms[0], row)
    assert bound.value == 1 and bound.numerator is None and bound.denominator is None
    assert len(facts) == 1 and facts[0].original_text == "1"
    assert claim.calculation is None
    with pytest.raises(ResearchPackageError):
        bind_ctgov_direct_safety_to_a_row(
            source, atoms[0], row.model_copy(update={"numerator": 1, "denominator": 35})
        )


def test_combined_safety_outcome_remains_unsplit_with_explicit_zero(
    tmp_path: Path,
) -> None:
    title = (
        "Number of Participants With Treatment-emergent Adverse Events (TEAEs), "
        "Serious Adverse Events (SAEs), and AEs Leading to Discontinuation"
    )
    source = _reported_count_source(
        tmp_path, title=title, classes=[{
            "title": "AE leading to discontinuation",
            "categories": [{"measurements": [{"groupId": "OG1", "value": "0"}]}],
        }],
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    assert atoms[0].category == "outcome" and atoms[0].value_quote == "0"
    semantic = describe_safety_concept(title)
    assert semantic.count_basis == "mixed"
    row = SafetyRow(
        row_id="combined-zero", product_id="dupilumab", trial_id="nct02277743",
        arm="Drug 200 mg", group_id="OG1", term=title,
        category=safety_category_zh(semantic.key), term_key=semantic.key,
        count_basis="mixed", source_class_title="AE leading to discontinuation",
        value=0, unit="人", measure_object="participant_count", time_window="Week 26",
    )
    bound, facts, claim = bind_ctgov_direct_safety_to_a_row(source, atoms[0], row)
    assert bound.value == 0 and bound.numerator is None and bound.denominator is None
    assert len(facts) == 2 and facts[0].disclosure_state == "reported_zero"
    assert all(fact.result_context and fact.result_context.category == "outcome" for fact in facts)
    assert claim.claim_kind == "direct_evidence" and claim.calculation is None


def test_reported_participant_count_binds_raw_count_and_same_group_denominator(
    tmp_path: Path,
) -> None:
    source = _reported_count_source(tmp_path)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    atom = atoms[0]
    assert (atom.numerator, atom.denominator, atom.display_value) == (30, 35, 85.7)
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    baseline = ReportAPortalData.model_validate(payload["report_data"])
    original = next(
        item for item in baseline.efficacy
        if item.trial_id.casefold() == "nct02277743"
    )
    row = EfficacyRow.model_validate({
        **original.model_dump(mode="json"),
        "endpoint": "Participants With Response", "timepoint": "Week 26",
        "arm": "Drug 200 mg", "arm_detail": None, "group_id": None,
        "value": 30, "unit": "Participants", "numerator": None,
        "denominator": None, "source_field_path": None,
        "source_version_id": None, "source_text": None,
    })
    bound, facts = bind_ctgov_outcome_to_a_row(source, atom, row)
    assert (bound.value, bound.numerator, bound.denominator) == (30, 30, 35)
    assert [fact.original_text for fact in facts] == ["30", "35"]
    assert [fact.result_context.value_role for fact in facts if fact.result_context] == [
        "participant_count", "denominator",
    ]
    assert facts[0].result_context is not None
    assert not {
        "class_title", "category_title", "observation_timepoint"
    } & facts[0].result_context.model_dump(mode="json").keys()
    report = ReportAPortalData.model_validate({
        **baseline.model_dump(mode="json"),
        "efficacy": [
            bound.model_dump(mode="json") if item.row_id == row.row_id
            else item.model_dump(mode="json")
            for item in baseline.efficacy
        ],
    })
    _validate_bound_ctgov_a_results(report, (source,), facts)
    render_report_a_site(report, tmp_path / "count-site")
    report_js = (tmp_path / "count-site/data/report.js").read_text()
    rendered_rows = json.loads(
        report_js.removeprefix("window.REPORT_A=").rstrip(" ;\n")
    )["efficacy"]
    displayed = next(
        item for item in rendered_rows if item["row_id"] == bound.row_id
    )
    assert displayed["numeric_projection"]["kind"] == "participant_count"
    assert displayed["plot_value"] == 30
    assert displayed["source_field_path"] == atom.value_locator.field_path
    for changed in (
        row.model_copy(update={"value": 85.7, "unit": "%"}),
        row.model_copy(update={"denominator": 36}),
        row.model_copy(update={"arm": "Other Drug"}),
        row.model_copy(update={"timepoint": "Week 50"}),
    ):
        with pytest.raises(ValueError):
            bind_ctgov_outcome_to_a_row(source, atom, changed)
    with pytest.raises(ValueError, match="分母"):
        _validate_bound_ctgov_a_results(report, (source,), facts[:1])


@pytest.mark.parametrize("unit", ["participants", "number of participants"])
def test_count_unit_variants_bind_original_people_without_inventing_a_rate(
    tmp_path: Path, unit: str,
) -> None:
    source = _reported_count_source(tmp_path, unit=unit)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert len(atoms) == 1 and not issues
    baseline = ReportAPortalData.model_validate(json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )["report_data"])
    original = next(item for item in baseline.efficacy
                    if item.trial_id.casefold() == "nct02277743")
    row = EfficacyRow.model_validate({
        **original.model_dump(mode="json"),
        "endpoint": "Participants With Response", "timepoint": "Week 26",
        "arm": "Drug 200 mg", "arm_detail": None, "group_id": None,
        "value": 30, "unit": unit, "numerator": None, "denominator": None,
        "source_field_path": None, "source_version_id": None, "source_text": None,
    })
    bound, facts = bind_ctgov_outcome_to_a_row(source, atoms[0], row)
    assert (bound.value, bound.numerator, bound.denominator) == (30, 30, 35)
    assert [fact.original_text for fact in facts] == ["30", "35"]


def test_registry_class_visit_and_category_keep_same_value_observations_distinct(
    tmp_path: Path,
) -> None:
    classes = [
        {"title": title, "categories": [{
            "title": category,
            "measurements": [{"groupId": "OG1", "value": "30"}],
        }]}
        for title, category in (
            ("Baseline", "Responder"),
            ("Week 26", "Responder"),
            ("Week 26", "Non Responder"),
            ("≥2 g/dL increase from baseline", "Responder"),
        )
    ]
    source = _reported_count_source(
        tmp_path, classes=classes, timeframe="Baseline to Week 26"
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 4
    assert [atom.observation_timepoint for atom in atoms] == [
        "Baseline", "Week 26", "Week 26", "",
    ]
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    report = ReportAPortalData.model_validate(payload["report_data"])
    original = next(
        row for row in report.efficacy
        if row.trial_id.casefold() == "nct02277743"
    )
    row = EfficacyRow.model_validate({
        **original.model_dump(mode="json"),
        "endpoint": "Participants With Response", "timepoint": "Week 26",
        "arm": "Drug 200 mg", "arm_detail": None, "group_id": None,
        "population": "登记结果人群（Week 26；Responder）",
        "value": 30, "unit": "Participants", "numerator": None,
        "denominator": None, "source_field_path": None,
        "source_version_id": None, "source_text": None,
    })
    bound, facts = bind_ctgov_outcome_to_a_row(source, atoms[1], row)
    assert bound.timepoint == "Week 26"
    assert facts[0].result_context is not None
    assert (
        facts[0].result_context.timepoint,
        facts[0].result_context.observation_timepoint,
        facts[0].result_context.class_title,
        facts[0].result_context.category_title,
    ) == ("Baseline to Week 26", "Week 26", "Week 26", "Responder")
    for wrong_atom in (atoms[0], atoms[2], atoms[3]):
        with pytest.raises(ValueError):
            bind_ctgov_outcome_to_a_row(source, wrong_atom, row)
    misleading_baseline = row.model_copy(update={
        "timepoint": "Baseline",
        "population": "登记结果人群（≥2 g/dL increase from baseline；Responder）",
    })
    with pytest.raises(ValueError):
        bind_ctgov_outcome_to_a_row(source, atoms[3], misleading_baseline)
    duplicate_source = _reported_count_source(
        tmp_path, classes=[*classes, classes[1]], timeframe="Baseline to Week 26"
    )
    duplicate_atoms, _ = extract_ctgov_atomic_results(duplicate_source)
    with pytest.raises(ValueError, match="唯一"):
        bind_ctgov_outcome_to_a_row(duplicate_source, duplicate_atoms[1], row)


def test_a_builder_does_not_mistake_from_baseline_for_baseline_visit() -> None:
    from ci_workflow.application.source_research_service import (
        ctgov_class_observation_timepoint,
    )

    assert ctgov_class_observation_timepoint("≥2 g/dL increase from baseline") == ""
    assert ctgov_class_observation_timepoint("Baseline") == "Baseline"
    assert ctgov_class_observation_timepoint("Fatigue: Day 253") == "Fatigue: Day 253"
    assert ctgov_class_observation_timepoint("Day 1 and Day 253") == ""


def test_outcome_batch_persists_only_unique_rows_and_classifies_gaps(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    contract = verify_project_workspace(project).contract
    source = _reported_count_source(
        project,
        classes=[
            {"title": "Baseline", "categories": [{"title": "Responder", "measurements": [
                {"groupId": "OG1", "value": "30"},
            ]}]},
            {"title": "Week 26", "categories": [{"title": "Responder", "measurements": [
                {"groupId": "OG1", "value": "31"},
            ]}]},
        ],
        timeframe="Baseline to Week 26",
    )
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    base = next(
        row for row in ReportAPortalData.model_validate(payload["report_data"]).efficacy
        if row.trial_id.casefold() == "nct02277743"
    )

    def row(row_id: str, visit: str, value: int) -> EfficacyRow:
        return EfficacyRow.model_validate({
            **base.model_dump(mode="json"), "row_id": row_id,
            "endpoint": "Participants With Response", "timepoint": visit,
            "arm": "Drug 200 mg", "arm_detail": None, "group_id": None,
            "population": f"登记结果人群（{visit}；Responder）",
            "value": value, "unit": "Participants", "numerator": None,
            "denominator": None, "source_field_path": None,
            "source_version_id": None, "source_text": None,
        })

    baseline = row("baseline", "Baseline", 30)
    week = row("week-26", "Week 26", 31)
    missing = row("unmatched", "Week 50", 31)
    batch = build_ctgov_a_outcome_candidate_batch((source,), (baseline, week, missing))
    assert [item.row_id for item in batch.bound_rows] == ["baseline", "week-26"]
    assert [(gap.row_id, gap.reason, gap.candidate_count) for gap in batch.gaps] == [
        ("unmatched", "no_exact_match", 0),
    ]
    assert [item.original_text for item in batch.facts] == ["30", "35", "31", "35"]
    assert len(batch.claims) == 2
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"two-exact-outcomes").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(),
        facts=batch.facts, claims=batch.claims,
    )
    assert len(lineage.fact_version_ids) == 4
    assert len(lineage.claim_version_ids) == 2
    with open_database(project / "state/project.sqlite") as database:
        persisted = database.execute(
            "SELECT content_text,locator FROM evidence_fragments "
            "WHERE fragment_id IN (?,?,?,?)",
            tuple(lineage.fragment_by_fact_id[fact.fact_id] for fact in batch.facts),
        ).fetchall()
    assert {item[0] for item in persisted} == {"30", "31", "35"}
    assert all('"field_path":"$.' in item[1] for item in persisted)

    reused = build_ctgov_a_outcome_candidate_batch(
        (source,), (baseline, baseline.model_copy(update={"row_id": "copy"}))
    )
    assert not reused.bound_rows and not reused.facts
    assert [gap.reason for gap in reused.gaps] == [
        "source_atom_reused", "source_atom_reused"
    ]
    with pytest.raises(ResearchPackageError, match="标识重复"):
        build_ctgov_a_outcome_candidate_batch((source,), (baseline, baseline))


def test_outcome_batch_rejects_two_exact_source_versions(tmp_path: Path) -> None:
    source = _reported_count_source(tmp_path)
    atoms, _ = extract_ctgov_atomic_results(source)
    assert len(atoms) == 1
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    base = next(
        row for row in ReportAPortalData.model_validate(payload["report_data"]).efficacy
        if row.trial_id.casefold() == "nct02277743"
    )
    target = EfficacyRow.model_validate({
        **base.model_dump(mode="json"), "endpoint": "Participants With Response",
        "timepoint": "Week 26", "arm": "Drug 200 mg", "arm_detail": None,
        "group_id": None, "value": 30, "unit": "Participants",
        "numerator": None, "denominator": None, "source_field_path": None,
        "source_version_id": None, "source_text": None,
    })
    second = source.model_copy(update={"source_id": "ctgov-second-version"})
    batch = build_ctgov_a_outcome_candidate_batch((source, second), (target,))
    assert not batch.bound_rows and not batch.facts
    assert [(gap.reason, gap.candidate_count) for gap in batch.gaps] == [
        ("ambiguous", 2)
    ]


def test_explicit_source_reference_binds_only_current_raw_page_and_exact_atom(
    tmp_path: Path,
) -> None:
    source = _reported_count_source(tmp_path, classes=[{
        "title": "Baseline-none",
        "categories": [{"measurements": [{"groupId": "OG1", "value": "30"}]}],
    }])
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    assert source.text_derivation is not None
    row = EfficacyRow(
        row_id="eff-source-map", product_id="dupilumab", trial_id="nct02277743",
        endpoint="Participants With Response", timepoint="Week 26",
        arm="Drug 200 mg", group_id="OG1", value=30,
        unit="Participants", population="登记结果人群（基线-无）",
    )
    ref = CtgovARowSourceRef(
        row_id=row.row_id, trial_id=row.trial_id,
        source_page_sha256=source.text_derivation.raw_asset.sha256,
        value_path=atoms[0].value_locator.field_path or "",
        raw_class_title="Baseline-none",
        raw_category_title="",
        display_population="登记结果人群（基线-无）",
    )
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row,),
    ).gaps] == ["no_exact_match"]
    good = build_ctgov_a_outcome_candidate_batch(
        (source,), (row,), row_source_refs=(ref,),
    )
    assert len(good.bound_rows) == 1 and not good.gaps
    assert good.bound_rows[0].source_field_path == ref.value_path
    wrong_page = CtgovARowSourceRef(
        row_id=ref.row_id, trial_id=ref.trial_id,
        source_page_sha256="0" * 64, value_path=ref.value_path,
    )
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row,), row_source_refs=(wrong_page,),
    ).gaps] == ["source_reference_mismatch"]
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row,), row_source_refs=(),
    ).gaps] == ["source_reference_missing"]
    wrong_path = CtgovARowSourceRef(
        row_id=ref.row_id, trial_id=ref.trial_id,
        source_page_sha256=ref.source_page_sha256,
        value_path="$.resultsSection.outcomeMeasuresModule.outcomeMeasures[99].value",
    )
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row,), row_source_refs=(wrong_path,),
    ).gaps] == ["source_reference_mismatch"]
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row.model_copy(update={"value": 31}),), row_source_refs=(ref,),
    ).gaps] == ["no_exact_match"]
    assert [gap.reason for gap in build_ctgov_a_outcome_candidate_batch(
        (source,), (row.model_copy(update={"population": "登记结果人群（基线-轻度）"}),),
        row_source_refs=(ref,),
    ).gaps] == ["no_exact_match"]


def test_explicit_source_reference_keeps_direct_safety_count_identity(
    tmp_path: Path,
) -> None:
    title = "Number of Participants With Treatment-emergent Adverse Events (TEAEs)"
    source = _reported_count_source(tmp_path, title=title, classes=[{
        "categories": [{"measurements": [{"groupId": "OG1", "value": "8"}]}],
    }])
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues and len(atoms) == 1
    assert source.text_derivation is not None
    semantic = describe_safety_concept(title)
    row = SafetyRow(
        row_id="safe-source-map", product_id="dupilumab", trial_id="nct02277743",
        arm="Drug 200 mg", group_id="OG1",
        category=safety_category_zh(semantic.key), term=title,
        term_key=semantic.key, count_basis=semantic.count_basis,
        value=8, unit="人", measure_object="participant_count",
        numerator=8, denominator=35, time_window="Week 26",
    )
    ref = CtgovARowSourceRef(
        row_id=row.row_id, trial_id=row.trial_id or "",
        source_page_sha256=source.text_derivation.raw_asset.sha256,
        value_path=atoms[0].value_locator.field_path or "",
    )
    good = build_ctgov_a_safety_candidate_batch(
        (source,), (row,), row_source_refs=(ref,),
    )
    assert len(good.bound_rows) == 1 and not good.gaps
    assert good.bound_rows[0].source_text == "8"
    wrong_path = CtgovARowSourceRef(
        row_id=ref.row_id, trial_id=ref.trial_id,
        source_page_sha256=ref.source_page_sha256,
        value_path="$.resultsSection.adverseEventsModule.eventGroups[0].seriousNumAffected",
    )
    assert [gap.reason for gap in build_ctgov_a_safety_candidate_batch(
        (source,), (row,), row_source_refs=(wrong_path,),
    ).gaps] == ["source_reference_mismatch"]


def test_ctgov_study_capture_reopens_raw_and_preserves_calendar_day(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    capture = source_capture_from_ctgov_study(tmp_path, study)
    assert capture.source_id == "ctgov-nct04558918"
    assert capture.source_type == "clinical_trial_registry"
    assert capture.text_derivation == study.text_derivation
    assert capture.date_evidence("published_at").precision == "calendar_day"
    assert capture.date_evidence("first_disclosed_at").precision == "calendar_day"
    assert capture.locator.field_path == "$.protocolSection.identificationModule.nctId"


def test_ctgov_study_capture_rejects_identity_date_or_raw_drift(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    for changed in (
        study.model_copy(update={"nct_id": "NCT00000001"}),
        study.model_copy(update={"registry_posted_version_date": "2026-08-02"}),
        study.model_copy(update={"content_text": study.content_text.replace("PNH", "ABC")}),
    ):
        with pytest.raises(ValueError):
            source_capture_from_ctgov_study(tmp_path, changed)


def test_real_registry_atoms_enter_existing_fact_snapshot_with_exact_quotes(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert "result_context" not in ResearchFact.model_validate(
        payload["facts"][0]
    ).model_dump(mode="json")
    assert not issues
    reported = next(item for item in atoms if item.category == "outcome")
    zero = next(
        item for item in atoms
        if item.category == "sae" and item.group_id == "EG001"
        and item.value_quote == "0" and item.denominator_quote == "229"
    )
    facts = (
        *research_facts_from_ctgov_atom(reported),
        *research_facts_from_ctgov_atom(zero),
    )
    assert len(facts) == 3
    assert facts[0].raw_value == "10.3"
    assert facts[1].disclosure_state == "reported_zero"
    assert facts[2].raw_value == "229"
    assert facts[1].result_context is not None
    assert facts[1].result_context.group_id == "EG001"
    assert facts[1].result_context.term == zero.term
    assert "Week 28" in facts[1].result_context.timepoint
    assert facts[1].result_context.value_role == "affected_count"
    with pytest.raises(ValueError, match="领域不一致"):
        research_facts_from_ctgov_atom(zero, report_row_ref="efficacy:wrong")

    project = _project(tmp_path)
    contract = verify_project_workspace(project).contract
    claim = ResearchClaim(
        claim_id="direct-registry-atoms", claim_text="登记原始数值和独立分母字段",
        claim_kind="direct_evidence", fact_ids=tuple(item.fact_id for item in facts),
    )
    digest = sha256(b"NCT02277743:three-atomic-facts").hexdigest()
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=digest, created_at=source.acquired_at,
        sources=(source,), route_attempts=(), facts=facts, claims=(claim,),
    )

    assert len(lineage.source_version_ids) == 1
    assert len(lineage.fact_version_ids) == len(facts)
    with open_database(project / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT raw_value,disclosure_state,scientific_context_json "
            "FROM fact_versions WHERE fact_id IN (?,?,?) ORDER BY raw_value",
            tuple(item.fact_id for item in facts),
        ).fetchall()
        fragments = database.execute(
            "SELECT content_text,locator FROM evidence_fragments "
            "WHERE fragment_id IN (?,?,?)",
            tuple(lineage.fragment_by_fact_id[item.fact_id] for item in facts),
        ).fetchall()
    assert {row[0] for row in rows} == {"10.3", "0", "229"}
    assert any(row[0] == "0" and row[1] == "reported_zero" for row in rows)
    assert any('"group_id":"EG001"' in row[2] for row in rows)
    assert {row[0] for row in fragments} == {"10.3", "0", "229"}
    assert all('"field_path":"$.' in row[1] for row in fragments)


def test_source_fact_version_is_independent_of_a_or_b_consumer_row(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item) for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    atom = next(
        item for item in extract_ctgov_atomic_results(source)[0]
        if item.category == "outcome" and item.numerator is None
    )
    raw_fact = research_facts_from_ctgov_atom(atom)[0]
    a_fact = raw_fact.model_copy(update={"row_ref": "efficacy:a-row"})
    b_fact = raw_fact.model_copy(update={"row_ref": "b:evidence-row"})
    claim = ResearchClaim(
        claim_id="same-source-atom", claim_text="同一登记原子",
        claim_kind="direct_evidence", fact_ids=(raw_fact.fact_id,),
    )
    project = _project(tmp_path)
    contract = verify_project_workspace(project).contract
    arguments = dict(
        project_root=project, project_id=contract.project_id, contract_version=1,
        data_cutoff=contract.data_cutoff, created_at=source.acquired_at,
        sources=(source,), route_attempts=(), claims=(claim,),
    )
    first = ingest_research_evidence(
        **arguments, report_kind="A", facts=(a_fact,),
        scientific_content_digest=sha256(b"r24-a-consumer").hexdigest(),
    )
    second = ingest_research_evidence(
        **arguments, report_kind="B", facts=(b_fact,),
        scientific_content_digest=sha256(b"r24-b-consumer").hexdigest(),
    )
    assert first.fact_version_by_ref[a_fact.row_ref] == (
        second.fact_version_by_ref[b_fact.row_ref]
    )
    with open_database(project / "state/project.sqlite") as database:
        versions = database.execute(
            "SELECT scientific_context_json FROM fact_versions WHERE fact_id=?",
            (raw_fact.fact_id,),
        ).fetchall()
    assert len(versions) == 1
    assert "row_ref" not in json.loads(versions[0][0])


def test_missing_affected_count_never_becomes_a_zero_atom_or_fact() -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT05131477"
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    missing = next(
        issue for issue in issues
        if issue.source_path.endswith("seriousEvents[16].stats[7].numAffected")
    )
    assert missing.status == "missing"
    assert "未知，待核" in missing.reason_zh
    assert all(
        atom.value_locator.field_path != f"$.{missing.source_path}"
        for atom in atoms
    )
    assert all(
        fact.locator.field_path != f"$.{missing.source_path}"
        for atom in atoms for fact in research_facts_from_ctgov_atom(atom)
    )


def test_registry_explicitly_without_results_is_not_a_parse_failure() -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item) for item in payload["sources"]
        if item["query_or_identifier"] == "NCT04875169"
    )
    record = json.loads(source.content_text)
    assert record["hasResults"] is False and "resultsSection" not in record
    assert extract_ctgov_atomic_results(source) == ((), ())
    record["hasResults"] = True
    with pytest.raises(ResearchPackageError, match="resultsSection"):
        extract_ctgov_atomic_results(
            source.model_copy(update={"content_text": json.dumps(record)})
        )


def test_zero_over_zero_is_undefined_but_other_registry_results_survive() -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item) for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    record = json.loads(source.content_text)
    measure = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    measure["unitOfMeasure"] = "Participants"
    measurement = measure["classes"][0]["categories"][0]["measurements"][0]
    measure["classes"][0]["categories"][0]["measurements"] = [measurement]
    measurement["value"] = "0"
    group_id = measurement["groupId"]
    count = next(
        item for denom in measure["denoms"] for item in denom["counts"]
        if item["groupId"] == group_id
    )
    count["value"] = "0"
    event_group = record["resultsSection"]["adverseEventsModule"]["eventGroups"][1]
    event_group["seriousNumAffected"] = 0
    event_group["seriousNumAtRisk"] = 0
    changed = source.model_copy(update={"content_text": json.dumps(record)})
    atoms, issues = extract_ctgov_atomic_results(changed)
    assert atoms
    zero_issues = [item for item in issues if "0/0" in item.reason_zh]
    assert {item.category for item in zero_issues} >= {"outcome", "sae"}
    assert all(item.status == "missing" for item in zero_issues)
    assert all("NumAtRisk" in item.source_path or ".denoms[" in item.source_path
               for item in zero_issues)
    # The reported outcome 0 and denominator 0 are still two source atoms;
    # only their 0/0 percentage is undefined. AE event-group raw n/N also
    # remain source atoms; no undefined rate may enter a numeric plot.
    outcome_zero = next(item for item in zero_issues if item.category == "outcome")
    assert any(
        atom.result_key == outcome_zero.result_key
        and atom.numerator == atom.denominator == 0
        and atom.display_value == 0 and atom.display_unit == "人"
        for atom in atoms
    )
    assert any(
        atom.result_key == item.result_key
        and atom.numerator == atom.denominator == 0
        and atom.display_value == 0 and atom.display_unit == "人"
        for item in zero_issues if item.category == "sae" for atom in atoms
    )


def test_verified_registry_outcome_binds_exact_a_row_and_visible_payload(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    atom = next(
        item for item in extract_ctgov_atomic_results(source)[0]
        if item.category == "outcome" and item.value_quote == "10.3"
    )
    report = ReportAPortalData.model_validate(payload["report_data"])
    row = next(
        item for item in report.efficacy
        if item.trial_id.casefold() == atom.trial_id.casefold()
        and item.value == atom.display_value
        and item.arm_detail == atom.group_title
        and item.endpoint == atom.endpoint
    )
    bound, facts = bind_ctgov_outcome_to_a_row(source, atom, row)
    assert bound.source_field_path == atom.value_locator.field_path
    assert bound.source_text == atom.value_quote == facts[0].original_text
    assert bound.source_version_id is not None
    assert bound.group_id == atom.group_id
    real_batch = build_ctgov_a_outcome_candidate_batch((source,), (row,))
    assert real_batch.bound_rows == (bound,)
    assert real_batch.facts == facts
    assert real_batch.claims[0].claim_text == "ClinicalTrials.gov 登记结局原始数值"
    assert facts[0].row_ref == f"efficacy:{row.row_id}"
    assert facts[0].result_context is not None
    assert facts[0].result_context.group_title == atom.group_title
    assert atom.raw_unit == "percentage of participants"
    original_unit_row = EfficacyRow.model_validate({
        **row.model_dump(mode="json"), "unit": atom.raw_unit,
    })
    original_unit_bound, original_unit_facts = bind_ctgov_outcome_to_a_row(
        source, atom, original_unit_row
    )
    assert original_unit_bound.value == row.value
    assert original_unit_facts[0].result_context is not None
    assert original_unit_facts[0].result_context.source_unit == atom.raw_unit
    with pytest.raises(ValueError):
        bind_ctgov_outcome_to_a_row(
            source, atom, row.model_copy(update={"unit": "percentage reduction"})
        )

    ae_atom = next(
        item for item in extract_ctgov_atomic_results(source)[0]
        if item.category == "sae" and item.term == "任何SAE"
        and item.group_id == "EG001" and item.value_quote == "7"
    )
    safety_row = next(
        item for item in report.safety
        if item.trial_id and item.trial_id.casefold() == ae_atom.trial_id.casefold()
        and item.term == ae_atom.term and item.arm_detail == ae_atom.group_title
        and item.numerator == ae_atom.numerator
    )
    with pytest.raises(ValueError, match="时间"):
        bind_ctgov_ae_to_a_row(source, ae_atom, safety_row)
    corrected_safety = safety_row.model_copy(update={"time_window": ae_atom.timepoint})
    bound_safety, ae_facts, ae_claim = bind_ctgov_ae_to_a_row(
        source, ae_atom, corrected_safety
    )
    assert bound_safety.source_field_path == ae_atom.value_locator.field_path
    assert bound_safety.source_text == "7"
    assert (ae_facts[0].original_text, ae_facts[1].original_text) == ("7", "229")
    assert ae_claim.fact_ids == (ae_facts[0].fact_id, ae_facts[1].fact_id)
    assert ae_claim.claim_kind == "deterministic_calculation"
    for changed in (
        corrected_safety.model_copy(update={"denominator": 228}),
        corrected_safety.model_copy(update={"value": 3.2}),
        corrected_safety.model_copy(update={"arm_detail": "另一剂量组"}),
        corrected_safety.model_copy(update={"source_text": "3.1%"}),
    ):
        with pytest.raises(ValueError):
            bind_ctgov_ae_to_a_row(source, ae_atom, changed)

    rendered = ReportAPortalData.model_validate({
        **report.model_dump(mode="json"),
        "efficacy": [
            bound.model_dump(mode="json") if item.row_id == row.row_id
            else item.model_dump(mode="json")
            for item in report.efficacy
        ],
        "safety": [
            bound_safety.model_dump(mode="json") if item.row_id == safety_row.row_id
            else item.model_dump(mode="json")
            for item in report.safety
        ],
    })
    _validate_bound_ctgov_a_results(rendered, (source,), (*facts, *ae_facts), (ae_claim,))
    render_report_a_site(rendered, tmp_path / "site")
    report_js = (tmp_path / "site/data/report.js").read_text()
    assert bound.source_field_path in report_js
    assert bound.source_version_id in report_js
    assert bound_safety.source_field_path in report_js

    for changed in (
        row.model_copy(update={"trial_id": "nct00000000"}),
        row.model_copy(update={"value": 10.4}),
        row.model_copy(update={"arm_detail": "另一剂量组"}),
        row.model_copy(update={"group_id": "OG999"}),
        row.model_copy(update={"source_text": "编造引文"}),
    ):
        with pytest.raises(ValueError):
            bind_ctgov_outcome_to_a_row(source, atom, changed)

    for bad_facts in (
        (facts[0].model_copy(update={"original_text": "11.3"}),),
        (facts[0].model_copy(update={"row_ref": "efficacy:wrong"}),),
        (
            facts[0],
            next(
                ResearchFact.model_validate(item) for item in payload["facts"]
                if item["row_ref"] == facts[0].row_ref
            ),
        ),
    ):
        with pytest.raises(ValueError):
            _validate_bound_ctgov_a_results(rendered, (source,), bad_facts)
    for bad_facts, bad_claims in (
        ((*facts, ae_facts[0]), (ae_claim,)),
        ((*facts, *ae_facts), ()),
        ((*facts, ae_facts[0], ae_facts[1].model_copy(update={"original_text": "228"})),
         (ae_claim,)),
    ):
        with pytest.raises(ValueError):
            _validate_bound_ctgov_a_results(
                rendered, (source,), bad_facts, bad_claims
            )
    altered_rows = [
        item.model_copy(update={"source_field_path": "$.wrong"})
        if item.row_id == row.row_id else item
        for item in rendered.efficacy
    ]
    with pytest.raises(ValueError):
        _validate_bound_ctgov_a_results(
            rendered.model_copy(update={"efficacy": tuple(altered_rows)}),
            (source,), facts,
        )

    # The actual pre-review package boundary consumes the same verifier. The
    # historical AD package has an unrelated known missing SAE field, so this
    # negative assertion targets the earlier atomic binding failure only.
    candidate = json.loads(json.dumps(payload))
    candidate.pop("scientific_review", None)
    candidate["report_data"]["efficacy"] = [
        {**bound.model_dump(mode="json"), "source_text": "编造引文"}
        if item["row_id"] == row.row_id else item
        for item in candidate["report_data"]["efficacy"]
    ]
    obsolete = [
        item["fact_id"] for item in candidate["facts"]
        if item["row_ref"] == facts[0].row_ref
    ]
    candidate["facts"] = [
        item for item in candidate["facts"]
        if item["fact_id"] not in obsolete
    ] + [facts[0].model_dump(mode="json")]
    for claim in candidate["claims"]:
        claim["fact_ids"] = [
            item for item in claim["fact_ids"] if item not in obsolete
        ]
    with pytest.raises(ValueError, match="冲突的source_text"):
        FreshAResearchContent.model_validate(candidate)


def test_ae_rate_derivation_is_version_bound_and_restorable(tmp_path: Path) -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    atom = next(
        item for item in extract_ctgov_atomic_results(source)[0]
        if item.category == "sae" and item.term == "任何SAE"
        and item.group_id == "EG001" and item.value_quote == "7"
    )
    report = ReportAPortalData.model_validate(payload["report_data"])
    row = next(
        item for item in report.safety
        if item.trial_id and item.trial_id.casefold() == atom.trial_id.casefold()
        and item.term == atom.term and item.arm_detail == atom.group_title
        and item.numerator == atom.numerator
    )
    bound, facts, claim = bind_ctgov_ae_to_a_row(
        source, atom, row.model_copy(update={"time_window": atom.timepoint})
    )
    assert claim.calculation is not None
    assert claim.calculation.scope_row_ref == f"safety:{bound.row_id}"
    project = _project(tmp_path)
    contract = verify_project_workspace(project).contract
    arguments = dict(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=sha256(b"NCT02277743:AE:7/229").hexdigest(),
        created_at=source.acquired_at, sources=(source,), route_attempts=(),
        facts=facts,
    )
    bad_calculation = claim.calculation.model_copy(update={"output_value": 3.2})
    with pytest.raises(ValueError, match="计算输出"):
        ingest_research_evidence(
            **arguments, claims=(claim.model_copy(update={"calculation": bad_calculation}),)
        )
    with open_database(project / "state/project.sqlite") as database:
        assert database.execute("SELECT count(*) FROM source_versions").fetchone()[0] == 0

    lineage = ingest_research_evidence(**arguments, claims=(claim,))
    snapshot = SnapshotStore(project).read(lineage.evidence_snapshot)
    calculations = [
        item for item in snapshot["closure"]["derivations"]
        if item["derivation_kind"] == "calculation"
    ]
    assert len(calculations) == 1
    calculation = calculations[0]
    assert calculation["rule_version"] == "1"
    assert calculation["input_fragment_ids"] == [
        lineage.fragment_by_fact_id[item.fact_id] for item in facts
    ]
    assert calculation["output"]["input_fact_version_ids"] == [
        lineage.fact_version_by_ref[item.fact_id] for item in facts
    ]
    assert calculation["output"]["value"] == 3.1
    assert calculation["output"]["scope_row_ref"] == f"safety:{bound.row_id}"
    with open_database(project / "state/project.sqlite") as database:
        recorded = database.execute(
            "SELECT output_json FROM evidence_derivations WHERE derivation_kind='calculation'"
        ).fetchone()
    assert recorded is not None
    assert json.loads(recorded[0]) == calculation["output"]
    repeated = ingest_research_evidence(**arguments, claims=(claim,))
    assert repeated.evidence_snapshot.snapshot_id == lineage.evidence_snapshot.snapshot_id
    with open_database(project / "state/project.sqlite") as database:
        assert database.execute(
            "SELECT count(*) FROM evidence_derivations WHERE derivation_kind='calculation'"
        ).fetchone() == (1,)

    report_data = report.model_copy(update={
        "safety": tuple(
            bound if item.row_id == row.row_id else item for item in report.safety
        )
    })
    public_lineage = ResearchLineage(
        package_digest=arguments["scientific_content_digest"],
        evidence_snapshot=lineage.evidence_snapshot,
        claim_snapshot_id="test-claim-snapshot",
        coverage_set_id="test-coverage-set",
        coverage_projection_id="test-coverage-projection",
        claim_ids=lineage.claim_ids,
        source_version_ids=lineage.source_version_ids,
        source_fragment_ids=lineage.source_fragment_ids,
        fact_version_ids=lineage.fact_version_ids,
        fragment_ids=lineage.fragment_ids,
    )
    visible = project_a_calculation_evidence(project, report_data, public_lineage)
    assert len(visible) == 1
    assert visible[0].row_id == bound.row_id
    assert (visible[0].numerator_quote, visible[0].denominator_quote) == ("7", "229")
    assert visible[0].source_version_id == bound.source_version_id
    assert visible[0].numerator_field_path == bound.source_field_path
    assert visible[0].denominator_field_path != visible[0].numerator_field_path
    public_sources = PublicProvenance(
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        report_data_digest=sha256(report_data.model_dump_json().encode("utf-8")).hexdigest(),
        sources=(PublicSource(
            source_version_id=visible[0].source_version_id,
            label=source.title,
            url=source.url,
            source_type="临床试验登记",
            published_at=(
                source.published_at.date().isoformat()
                if source.published_at is not None else "未知（来源未明确公开）"
            ),
            data_cutoff=report_data.data_cutoff.date().isoformat(),
            limitation="此处只核对一条安全性比例，不代表全站来源闭包。",
        ),),
    )
    render_report_a_site(
        report_data, tmp_path / "calculation-site",
        calculation_evidence=visible, public_provenance=public_sources,
    )
    report_js = (tmp_path / "calculation-site/data/report.js").read_text()
    assert '"calculation_evidence"' in report_js
    assert visible[0].denominator_field_path in report_js
    wrong_row = bound.model_copy(update={"value": 3.2})
    with pytest.raises(ValueError, match="计算派生"):
        project_a_calculation_evidence(
            project,
            report_data.model_copy(update={
                "safety": tuple(
                    wrong_row if item.row_id == row.row_id else item
                    for item in report_data.safety
                )
            }),
            public_lineage,
        )

    restored_root = tmp_path / "restored-evidence"
    restored = SnapshotStore(restored_root).restore_evidence_manifest(
        project / lineage.evidence_snapshot.relative_path
    )
    assert restored.snapshot_id == lineage.evidence_snapshot.snapshot_id
    with open_database(restored_root / "state/project.sqlite") as database:
        restored_output = database.execute(
            "SELECT output_json FROM evidence_derivations WHERE derivation_kind='calculation'"
        ).fetchone()
    assert restored_output is not None
    assert json.loads(restored_output[0]) == calculation["output"]
