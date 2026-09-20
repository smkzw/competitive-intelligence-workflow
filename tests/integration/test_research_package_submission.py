from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.research_package_submission import (
    AUDIT_PACKAGE_PATH,
    SUBMISSION_MANIFEST_PATH,
    ResearchPackageSubmissionError,
    _capture_source_classification,
    load_product_research_submission,
    submit_product_research_package,
)
from ci_workflow.application.run_service import ContractConfigError, run_project
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.research_package import compute_universe_review_digest

ROOT = Path(__file__).resolve().parents[2]


def _expansion_receipts(product_ids: list[str], source_id: str) -> list[dict[str, object]]:
    specs = (
        ("alias-1", "alias", "0", "global-registry", product_ids),
        ("target-1", "target", "0", "global-registry", []),
        ("company-1", "company", "1", "china-registry", []),
        ("trial-1", "trial", "1", "china-registry", []),
        ("alias-2", "alias", "2", "global-registry", []),
        ("target-2", "target", "2", "china-registry", []),
    )
    return [
        {
            "receipt_id": receipt_id,
            "dimension": dimension,
            "round_id": round_id,
            "strategy_id": f"{dimension}-reverse-{round_id}",
            "route_ids": [route_id],
            "attempt_ids": [f"attempt-{receipt_id}"],
            "input_entity_ids": product_ids,
            "discovered_entity_ids": discovered,
            "source_ids": [source_id] if discovered else [],
            "query_sha256": hashlib.sha256(receipt_id.encode()).hexdigest(),
            "result_class": "success_with_evidence" if discovered else "searched_no_evidence",
            "diagnostic": None if discovered else "反向扩展无新增实体",
        }
        for receipt_id, dimension, round_id, route_id, discovered in specs
    ]


