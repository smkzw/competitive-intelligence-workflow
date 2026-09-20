"""Task 5.5：A 类新鲜来源研究包必须形成真实、闭合、可追溯的报告谱系。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.run_service import MANIFEST_RELATIVE_PATH, run_project
from ci_workflow.application.source_research_service import (
    ResearchPackageError,
    compute_research_content_digest,
    load_fresh_a_research_package,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.sqlite import open_database


def _package_payload() -> dict[str, object]:
    source_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    report = json.loads(source_path.read_text(encoding="utf-8"))
    report["report_version"] = "v1"
    trial_by_product = {row["product_id"]: row["id"] for row in report["trials"]}
    for row in report["safety"]:
        row["trial_id"] = trial_by_product[row["product_id"]]
        row["arm"] = "治疗组"
    report["safety"].extend(
        {
            **row,
            "row_id": f"{row['row_id']}-control",
            "arm": "对照组",
        }
        for row in list(report["safety"])
        if row["term"] in {"任何TEAE", "任何SAE"} and row["value"] is not None
    )
    locator = {
        "document_role": "测试用已存来源",
        "field_path": "完整结构化记录",
        "url": "https://clinicaltrials.gov/study/NCT00000001",
    }
    facts: list[dict[str, object]] = []

    def add_fact(row_ref: str, entity_id: str, name: str, field_id: str) -> None:
        facts.append(
            {
                "fact_id": f"fact-{len(facts) + 1}",
                "row_ref": row_ref,
                "entity_id": entity_id,
                "entity_type": "drug" if row_ref.startswith("product:") else "trial",
                "canonical_name": name,
                "field_id": field_id,
                "raw_value": name,
                "normalized_value": name,
                "disclosure_state": "reported_value",
                "source_id": "source-ctgov-recorded",
                "locator": locator,
                "original_text": f"{row_ref} 的已存来源定位文本",
            }
        )

    for row in report["products"]:
        add_fact(f"product:{row['id']}", row["id"], row["name"], "product.status")
    for row in report["trials"]:
        add_fact(f"trial:{row['id']}", row["id"], row["name"], "trial.status")
    for row in report["efficacy"]:
        add_fact(
            f"efficacy:{row['row_id']}",
            row["trial_id"],
            row["endpoint"],
            "result.efficacy",
        )
    for row in report["safety"]:
        add_fact(
            f"safety:{row['row_id']}",
            row["product_id"],
            row["term"],
            "result.safety",
        )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "indication": "特应性皮炎",
        "data_cutoff": report["data_cutoff"],
        "report_version": "v1",
        "universe_closed": True,
        "universe_product_ids": [row["id"] for row in report["products"]],
        "report_data": report,
        "sources": [
            {
                "source_id": "source-ctgov-recorded",
                "route_id": "clinicaltrials-gov-api",
                "source_type": "clinical_trial_registry",
                "title": "ClinicalTrials.gov 已存测试记录",
                "url": "https://clinicaltrials.gov/study/NCT00000001",
                "query_or_identifier": "NCT00000001",
                "language": "en",
                "access_method": "official_api",
                "media_type": "application/json",
                "content_text": source_path.read_text(encoding="utf-8"),
                "acquired_at": "2026-08-18T09:00:00+08:00",
                "published_at": "2026-07-01T00:00:00+00:00",
                "effective_at": None,
                "first_disclosed_at": "2026-07-01T00:00:00+00:00",
                "locator": locator,
            }
        ],
        "facts": facts,
        "claims": [
            {
                "claim_id": "claim-a-complete",
                "claim_text": "报告所列产品、试验及公开结果均可回到已存来源。",
                "claim_kind": "direct_evidence",
                "fact_ids": [item["fact_id"] for item in facts],
            }
        ],
        "gate_status": "passed",
    }
    payload["scientific_review"] = {
        "reviewer_id": "independent-review-fixture",
        "reviewer_role": "independent_scientific_verifier",
        "status": "accepted",
        "reviewed_at": "2026-08-18T10:00:00+08:00",
        "reviewed_content_digest": compute_research_content_digest(payload),
        "observations": ["测试包关系闭合"],
    }
    return payload


def test_fresh_a_package_builds_real_source_fact_claim_snapshot_lineage(
    tmp_path: Path,
) -> None:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    project = create_project_workspace(tmp_path / "项目", contract)
    package_path = project / "evidence/library/a-research-package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(_package_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = run_project(project, capability_probe=StaticCapabilityProbe())

    assert result.outcome == "completed"
    assert {
        "universe",
        "route",
        "ingest",
        "extract",
        "resolve",
        "gate:A",
        "snapshot:A",
        "analyze:A",
        "format:A",
    } <= set(result.node_summary)
    assert "scientific_qc:A" not in result.node_summary
    run_manifest = json.loads(
        (project / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    assert run_manifest["report_states"] == {"A": "rendered_unreviewed"}
    assert run_manifest["scientific_review_portal_bindings"]["A"]["site_total_bytes"] > 0
    manifest = json.loads(
        (project / "reports/A/v1/html.manifest.json").read_text(encoding="utf-8")
    )
    with open_database(project / "state/project.sqlite") as database:
        assert database.execute("SELECT count(*) FROM source_versions").fetchone()[0] == 1
        assert database.execute("SELECT count(*) FROM fact_versions").fetchone()[0] > 20
        assert database.execute("SELECT count(*) FROM claim_versions").fetchone()[0] == 1
        report_snapshot = database.execute(
            "SELECT snapshot_id FROM report_snapshots"
        ).fetchone()[0]
        assert database.execute("SELECT count(*) FROM coverage_sets").fetchone()[0] == 1
        assert database.execute("SELECT count(*) FROM coverage_projections").fetchone()[0] == 1
    assert manifest["report_snapshot_id"] == report_snapshot
    assert manifest["evidence_reference_ids"]
    assert manifest["evidence_snapshot_id"] != manifest["claim_snapshot_id"]


def test_fresh_a_package_rejects_missing_core_row_before_render(tmp_path: Path) -> None:
    payload = _package_payload()
    payload["facts"] = payload["facts"][:-1]  # type: ignore[index]
    payload["claims"][0]["fact_ids"] = [  # type: ignore[index]
        item["fact_id"] for item in payload["facts"]  # type: ignore[union-attr]
    ]
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ResearchPackageError, match="核心受众事实缺少来源绑定"):
        load_fresh_a_research_package(path)
