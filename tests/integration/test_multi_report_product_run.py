"""已提交 A/B/C 多报告产品运行：逐报告独立执行、状态聚合与幂等 resume。

- 多报告项目消费同一份严格提交（审计信封 + 每报告科学载荷），逐报告独立
  走既有单报告谱系管线；A/B/C 各自保留独立站点、清单与报告状态，不建立
  融合门户。
- 聚合结局诚实反映逐报告进度：全部渲染完成才 completed；任一报告等待恢复
  检索时保持 running，不伪装完成，也不丢弃已完成报告的产物。
- resume 幂等：已完成报告的节点全部按输入摘要复用，站点与复核请求字节
  保持不变，不产生新产物；未完成报告继续按既有恢复语义推进。
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

import pytest
from pypdf import PdfWriter

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.publication_manual_gate import (
    mark_publication_files_unavailable,
)
from ci_workflow.application.research_package_submission import (
    REPORT_PACKAGE_PATHS,
    submit_product_research_package,
)
from ci_workflow.application.run_service import (
    ContractConfigError,
    run_project,
    validate_run_manifest,
)
from ci_workflow.application.source_research_service import compute_research_content_digest
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.research_package import compute_universe_review_digest
from ci_workflow.gates.blocker_audit import (
    BlockerAuditDriftError,
    validate_existing_blocker_package,
)
from ci_workflow.storage.event_store import EventStore
from tests.integration.test_fresh_a_research_package import (
    _package_payload as _a_package_payload,
)
from tests.integration.test_fresh_c_research_package import (
    _content_payload as _c_content_payload,
)
from tests.integration.test_fresh_c_research_package import (
    _module as _c_module,
)
from tests.integration.test_fresh_c_research_package import (
    _review as _c_review,
)
from tests.integration.test_fresh_c_research_package import (
    _synthesis_payload as _c_synthesis_payload,
)
from tests.integration.test_research_package_submission import _bind_reviewed_universe
from tests.unit.reports.b.test_fresh_b_research_package import (
    _package_payload as _b_package_payload,
)
from tests.unit.reports.b.test_fresh_b_research_package import (
    _with_review as _b_with_review,
)

ROOT = Path(__file__).resolve().parents[2]
CUTOFF_DATE = "2026-08-18"
A_CUTOFF = "2026-08-18T23:59:59.999999+08:00"
B_CUTOFF = "2026-08-18T23:59:59.999999+08:00"
C_CUTOFF = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _a_payload(_project_id: str) -> dict[str, object]:
    """可完整走通 A 类谱系管线的合成载荷，截止日对齐联合项目合同。"""
    payload = _a_package_payload()
    payload["data_cutoff"] = A_CUTOFF
    report_data = cast(dict[str, Any], payload["report_data"])
    report_data["data_cutoff"] = A_CUTOFF
    payload["scientific_review"] = {
        "reviewer_id": "independent-review-fixture",
        "reviewer_role": "independent_scientific_verifier",
        "status": "accepted",
        "reviewed_at": "2026-08-18T10:00:00+08:00",
        "reviewed_content_digest": compute_research_content_digest(payload),
        "observations": ["测试包关系闭合"],
    }
    return payload


def _b_payload(project_id: str) -> dict[str, object]:
    payload = _b_package_payload(project_id)
    payload["data_cutoff"] = B_CUTOFF
    report_data = cast(dict[str, Any], payload["report_data"])
    report_data["data_cutoff"] = B_CUTOFF
    return _b_with_review(payload)


def _b_blocked_payload(project_id: str) -> dict[str, object]:
    """安全性结果缺失的 B 载荷：门槛阻断并留下可恢复待办，不渲染门户。"""
    payload = _b_package_payload(project_id)
    payload["data_cutoff"] = B_CUTOFF
    payload["safety"] = []
    payload["safety_review"] = []
    payload["facts"] = [
        fact
        for fact in cast(list[dict[str, Any]], payload["facts"])
        if not str(fact["row_ref"]).startswith("saf-")
    ]
    claims = cast(list[dict[str, Any]], payload["claims"])
    payload["claims"] = [
        {
            **claims[0],
            "fact_ids": [item["fact_id"] for item in cast(list[dict[str, Any]], payload["facts"])],
        }
    ]
    payload.pop("report_data")
    return _b_with_review(payload)


def _c_payload(project_id: str) -> dict[str, object]:
    del project_id
    module = _c_module()
    payload = _c_content_payload()
    payload["design_paths"] = _c_synthesis_payload(module)
    payload["data_cutoff"] = C_CUTOFF
    report_data = cast(dict[str, Any], payload["report_data"])
    report_data["data_cutoff"] = C_CUTOFF
    content = module.validate_fresh_c_content(payload)
    return {**payload, "scientific_review": _c_review(module, content.content_digest)}


def _audit_source_row(item: dict[str, Any]) -> dict[str, object]:
    locator = cast(dict[str, Any], item["locator"])
    # These synthetic inputs contain registries and explicitly primary papers.
    # Keep expectations independent of the production classification mapping.
    source_type, role, classification = {
        "clinical_trial_registry": ("registry", "official_registry", "not_applicable"),
        "primary_trial_report": ("publication", "primary_publication", "primary_result"),
    }[item["source_type"]]
    return {
        "source_id": item["source_id"],
        "locator_detail": item["locator"],
        "title": item["title"],
        "source_role": role,
        "source_type": source_type,
        "url": item["url"],
        "locator": locator.get("url") or locator.get("field_path") or "正文",
        "content_sha256": hashlib.sha256(str(item["content_text"]).strip().encode()).hexdigest(),
        "retrieved_at": item["acquired_at"],
        "published_at": (
            datetime.fromisoformat(item["published_at"]).astimezone(
                ZoneInfo("Asia/Shanghai")
            ).date().isoformat() if item["published_at"] is not None else None
        ),
        "effective_at": (
            datetime.fromisoformat(item["effective_at"]).astimezone(
                ZoneInfo("Asia/Shanghai")
            ).date().isoformat() if item["effective_at"] is not None else None
        ),
        "publication_classification": classification,
        "access_state": "available",
    }


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


def _audit_payload(
    project_id: str,
    reports: tuple[str, ...],
    package_bytes: dict[str, bytes],
    package_payloads: dict[str, dict[str, Any]],
) -> dict[str, object]:
    source_rows: dict[str, dict[str, object]] = {}
    product_ids: list[str] = []
    attempt_ids: list[str] = []
    for report in reports:
        payload = package_payloads[report]
        for item in cast(list[dict[str, Any]], payload["sources"]):
            row = _audit_source_row(item)
            source_rows[str(row["source_id"])] = row
        # C 载荷的竞品宇宙由门户产品行派生（模型属性），信封按同一真源合并
        universe_ids = (
            [
                str(row["id"])
                for row in cast(list[dict[str, Any]], payload["report_data"]["products"])
            ]
            if report == "C"
            else cast(list[str], payload["universe_product_ids"])
        )
        for product_id in universe_ids:
            if product_id not in product_ids:
                product_ids.append(product_id)
        attempt_ids.extend(
            str(item["attempt_id"])
            for item in cast(list[dict[str, Any]], payload.get("route_attempts", []))
        )
    first_source = next(iter(source_rows.values()))
    payload: dict[str, object] = {
        "schema_version": "1.3",
        "package_id": "audit-multi-001",
        "contract_identity": {
            "project_id": project_id,
            "indication": "特应性皮炎",
            "contract_version": "1.3",
        },
        "reports": list(reports),
        "data_cutoff": CUTOFF_DATE,
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
                "identity_evidence_ids": [first_source["source_id"]],
            }
            for product_id in product_ids
        ],
        "sources": list(source_rows.values()),
        "routes": [
            {
                "route_id": "global-registry",
                "region": "global",
                "strategy_id": "global-baseline",
                "result_class": "completed",
                "attempt_ids": attempt_ids or ["global-complete"],
                "source_ids": list(source_rows),
            },
            {
                "route_id": "china-registry",
                "region": "china",
                "strategy_id": "china-baseline",
                "result_class": "completed",
                "attempt_ids": attempt_ids or ["china-complete"],
                "source_ids": list(source_rows),
            },
        ],
        "expansion_receipts": _expansion_receipts(product_ids, str(first_source["source_id"])),
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
                "report": report,
                "relative_path": REPORT_PACKAGE_PATHS[cast(Literal["A", "B", "C"], report)],
                "content_sha256": hashlib.sha256(package_bytes[report]).hexdigest(),
                "content_schema_version": "1.0",
                "universe_product_ids": (
                    [
                        str(row["id"])
                        for row in cast(
                            list[dict[str, Any]],
                            package_payloads[report]["report_data"]["products"],
                        )
                    ]
                    if report == "C"
                    else cast(
                        list[str], package_payloads[report]["universe_product_ids"]
                    )
                ),
            }
            for report in reports
        ],
        "metadata": {"origin": "autonomous-research"},
    }
    if "B" in reports:
        # Study-1 is the existing synthetic primary publication, not a
        # secondary source. Bind its acquisition and search evidence explicitly.
        source = next(row for row in source_rows.values() if row["source_type"] == "publication")
        source["linked_trial_ids"] = ["study-1"]
        cast(list[dict[str, Any]], payload["entities"]).append({
            "entity_id": "study-1", "entity_type": "trial", "name": "Study-1",
            "identity_status": "resolved", "disposition": "included",
            "ontology_rule_id": "innovation-therapy-v1",
            "identity_evidence_ids": [source["source_id"]],
        })
        payload["publication_records"] = [{
            "publication_id": "pub-study-1", "source_id": source["source_id"],
            "product_id": "prod-1", "linked_trial_ids": ["study-1"],
            "registry_identifiers": ["Study-1"], "title": source["title"],
            "source_url": source["url"], "publication_class": "primary_result",
            "model_suggestion": "primary_result", "classification_reason": "合成主要报告合同测试",
            "producer_id": "synthetic-producer", "producer_context": "synthetic-context",
            "acquisition_disposition": "acquired", "affected_reports": ["B"],
            "fetch_attempts": [{
                "attempt_id": "fetch-study-1", "strategy_id": "publisher-fetch",
                "route_family": "publisher", "attempted_at": source["retrieved_at"],
                "result_class": "acquired", "source_id": source["source_id"],
            }],
        }]
        payload["publication_search_receipts"] = [{
            "search_id": "search-study-1", "trial_id": "study-1",
            "registry_identifiers": ["Study-1"],
            "route_families": ["publisher", "bibliographic_index"],
            "attempt_ids": ["publisher-search", "index-search"],
            "query_sha256": hashlib.sha256(b"synthetic-study-1").hexdigest(),
            "result": "publications_classified", "discovered_publication_ids": ["pub-study-1"],
        }]
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
        report_payloads=cast(list[dict[str, Any]], payload["report_payloads"]),
    )
    return payload


def _submit_multi_report_project(
    tmp_path: Path,
    reports: tuple[str, ...],
    payload_builders: dict[str, Callable[[str], dict[str, object]]],
    audit_mutator: Callable[[dict[str, object]], None] | None = None,
) -> Path:
    """提交合成多报告项目；A 的来源文本复用登记存档，非真实报告验收。"""
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=list(reports),
        outputs=["html"],
        cutoff=CUTOFF_DATE,
    )
    project = create_project_workspace(tmp_path / "project", contract)
    project_id = json.loads((project / "project.yaml").read_text(encoding="utf-8"))[
        "project_contract_versions"
    ][0]["project_id"]

    package_paths: dict[str, Path] = {}
    for report in reports:
        path = tmp_path / f"{report.lower()}-research-package.json"
        path.write_text(
            json.dumps(payload_builders[report](project_id), ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        package_paths[report] = path

    package_bytes = {report: package_paths[report].read_bytes() for report in reports}
    parsed = {report: json.loads(package_bytes[report].decode("utf-8")) for report in reports}
    audit = tmp_path / "audit.json"
    audit_payload = _audit_payload(project_id, reports, package_bytes, parsed)
    if audit_mutator is not None:
        audit_mutator(audit_payload)
        closure = cast(dict[str, Any], audit_payload["closure"])
        closure["reviewed_universe_sha256"] = compute_universe_review_digest(
            sources=cast(list[dict[str, Any]], audit_payload["sources"]),
            contract_identity=cast(dict[str, Any], audit_payload["contract_identity"]),
            data_cutoff=cast(str, audit_payload["data_cutoff"]),
            source_policy_id=cast(str, audit_payload["source_policy_id"]),
            source_policy_version=cast(str, audit_payload["source_policy_version"]),
            entities=cast(list[dict[str, Any]], audit_payload["entities"]),
            routes=cast(list[dict[str, Any]], audit_payload["routes"]),
            expansion_receipts=cast(list[dict[str, Any]], audit_payload["expansion_receipts"]),
            closure=closure,
            report_payloads=cast(
                list[dict[str, Any]], audit_payload["report_payloads"]
            ),
        )
    audit.write_text(json.dumps(audit_payload, ensure_ascii=False), encoding="utf-8")
    submit_product_research_package(
        project,
        audit_package=audit,
        report_packages=cast(
            dict[Literal["A", "B", "C"], Path],
            {report: package_paths[report] for report in reports},
        ),
    )
    return project


def _dir_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_manifest(project: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((project / "manifests/current_run.json").read_text(encoding="utf-8")),
    )


def test_multi_report_submission_runs_each_report_independently_and_resumes_idempotently(
    tmp_path: Path,
) -> None:
    reports = ("A", "B", "C")
    project = _submit_multi_report_project(
        tmp_path, reports, {"A": _a_payload, "B": _b_payload, "C": _c_payload}
    )

    first = run_project(
        project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )

    assert first.outcome == "completed"
    assert first.exit_code == 0
    for kind in reports:
        assert first.node_summary.get(f"gate:{kind}") == "completed"
        assert first.node_summary.get(f"format:{kind}") == "completed"

    manifest = _run_manifest(project)
    assert manifest["report_states"] == {kind: "rendered_unreviewed" for kind in reports}
    assert manifest["format_states"] == {kind: {"html": "quality_check"} for kind in reports}
    assert len(set(manifest["snapshot_ids"].values())) == len(reports)
    assert set(manifest["artifact_manifest_sha256"]) == set(reports)
    assert manifest["per_report_outcomes"] == {kind: "completed" for kind in reports}

    universe_events = [
        event
        for event in EventStore(project).read_all()
        if event.run_id == first.run_id
        and event.event_type == "graph.node.completed"
        and event.payload["node_id"] == "universe"
    ]
    assert len(universe_events) == 1
    assert first.node_summary["universe"] == "completed"

    # 逐报告独立产物：三份独立站点与清单，不建立融合门户
    assert {output["relative_path"] for output in manifest["outputs"]} == {
        f"reports/{kind}/v1/html.manifest.json" for kind in reports
    }
    for kind in reports:
        assert (project / f"reports/{kind}/v1/html").is_dir()
        artifact_manifest = json.loads(
            (project / f"reports/{kind}/v1/html.manifest.json").read_text(encoding="utf-8")
        )
        assert artifact_manifest["report"] == kind
    assert validate_run_manifest(project)["run_id"] == first.run_id

    # 幂等 resume：已完成报告全部复用，字节不变，不产生新产物
    site_digests = {kind: _dir_digest(project / f"reports/{kind}/v1/html") for kind in reports}
    request_bytes = {
        kind: (project / f"state/scientific_review/{kind}/review_request.json").read_bytes()
        for kind in reports
    }

    second = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())

    assert second.outcome == "completed"
    assert second.node_summary["intake"] == "reused"
    assert second.node_summary["preflight"] == "completed"
    for kind in reports:
        assert second.node_summary.get(f"gate:{kind}") == "reused"
        assert second.node_summary.get(f"format:{kind}") == "reused"
        assert _dir_digest(project / f"reports/{kind}/v1/html") == site_digests[kind]
        assert (
            project / f"state/scientific_review/{kind}/review_request.json"
        ).read_bytes() == request_bytes[kind]

    resumed_manifest = _run_manifest(project)
    assert resumed_manifest["outputs"] == []
    assert {item["relative_path"] for item in resumed_manifest["reused_artifacts"]} == {
        f"reports/{kind}/v1/html.manifest.json" for kind in reports
    }
    assert resumed_manifest["report_states"] == {kind: "rendered_unreviewed" for kind in reports}
    assert validate_run_manifest(project)["run_id"] == second.run_id


def test_multi_report_run_aggregates_awaiting_recovery_honestly(
    tmp_path: Path,
) -> None:
    reports = ("A", "B")
    project = _submit_multi_report_project(
        tmp_path, reports, {"A": _a_payload, "B": _b_blocked_payload}
    )

    first = run_project(
        project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )

    # A 已渲染、B 等待恢复：聚合保持 running，不伪装完成也不丢弃 A 的产物
    assert first.outcome == "running"
    assert first.exit_code == 0
    manifest = _run_manifest(project)
    assert manifest["report_states"] == {
        "A": "rendered_unreviewed",
        "B": "recovery_required",
    }
    assert manifest["format_states"] == {
        "A": {"html": "quality_check"},
        "B": {"html": "not_generated"},
    }
    assert manifest["per_report_outcomes"] == {"A": "completed", "B": "running"}
    assert manifest["blocked_unit_ids"]["B"]
    assert (project / "reports/A/v1/html").is_dir()
    assert not (project / "reports/B/v1/html").exists()
    work_item_path = project / "state/work-items/b-evidence-recovery.json"
    assert work_item_path.is_file()
    work_item_bytes = work_item_path.read_bytes()
    recovery = json.loads(work_item_bytes)
    assert "b_safety_minimum_record" in recovery["blocked_unit_ids"]
    assert validate_run_manifest(project)["run_id"] == first.run_id

    # resume：A 全部复用且站点字节不变；B 待办字节稳定，仍诚实保持 running
    a_site_digest = _dir_digest(project / "reports/A/v1/html")
    second = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())

    assert second.outcome == "running"
    assert second.node_summary.get("format:A") == "reused"
    assert second.node_summary.get("gate:B") == "reused"
    assert second.node_summary.get("recovery:B") == "awaiting_recovery"
    assert _dir_digest(project / "reports/A/v1/html") == a_site_digest
    assert work_item_path.read_bytes() == work_item_bytes
    assert not (project / "reports/B/v1/html").exists()
    resumed_manifest = _run_manifest(project)
    assert resumed_manifest["report_states"] == {
        "A": "rendered_unreviewed",
        "B": "recovery_required",
    }
    assert validate_run_manifest(project)["run_id"] == second.run_id


def test_manual_publication_pauses_only_affected_report_and_is_not_reprompted(
    tmp_path: Path,
) -> None:
    def add_missing_publication(payload: dict[str, object]) -> None:
        entities = cast(list[dict[str, Any]], payload["entities"])
        sources = cast(list[dict[str, Any]], payload["sources"])
        product_id = str(entities[0]["entity_id"])
        entities.append(
            {
                "entity_id": "trial-manual-1",
                "entity_type": "trial",
                "name": "NCT00000001",
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": [sources[0]["source_id"]],
            }
        )
        sources.append(
            {
                "source_id": "source-publication-manual-1",
                "title": "Primary result requiring full text",
                "source_role": "primary_publication",
                "source_type": "publication",
                "url": "https://doi.org/10.1000/manual",
                "locator": "publisher landing page",
                "content_sha256": None,
                "retrieved_at": "2026-08-18T10:00:00+00:00",
                "linked_trial_ids": ["trial-manual-1"],
                "publication_classification": "primary_result",
                "access_state": "not_accessible",
            }
        )
        payload["publication_records"] = [
            {
                "publication_id": "publication-manual-1",
                "source_id": "source-publication-manual-1",
                "product_id": product_id,
                "linked_trial_ids": ["trial-manual-1"],
                "registry_identifiers": ["NCT00000001"],
                "title": "Primary result requiring full text",
                "source_url": "https://doi.org/10.1000/manual",
                "publication_class": "primary_result",
                "model_suggestion": "primary_result",
                "classification_reason": "登记关联的主要结果论文",
                "producer_id": "publication-worker-1",
                "producer_context": "publication-context-1",
                "doi": "10.1000/manual",
                "fetch_attempts": [
                    {
                        "attempt_id": "publication-fetch-1",
                        "strategy_id": "publisher-full-text",
                        "route_family": "publisher",
                        "attempted_at": "2026-08-18T10:00:00+00:00",
                        "result_class": "access_or_permission_blocked",
                        "diagnostic": "出版社要求机构权限",
                    },
                    {
                        "attempt_id": "publication-fetch-2",
                        "strategy_id": "repository-full-text",
                        "route_family": "open_repository",
                        "attempted_at": "2026-08-18T10:05:00+00:00",
                        "result_class": "searched_no_evidence",
                        "diagnostic": "开放仓储未找到全文",
                    },
                ],
                "acquisition_disposition": "manual_required",
                "blocking_fields": ["b_core_efficacy_endpoint"],
                "affected_reports": ["B"],
            }
        ] + cast(list[dict[str, Any]], payload.get("publication_records", []))
        payload["publication_search_receipts"] = [
            {
                "search_id": "publication-search-trial-manual-1",
                "trial_id": "trial-manual-1",
                "registry_identifiers": ["NCT00000001"],
                "route_families": ["registry_attachment", "bibliographic_index"],
                "attempt_ids": [
                    "publication-search-registry-manual-1",
                    "publication-search-index-manual-1",
                ],
                "query_sha256": "d" * 64,
                "result": "publications_classified",
                "discovered_publication_ids": ["publication-manual-1"],
            }
        ] + cast(list[dict[str, Any]], payload.get("publication_search_receipts", []))

    project = _submit_multi_report_project(
        tmp_path,
        ("A", "B"),
        {"A": _a_payload, "B": _b_payload},
        audit_mutator=add_missing_publication,
    )
    first = run_project(
        project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )

    assert first.outcome == "awaiting_user"
    assert first.exit_code == 6
    b_transitions = [
        event.payload
        for event in EventStore(project).read_all()
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "report_evidence"
        and event.payload.get("object_id") == "report_B"
    ]
    assert b_transitions[-1]["to_state"] == "awaiting_user"
    manifest = _run_manifest(project)
    assert manifest["per_report_outcomes"] == {"A": "completed", "B": "awaiting_user"}
    assert (project / "reports/A/v1/html").is_dir()
    assert not (project / "reports/B/v1/html").exists()
    gate_path = project / manifest["manual_supply_gate"]["relative_path"]
    gate_bytes = gate_path.read_bytes()
    assert (project / "logs/manual-supply-request.md").is_file()
    gate_payload = json.loads(gate_bytes)
    request_id = gate_payload["requests"][0]["request_id"]
    download_requests = (project / "receipts/download_requests.jsonl").read_text(encoding="utf-8")
    assert request_id in download_requests

    second = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())
    assert second.outcome == "awaiting_user"
    assert gate_path.read_bytes() == gate_bytes
    assert _run_manifest(project)["manual_supply_gate"]["user_response_count"] == 0

    inbox = project / gate_payload["requests"][0]["delivery_directory"]
    wrong_writer = PdfWriter()
    wrong_writer.add_blank_page(width=72, height=72)
    wrong_writer.add_metadata({"/Title": "Unrelated review article"})
    wrong_buffer = io.BytesIO()
    wrong_writer.write(wrong_buffer)
    (inbox / "wrong.pdf").write_bytes(wrong_buffer.getvalue())

    third = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())
    assert third.outcome == "awaiting_user"
    assert "needs_re_download" in (project / "receipts/download_requests.jsonl").read_text(
        encoding="utf-8"
    )

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "NCT00000001 10.1000/manual Primary result requiring full text"})
    buffer = io.BytesIO()
    writer.write(buffer)
    original = inbox / "publisher-original.pdf"
    original.write_bytes(buffer.getvalue())
    original_inode = original.stat().st_ino

    fourth = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())
    assert fourth.outcome == "recovery_required"
    assert fourth.exit_code == 7
    b_transitions = [
        event.payload
        for event in EventStore(project).read_all()
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "report_evidence"
        and event.payload.get("object_id") == "report_B"
    ]
    assert b_transitions[-1]["to_state"] == "recovering"
    accepted_gate = json.loads(gate_path.read_bytes())
    assert accepted_gate["user_response_count"] == 1
    assert accepted_gate["state"] == "accepted"
    canonical = (
        project / accepted_gate["response"]["validation_receipts"][0]["canonical_relative_path"]
    )
    assert canonical.is_file()
    assert canonical.stat().st_ino == original_inode
    accepted_bytes = gate_path.read_bytes()
    re_extraction_jobs = [
        json.loads(line)
        for line in (project / "receipts/re-extraction-jobs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert re_extraction_jobs
    assert {job["extraction_mode"] for job in re_extraction_jobs} == {"ocr_required"}

    fifth = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())
    assert fifth.outcome == "recovery_required"
    assert gate_path.read_bytes() == accepted_bytes

    receipt = accepted_gate["response"]["validation_receipts"][0]
    recovered_audit = json.loads(
        (project / "evidence/library/research-package.json").read_text(encoding="utf-8")
    )
    publication_source = next(
        item
        for item in recovered_audit["sources"]
        if item["source_id"] == "source-publication-manual-1"
    )
    publication_source["content_sha256"] = receipt["content_sha256"]
    publication_source["access_state"] = "available"
    publication_record = recovered_audit["publication_records"][0]
    publication_record["fetch_attempts"].append(
        {
            "attempt_id": "publication-fetch-manual-accepted",
            "strategy_id": "validated-manual-inbox",
            "route_family": "publisher",
            "attempted_at": "2026-08-18T10:10:00+00:00",
            "result_class": "acquired",
            "source_id": "source-publication-manual-1",
        }
    )
    publication_record["acquisition_disposition"] = "acquired"
    publication_record["blocking_fields"] = []
    # The new source bytes require a new synthetic universe review, not reuse
    # of the old missing-publication receipt.
    _bind_reviewed_universe(recovered_audit)
    recovered_path = tmp_path / "recovered-audit.json"
    recovered_path.write_text(json.dumps(recovered_audit, ensure_ascii=False), encoding="utf-8")
    old_audit_digest = hashlib.sha256(
        (project / "evidence/library/research-package.json").read_bytes()
    ).hexdigest()
    submit_product_research_package(
        project,
        audit_package=recovered_path,
        report_packages={
            "A": project / REPORT_PACKAGE_PATHS["A"],
            "B": project / REPORT_PACKAGE_PATHS["B"],
        },
    )
    assert (
        project
        / "snapshots/research-submissions"
        / old_audit_digest
        / "evidence/library/research-package.json"
    ).is_file()

    recovered = run_project(project, resume=True, capability_probe=StaticCapabilityProbe())
    assert recovered.outcome == "completed"
    assert (project / "reports/B/v1/html").is_dir()

    limited_project = _submit_multi_report_project(
        tmp_path / "limited",
        ("A", "B"),
        {"A": _a_payload, "B": _b_payload},
        audit_mutator=add_missing_publication,
    )
    waiting = run_project(
        limited_project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )
    assert waiting.outcome == "awaiting_user"
    waiting_manifest = _run_manifest(limited_project)
    limitation = "主要结果全文未能取得；疗效结论仅依据官方登记结果，未核验论文补充分析。"
    mark_publication_files_unavailable(
        limited_project,
        snapshot_id=waiting_manifest["manual_supply_gate"]["snapshot_id"],
        official_evidence_sufficient=True,
        limitation_zh=limitation,
    )
    limited = run_project(
        limited_project,
        resume=True,
        capability_probe=StaticCapabilityProbe(),
    )
    assert limited.outcome == "completed"
    assert limitation not in (limited_project / "reports/A/v1/html/overview.html").read_text(
        encoding="utf-8"
    )
    b_pages = tuple((limited_project / "reports/B/v1/html").rglob("*.html"))
    assert b_pages
    assert all(limitation in page.read_text(encoding="utf-8") for page in b_pages)
    assert "本次研究将基于现有官方证据继续" in (
        limited_project / "logs/manual-supply-request.md"
    ).read_text(encoding="utf-8")
    assert "Primary result requiring full text" not in (
        limited_project / "logs/download_requests.md"
    ).read_text(encoding="utf-8")

    insufficient_project = _submit_multi_report_project(
        tmp_path / "insufficient",
        ("A", "B"),
        {"A": _a_payload, "B": _b_payload},
        audit_mutator=add_missing_publication,
    )
    insufficient_waiting = run_project(
        insufficient_project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )
    insufficient_manifest = _run_manifest(insufficient_project)
    mark_publication_files_unavailable(
        insufficient_project,
        snapshot_id=insufficient_manifest["manual_supply_gate"]["snapshot_id"],
        official_evidence_sufficient=False,
    )
    insufficient = run_project(
        insufficient_project,
        resume=True,
        capability_probe=StaticCapabilityProbe(),
    )
    assert insufficient_waiting.outcome == "awaiting_user"
    assert insufficient.outcome == "evidence_blocked"
    assert (insufficient_project / "reports/A/v1/html").is_dir()
    assert not (insufficient_project / "reports/B/v1/html").exists()
    assert "现有官方证据不足以回答" in (
        insufficient_project / "logs/manual-supply-request.md"
    ).read_text(encoding="utf-8")
    blocker = json.loads(
        (insufficient_project / "blockers/B/v1/audit.json").read_text(encoding="utf-8")
    )
    from jsonschema import Draft202012Validator, FormatChecker

    blocker_schema = json.loads(
        (ROOT / "schemas/publication-blocker-audit.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(blocker_schema)
    Draft202012Validator(
        blocker_schema, format_checker=FormatChecker()
    ).validate(blocker)
    validated_blocker = validate_existing_blocker_package(
        insufficient_project / "blockers/B/v1",
        project_id=json.loads(
            (insufficient_project / "project.yaml").read_text(encoding="utf-8")
        )["project_contract_versions"][0]["project_id"],
        report_kind=ReportKind.B,
        report_version="v1",
    )
    assert validated_blocker.blocker_kind == "publication_unavailable"
    assert validated_blocker.no_draft is True
    assert validated_blocker.resume_node == "recovery"
    assert blocker["reason"] == "required_publication_unavailable"
    b_transitions = [
        event.payload
        for event in EventStore(insufficient_project).read_all()
        if event.event_type == "graph.transition.accepted"
        and event.payload.get("family") == "report_evidence"
        and event.payload.get("object_id") == "report_B"
    ]
    assert b_transitions[-1]["to_state"] == "evidence_blocked"

    bound_gate_path = (
        insufficient_project
        / "state/manual-supply-gates"
        / f"{validated_blocker.evidence_snapshot_id}.json"
    )
    bound_gate_path.write_bytes(bound_gate_path.read_bytes() + b" ")
    with pytest.raises(BlockerAuditDriftError, match="补件门字节"):
        validate_existing_blocker_package(
            insufficient_project / "blockers/B/v1",
            project_id=validated_blocker.project_id,
            report_kind=ReportKind.B,
            report_version="v1",
        )

    tampered_project = _submit_multi_report_project(
        tmp_path / "tampered",
        ("A", "B"),
        {"A": _a_payload, "B": _b_payload},
        audit_mutator=add_missing_publication,
    )
    tampered_waiting = run_project(
        tampered_project,
        require_bound_submission=True,
        capability_probe=StaticCapabilityProbe(),
    )
    tampered_manifest = _run_manifest(tampered_project)
    tampered_gate_path = tampered_project / tampered_manifest["manual_supply_gate"][
        "relative_path"
    ]
    tampered_gate = json.loads(tampered_gate_path.read_text(encoding="utf-8"))
    tampered_gate["requests"][0]["exact_title"] = "Tampered publication identity"
    tampered_gate_path.write_text(json.dumps(tampered_gate, ensure_ascii=False), encoding="utf-8")
    assert tampered_waiting.outcome == "awaiting_user"
    with pytest.raises(ContractConfigError, match="身份已漂移"):
        run_project(
            tampered_project,
            resume=True,
            capability_probe=StaticCapabilityProbe(),
        )