def _source_payload(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    # Use the existing synthetic registry-only A package for admission tests.
    # The real fixture's generic peer_reviewed_publication is deliberately not
    # reclassified or rewritten merely to make submission pass.
    from test_fresh_a_research_package import _package_payload

    payload = _package_payload()
    path = tmp_path / "synthetic-a-package.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, payload


def _bind_reviewed_universe(payload: dict[str, object]) -> None:
    closure = cast(dict[str, Any], payload["closure"])
    closure["review_digest_version"] = "2"
    closure["reviewed_universe_sha256"] = compute_universe_review_digest(
        sources=cast(list[dict[str, Any]], payload["sources"]),
        contract_identity=cast(dict[str, Any], payload["contract_identity"]),
        data_cutoff=cast(str, payload["data_cutoff"]),
        source_policy_id=cast(str, payload["source_policy_id"]),
        source_policy_version=cast(str, payload["source_policy_version"]),
        entities=cast(list[dict[str, Any]], payload["entities"]),
        routes=cast(list[dict[str, Any]], payload["routes"]),
        expansion_receipts=cast(list[dict[str, Any]], payload["expansion_receipts"]),
        closure=closure,
        report_payloads=cast(list[dict[str, Any]], payload.get("report_payloads", [])),
    )


def _audit_payload(
    project_id: str, report_bytes: bytes, report: dict[str, object]
) -> dict[str, object]:
    sources = cast(list[dict[str, Any]], report["sources"])
    product_ids = cast(list[str], report["universe_product_ids"])
    source_rows = []
    for item in sources:
        capture = SourceCapture.model_validate(item)
        source_type, role, classification = _capture_source_classification(capture.source_type)
        source_rows.append(
            {
                "source_id": item["source_id"],
                "locator_detail": capture.locator.model_dump(mode="json"),
                "text_derivation": (
                    capture.text_derivation.model_dump(mode="json")
                    if capture.text_derivation is not None else None
                ),
                "title": item["title"],
                "source_role": role,
                "source_type": source_type,
                "url": item["url"],
                "locator": item["locator"].get("url")
                or item["locator"].get("field_path")
                or "正文",
                "content_sha256": hashlib.sha256(capture.content_text.encode("utf-8")).hexdigest(),
                "retrieved_at": item["acquired_at"],
                "published_at": (
                    capture.published_at.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
                    if capture.published_at is not None else None
                ),
                "effective_at": (
                    capture.effective_at.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
                    if capture.effective_at is not None else None
                ),
                "publication_classification": classification,
                "access_state": "available",
            }
        )
    attempts = cast(list[dict[str, Any]], report.get("route_attempts", []))
    attempt_ids = [item["attempt_id"] for item in attempts]
    payload: dict[str, object] = {
        "schema_version": "1.3",
        "package_id": "audit-a-001",
        "contract_identity": {
            "project_id": project_id,
            "indication": "特应性皮炎",
            "contract_version": "1.3",
        },
        "reports": ["A"],
        "data_cutoff": "2026-07-31",
        "source_policy_id": "source-policy-v1",
        "source_policy_version": "1.1",
        "producer_id": "research-worker-1",
        "producer_context": "producer-context-1",
        "entities": [
            {
                "entity_id": product_id,
                "entity_type": "product",
                "name": product_id,
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": [source_rows[0]["source_id"]],
            }
            for product_id in product_ids
        ],
        "sources": source_rows,
        "routes": [
            {
                "route_id": "global-registry",
                "region": "global",
                "strategy_id": "global-baseline",
                "result_class": "completed",
                "attempt_ids": attempt_ids or ["global-complete"],
                "source_ids": [item["source_id"] for item in source_rows],
            },
            {
                "route_id": "china-registry",
                "region": "china",
                "strategy_id": "china-baseline",
                "result_class": "completed",
                "attempt_ids": attempt_ids or ["china-complete"],
                "source_ids": [item["source_id"] for item in source_rows],
            },
        ],
        "expansion_receipts": _expansion_receipts(product_ids, str(source_rows[0]["source_id"])),
        "closure": {
            "closed": True,
            "global_route_ids": ["global-registry"],
            "china_route_ids": ["china-registry"],
            "alias_expansion_receipts": ["alias-1", "alias-2"],
            "target_expansion_receipts": ["target-1", "target-2"],
            "company_expansion_receipts": ["company-1"],
            "trial_expansion_receipts": ["trial-1"],
            "independent_review_id": "review-1",
            "independent_reviewer_id": "independent-reviewer-1",
            "independent_context": "clean-context-1",
            "candidate_entity_ids": product_ids,
            "new_entity_ids_by_round": {"0": product_ids, "1": [], "2": []},
            "convergence_round_ids": ["1", "2"],
        },
        "report_payloads": [
            {
                "report": "A",
                "relative_path": "evidence/library/a-research-package.json",
                "content_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "content_schema_version": "1.0",
                "universe_product_ids": product_ids,
            }
        ],
        "metadata": {"origin": "autonomous-research"},
    }
    _bind_reviewed_universe(payload)
    return payload


def _project(tmp_path: Path) -> Path:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    return create_project_workspace(tmp_path / "project", contract)


def test_submission_binds_audit_and_scientific_payload_bytes(tmp_path: Path) -> None:
    project = _project(tmp_path)
    source_path, report = _source_payload(tmp_path)
    report_path = tmp_path / "report-package.json"
    report_path.write_bytes(source_path.read_bytes())
    report_bytes = report_path.read_bytes()
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            _audit_payload(contract["project_id"], report_bytes, report),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = submit_product_research_package(
        project, audit_package=audit, report_packages={"A": report_path}
    )
    assert result.replayed is False
    assert (project / AUDIT_PACKAGE_PATH).read_bytes() == audit.read_bytes()
    assert (project / "evidence/library/a-research-package.json").read_bytes() == report_bytes
    assert (project / SUBMISSION_MANIFEST_PATH).is_file()

    replay = load_product_research_submission(project)
    assert replay.replayed is True
    assert replay.package.package_id == "audit-a-001"


def test_submission_rejects_payload_drift_and_loose_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    report_path, report = _source_payload(tmp_path)
    report_bytes = report_path.read_bytes()
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    payload = _audit_payload(contract["project_id"], report_bytes, report)
    payload["report_payloads"][0]["content_sha256"] = "0" * 64  # type: ignore[index]
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ResearchPackageSubmissionError, match="审计包|摘要"):
        submit_product_research_package(
            project, audit_package=audit, report_packages={"A": report_path}
        )

    (project / "evidence/library/a-research-package.json").write_bytes(report_bytes)
    with pytest.raises(ContractConfigError, match="松散输入"):
        run_project(project, require_bound_submission=True)
    with pytest.raises(ResearchPackageSubmissionError, match="清单"):
        load_product_research_submission(project)


def test_submission_rejects_report_payload_that_drops_reviewed_candidate(
    tmp_path: Path,
) -> None:
    """报告载荷不得从独立复核并锁定的候选宇宙中删去竞品。"""
    project = _project(tmp_path)
    report_path, report = _source_payload(tmp_path)
    original_bytes = report_path.read_bytes()
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    audit_payload = _audit_payload(contract["project_id"], original_bytes, report)
    binding = cast(list[dict[str, object]], audit_payload["report_payloads"])[0]
    bound_products = cast(list[str], binding["universe_product_ids"])
    assert len(bound_products) > 1
    binding["universe_product_ids"] = bound_products[:-1]
    _bind_reviewed_universe(audit_payload)
    audit = tmp_path / "audit-dropped-candidate.json"
    audit.write_text(json.dumps(audit_payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ResearchPackageSubmissionError, match="候选宇宙|竞品"):
        submit_product_research_package(
            project, audit_package=audit, report_packages={"A": report_path}
        )


def test_submission_rejects_noncurrent_source_policy(tmp_path: Path) -> None:
    project = _project(tmp_path)
    report_path, report = _source_payload(tmp_path)
    report_bytes = report_path.read_bytes()
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    payload = _audit_payload(contract["project_id"], report_bytes, report)
    payload["source_policy_version"] = "0.9"
    _bind_reviewed_universe(payload)
    audit = tmp_path / "audit-old-policy.json"
    audit.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ResearchPackageSubmissionError, match="来源政策"):
        submit_product_research_package(
            project,
            audit_package=audit,
            report_packages={"A": report_path},
        )
