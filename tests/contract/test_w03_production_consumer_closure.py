from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.fresh_b_research_package import load_fresh_b_research_package
from ci_workflow.application.fresh_c_research_package import (
    derive_c_research_facts,
    load_fresh_c_research_package,
)
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    _page_records,
    _safety_records,
)
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import SnapshotStore

ROOT = Path(__file__).resolve().parents[2]


def test_pnh_a_builder_does_not_manufacture_cross_module_edges() -> None:
    source = (ROOT / "packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py").read_text()
    assert "_related_og_ids" not in source
    assert '"related_group_ids"' not in source


def test_pnh_b_c_builders_use_exact_wildcard_free_json_paths() -> None:
    for name in ("build_pnh_b_audit.py", "build_pnh_c_audit.py"):
        source = (ROOT / "packets/2026-09-11-pnh-vertical" / name).read_text()
        assert '"field_path": "studies[]"' not in source
        assert 'f"studies[]/' not in source


def test_report_a_efficacy_chart_uses_projection_not_raw_value() -> None:
    source = (ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js").read_text()
    body = source.split("function renderEfficacy(host)", 1)[1].split("function color", 1)[0]
    assert "numeric_projection" in body
    assert "item.value" not in body
    assert "item.unit" not in body


def test_report_b_matrix_has_no_arbitrary_mapping_contract() -> None:
    source = (ROOT / "src/ci_workflow/renderers/portal/report_b.py").read_text()
    assert "matrix_view: Mapping[str, Any]" not in source
    assert "matrix_views: Mapping[str, Any]" not in source


def test_pnh_b_builder_emits_closed_typed_nonpercent_matrix_projection() -> None:
    builder = _load_builder("build_pnh_b_audit.py")
    common = {
        "product_id": "drug-x",
        "trial_id": "nct-w03",
        "endpoint_family_id": "hb",
        "actual_timepoint": 24.0,
        "analysis_population": "ITT",
        "unit": "g/L",
        "analysis_form": "change_from_baseline",
        "direction": "higher_is_better",
    }
    matrix = builder.build_typed_matrix_view(
        [
            {**common, "row_id": "tx", "arm_role": "treatment", "value": 18.0},
            {**common, "row_id": "cx", "arm_role": "control", "value": 4.0},
        ],
        [
            {
                "trial_id": "nct-w03",
                "arm_role": "treatment",
                "count_basis": "participants",
                "value": 12,
                "numerator": 12,
                "denominator": 40,
                "unit": "例",
                "time_window_zh": "24周治疗期",
            }
        ],
    )
    row = matrix["rows"][0]
    assert row["treatment_projection"]["kind"] == "adjusted_estimate"
    assert row["treatment_projection"]["plot_unit"] == "g/L"
    assert row["safety_projection"]["plot_value"] == 30.0
    assert row["size_projection"]["size_basis"] == "治疗组安全性分析人数"


def test_b_safety_term_key_survives_builder_payload_filter_and_table() -> None:
    builder = _load_builder("build_pnh_b_audit.py")
    typed_row = {
        "row_id": "typed-absence-sae",
        "product_id": "iptacopan",
        "trial_id": "nct04558918",
        "family": "sae",
        "source_term": "No SAEs",
        "term_key": "absence_sae",
        "polarity": "negative_presence",
        "grade_set": [],
        "seriousness": "serious",
        "teae": False,
        "relatedness": "unspecified",
        "parent": None,
        "children": [],
        "count_basis": "participants",
        "at_risk_stat": "serious",
        "arm_label": "Iptacopan",
        "value": 0,
        "numerator": 0,
        "denominator": 62,
        "unit": "%",
        "time_window_zh": "24周治疗期",
    }
    portal_row = builder.build_portal_safety_rows([typed_row])[0]
    assert portal_row["term_key"] == "absence_sae"

    payload = json.loads(
        (ROOT / "fixtures/positive/b-pnh/inputs/report-data.json").read_text(encoding="utf-8")
    )
    payload["safety"].append(portal_row)
    payload["safety_views"]["facts"].append(typed_row)
    data = ReportBPortalData.model_validate(payload)
    names = {item.id: item.name for item in data.products}
    trial_names = {item.id: item.name for item in data.trials}
    records = _safety_records(data, names, trial_names)
    typed_record = next(row for row, _source in records if row["row_id"] == "typed-absence-sae")
    assert typed_record["clinical_concept"] == "absence_sae"
    table_rows = _page_records(
        data,
        page_id="safety",
        names=names,
        trial_names=trial_names,
        efficacy=(),
        safety=records,
    )
    assert any(row["term_key"] == "absence_sae" for row, _source in table_rows)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: (
            row["treatment_projection"].update({"plot_unit": "g/L"}),
            row["control_projection"].update({"plot_unit": "%"}),
        ),
        lambda row: row["size_projection"].update(
            {"plot_unit": "%", "plot_value": 40, "size_basis": ""}
        ),
    ],
    ids=("g-per-l-versus-percent", "forged-percent-size"),
)
def test_report_b_json_boundary_rejects_forged_typed_matrix(mutate) -> None:
    payload = json.loads(
        (ROOT / "fixtures/positive/b-pnh/inputs/report-data.json").read_text(encoding="utf-8")
    )
    row = payload["matrix_view"]["rows"][0]
    mutate(row)
    with pytest.raises(ValueError, match="投影|单位|气泡|口径|facet|canonical"):
        ReportBPortalData.model_validate(payload)


