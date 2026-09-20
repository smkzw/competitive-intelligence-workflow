"""Task 9.2 增量刷新与影响传播集成测试。

覆盖六个验收簇（PRD §验收）：

1. 两个批准节点：刷新图恰好有独立质控审定与版本接受两个批准节点，
   接受节点必须绑定重建回执与质控结论，不能绕过任一批准。
2. 父版本不变：父合同行、父快照与项目文件父条目字节不变且仍可读取；
   子版本在接受批准前不得登记为现行版本。
3. 错误截止日：等于/早于父截止日或晚于刷新请求日的截止日失败关闭，
   不产生子合同版本；合同层 ``refresh_project_contract`` 偏序回归钉死。
4. 重大合同变化：基线身份（合同 Schema/本体/证据合同）或项目身份/字段
   漂移不做局部刷新，明确返回"需要重新建立基线"；分支裁定由
   ``classify_refresh_branch`` 固定。
5. 影响范围：影响闭包确定性、排序稳定、去重，落到事实/声明/页面/格式；
   受影响报告回质控，未影响对象按摘要复用；格式级只允许站点式 HTML。
6. 中断恢复：计划/重建动作幂等重放，回执追加且不重复；
   未完成重建或门槛阻断时接受失败关闭，不生成草稿接受。

候选晋级复用 ``fixtures/synthetic/historical-cutoff`` 的来源版本记录；
门槛收紧材料复用 ``tests/reports/test_gate_override_strictness`` 的工厂。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.refresh_service import (
    ObjectChangeRecord,
    RefreshConflictError,
    RefreshIncompleteError,
    RefreshRebaselineRequired,
    RefreshService,
    RefreshServiceError,
    RefreshStateError,
)
from ci_workflow.domain.contracts import (
    ProjectContract,
    create_project_contract,
    refresh_project_contract,
)
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.evidence import DateEvidence, SourceVersionRecord
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateEvidenceBinding,
    GateSpec,
    ReportDecision,
    ReportGateResult,
)
from ci_workflow.graph.definitions.refresh import (
    BRANCH_LOCAL_REFRESH,
    BRANCH_REBASELINE_REQUIRED,
    REBASELINE_REQUIRED_MESSAGE_ZH,
    REFRESH_NODES,
    RefreshBaselineIdentity,
    classify_refresh_branch,
)
from ci_workflow.graph.impact import (
    ImpactEdge,
    ImpactGraph,
    ImpactGraphError,
    ImpactLayer,
    ImpactNode,
)
from ci_workflow.qc.scientific import (
    LocatorDetail,
    LocatorRef,
    ScientificIssue,
    ScientificQcReviewBundle,
    ScientificQcVerdict,
    SourceRef,
)
from ci_workflow.sources.planner import HistoricalCutoffState
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    ReportSnapshotManifest,
    SnapshotStore,
    compute_locked_snapshot,
)
from tests.reports.test_gate_override_strictness import (
    _satisfied_a_bindings,
    _snapshot,
    _spec_with_unit,
)

ROOT = Path(__file__).resolve().parents[2]
TZ = timezone(timedelta(hours=8))

REQUESTED_AT = datetime(2026, 8, 21, 10, 0, 0, tzinfo=TZ)
ACCEPTED_AT = datetime(2026, 8, 21, 11, 0, 0, tzinfo=TZ)
PARENT_CUTOFF = datetime(2026, 8, 9, 23, 59, 59, 999999, tzinfo=TZ)
NEW_CUTOFF = datetime(2026, 8, 20, 23, 59, 59, 999999, tzinfo=TZ)

ACTOR_ID = "owner-test"
CUTOFF_REQUEST_ACTOR = "owner-cutoff"
GATE_REQUEST_ACTOR = "owner-gates"

_CANDIDATE_FIXTURE = (
    ROOT / "fixtures" / "synthetic" / "historical-cutoff" / "disclosed-after-cutoff.json"
)
_UNKNOWN_FIXTURE = (
    ROOT / "fixtures" / "synthetic" / "historical-cutoff" / "unknown-first-disclosure.json"
)
_RECEIPT_LEDGER = Path("receipts") / "refresh_receipts.jsonl"

# 七个刷新流水节点；重建之后只有两个批准节点
_STAGE_NODE_IDS = (
    "refresh_parent",
    "refresh_candidates",
    "refresh_reevaluate",
    "refresh_gate",
    "refresh_rebuild",
    "refresh_qc",
    "refresh_accept_version",
)
_APPROVAL_NODE_IDS = ("refresh_qc", "refresh_accept_version")


def _dt(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    """按项目时区构造带偏移时间。"""

    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=TZ)


# ─── 候选来源记录（复用历史截止日 fixtures）─────────────────────────────────


def _candidate(source_version_id: str, disclosed_at: datetime) -> SourceVersionRecord:
    base = SourceVersionRecord.model_validate_json(_CANDIDATE_FIXTURE.read_text(encoding="utf-8"))
    disclosed = DateEvidence(
        state="reported",
        value=disclosed_at,
        precision="instant",
        locator=base.first_disclosed_at.locator,
    )
    return base.model_copy(
        update={
            "source_version_id": source_version_id,
            "source_id": f"candidate-{source_version_id}",
            "first_disclosed_at": disclosed,
            "acquired_at": disclosed_at + timedelta(days=1),
            "created_at": disclosed_at + timedelta(days=1, minutes=1),
        }
    )


def _unknown_disclosure_candidate(source_version_id: str) -> SourceVersionRecord:
    record = SourceVersionRecord.model_validate_json(_UNKNOWN_FIXTURE.read_text(encoding="utf-8"))
    return record.model_copy(update={"source_version_id": source_version_id})


# ─── 影响图登记：父版本站点构建的节点与依赖边 ───────────────────────────────


def _impact_nodes() -> tuple[ImpactNode, ...]:
    """父版本已登记影响对象；页面节点声明所属报告类型集合。"""

    return (
        ImpactNode(layer=ImpactLayer.FACT, object_id="fact-1"),
        ImpactNode(layer=ImpactLayer.FACT, object_id="fact-9"),
        ImpactNode(layer=ImpactLayer.CLAIM, object_id="claim-a-efficacy"),
        ImpactNode(layer=ImpactLayer.CLAIM, object_id="claim-b-results"),
        ImpactNode(
            layer=ImpactLayer.PAGE,
            object_id="page:A:efficacy",
            report_kinds=frozenset({"A"}),
        ),
        ImpactNode(
            layer=ImpactLayer.PAGE,
            object_id="page:B:results",
            report_kinds=frozenset({"B"}),
        ),
        ImpactNode(layer=ImpactLayer.FORMAT, object_id="html"),
    )


def _impact_edges() -> tuple[ImpactEdge, ...]:
    """依赖边：来源/事实 → 声明 → 页面 → 格式；两条报告链共享 html 格式节点。"""

    fact_a, fact_b, claim_a, claim_b, page_a, page_b, html = _impact_nodes()
    source_1 = ImpactNode(layer=ImpactLayer.SOURCE, object_id="cand-promote-1")
    source_2 = ImpactNode(layer=ImpactLayer.SOURCE, object_id="cand-promote-boundary")
    return (
        ImpactEdge(upstream=source_1, downstream=fact_a),
        ImpactEdge(upstream=source_2, downstream=fact_a),
        ImpactEdge(upstream=fact_a, downstream=claim_a),
        ImpactEdge(upstream=fact_b, downstream=claim_b),
        ImpactEdge(upstream=claim_a, downstream=page_a),
        ImpactEdge(upstream=claim_b, downstream=page_b),
        ImpactEdge(upstream=page_a, downstream=html),
        ImpactEdge(upstream=page_b, downstream=html),
    )


def _impact_graph() -> tuple[ImpactGraph, tuple[ImpactNode, ...], tuple[ImpactEdge, ...]]:
    """纯影响图（不含来源层）：用于影响闭包的确定性合同测试。"""

    fact_a = ImpactNode(layer=ImpactLayer.FACT, object_id="fact-1")
    fact_b = ImpactNode(layer=ImpactLayer.FACT, object_id="fact-9")
    claim_a = ImpactNode(layer=ImpactLayer.CLAIM, object_id="claim-a-efficacy")
    claim_b = ImpactNode(layer=ImpactLayer.CLAIM, object_id="claim-b-results")
    page_a = ImpactNode(
        layer=ImpactLayer.PAGE,
        object_id="page:A:efficacy",
        report_kinds=frozenset({"A"}),
    )
    page_b = ImpactNode(
        layer=ImpactLayer.PAGE,
        object_id="page:B:results",
        report_kinds=frozenset({"B"}),
    )
    html = ImpactNode(layer=ImpactLayer.FORMAT, object_id="html")
    nodes = (fact_a, fact_b, claim_a, claim_b, page_a, page_b, html)
    edges = (
        ImpactEdge(upstream=fact_a, downstream=claim_a),
        ImpactEdge(upstream=fact_b, downstream=claim_b),
        ImpactEdge(upstream=claim_a, downstream=page_a),
        ImpactEdge(upstream=claim_b, downstream=page_b),
        ImpactEdge(upstream=page_a, downstream=html),
        ImpactEdge(upstream=page_b, downstream=html),
    )
    return ImpactGraph(nodes=nodes, edges=edges), nodes, edges


# ─── 父版本项目工作区 ───────────────────────────────────────────────────────


def _build_parent_project(tmp_path: Path) -> tuple[Path, ProjectContract, LockedSnapshot]:
    """生产入口建立父版本：合同 v1（截止日 2026-08-09）+ 锁定证据/报告快照。"""

    contract = create_project_contract(
        indication="中度特应性皮炎",
        reports=["A", "B"],
        outputs=["html"],
        cutoff=date(2026, 8, 9),
        created_at=_dt(2026, 8, 10, 9),
    )
    assert contract.data_cutoff == PARENT_CUTOFF
    project_root = create_project_workspace(tmp_path / "project", contract)
    store = SnapshotStore(project_root)
    evidence_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 1,
        "data_cutoff": contract.data_cutoff,
        "source_version_ids": ("source-version-parent-1", "source-version-parent-2"),
        "fragment_ids": ("fragment-1", "fragment-2"),
        "fact_version_ids": ("fact-1", "fact-9"),
        "scientific_content_digest": hashlib.sha256(b"parent-evidence-v1").hexdigest(),
        "created_at": contract.created_at,
    }
    store.lock_evidence_snapshot(evidence_manifest)
    report_b_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 1,
        "report": "B",
        "report_version": "v1",
        "data_cutoff": contract.data_cutoff,
        "evidence_snapshot_id": "evidence-snapshot-parent",
        "claim_snapshot_id": "claim-snapshot-b-v1",
        "coverage_set_id": "coverage-b-v1",
        "claim_ids": ("claim-b-results",),
        "created_at": contract.created_at,
    }
    report_b_locked = store.lock_report_snapshot(report="B", manifest=report_b_manifest)
    return project_root, contract, report_b_locked


def _parent_a_gate_fixture(
    project_root: Path, contract: ProjectContract
) -> tuple[
    GateSpec,
    GateSpec,
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    ReportGateResult,
]:
    """构造 A 报告父门槛结果（收紧场景的父结果绑定与不变性断言）。"""

    evidence_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 1,
        "data_cutoff": contract.data_cutoff,
        "source_version_ids": ("source-version-parent-1",),
        "fragment_ids": ("fragment-1",),
        "fact_version_ids": ("fact-1",),
        "scientific_content_digest": hashlib.sha256(b"parent-evidence-v1").hexdigest(),
        "created_at": contract.created_at,
    }
    locked = SnapshotStore(project_root).lock_evidence_snapshot(evidence_manifest)
    universe = _snapshot(
        project_id=contract.project_id,
        evidence_snapshot_id=locked.snapshot_id,
    )
    a_spec = GateSpec.from_yaml(ROOT / "policies" / "gates" / "A-v1.yaml")
    b_spec = GateSpec.from_yaml(ROOT / "policies" / "gates" / "B-v1.yaml")
    bindings = _satisfied_a_bindings(a_spec)
    parent_result = evaluate_report(a_spec, universe, bindings, contract_version="1")
    assert parent_result.decision is ReportDecision.PASSED
    return a_spec, b_spec, universe, bindings, parent_result


# ─── 工作区状态观测 ─────────────────────────────────────────────────────────


def _snapshot_digests(project_root: Path) -> dict[str, str]:
    """snapshots/ 下全部快照文件的字节摘要；父历史不可变的观测面。"""

    return {
        path.relative_to(project_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((project_root / "snapshots").rglob("*"))
        if path.is_file()
    }


def _contract_rows(project_root: Path) -> dict[int, str]:
    with sqlite3.connect(project_root / "state" / "project.sqlite") as database:
        rows = database.execute(
            """
            SELECT contract_version, contract_json
            FROM project_contract_versions
            ORDER BY contract_version
            """
        ).fetchall()
    return {int(version): str(payload) for version, payload in rows}


def _project_document(project_root: Path) -> dict[str, object]:
    payload = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("project.yaml 顶层必须是对象")
    return payload


def _active_version(project_root: Path) -> int:
    value = _project_document(project_root)["active_contract_version"]
    if not isinstance(value, int):
        raise AssertionError("active_contract_version 必须是整数")
    return value


def _contract_entry(project_root: Path, version: int) -> object:
    versions = _project_document(project_root)["project_contract_versions"]
    if not isinstance(versions, list):
        raise AssertionError("project_contract_versions 必须是列表")
    for item in versions:
        if isinstance(item, dict) and item.get("contract_version") == version:
            return item
    raise AssertionError(f"project.yaml 缺少合同版本条目：{version}")


def _parent_history(project_root: Path) -> tuple[object, ...]:
    """父版本不可变观测面：父合同行 + 项目文件父条目 + 父快照字节。

    现行合同版本不在此观测面内：接受批准后合法翻转到子版本，由调用方单独断言。
    """

    rows = _contract_rows(project_root)
    return (rows[1], _contract_entry(project_root, 1), _snapshot_digests(project_root))


def _assert_parent_history_unchanged(project_root: Path, before: tuple[object, ...]) -> None:
    after = _parent_history(project_root)
    assert after[0] == before[0], "父合同行被改写"
    assert after[1] == before[1], "项目文件父合同条目被改写"
    before_digests, after_digests = before[2], after[2]
    assert isinstance(before_digests, dict) and isinstance(after_digests, dict)
    for relative, digest in before_digests.items():
        assert after_digests.get(relative) == digest, f"父快照被改写：{relative}"


def _receipt_lines(project_root: Path) -> list[dict[str, object]]:
    path = project_root / _RECEIPT_LEDGER
    if not path.is_file():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            assert isinstance(payload, dict)
            records.append(payload)
    return records


def _object_pairs(objects: object) -> set[tuple[str, str]]:
    return {(item.object_kind, item.object_id) for item in objects}  # type: ignore[attr-defined]


def _record_rebuilds(
    service: RefreshService, refresh_id: str, pairs: set[tuple[str, str]]
) -> list[str]:
    """为每个受影响对象追加重建回执；返回动作标识清单。"""

    action_ids: list[str] = []
    for kind, object_id in sorted(pairs):
        action = service.record_rebuild_action(
            refresh_id,
            object_kind=kind,
            object_id=object_id,
            disposition="rebuilt",
            basis_digest=hashlib.sha256(f"{kind}:{object_id}".encode()).hexdigest(),
            recorded_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
        )
        action_ids.append(action.action_id)
    return action_ids


def _gate_result_for(
    *,
    project_id: str,
    report_kind: ReportKind,
    contract_version: str,
    evidence_snapshot_id: str,
    spec: GateSpec | None = None,
) -> ReportGateResult:
    """生成经过完整评估器计算的报告级结果，禁止测试用字符串冒充通过。"""

    selected = spec or GateSpec.from_yaml(
        ROOT / "policies" / "gates" / f"{report_kind.value}-v1.yaml"
    )
    if report_kind is not ReportKind.A:
        raise AssertionError("Task 9.2 当前集成材料只构造 A 类完整门槛结果")
    universe = _snapshot(project_id=project_id, evidence_snapshot_id=evidence_snapshot_id)
    return evaluate_report(
        selected,
        universe,
        _satisfied_a_bindings(selected),
        contract_version=contract_version,
    )


def _evidence_snapshot_id(manifest: dict[str, object]) -> str:
    validated = EvidenceSnapshotManifest.model_validate(manifest)
    return compute_locked_snapshot(
        kind="evidence", report=None, manifest=validated.model_dump(mode="json")
    ).snapshot_id


def _record_accepted_qc(
    service: RefreshService,
    *,
    refresh_id: str,
    report_kind: ReportKind,
    snapshot_id: str,
    manifest: dict[str, object],
    gate_result: ReportGateResult,
    accepted: bool = True,
    valid_until: datetime | None = None,
) -> None:
    validated = ReportSnapshotManifest.model_validate(manifest)
    canonical = json.dumps(
        validated.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    evidence_manifest = json.loads(
        (
            service.project_root
            / "snapshots"
            / "evidence"
            / f"{gate_result.evidence_snapshot_id}.json"
        ).read_text(encoding="utf-8")
    )
    locator = LocatorRef(
        fragment_id=str(evidence_manifest["fragment_ids"][0]),
        locator=LocatorDetail(document_role="临床试验登记", field_path="results.primary"),
    )
    source_ref = SourceRef(
        source_version_id=str(evidence_manifest["source_version_ids"][0]),
        fragment_ids=(locator.fragment_id,),
        claim_ids=tuple(validated.claim_ids),
        fact_version_ids=(str(evidence_manifest["fact_version_ids"][0]),),
        locators=(locator,),
    )
    bundle = ScientificQcReviewBundle(
        producer_id="report-builder",
        project_id=validated.project_id,
        report_kind=report_kind,
        report_version=validated.report_version,
        report_object_id=snapshot_id,
        candidate_snapshot_id=snapshot_id,
        candidate_content_digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        criteria_version="refresh-qc-v1",
        gate_result_key=gate_result.result_key,
        coverage_set_id=validated.coverage_set_id,
        coverage_digest=hashlib.sha256(validated.coverage_set_id.encode()).hexdigest(),
        source_refs=(source_ref,),
        locators=(locator,),
    )
    verdict = ScientificQcVerdict(
        schema_version="1.0",
        criteria_version="refresh-qc-v1",
        verdict_id=f"qc-{refresh_id}-{report_kind.value}",
        verdict="accepted" if accepted else "veto",
        veto_disposition=None if accepted else "recoverable",
        project_id=validated.project_id,
        contract_version=str(validated.contract_version),
        report_kind=report_kind,
        report_version=validated.report_version,
        report_object_id=snapshot_id,
        candidate_snapshot_id=snapshot_id,
        candidate_content_digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        gate_result_key=gate_result.result_key,
        coverage_set_id=validated.coverage_set_id,
        coverage_digest=hashlib.sha256(validated.coverage_set_id.encode()).hexdigest(),
        source_refs=(source_ref,),
        locators=(locator,),
        issues=(
            ()
            if accepted
            else (
                ScientificIssue(
                    issue_id="qc-blocking-refresh",
                    severity="blocking",
                    category="证据一致性",
                    description_zh="关键疗效数值与来源定位尚未一致，暂不能接受。",
                    source_version_id=source_ref.source_version_id,
                    fragment_ids=(locator.fragment_id,),
                ),
            )
        ),
        reviewer_id="independent-qc-reviewer",
        review_input_digest=bundle.input_digest,
        reviewed_at=REQUESTED_AT,
        valid_until=valid_until or ACCEPTED_AT + timedelta(days=1),
    )
    service.record_scientific_qc(
        refresh_id,
        verdict=verdict,
        review_bundle=bundle,
    )


# ─── 1. 两个批准节点：刷新图合同 ────────────────────────────────────────────


def test_refresh_graph_declares_seven_stage_pipeline_with_exactly_two_approval_nodes() -> None:  # noqa: E501
    contracts = {contract.node_id: contract for contract in REFRESH_NODES}
    assert set(contracts) == set(_STAGE_NODE_IDS)

    # 重建之后只有独立质控审定与版本接受两个批准节点；验证本身不能批准发布。
    after_rebuild = [
        node_id
        for node_id in _STAGE_NODE_IDS
        if _STAGE_NODE_IDS.index(node_id) > _STAGE_NODE_IDS.index("refresh_rebuild")
    ]
    assert tuple(after_rebuild) == _APPROVAL_NODE_IDS

    qc = contracts["refresh_qc"]
    assert {field.name for field in qc.typed_outputs} == {
        "qc_verdict",
        "qc_verdict_digest",
    }
    assert "QCVerdictError" in qc.declared_errors

    accept = contracts["refresh_accept_version"]
    assert accept.side_effect_class == "move"
    assert "accepted" in {field.name for field in accept.typed_outputs}
    # 接受节点必须绑定重建回执与质控结论：任一批准未通过，子版本不得登记为已接受。
    assert {"child_contract_id", "rebuild_receipt_id", "qc_verdict_digest"} <= {
        field.name for field in accept.typed_inputs
    }
    assert "IncompleteRebuildError" in accept.declared_errors

    for node_id in _APPROVAL_NODE_IDS:
        assert contracts[node_id].idempotency_material, f"{node_id} 缺少稳定幂等键"
    for node_id, contract in contracts.items():
        assert contract.version
        assert contract.completion_summary
        assert contract.idempotency_material, f"{node_id} 缺少稳定幂等材料"

    # 重大合同变化分支在读取父版本节点显式声明，不得伪装成局部刷新。
    assert "RebaselineRequiredError" in contracts["refresh_parent"].declared_errors


def test_classify_refresh_branch_requires_rebaseline_on_major_contract_change() -> None:
    parent = RefreshBaselineIdentity(
        contract_schema_version="1.0",
        ontology_version="1.0",
        evidence_contract_version="1.0",
    )

    same = classify_refresh_branch(parent, parent)
    assert same.branch == BRANCH_LOCAL_REFRESH
    assert same.changed_dimensions == ()

    ontology = classify_refresh_branch(
        parent,
        RefreshBaselineIdentity(
            contract_schema_version="1.0",
            ontology_version="2.0",
            evidence_contract_version="1.0",
        ),
    )
    assert ontology.branch == BRANCH_REBASELINE_REQUIRED
    assert ontology.changed_dimensions == ("ontology_version",)
    assert "重新建立基线" in ontology.reason_zh
    assert ontology.reason_zh == REBASELINE_REQUIRED_MESSAGE_ZH

    schema = classify_refresh_branch(
        parent,
        RefreshBaselineIdentity(
            contract_schema_version="1.1",
            ontology_version="1.0",
            evidence_contract_version="1.0",
        ),
    )
    assert schema.branch == BRANCH_REBASELINE_REQUIRED
    assert schema.changed_dimensions == ("contract_schema_version",)

    combined = classify_refresh_branch(
        parent,
        RefreshBaselineIdentity(
            contract_schema_version="1.1",
            ontology_version="2.0",
            evidence_contract_version="2.0",
        ),
    )
    assert combined.changed_dimensions == (
        "contract_schema_version",
        "evidence_contract_version",
        "ontology_version",
    )


# ─── 5. 影响范围：影响闭包纯合同 ────────────────────────────────────────────


def test_impact_closure_is_deterministic_sorted_and_reaches_claims_pages_and_formats() -> None:  # noqa: E501
    graph, nodes, edges = _impact_graph()
    seeds = (nodes[0],)
    plan = graph.impact_closure(seeds)

    # 影响集合包含全部种子及下游，且落到事实/声明/页面/格式层。
    assert "fact-1" in plan.affected_ids(ImpactLayer.FACT)
    assert plan.affected_ids(ImpactLayer.CLAIM) == ("claim-a-efficacy",)
    assert plan.affected_ids(ImpactLayer.PAGE) == ("page:A:efficacy",)
    assert plan.affected_ids(ImpactLayer.FORMAT) == ("html",)

    # 未受影响链按摘要复用。
    assert "fact-9" in plan.reused_ids(ImpactLayer.FACT)
    assert "claim-b-results" in plan.reused_ids(ImpactLayer.CLAIM)
    assert "page:B:results" in plan.reused_ids(ImpactLayer.PAGE)

    # 排序稳定、去重、影响与复用不相交。
    layer_rank = {layer: order for order, layer in enumerate(ImpactLayer)}
    assert plan.affected == tuple(
        sorted(plan.affected, key=lambda node: (layer_rank[node.layer], node.object_id))
    )
    assert plan.reused == tuple(
        sorted(plan.reused, key=lambda node: (layer_rank[node.layer], node.object_id))
    )
    assert len(plan.affected) == len(set(plan.affected))
    assert len(plan.reused) == len(set(plan.reused))
    assert not set(plan.affected) & set(plan.reused)
    assert set(seeds) <= set(plan.affected)

    # 确定性：边乱序 + 重复输入产生同一图摘要、同一闭包与同一计划摘要。
    reordered = ImpactGraph(nodes=tuple(reversed(nodes)), edges=edges[::-1] + edges[:2])
    assert reordered.graph_digest == graph.graph_digest
    replayed = reordered.impact_closure(seeds)
    assert replayed == plan
    assert replayed.plan_digest == plan.plan_digest


def test_impact_closure_rejects_backward_edges_unregistered_seeds_and_empty_seeds() -> None:  # noqa: E501
    graph, nodes, _edges = _impact_graph()
    fact_a, _fact_b, _claim_a, _claim_b, page_a, _page_b, _html = nodes

    with pytest.raises(ImpactGraphError):
        ImpactGraph(
            nodes=(fact_a, page_a),
            edges=(ImpactEdge(upstream=page_a, downstream=fact_a),),
        )
    with pytest.raises(ImpactGraphError, match="相邻层"):
        ImpactEdge(upstream=fact_a, downstream=page_a)
    with pytest.raises(ImpactGraphError, match="投影到交付格式"):
        ImpactGraph(nodes=(page_a,), edges=())
    with pytest.raises(ImpactGraphError):
        graph.impact_closure((ImpactNode(layer=ImpactLayer.FACT, object_id="fact-x"),))
    with pytest.raises(ImpactGraphError):
        graph.impact_closure(())

    # 非页面节点不得声明报告类型；页面报告类型不得超出封闭词表。
    with pytest.raises(ImpactGraphError):
        ImpactNode(
            layer=ImpactLayer.CLAIM,
            object_id="claim-tagged",
            report_kinds=frozenset({"A"}),
        )
    with pytest.raises(ImpactGraphError):
        ImpactNode(
            layer=ImpactLayer.PAGE,
            object_id="page:X:bad",
            report_kinds=frozenset({"D"}),
        )


def test_impact_for_report_kinds_reroutes_only_affected_report_pages() -> None:
    graph, _nodes, _edges = _impact_graph()
    plan = graph.impact_for_report_kinds(("A",))

    # 受影响报告页面进入闭包并传播到格式；事实/声明内容未变化按摘要复用。
    assert plan.affected_ids(ImpactLayer.PAGE) == ("page:A:efficacy",)
    assert plan.affected_ids(ImpactLayer.FORMAT) == ("html",)
    assert "claim-a-efficacy" in plan.reused_ids(ImpactLayer.CLAIM)
    assert "fact-1" in plan.reused_ids(ImpactLayer.FACT)
    assert "page:B:results" in plan.reused_ids(ImpactLayer.PAGE)

    # 声明的受影响报告没有登记页面时失败关闭，不允许静默缩小影响范围。
    with pytest.raises(ImpactGraphError):
        graph.impact_for_report_kinds(("C",))


# ─── 3. 错误截止日：失败关闭 + 合同层回归 ───────────────────────────────────


def test_cutoff_expansion_fails_closed_on_wrong_cutoff_and_pins_contract_regression(
    tmp_path: Path,
) -> None:  # noqa: E501
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    before = _parent_history(project_root)

    for wrong_cutoff in (
        PARENT_CUTOFF,
        _dt(2026, 8, 1),
        _dt(2026, 8, 25, 23, 59, 59, 999999),
    ):
        with pytest.raises(RefreshServiceError):
            service.plan_refresh(
                requested_cutoff=wrong_cutoff,
                requested_at=REQUESTED_AT,
                actor_id=CUTOFF_REQUEST_ACTOR,
                impact_edges=_impact_edges(),
                impact_nodes=_impact_nodes(),
                sources=(_candidate("cand-promote-1", _dt(2026, 8, 12, 9)),),
            )

    # 合同层回归：错误截止日的只收紧偏序由既有合同函数固定，服务不得绕开。
    with pytest.raises(ValueError):
        refresh_project_contract(contract, cutoff=PARENT_CUTOFF, created_at=REQUESTED_AT)
    with pytest.raises(ValueError):
        refresh_project_contract(contract, cutoff=_dt(2026, 8, 25), created_at=REQUESTED_AT)

    assert set(_contract_rows(project_root)) == {1}
    assert _active_version(project_root) == 1
    _assert_parent_history_unchanged(project_root, before)


# ─── 4. 重大合同变化：明确要求再基线 ────────────────────────────────────────


def test_major_contract_change_requires_explicit_rebaseline_not_partial_refresh(
    tmp_path: Path,
) -> None:  # noqa: E501
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    before = _parent_history(project_root)
    promoted_source = _candidate("cand-promote-1", _dt(2026, 8, 12, 9))

    # 证据合同版本漂移：不做局部刷新，明确要求重新建立基线。
    with pytest.raises(RefreshRebaselineRequired) as evidence_error:
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            child_baseline=RefreshBaselineIdentity(
                contract_schema_version="1.0",
                ontology_version="1.0",
                evidence_contract_version="2.0",
            ),
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=(promoted_source,),
        )
    assert "重新建立基线" in str(evidence_error.value)
    assert "evidence_contract_version" in str(evidence_error.value)

    # 本体版本漂移：同样必须再基线。
    with pytest.raises(RefreshRebaselineRequired) as ontology_error:
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            child_baseline=RefreshBaselineIdentity(
                contract_schema_version="1.0",
                ontology_version="2.0",
                evidence_contract_version="1.0",
            ),
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=(promoted_source,),
        )
    assert "ontology_version" in str(ontology_error.value)

    # 项目身份漂移：不得跨项目局部刷新。
    foreign = contract.model_copy(update={"project_id": "project-foreign"})
    with pytest.raises(RefreshRebaselineRequired) as identity_error:
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            requested_contract=foreign,
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=(promoted_source,),
        )
    assert "重新建立基线" in str(identity_error.value)

    # 项目合同字段漂移（适应症变化）：不得伪装成截止日刷新。
    drifted = contract.model_copy(update={"indication": "重度特应性皮炎"})
    with pytest.raises(RefreshRebaselineRequired) as field_error:
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            requested_contract=drifted,
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=(promoted_source,),
        )
    assert "indication" in str(field_error.value)

    # 没有任何增量变化：不接受空刷新。
    with pytest.raises(RefreshStateError):
        service.plan_refresh(
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
        )

    assert set(_contract_rows(project_root)) == {1}
    assert _active_version(project_root) == 1
    _assert_parent_history_unchanged(project_root, before)


# ─── 1/2/5/6. 扩大截止日：晋级、影响范围、不可变历史、中断恢复 ───────────────


def _cutoff_sources() -> tuple[SourceVersionRecord, ...]:
    return (
        _candidate("cand-promote-1", _dt(2026, 8, 12, 9)),
        _candidate("cand-promote-boundary", NEW_CUTOFF),
        _candidate("cand-beyond", _dt(2026, 8, 25, 9)),
        _candidate("cand-already", _dt(2026, 8, 1, 9)),
        _candidate("cand-at-parent", PARENT_CUTOFF),
        _unknown_disclosure_candidate("cand-unknown"),
    )


def test_expanding_cutoff_creates_new_contract_version_and_promotes_only_now_eligible_candidates(
    tmp_path: Path,
) -> None:  # noqa: E501
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    before = _parent_history(project_root)

    plan = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=CUTOFF_REQUEST_ACTOR,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )

    # 新建合同版本：紧邻子版本、同项目身份、扩大后的截止日；父版本对象不变。
    assert plan.change_kinds == ("cutoff_expansion",)
    assert plan.parent_contract == contract
    assert plan.child_contract.project_id == contract.project_id
    assert plan.child_contract.contract_version == 2
    assert plan.child_contract.data_cutoff == NEW_CUTOFF
    assert plan.requested_cutoff == NEW_CUTOFF

    # 只晋级 (父截止日, 新截止日] 区间内首次披露的候选；资格按披露时间而非获取时间。
    promoted = {item.source_version_id for item in plan.promoted}
    assert promoted == {"cand-promote-1", "cand-promote-boundary"}
    blocked = {item.source_version_id: item for item in plan.blocked}
    assert set(blocked) == {"cand-beyond", "cand-unknown"}
    assert blocked["cand-beyond"].reason_code == HistoricalCutoffState.REFRESH_CANDIDATE.value
    assert (
        blocked["cand-unknown"].reason_code
        == HistoricalCutoffState.BLOCKED_UNKNOWN_DISCLOSURE.value
    )
    for promotion in plan.promoted:
        assert PARENT_CUTOFF < promotion.first_disclosed_at <= NEW_CUTOFF
        assert promotion.rationale_zh

    # 已适格（父截止日边界内）候选既不晋级也不阻断：不重评已接受且未变化的来源。
    assert "cand-already" not in promoted | set(blocked)
    assert "cand-at-parent" not in promoted | set(blocked)

    # 影响范围：种子来源沿依赖边确定性传播；影响与复用集合恰好覆盖登记对象。
    affected = _object_pairs(plan.affected_objects)
    assert affected == {
        ("source", "cand-promote-1"),
        ("source", "cand-promote-boundary"),
        ("fact", "fact-1"),
        ("claim", "claim-a-efficacy"),
        ("page", "page:A:efficacy"),
        ("format", "html"),
    }
    assert _object_pairs(plan.reuse_objects) == {
        ("fact", "fact-9"),
        ("claim", "claim-b-results"),
        ("page", "page:B:results"),
    }
    assert plan.impact_plan_digest
    assert plan.rebuild_report_kinds == (ReportKind.A,)
    assert plan.reuse_report_kinds == (ReportKind.B,)

    # 计划幂等：同一输入精确重放返回同一计划；事件流可重建同一计划。
    replayed = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=CUTOFF_REQUEST_ACTOR,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )
    assert replayed == plan
    assert service.load_plan(plan.refresh_id) == plan

    # 计划阶段不改写父历史：父合同行、项目文件父条目与父快照字节不变。
    assert set(_contract_rows(project_root)) == {1, 2}
    assert _active_version(project_root) == 1
    _assert_parent_history_unchanged(project_root, before)


def test_refresh_plan_records_all_supported_change_states_without_silent_objects(
    tmp_path: Path,
) -> None:
    project_root, _contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    assignments = {
        ("fact", "fact-1"): "changed",
        ("claim", "claim-a-efficacy"): "withdrawn",
        ("page", "page:A:efficacy"): "revised",
        ("format", "html"): "superseded",
    }
    declared = tuple(
        ObjectChangeRecord(
            object_kind=kind,
            object_id=object_id,
            change_kind=change_kind,
            basis_digest=hashlib.sha256(f"{kind}:{object_id}:{change_kind}".encode()).hexdigest(),
            related_object_id=("html-v2" if change_kind == "superseded" else None),
            rationale_zh="上游已提供本轮对象变化依据。",
        )
        for (kind, object_id), change_kind in assignments.items()
    )
    plan = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=CUTOFF_REQUEST_ACTOR,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
        declared_change_records=declared,
    )
    assert {record.change_kind for record in plan.change_records} == {
        "new",
        "changed",
        "withdrawn",
        "revised",
        "superseded",
        "unchanged",
    }
    assert {
        (record.object_kind, record.object_id) for record in plan.change_records
    } == _object_pairs(plan.affected_objects) | _object_pairs(plan.reuse_objects)

    with pytest.raises(RefreshStateError, match="影响图之外"):
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=CUTOFF_REQUEST_ACTOR,
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=_cutoff_sources(),
            declared_change_records=(
                ObjectChangeRecord(
                    object_kind="claim",
                    object_id="claim-not-registered",
                    change_kind="changed",
                    basis_digest=hashlib.sha256(b"unknown-change").hexdigest(),
                    rationale_zh="该对象未在本轮影响图登记。",
                ),
            ),
        )


def test_second_pending_plan_cannot_claim_the_same_child_contract_version(
    tmp_path: Path,
) -> None:
    project_root, _contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    first = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )
    assert first.child_contract.contract_version == 2
    with pytest.raises(RefreshConflictError, match="已有未完成刷新计划"):
        service.plan_refresh(
            requested_cutoff=NEW_CUTOFF,
            requested_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
            sources=(
                _candidate("cand-promote-1", _dt(2026, 8, 12, 9)),
                _candidate("cand-promote-boundary", NEW_CUTOFF),
            ),
            declared_change_records=(
                ObjectChangeRecord(
                    object_kind="fact",
                    object_id="fact-1",
                    change_kind="revised",
                    basis_digest=hashlib.sha256(b"parallel-plan").hexdigest(),
                    rationale_zh="另一份计划试图占用同一子版本。",
                ),
            ),
        )
    assert service.resume_status(first.refresh_id)["completion"] is None


def test_refresh_replay_is_idempotent_and_incomplete_rebuild_cannot_be_accepted(
    tmp_path: Path,
) -> None:  # noqa: E501
    project_root, contract, report_b_locked = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    plan = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=CUTOFF_REQUEST_ACTOR,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )
    refresh_id = plan.refresh_id
    affected = _object_pairs(plan.affected_objects)

    # 中断点一：仅完成计划。恢复视图暴露缺口，接受失败关闭。
    status = service.resume_status(refresh_id)
    assert status["completion"] is None
    assert _object_pairs(status["missing_rebuild_objects"]) == affected
    with pytest.raises(RefreshIncompleteError):
        service.accept_refresh(refresh_id, occurred_at=ACCEPTED_AT, actor_id=ACTOR_ID)
    assert _active_version(project_root) == 1

    # 处置约束：受影响对象必须重建；计划外对象不得登记回执。
    sample = sorted(affected)[0]
    with pytest.raises(RefreshStateError):
        service.record_rebuild_action(
            refresh_id,
            object_kind=sample[0],
            object_id=sample[1],
            disposition="reuse",
            basis_digest=hashlib.sha256(sample[1].encode()).hexdigest(),
            recorded_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
        )
    with pytest.raises(RefreshStateError):
        service.record_rebuild_action(
            refresh_id,
            object_kind="claim",
            object_id="claim-not-in-plan",
            disposition="rebuilt",
            basis_digest=hashlib.sha256(b"unknown").hexdigest(),
            recorded_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
        )

    # 逐对象追加重建回执（中断点二：部分完成后重放同一动作得到同一回执）。
    action_ids = _record_rebuilds(service, refresh_id, affected)
    first = sorted(affected)[0]
    replayed_action = service.record_rebuild_action(
        refresh_id,
        object_kind=first[0],
        object_id=first[1],
        disposition="rebuilt",
        basis_digest=hashlib.sha256(f"{first[0]}:{first[1]}".encode()).hexdigest(),
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    assert replayed_action.action_id == action_ids[0]

    # 回执投影追加保存且不重复；恢复视图缺口清零。
    lines = _receipt_lines(project_root)
    action_line_ids = [str(line.get("action_id")) for line in lines]
    assert sorted(action_line_ids) == sorted(action_ids)
    assert len(action_line_ids) == len(set(action_line_ids))
    status = service.resume_status(refresh_id)
    assert _object_pairs(status["missing_rebuild_objects"]) == set()

    evidence_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "data_cutoff": NEW_CUTOFF,
        "source_version_ids": (
            "source-version-parent-1",
            "cand-promote-1",
            "cand-promote-boundary",
        ),
        "fragment_ids": ("fragment-1", "fragment-2"),
        "fact_version_ids": ("fact-1", "fact-9"),
        "scientific_content_digest": hashlib.sha256(b"refresh-evidence-v2").hexdigest(),
        "created_at": REQUESTED_AT,
    }
    evidence_snapshot_id = _evidence_snapshot_id(evidence_manifest)
    SnapshotStore(project_root).lock_evidence_snapshot(evidence_manifest)

    # 晋级候选必须至少重建一份报告快照：登记绑定子版本与新截止日的 A 报告快照。
    report_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "report": "A",
        "report_version": "v1",
        "data_cutoff": NEW_CUTOFF,
        "evidence_snapshot_id": evidence_snapshot_id,
        "claim_snapshot_id": "claim-snapshot-a-v2",
        "coverage_set_id": "coverage-a-v2",
        "claim_ids": ("claim-a-efficacy",),
        "created_at": REQUESTED_AT,
    }
    snapshot_id = service.register_report_snapshot(
        refresh_id,
        report_kind=ReportKind.A,
        manifest=report_manifest,
    )
    assert snapshot_id
    gate_result = _gate_result_for(
        project_id=contract.project_id,
        report_kind=ReportKind.A,
        contract_version="2",
        evidence_snapshot_id=evidence_snapshot_id,
    )
    service.record_gate_decision(
        refresh_id,
        gate_result=gate_result,
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    with pytest.raises(RefreshIncompleteError, match="独立科学质控"):
        service.accept_refresh(
            refresh_id,
            occurred_at=ACCEPTED_AT,
            actor_id=ACTOR_ID,
            evidence_snapshot_manifest=evidence_manifest,
        )
    _record_accepted_qc(
        service,
        refresh_id=refresh_id,
        report_kind=ReportKind.A,
        snapshot_id=snapshot_id,
        manifest=report_manifest,
        gate_result=gate_result,
    )

    # 接受批准：晋级候选建立新的不可变证据快照，子版本登记为现行版本；
    # 父历史不变且父快照仍可读取。
    before_accept = _parent_history(project_root)
    completion = service.accept_refresh(
        refresh_id,
        occurred_at=ACCEPTED_AT,
        actor_id=ACTOR_ID,
        evidence_snapshot_manifest=evidence_manifest,
    )
    assert completion.child_contract_version == 2
    assert completion.evidence_snapshot_id is not None
    assert completion.report_snapshot_ids == (snapshot_id,)
    assert _active_version(project_root) == 2
    rows = _contract_rows(project_root)
    assert set(rows) == {1, 2}
    child = ProjectContract.model_validate_json(rows[2])
    assert child.project_id == contract.project_id
    assert child.contract_version == 2
    assert child.data_cutoff == NEW_CUTOFF
    _assert_parent_history_unchanged(project_root, before_accept)
    store = SnapshotStore(project_root)
    assert store.read(report_b_locked)["report"] == "B"

    # 接受幂等：同一刷新同一输入重复接受返回同一登记，不产生第二份接受记录。
    replayed_completion = service.accept_refresh(
        refresh_id,
        occurred_at=ACCEPTED_AT,
        actor_id=ACTOR_ID,
        evidence_snapshot_manifest=evidence_manifest,
    )
    status = service.resume_status(refresh_id)
    assert status["completion"] == replayed_completion


def test_report_snapshot_registration_recovers_after_database_commit_before_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    plan = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=CUTOFF_REQUEST_ACTOR,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=(_candidate("cand-promote-1", _dt(2026, 8, 12, 9)),),
    )
    manifest = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "report": "A",
        "report_version": "v1",
        "data_cutoff": NEW_CUTOFF,
        "evidence_snapshot_id": "evidence-snapshot-refresh",
        "claim_snapshot_id": "claim-snapshot-a-v2",
        "coverage_set_id": "coverage-a-v2",
        "claim_ids": ("claim-a-efficacy",),
        "created_at": REQUESTED_AT,
    }

    def interrupt_after_database_commit(**_kwargs: object) -> None:
        raise RuntimeError("模拟数据库提交后进程中断")

    monkeypatch.setattr(service, "_append_snapshot_event", interrupt_after_database_commit)
    with pytest.raises(RuntimeError, match="模拟数据库提交后进程中断"):
        service.register_report_snapshot(
            plan.refresh_id,
            report_kind=ReportKind.A,
            manifest=manifest,
        )

    resumed = RefreshService(project_root)
    snapshot_id = resumed.register_report_snapshot(
        plan.refresh_id,
        report_kind=ReportKind.A,
        manifest=manifest,
    )
    assert resumed.resume_status(plan.refresh_id)["registered_report_snapshot_ids"] == {
        ReportKind.A: snapshot_id
    }


def test_stricter_gate_override_recomputes_only_affected_gates_claims_pages_and_formats(
    tmp_path: Path,
) -> None:  # noqa: E501
    project_root, contract, report_b_locked = _build_parent_project(tmp_path)
    a_spec, b_spec, _universe, bindings, parent_result = _parent_a_gate_fixture(
        project_root, contract
    )
    service = RefreshService(project_root)
    before = _parent_history(project_root)

    tightened = _spec_with_unit(
        a_spec,
        "a_developer_originator",
        allowed_source_roles=["clinical_trial_registry"],
    )
    plan = service.plan_refresh(
        requested_at=REQUESTED_AT,
        actor_id=GATE_REQUEST_ACTOR,
        gate_specs={ReportKind.A: (a_spec, tightened), ReportKind.B: (b_spec, b_spec)},
        declared_affected_report_kinds=(ReportKind.A,),
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
    )

    # 只收紧覆盖生成紧邻子版本；受影响报告由 gates.coverage 反向依赖计算。
    assert plan.change_kinds == ("gate_tightening",)
    assert plan.child_contract.contract_version == 2
    assert plan.child_contract.data_cutoff == contract.data_cutoff
    assert plan.affected_report_kinds == (ReportKind.A,)
    assert plan.reuse_report_kinds == (ReportKind.B,)
    override = plan.gate_override
    assert override is not None
    assert override.changed_unit_ids == ("a_developer_originator",)
    assert override.parent_contract_version == "1"
    assert override.child_contract_version == "2"

    # 影响范围：受影响报告页面进入闭包并传播到站点格式；其余对象按摘要复用。
    assert _object_pairs(plan.affected_objects) == {
        ("page", "page:A:efficacy"),
        ("format", "html"),
    }
    assert {
        ("fact", "fact-9"),
        ("claim", "claim-b-results"),
        ("page", "page:B:results"),
    } <= _object_pairs(plan.reuse_objects)

    # 父门槛结果不可变：对象字段与决定保持原值。
    assert parent_result.contract_version == "1"
    assert parent_result.decision is ReportDecision.PASSED

    # 批准节点一之前不得接受：缺重建回执/门槛决定/新快照时失败关闭。
    with pytest.raises(RefreshIncompleteError):
        service.accept_refresh(plan.refresh_id, occurred_at=ACCEPTED_AT, actor_id=ACTOR_ID)
    assert _active_version(project_root) == 1

    # 局部重建：受影响页面与站点格式逐项追加回执。
    action_ids = _record_rebuilds(service, plan.refresh_id, _object_pairs(plan.affected_objects))
    assert len(action_ids) == 2

    # 重算门槛：受影响报告登记通过决定；重复登记不同决定失败关闭。
    parent_spec_result = _gate_result_for(
        project_id=contract.project_id,
        report_kind=ReportKind.A,
        contract_version="2",
        evidence_snapshot_id=parent_result.evidence_snapshot_id,
        spec=a_spec,
    )
    with pytest.raises(RefreshStateError, match="收紧后的规则"):
        service.record_gate_decision(
            plan.refresh_id,
            gate_result=parent_spec_result,
            recorded_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
        )
    refreshed_result = evaluate_report(
        tightened,
        _universe,
        bindings,
        contract_version="2",
    )
    decision = service.record_gate_decision(
        plan.refresh_id,
        gate_result=refreshed_result,
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    assert decision.decision == "passed"
    conflicting_result = _gate_result_for(
        project_id=contract.project_id,
        report_kind=ReportKind.A,
        contract_version="2",
        evidence_snapshot_id="evidence-snapshot-conflict",
        spec=tightened,
    )
    with pytest.raises(RefreshConflictError):
        service.record_gate_decision(
            plan.refresh_id,
            gate_result=conflicting_result,
            recorded_at=REQUESTED_AT,
            actor_id=ACTOR_ID,
        )

    # 新报告快照：绑定子合同版本与刷新后截止日。
    report_manifest = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "report": "A",
        "report_version": "v1",
        "data_cutoff": plan.child_contract.data_cutoff,
        "evidence_snapshot_id": parent_result.evidence_snapshot_id,
        "claim_snapshot_id": "claim-snapshot-a-v2",
        "coverage_set_id": "coverage-a-v2",
        "claim_ids": ("claim-a-efficacy",),
        "created_at": REQUESTED_AT,
    }
    snapshot_id = service.register_report_snapshot(
        plan.refresh_id,
        report_kind=ReportKind.A,
        manifest=report_manifest,
    )
    assert snapshot_id
    _record_accepted_qc(
        service,
        refresh_id=plan.refresh_id,
        report_kind=ReportKind.A,
        snapshot_id=snapshot_id,
        manifest=report_manifest,
        gate_result=refreshed_result,
    )

    completion = service.accept_refresh(plan.refresh_id, occurred_at=ACCEPTED_AT, actor_id=ACTOR_ID)
    assert completion.child_contract_version == 2
    assert completion.report_snapshot_ids == (snapshot_id,)

    # 接受后：现行版本翻转到子版本，父历史不变且未影响报告快照仍可读取。
    assert _active_version(project_root) == 2
    assert set(_contract_rows(project_root)) == {1, 2}
    _assert_parent_history_unchanged(project_root, before)
    store = SnapshotStore(project_root)
    assert store.read(report_b_locked)["report"] == "B"


def test_cutoff_expansion_and_gate_tightening_share_one_complete_refresh_plan(
    tmp_path: Path,
) -> None:
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    a_spec, b_spec, _universe, _bindings, _parent_result = _parent_a_gate_fixture(
        project_root, contract
    )
    tightened = _spec_with_unit(
        a_spec,
        "a_developer_originator",
        allowed_source_roles=["clinical_trial_registry"],
    )
    plan = RefreshService(project_root).plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
        gate_specs={ReportKind.A: (a_spec, tightened), ReportKind.B: (b_spec, b_spec)},
        declared_affected_report_kinds=(ReportKind.A,),
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )
    assert plan.change_kinds == ("cutoff_expansion", "gate_tightening")
    assert plan.rebuild_report_kinds == (ReportKind.A,)
    assert plan.gate_spec_bindings[0].spec_fingerprint == tightened.spec_fingerprint
    assert {item.source_version_id for item in plan.promoted} == {
        "cand-promote-1",
        "cand-promote-boundary",
    }


def test_cutoff_acceptance_rejects_report_built_from_another_evidence_snapshot(
    tmp_path: Path,
) -> None:
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    service = RefreshService(project_root)
    plan = service.plan_refresh(
        requested_cutoff=NEW_CUTOFF,
        requested_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
        sources=_cutoff_sources(),
    )
    _record_rebuilds(service, plan.refresh_id, _object_pairs(plan.affected_objects))
    foreign_evidence_id = "evidence-snapshot-from-another-refresh"
    report_manifest = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "report": "A",
        "report_version": "v1",
        "data_cutoff": NEW_CUTOFF,
        "evidence_snapshot_id": foreign_evidence_id,
        "claim_snapshot_id": "claim-snapshot-a-v2",
        "coverage_set_id": "coverage-a-v2",
        "claim_ids": ("claim-a-efficacy",),
        "created_at": REQUESTED_AT,
    }
    service.register_report_snapshot(
        plan.refresh_id, report_kind=ReportKind.A, manifest=report_manifest
    )
    service.record_gate_decision(
        plan.refresh_id,
        gate_result=_gate_result_for(
            project_id=contract.project_id,
            report_kind=ReportKind.A,
            contract_version="2",
            evidence_snapshot_id=foreign_evidence_id,
        ),
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    accepted_evidence_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "data_cutoff": NEW_CUTOFF,
        "source_version_ids": ("cand-promote-1", "cand-promote-boundary"),
        "fragment_ids": ("fragment-1",),
        "fact_version_ids": ("fact-1",),
        "scientific_content_digest": hashlib.sha256(b"actual-refresh-evidence").hexdigest(),
        "created_at": REQUESTED_AT,
    }
    with pytest.raises(RefreshIncompleteError, match="即将接受的证据快照"):
        service.accept_refresh(
            plan.refresh_id,
            occurred_at=ACCEPTED_AT,
            actor_id=ACTOR_ID,
            evidence_snapshot_manifest=accepted_evidence_manifest,
        )
    assert _active_version(project_root) == 1


@pytest.mark.parametrize(
    ("accepted", "valid_until", "error_text"),
    (
        (False, ACCEPTED_AT + timedelta(days=1), "未通过独立科学质控"),
        (True, REQUESTED_AT + timedelta(minutes=30), "已过期"),
    ),
)
def test_scientific_qc_veto_or_expiry_blocks_refresh_acceptance(
    tmp_path: Path,
    accepted: bool,
    valid_until: datetime,
    error_text: str,
) -> None:
    project_root, contract, _report_b = _build_parent_project(tmp_path)
    a_spec, b_spec, universe, bindings, parent_result = _parent_a_gate_fixture(
        project_root, contract
    )
    tightened = _spec_with_unit(
        a_spec,
        "a_developer_originator",
        allowed_source_roles=["clinical_trial_registry"],
    )
    service = RefreshService(project_root)
    plan = service.plan_refresh(
        requested_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
        gate_specs={ReportKind.A: (a_spec, tightened), ReportKind.B: (b_spec, b_spec)},
        declared_affected_report_kinds=(ReportKind.A,),
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
    )
    _record_rebuilds(service, plan.refresh_id, _object_pairs(plan.affected_objects))
    result = evaluate_report(tightened, universe, bindings, contract_version="2")
    service.record_gate_decision(
        plan.refresh_id,
        gate_result=result,
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    report_manifest: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": contract.project_id,
        "contract_version": 2,
        "report": "A",
        "report_version": "v1",
        "data_cutoff": plan.child_contract.data_cutoff,
        "evidence_snapshot_id": parent_result.evidence_snapshot_id,
        "claim_snapshot_id": "claim-snapshot-a-v2",
        "coverage_set_id": "coverage-a-v2",
        "claim_ids": ("claim-a-efficacy",),
        "created_at": REQUESTED_AT,
    }
    snapshot_id = service.register_report_snapshot(
        plan.refresh_id, report_kind=ReportKind.A, manifest=report_manifest
    )
    _record_accepted_qc(
        service,
        refresh_id=plan.refresh_id,
        report_kind=ReportKind.A,
        snapshot_id=snapshot_id,
        manifest=report_manifest,
        gate_result=result,
        accepted=accepted,
        valid_until=valid_until,
    )
    with pytest.raises(RefreshIncompleteError, match=error_text):
        service.accept_refresh(plan.refresh_id, occurred_at=ACCEPTED_AT, actor_id=ACTOR_ID)
    assert _active_version(project_root) == 1


def test_gate_tightening_rejects_relaxation_and_declaration_mismatch(tmp_path: Path) -> None:  # noqa: E501
    project_root, _contract, _report_b = _build_parent_project(tmp_path)
    a_spec, b_spec, _universe, _bindings, _parent_result = _parent_a_gate_fixture(
        project_root, _contract
    )
    service = RefreshService(project_root)
    before = _parent_history(project_root)
    tightened = _spec_with_unit(a_spec, "a_developer_originator", threshold=2)

    # 1) 放松（允许来源角色放宽）失败关闭。
    base_unit = next(unit for unit in a_spec.units if unit.unit_id == "a_developer_originator")
    relaxed = _spec_with_unit(
        a_spec,
        "a_developer_originator",
        allowed_source_roles=[role.value for role in base_unit.allowed_source_roles]
        + ["protocol_sap"],
    )
    with pytest.raises(RefreshServiceError):
        service.plan_refresh(
            requested_at=REQUESTED_AT,
            actor_id=GATE_REQUEST_ACTOR,
            gate_specs={ReportKind.A: (a_spec, relaxed), ReportKind.B: (b_spec, b_spec)},
            declared_affected_report_kinds=(ReportKind.A,),
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
        )

    # 2) 声明受影响集合与反向依赖计算不一致 → 失败关闭。
    with pytest.raises(RefreshServiceError):
        service.plan_refresh(
            requested_at=REQUESTED_AT,
            actor_id=GATE_REQUEST_ACTOR,
            gate_specs={ReportKind.A: (a_spec, tightened), ReportKind.B: (b_spec, b_spec)},
            declared_affected_report_kinds=(ReportKind.A, ReportKind.B),
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
        )

    # 3) 覆盖没有任何单元变化，不构成增量刷新 → 失败关闭。
    with pytest.raises(RefreshServiceError):
        service.plan_refresh(
            requested_at=REQUESTED_AT,
            actor_id=GATE_REQUEST_ACTOR,
            gate_specs={ReportKind.A: (a_spec, a_spec), ReportKind.B: (b_spec, b_spec)},
            declared_affected_report_kinds=(),
            impact_edges=_impact_edges(),
            impact_nodes=_impact_nodes(),
        )

    assert set(_contract_rows(project_root)) == {1}
    _assert_parent_history_unchanged(project_root, before)


def test_blocked_gate_decision_fails_closed_without_draft_acceptance(tmp_path: Path) -> None:  # noqa: E501
    project_root, contract, report_b_locked = _build_parent_project(tmp_path)
    a_spec, b_spec, _universe, _bindings, _parent_result = _parent_a_gate_fixture(
        project_root, contract
    )
    service = RefreshService(project_root)
    tightened = _spec_with_unit(a_spec, "a_developer_originator", threshold=2)
    plan = service.plan_refresh(
        requested_at=REQUESTED_AT,
        actor_id=GATE_REQUEST_ACTOR,
        gate_specs={ReportKind.A: (a_spec, tightened), ReportKind.B: (b_spec, b_spec)},
        declared_affected_report_kinds=(ReportKind.A,),
        impact_edges=_impact_edges(),
        impact_nodes=_impact_nodes(),
    )
    _record_rebuilds(service, plan.refresh_id, _object_pairs(plan.affected_objects))

    # 关键证据仍未达门槛：继续阻断，不生成草稿，子版本不得登记为已接受。
    blocked_result = evaluate_report(
        tightened,
        _universe,
        _bindings,
        contract_version="2",
    )
    assert blocked_result.decision is ReportDecision.BLOCKED
    service.record_gate_decision(
        plan.refresh_id,
        gate_result=blocked_result,
        recorded_at=REQUESTED_AT,
        actor_id=ACTOR_ID,
    )
    with pytest.raises(RefreshIncompleteError) as blocked_error:
        service.accept_refresh(plan.refresh_id, occurred_at=ACCEPTED_AT, actor_id=ACTOR_ID)
    assert "阻断" in str(blocked_error.value)
    assert _active_version(project_root) == 1
    status = service.resume_status(plan.refresh_id)
    assert status["completion"] is None
    assert status["pending_gate_report_kinds"] == ()
    assert contract.data_cutoff == PARENT_CUTOFF
    store = SnapshotStore(project_root)
    assert store.read(report_b_locked)["report"] == "B"
