"""Task 3.4 新建报告图节点合同与 A/B/C 分支隔离：GT07–GT10 四个顶层节点。

节点清单、字段与行为期望都是 v1.2 §5.3/§10.1 字面 fixture；输出校验使用
合同声明的封闭类型词表（validate_typed_outputs），每个声明输出都翻转一次
非法类型。GT10 机械证明共享证据、分离的 gate/候选快照/分析/产物状态。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.graph.state import EVIDENCE_LEDGER_KEY

_NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)

# v1.2 §10.1 新建报告图节点清单（字面 fixture，missing=0 extra=0）
GT07_NODE_IDS: tuple[str, ...] = (
    "intake",
    "preflight",
    "universe",
    "route",
    "ingest",
    "extract",
    "resolve",
    "gate",
    "recovery",
    "snapshot",
    "scientific_qc",
    "analyze",
    "format",
    "acceptance",
)

# 三个合同节点各自的节点组（并集覆盖全部 14 个节点）
GT07_INTAKE_GROUP: tuple[str, ...] = ("intake", "preflight", "universe", "route")
GT08_MID_GROUP: tuple[str, ...] = ("ingest", "extract", "resolve", "gate", "recovery")
GT09_TAIL_GROUP: tuple[str, ...] = ("snapshot", "scientific_qc", "analyze", "format", "acceptance")

# 报告写键族：gate / 候选快照 / 科学质控 / 分析 / 格式产物；不存在共享的 gate 状态键
GT09_REPORT_SCOPED_FAMILIES: tuple[str, ...] = (
    "gate", "snapshot", "qc", "analysis", "artifact",
)
GT09_REPORT_KINDS: tuple[str, ...] = ("A", "B", "C")
GT09_SIDE_EFFECT_CLASSES: frozenset[str] = frozenset(
    {"none", "publish", "move", "approve", "delete"}
)
GT09_SCOPES: frozenset[str] = frozenset({"shared", "report", "artifact"})
# §10.4：可重试故障至少三次同路径尝试的节点
GT09_RETRY_NODES: frozenset[str] = frozenset(
    {"route", "ingest", "extract", "recovery", "format"}
)

# 每个节点的合法类型化输出 fixture（字面；sha256/evidence_digest 为 64 位十六进制）
_TYPED_OUTPUT_FIXTURES: dict[str, dict[str, object]] = {
    "intake": {"project_contract_id": "contract_1"},
    "preflight": {"capability_matrix_id": "matrix_1"},
    "universe": {"universe_receipt_id": "universe_1"},
    "route": {"source_graph_id": "graph_1"},
    "ingest": {"ingest_receipt_id": "ingest_1"},
    "extract": {"extract_receipt_id": "extract_1"},
    "resolve": {"evidence_references": [{"fragment_id": "frag_1", "sha256": "0" * 64}]},
    "gate": {"gate_passed": True, "failures": ["unit_x"], "evidence_digest": "d" * 64},
    "recovery": {"recovery_receipt": "recovery_1"},
    "snapshot": {"snapshot_id": "snap_1"},
    "scientific_qc": {
        "qc_verdict": {
            "verdict_id": "qc-verdict-1",
            "verdict_digest": "a" * 64,
            "candidate_snapshot_id": "snap_1",
            "candidate_content_digest": "b" * 64,
            "review_input_digest": "c" * 64,
        }
    },
    "analyze": {"pages": ["page_1"]},
    "format": {
        "format": "html",
        "artifact_id": "art_1",
        "site_relative_path": "reports/A/v1/html",
        "manifest_relative_path": "reports/A/v1/html.manifest.json",
        "candidate_artifact_digest": "b" * 64,
        "visual_plan_digest": "a" * 64,
    },
    "acceptance": {
        "acceptance_verdict": "passed",
        "render_evidence": {"rendered": True},
        "beautification_loop": {"round": 1},
        "visual_verdict": {"verdict": "accepted"},
    },
}

# 每个声明输出类型的非法翻转值（字面）
_INVALID_FLIPS: dict[str, object] = {
    "str": 5,
    "bool": "yes",
    "tuple[str]": ["ok", 5],
    "tuple[EvidenceReference]": [{"fragment_id": "", "sha256": "0" * 64}],
    "OutputFormat": "unknown_format",
    "dict[str, object]": [],
    "QCVerificationReference": "accepted",
    "ReportKind": "X",
    "tuple[ReportKind]": ["X"],
    "tuple[OutputFormat]": ["bogus"],
}


def _valid_state_key_templates() -> frozenset[str]:
    """有效状态键词表（含报告模板）：运行时族键 + 共享证据键 + 报告写族模板。"""
    runtime_families = (
        "project",
        "report_evidence",
        "format_artifact",
        "download_request",
        "revision_approval",
    )
    keys = set(runtime_families)
    keys.add(EVIDENCE_LEDGER_KEY)
    keys.update(
        f"{family}.{{report_kind}}" for family in GT09_REPORT_SCOPED_FAMILIES
    )
    return frozenset(keys)


def _assert_complete_contract(contract: object) -> None:
    """单节点合同结构断言：版本、类型化字段、完成谓词存在、读写集、
    重试策略、声明错误、幂等材料、副作用类、作用域与不可变性。"""
    from ci_workflow.graph.types import NodeContract

    node = contract
    assert isinstance(node, NodeContract)
    assert node.node_id
    assert node.version.startswith("1.")
    assert node.typed_inputs, f"{node.node_id} 缺少类型化输入"
    assert node.typed_outputs, f"{node.node_id} 缺少类型化输出"
    assert callable(node.completion_predicate), f"{node.node_id} 缺少完成谓词"
    assert node.completion_summary, f"{node.node_id} 缺少完成摘要"
    assert isinstance(node.reads, tuple) and isinstance(node.writes, tuple)
    assert node.retry_policy is not None
    assert node.declared_errors, f"{node.node_id} 缺少声明错误"
    assert node.idempotency_material, f"{node.node_id} 缺少幂等材料"
    assert node.side_effect_class in GT09_SIDE_EFFECT_CLASSES
    assert node.scope in GT09_SCOPES
    # 合同不可变
    with pytest.raises(FrozenInstanceError):
        node.typed_inputs = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        node.retry_policy = None  # type: ignore[misc]
    # 类型化字段逐字段完整
    for field in (*node.typed_inputs, *node.typed_outputs):
        assert field.name, f"{node.node_id} 字段名缺失"
        assert field.type, f"{node.node_id}.{field.name} 类型缺失"
        assert field.description, f"{node.node_id}.{field.name} 描述缺失"
    # 读写集引用有效状态键（含报告模板）
    valid_templates = _valid_state_key_templates()
    for key in node.reads:
        assert key in valid_templates, f"{node.node_id} 读取未声明键 {key}"
    for key in node.writes:
        assert key in valid_templates, f"{node.node_id} 写入未声明键 {key}"
    # 重试策略与声明错误
    assert node.retry_policy.max_attempts >= 1
    assert node.retry_policy.backoff_seconds >= 0.0
    assert node.retry_policy.retryable_errors, f"{node.node_id} 无可重试错误"
    # 作用域与写集一致：report/artifact 只写自己的报告模板；shared 只写共享证据键
    if node.scope in ("report", "artifact"):
        for key in node.writes:
            assert "{report_kind}" in key, f"{node.node_id} 写集必须按报告模板隔离"
            assert key.split(".", 1)[0] in GT09_REPORT_SCOPED_FAMILIES
    else:
        for key in node.writes:
            assert key == EVIDENCE_LEDGER_KEY, f"{node.node_id} shared 只写共享证据键"


def _assert_contract_with_fixture(contract: object) -> None:
    """合同结构 + 合法类型化输出 fixture + 完成谓词 + 逐个输出翻转为非法类型。"""
    from ci_workflow.graph.types import NodeContract, validate_typed_outputs

    node = contract
    assert isinstance(node, NodeContract)
    _assert_complete_contract(node)
    fixture = _TYPED_OUTPUT_FIXTURES[node.node_id]
    assert set(fixture) == {field.name for field in node.typed_outputs}
    # 合法类型化 fixture 通过类型校验与完成谓词
    validate_typed_outputs(node, fixture)
    assert node.completion_predicate(fixture) is True, (
        f"{node.node_id} 合法类型化输出未通过完成谓词"
    )
    assert node.completion_predicate({}) is False, f"{node.node_id} 空输出不应完成"
    partial = dict(fixture)
    partial.pop(next(iter(partial)))
    assert node.completion_predicate(partial) is False, (
        f"{node.node_id} 缺少声明输出不应完成"
    )
    # 逐个声明输出翻转为非法类型 → 拒绝
    for field in node.typed_outputs:
        flipped = dict(fixture)
        flipped[field.name] = _INVALID_FLIPS[field.type]
        with pytest.raises(ValueError, match="输出类型"):
            validate_typed_outputs(node, flipped)


def test_intake_preflight_universe_and_route_nodes_declare_complete_contracts() -> None:
    """GT07：入口/预检/本体宇宙/来源路由节点合同完整、类型化、不可变。"""
    from ci_workflow.graph.definitions import NEW_REPORT_NODES, node_contract

    actual_ids = {node.node_id for node in NEW_REPORT_NODES}
    expected_ids = set(GT07_NODE_IDS)
    assert actual_ids == expected_ids, (
        f"missing={sorted(expected_ids - actual_ids)} extra={sorted(actual_ids - expected_ids)}"
    )
    assert len(NEW_REPORT_NODES) == len(GT07_NODE_IDS) == 14
    for node_id in GT07_INTAKE_GROUP:
        _assert_contract_with_fixture(node_contract(node_id))


def test_ingest_extract_resolve_and_gate_nodes_declare_complete_contracts(
    tmp_path: Path,
) -> None:
    """GT08：摄取/抽取/解析/门槛/恢复节点合同；complete_node 身份、类型与谓词。"""
    from ci_workflow.graph.definitions import node_contract
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.storage.event_store import EventConflictError, EventStore

    for node_id in GT08_MID_GROUP:
        _assert_contract_with_fixture(node_contract(node_id))

    executor_a = GraphExecutor(tmp_path / "项目", run_id="run_a")
    executor_b = GraphExecutor(tmp_path / "项目", run_id="run_b")

    # input_digest 必须非空
    with pytest.raises(ValueError, match="input_digest"):
        executor_a.complete_node(
            "resolve",
            outputs=_TYPED_OUTPUT_FIXTURES["resolve"],
            input_digest="   ",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 完成谓词：声明名齐但值为 None → 拒绝
    with pytest.raises(ValueError, match="完成谓词"):
        executor_a.complete_node(
            "gate",
            outputs={
                "gate_passed": None,
                "failures": ["unit_x"],
                "evidence_digest": "d" * 64,
            },
            input_digest="gate:A:1",
            report_kind="A",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 空输出 → 拒绝
    with pytest.raises(ValueError):
        executor_a.complete_node(
            "gate",
            outputs={},
            input_digest="gate:A:1",
            report_kind="A",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 类型化：gate_passed="yes" → 拒绝
    with pytest.raises(ValueError, match="输出类型"):
        executor_a.complete_node(
            "gate",
            outputs={
                "gate_passed": "yes",
                "failures": ["unit_x"],
                "evidence_digest": "d" * 64,
            },
            input_digest="gate:A:1",
            report_kind="A",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 无效证据引用 → 拒绝
    with pytest.raises(ValueError, match="输出类型"):
        executor_a.complete_node(
            "resolve",
            outputs={
                "evidence_references": [
                    {"fragment_id": "", "sha256": "0" * 64}
                ]
            },
            input_digest="resolve:bad",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 未知 format → 拒绝
    with pytest.raises(ValueError, match="输出类型"):
        executor_a.complete_node(
            "format",
            outputs={
                "format": "unknown_format",
                "artifact_id": "art_1",
                "site_relative_path": "reports/A/v1/html",
                "manifest_relative_path": "reports/A/v1/html.manifest.json",
                "candidate_artifact_digest": "b" * 64,
                "visual_plan_digest": "a" * 64,
            },
            input_digest="format:A:1",
            report_kind="A",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )

    # 同项目两运行完成同一节点同一输入输出 → 两个不同有效事件
    outputs = _TYPED_OUTPUT_FIXTURES["resolve"]
    first = executor_a.complete_node(
        "resolve",
        outputs=outputs,
        input_digest="resolve:shared:1",
        project_id="p_gt08",
        actor_id="pi",
        occurred_at=_NOW,
    )
    second = executor_b.complete_node(
        "resolve",
        outputs=outputs,
        input_digest="resolve:shared:1",
        project_id="p_gt08",
        actor_id="pi",
        occurred_at=_NOW,
    )
    assert first.event_id != second.event_id
    assert first.idempotency_key != second.idempotency_key
    events = EventStore(tmp_path / "项目").read_all()
    assert len(events) == 2
    assert {event.run_id for event in events} == {"run_a", "run_b"}
    # 项目身份：项目根已确立 p_gt08；另一项目写前失败关闭
    with pytest.raises(ValueError, match="项目身份"):
        executor_a.complete_node(
            "resolve",
            outputs=outputs,
            input_digest="resolve:other:1",
            project_id="p_other",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 精确重试（同一输入+输出，更晚时间戳）→ 返回原事件，不新增
    replay = executor_a.complete_node(
        "resolve",
        outputs=outputs,
        input_digest="resolve:shared:1",
        project_id="p_gt08",
        actor_id="pi",
        occurred_at=_NOW + timedelta(minutes=5),
    )
    assert replay == first
    assert len(EventStore(tmp_path / "项目").read_all()) == 2
    # 同一输入身份、输出漂移 → EventConflictError
    with pytest.raises(EventConflictError):
        executor_a.complete_node(
            "resolve",
            outputs={"evidence_references": [{"fragment_id": "f2", "sha256": "0" * 64}]},
            input_digest="resolve:shared:1",
            project_id="p_gt08",
            actor_id="pi",
            occurred_at=_NOW,
        )
    # 不同输入摘要 → 新完成
    fresh = executor_a.complete_node(
        "resolve",
        outputs=outputs,
        input_digest="resolve:shared:2",
        project_id="p_gt08",
        actor_id="pi",
        occurred_at=_NOW,
    )
    assert fresh.event_id != first.event_id
    assert len(EventStore(tmp_path / "项目").read_all()) == 3


def test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts() -> None:
    """GT09：快照/科学质控/分析/格式/验收节点合同；读写集、重试、作用域与隔离词表。"""
    from ci_workflow.graph.definitions import node_contract
    from ci_workflow.graph.state import initial_state, report_scoped_key

    for node_id in GT09_TAIL_GROUP:
        _assert_contract_with_fixture(node_contract(node_id))
    # §10.4：可重试节点至少三次同路径尝试
    for node_id in GT09_RETRY_NODES:
        assert node_contract(node_id).retry_policy.max_attempts >= 3, (
            f"{node_id} 重试次数不足三次"
        )
    # A/B/C 共享证据读取：gate 读取共享证据键
    gate = node_contract("gate")
    assert EVIDENCE_LEDGER_KEY in gate.reads
    assert gate.writes == ("gate.{report_kind}",)
    # 机械隔离断言：不存在共享的 gate/快照/分析/产物状态键；A/B/C 写键互不相同
    state = initial_state()
    assert EVIDENCE_LEDGER_KEY in state
    scoped_keys = set()
    for family in GT09_REPORT_SCOPED_FAMILIES:
        assert family not in state, f"存在共享 {family} 状态键"
        for kind in GT09_REPORT_KINDS:
            key = report_scoped_key(family, kind)
            assert key in state
            scoped_keys.add(key)
    assert len(scoped_keys) == 15
    for family in GT09_REPORT_SCOPED_FAMILIES:
        rendered = {report_scoped_key(family, kind) for kind in GT09_REPORT_KINDS}
        assert len(rendered) == 3
    # 科学质控只写自己的质控键，绝不改写快照/证据/分析/产物键
    qc_contract = node_contract("scientific_qc")
    assert qc_contract.writes == ("qc.{report_kind}",)
    forbidden_writes = {
        "snapshot.{report_kind}", "evidence",
        "analysis.{report_kind}", "artifact.{report_kind}",
    }
    assert not (set(qc_contract.writes) & forbidden_writes)
    assert "snapshot.{report_kind}" in qc_contract.reads


def test_report_branches_share_evidence_without_sharing_gate_state(
    tmp_path: Path,
) -> None:
    """GT10：A/B/C 读同一共享证据，但 gate/候选快照/分析与产物状态按报告隔离。

    一个报告阻断不得改写另一个报告的门槛、快照或运行状态；不建模共享 gate 状态。
    分支初始化必须走真实声明路径 queued -> collecting。
    """
    from ci_workflow.graph.definitions import node_contract
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.state import EVIDENCE_LEDGER_KEY, report_scoped_key
    from ci_workflow.graph.types import TransitionRequest

    executor = GraphExecutor(tmp_path / "项目", run_id="run_gt10")

    def complete(
        node_id: str,
        *,
        report_kind: str | None,
        outputs: dict[str, object],
        input_digest: str,
    ) -> None:
        executor.complete_node(
            node_id,
            outputs=outputs,
            report_kind=report_kind,
            project_id="p_gt10",
            actor_id="gt10",
            occurred_at=_NOW,
            input_digest=input_digest,
        )

    def transition(
        *,
        request_id: str,
        object_id: str,
        from_state: str,
        to_state: str,
        trigger: str,
        evidence: dict[str, object],
    ) -> None:
        if trigger == "isolated_qc_accepted":
            evidence = dict(evidence)
            evidence_without_auth = {
                k: v for k, v in evidence.items()
                if k != "qc_authorization_id"
            }
            evidence_digest = _canonical_digest(evidence_without_auth)
            from tests.graph._qc_authorization_fixture import (
                issue_test_qc_authorization,
            )

            auth_id = issue_test_qc_authorization(
                executor,
                report_object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                verdict="accepted",
                evidence_digest=evidence_digest,
                actor_id="gt10",
                project_id="p_gt10",
                occurred_at=_NOW,
            )
            evidence["qc_authorization_id"] = auth_id
        executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=request_id,
                project_id="p_gt10",
                run_id="run_gt10",
                family="report_evidence",
                object_id=object_id,
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                evidence=evidence,
                actor_id="gt10",
                occurred_at=_NOW,
            )
        )

    # 1) 共享证据：resolve 节点（shared 作用域）写入共享证据账本
    assert node_contract("resolve").scope == "shared"
    complete(
        "resolve",
        report_kind=None,
        outputs={
            "evidence_references": [
                {"fragment_id": "frag_shared_1", "sha256": "0" * 64},
                {"fragment_id": "frag_shared_2", "sha256": "1" * 64},
            ]
        },
        input_digest="resolve:1",
    )
    state = executor.state()
    ledger_refs = state[EVIDENCE_LEDGER_KEY]["evidence_references"]
    assert {ref["fragment_id"] for ref in ledger_refs} == {"frag_shared_1", "frag_shared_2"}
    evidence_digest = _canonical_digest(state[EVIDENCE_LEDGER_KEY])

    # 2) A/B/C 各 gate 读同一共享证据，写各自隔离的 gate 键
    gate_contract = node_contract("gate")
    assert EVIDENCE_LEDGER_KEY in gate_contract.reads
    assert gate_contract.writes == ("gate.{report_kind}",)
    complete(
        "gate",
        report_kind="A",
        outputs={
            "gate_passed": False,
            "failures": ["unit_x"],
            "evidence_digest": evidence_digest,
        },
        input_digest="gate:A:1",
    )
    complete(
        "gate",
        report_kind="B",
        outputs={
            "gate_passed": True,
            "failures": [],
            "evidence_digest": evidence_digest,
        },
        input_digest="gate:B:1",
    )
    complete(
        "gate",
        report_kind="C",
        outputs={
            "gate_passed": True,
            "failures": [],
            "evidence_digest": evidence_digest,
        },
        input_digest="gate:C:1",
    )
    state = executor.state()
    gate_a = state[report_scoped_key("gate", "A")]
    gate_b = state[report_scoped_key("gate", "B")]
    assert gate_a["gate_passed"] is False and gate_a["failures"] == ["unit_x"]
    assert gate_b["gate_passed"] is True and gate_b["failures"] == []
    # 两个报告读取同一共享证据快照摘要
    assert gate_a["evidence_digest"] == gate_b["evidence_digest"] == evidence_digest
    # 不存在共享 gate 状态键
    assert "gate" not in state
    assert report_scoped_key("gate", "A") != report_scoped_key("gate", "B")

    # 3) 候选快照、分析与格式产物按报告隔离
    complete(
        "snapshot", report_kind="A", outputs={"snapshot_id": "snap_A_1"},
        input_digest="snapshot:A:1",
    )
    complete(
        "snapshot", report_kind="B", outputs={"snapshot_id": "snap_B_1"},
        input_digest="snapshot:B:1",
    )
    complete(
        "analyze", report_kind="A", outputs={"pages": ["page_A_1", "page_A_2"]},
        input_digest="analyze:A:1",
    )
    complete(
        "analyze", report_kind="B", outputs={"pages": ["page_B_1"]},
        input_digest="analyze:B:1",
    )
    complete(
        "format", report_kind="A",
        outputs={
            "format": "html",
            "artifact_id": "art_A_html",
            "site_relative_path": "reports/A/v1/html",
            "manifest_relative_path": "reports/A/v1/html.manifest.json",
            "candidate_artifact_digest": "b" * 64,
            "visual_plan_digest": "a" * 64,
        },
        input_digest="format:A:html:1",
    )
    complete(
        "format", report_kind="B",
        outputs={
            "format": "html",
            "artifact_id": "art_B_html",
            "site_relative_path": "reports/B/v1/html",
            "manifest_relative_path": "reports/B/v1/html.manifest.json",
            "candidate_artifact_digest": "d" * 64,
            "visual_plan_digest": "c" * 64,
        },
        input_digest="format:B:html:1",
    )
    state = executor.state()
    assert state[report_scoped_key("snapshot", "A")]["snapshot_id"] == "snap_A_1"
    assert state[report_scoped_key("snapshot", "B")]["snapshot_id"] == "snap_B_1"
    assert state[report_scoped_key("analysis", "A")]["pages"] == ["page_A_1", "page_A_2"]
    assert state[report_scoped_key("analysis", "B")]["pages"] == ["page_B_1"]
    assert state[report_scoped_key("artifact", "A")]["html"]["artifact_id"] == "art_A_html"
    assert state[report_scoped_key("artifact", "B")]["html"]["artifact_id"] == "art_B_html"
    for family in ("snapshot", "analysis", "artifact"):
        assert family not in state

    # 4) 分支初始化走真实声明路径 queued -> collecting，再阻断/质控互不改写
    for kind in ("A", "B"):
        transition(
            request_id=f"gt10:{kind}:collect",
            object_id=f"report_{kind}",
            from_state="queued",
            to_state="collecting",
            trigger="candidate_scope_locked",
            evidence={"candidate_scope_locked": True},
        )
    transition(
        request_id="gt10:a:blocked",
        object_id="report_A",
        from_state="collecting",
        to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        evidence={
            "critical_units_still_failing": True,
            "recovery_exhausted": True,
            "independent_review_exhausted": True,
            "no_continuable_user_action": True,
        },
    )
    transition(
        request_id="gt10:b:qc",
        object_id="report_B",
        from_state="collecting",
        to_state="scientific_qc",
        trigger="gate_deterministic_pass",
        evidence={"gate_deterministic_pass": True, "candidate_snapshot_established": True},
    )
    transition(
        request_id="gt10:b:locked",
        object_id="report_B",
        from_state="scientific_qc",
        to_state="snapshot_locked",
        trigger="isolated_qc_accepted",
        evidence={
            "isolated_qc_accepted": True,
            "qc_verdict_id": "qc-verdict-1",
            "qc_verdict_digest": "a" * 64,
            "qc_candidate_snapshot_id": "snap_B_1",
            "qc_candidate_content_digest": "b" * 64,
            "qc_review_input_digest": "c" * 64,
            "qc_report_object_id": "report_B",
            "qc_context_digest": "d" * 64,
        },
    )
    state = executor.state()
    assert state["report_evidence"]["report_A"] == "evidence_blocked"
    assert state["report_evidence"]["report_B"] == "snapshot_locked"
    # A 阻断后，B 的门槛与快照状态仍独立且未变
    assert state[report_scoped_key("gate", "B")]["gate_passed"] is True
    assert state[report_scoped_key("snapshot", "B")]["snapshot_id"] == "snap_B_1"


def _canonical_digest(value: object) -> str:
    import hashlib
    import json

    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