def _load_builder(name: str):
    path = ROOT / "packets/2026-09-11-pnh-vertical" / name
    spec = importlib.util.spec_from_file_location("w03_" + name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_production_b_c_builder_rows_roundtrip_w01_and_manifest_only_restore(
    tmp_path: Path,
) -> None:
    b_builder = _load_builder("build_pnh_b_audit.py")
    c_builder = _load_builder("build_pnh_c_audit.py")
    payload = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT-W03"},
                    "outcomesModule": {
                        "primaryOutcomes": [{"measure": "Response", "timeFrame": "Week 12"}]
                    },
                },
                "resultsSection": {
                    "outcomeMeasuresModule": {
                        "outcomeMeasures": [
                            {"classes": [{"categories": [{"measurements": [{"value": "12"}]}]}]}
                        ]
                    }
                },
            }
        ]
    }
    content_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    b_row = next(
        b_builder.b_facts(
            {
                "efficacy": [
                    {
                        "row_id": "eff-1",
                        "product_id": "drug-x",
                        "trial_id": "nct-w03",
                        "endpoint": "Response",
                        "timepoint": "Week 12",
                        "unit": "人",
                        "arm": "Drug X",
                        "value": 12,
                        "population": "ITT",
                        "source_field_path": (
                            "$.studies[0].resultsSection.outcomeMeasuresModule."
                            "outcomeMeasures[0].classes[0].categories[0]."
                            "measurements[0].value"
                        ),
                        "source_text": "12",
                    }
                ]
            }
        )
    )
    c_row = c_builder._row(
        "nct-w03",
        "drug-x",
        "NCT-W03",
        1,
        "endpoint",
        "primary_endpoint_definition",
        "Response",
        seq="pri0",
        field_path="$.studies[0].protocolSection.outcomesModule.primaryOutcomes[0].measure",
        source_value="Response",
        endpoint_key="primary",
        outcome_id="pri0",
        period="overall",
        timepoint="Week 12",
    )
    acquired = datetime(2026, 9, 22, tzinfo=UTC)
    source = SourceCapture(
        source_id="prod-source",
        route_id="production-pnh-builders",
        source_type="clinical_trial_registry",
        title="Production PNH builder replay",
        url="https://clinicaltrials.gov/",
        query_or_identifier="NCT-W03",
        language="en",
        access_method="persisted_fixture",
        content_text=content_text,
        acquired_at=acquired,
        published_at=None,
        effective_at=None,
        first_disclosed_at=acquired,
        locator=EvidenceLocator(document_role="registry-search-page", field_path="$.studies"),
    )
    facts = (
        ResearchFact(
            fact_id="prod-b",
            row_ref=b_row["row_id"],
            entity_id="nct-w03",
            entity_type="trial",
            canonical_name="Response",
            field_id="result.efficacy",
            raw_value="12",
            normalized_value="12",
            disclosure_state="reported_value",
            source_id="prod-source",
            locator=EvidenceLocator(
                document_role="registry-search-page", field_path=b_row["source_field_path"]
            ),
            original_text=b_row["source_text"],
        ),
        ResearchFact(
            fact_id="prod-c",
            row_ref=c_row["row_id"],
            entity_id="nct-w03",
            entity_type="trial",
            canonical_name="Primary endpoint",
            field_id="design.endpoint",
            raw_value="Response",
            normalized_value="Response",
            disclosure_state="reported_value",
            source_id="prod-source",
            locator=EvidenceLocator.model_validate(c_row["source_locator"]),
            original_text=c_row["source_text"],
        ),
    )
    project = tmp_path / "ingested"
    apply_migrations(project / "state/project.sqlite")
    lineage = ingest_research_evidence(
        project_root=project,
        project_id="w03-prod",
        contract_version=1,
        report_kind="B",
        data_cutoff=acquired,
        scientific_content_digest=sha256(content_text.encode()).hexdigest(),
        created_at=acquired,
        sources=(source,),
        route_attempts=(),
        facts=facts,
        claims=(
            ResearchClaim(
                claim_id="prod-chain",
                claim_text="B/C production rows replay",
                claim_kind="direct_evidence",
                fact_ids=("prod-b", "prod-c"),
            ),
        ),
    )
    exported = tmp_path / "manifest.json"
    exported.write_bytes((project / lineage.evidence_snapshot.relative_path).read_bytes())
    restored = tmp_path / "restored"
    SnapshotStore(restored).restore_evidence_manifest(exported)
    assert (restored / "state/project.sqlite").is_file()


def test_fixed_cas_a_to_b_c_full_chain_roundtrips_every_fact_and_site_bytes(
    tmp_path: Path,
) -> None:
    packet = ROOT / "packets/2026-09-11-pnh-vertical"
    build_root = tmp_path / "builder-inputs"
    build_root.mkdir()
    shutil.copyfile(packet / "pnh-b-payload.json", build_root / "pnh-b-payload.json")

    contract = create_project_contract(
        indication="阵发性睡眠性血红蛋白尿症",
        reports=["B", "C"],
        outputs=["html"],
        cutoff="2026-09-06",
    )
    project = create_project_workspace(tmp_path / "project", contract)

    a_builder = _load_builder("build_pnh_a_payload.py")
    a_builder.OUT = build_root / "pnh-a-payload.json"
    a_builder.main()
    a_payload = json.loads(a_builder.OUT.read_text(encoding="utf-8"))
    consumed_rows = [*a_payload["efficacy"], *a_payload["safety"]]
    assert consumed_rows
    assert all(
        row.get("source_field_path") and row.get("source_text") is not None for row in consumed_rows
    )

    b_builder = _load_builder("build_pnh_b_audit.py")
    b_builder.HERE = build_root
    b_builder.PROJECT = project
    b_builder.main()
    c_builder = _load_builder("build_pnh_c_audit.py")
    c_builder.HERE = build_root
    c_builder.PROJECT = project
    c_builder.main()

    package_paths = {
        "B": project / "evidence/library/b-research-package.json",
        "C": project / "evidence/library/c-research-package.json",
    }
    packages = {
        "B": load_fresh_b_research_package(package_paths["B"]),
        "C": load_fresh_c_research_package(package_paths["C"]),
    }
    for report, package in packages.items():
        facts = package.facts if report == "B" else derive_c_research_facts(package)
        assert facts
        ingest_root = tmp_path / f"ingest-{report}"
        apply_migrations(ingest_root / "state/project.sqlite")
        lineage = ingest_research_evidence(
            project_root=ingest_root,
            project_id=contract.project_id,
            contract_version=contract.contract_version,
            report_kind=report,
            data_cutoff=package.data_cutoff,
            scientific_content_digest=package.research_content_digest,
            created_at=package.scientific_review.reviewed_at,
            sources=package.sources,
            route_attempts=package.route_attempts,
            facts=facts,
            claims=package.claims,
        )
        exported = tmp_path / f"{report}-manifest.json"
        exported.write_bytes((ingest_root / lineage.evidence_snapshot.relative_path).read_bytes())
        restored = tmp_path / f"restored-{report}"
        SnapshotStore(restored).restore_evidence_manifest(exported)
        assert (restored / "state/project.sqlite").is_file()

    from ci_workflow.renderers.portal.report_c import render_report_c_site

    site_root = tmp_path / "c-site"
    render_report_c_site(packages["C"].report_data, site_root)
    report_js = site_root / "data/report.js"
    assert report_js.is_file()
    assert sha256(report_js.read_bytes()).hexdigest()


def test_w03_browser_freeze_rebinds_report_data_sources_and_screenshots() -> None:
    freeze = ROOT / "packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze"
    manifest = json.loads((freeze / "site.manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "w03-browser-freeze-v2"
    report_js = freeze / manifest["generated"]["retained_report_js"]
    assert (
        sha256(report_js.read_bytes()).hexdigest()
        == (manifest["generated"]["retained_report_js_sha256"])
    )
    sitemap = freeze / manifest["generated"]["retained_sitemap"]
    assert (
        sha256(sitemap.read_bytes()).hexdigest()
        == (manifest["generated"]["retained_sitemap_sha256"])
    )
    report_source = report_js.read_text(encoding="utf-8")
    report_payload = json.loads(report_source.removeprefix("window.REPORT_C=").removesuffix(";\n"))
    report_trial_ids = sorted(trial["display_id"] for trial in report_payload["trials"])
    assert len(report_trial_ids) == 6
    assert manifest["generated"]["trial_display_ids"] == report_trial_ids

    for binding in [
        *manifest["fixed_cas"],
        *manifest["current_sources"],
        *manifest["journeys"],
        *manifest["screenshots"],
    ]:
        path = ROOT / binding["path"]
        assert path.is_file(), binding["path"]
        assert sha256(path.read_bytes()).hexdigest() == binding["sha256"]

    assert len(manifest["journeys"]) == 2
    assert len(manifest["screenshots"]) == 2
    assert not any("W03-repair-C-" in item["path"] for item in manifest["screenshots"])
    page_bindings = {item["page_id"]: item for item in manifest["generated"]["pages"]}
    assert page_bindings["endpoint-timepoint-matrix"]["route"] == ("/c/endpoint-timepoint-matrix")
    assert page_bindings["treatment-arms"]["route"] == "/c/treatment-arms"
    screenshot_bindings = {item["page_id"]: item for item in manifest["screenshots"]}
    for binding in manifest["journeys"]:
        receipt = json.loads((ROOT / binding["path"]).read_text(encoding="utf-8"))
        page_id = receipt["page_id"]
        assert page_id in {"endpoint-timepoint-matrix", "treatment-arms"}
        assert receipt["runner"] == "playwright-cli"
        assert receipt["report_js_sha256"] == sha256(report_js.read_bytes()).hexdigest()
        assert receipt["payload_trial_display_ids"] == report_trial_ids
        assert receipt["dom_trial_display_ids"] == report_trial_ids
        assert receipt["assertions"]["payload_matches_report_js"] is True
        assert receipt["assertions"]["dom_matches_payload"] is True
        assert receipt["assertions"]["all_trials_visible"] is True
        assert receipt["console"]["errors"] == []
        assert receipt["console"]["warnings"] == []
        assert receipt["page_sha256"] == page_bindings[page_id]["sha256"]
        screenshot = ROOT / receipt["screenshot"]["path"]
        assert sha256(screenshot.read_bytes()).hexdigest() == receipt["screenshot"]["sha256"]
        assert screenshot_bindings[page_id]["path"] == receipt["screenshot"]["path"]
        assert screenshot_bindings[page_id]["sha256"] == receipt["screenshot"]["sha256"]
