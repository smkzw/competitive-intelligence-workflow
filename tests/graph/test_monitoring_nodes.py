"""Task 9.3 监测图节点合同测试：六节点管线、越权边界与内部 Skill 中文边界。

设计合同（Task 9.3 design.md §图与Skill）：

- 管线恰为读取监测范围 → 执行来源观察 → 归一化与去重 → 记录候选/诊断
  → 等待用户处置 → 生成刷新交接，顺序即元组顺序。
- 节点输出不含事实、声明、快照、报告或发布能力：全部节点副作用类为
  none、共享作用域、只写 monitoring.* 键；导入期不变量被直接复跑。
- 观察四类结果在 observe 节点输出层面可区分；处置与交接去向词表封闭，
  交接只进入正常刷新，不进入修订批准流。
- 内部监测 Skill 必须给出四类诊断中文提示边界，并明确候选进入
  "正常刷新"而非直接进入修订流。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ci_workflow.graph.definitions.monitoring import (
    DISPOSITION_DEFER,
    DISPOSITION_START_REFRESH,
    HANDOFF_TARGET_NORMAL_REFRESH,
    MONITORING_DISPOSITIONS,
    MONITORING_NODE_IDS,
    MONITORING_NODES,
    MONITORING_OUTCOMES,
    MONITORING_STATE_PREFIX,
    OUTCOME_CHANGED,
    OUTCOME_NEEDS_USER,
    OUTCOME_NO_CHANGE,
    OUTCOME_NOT_PUBLIC,
    OUTCOME_TECHNICAL_FAILURE,
    monitoring_node_contract,
)
from ci_workflow.graph.definitions.new_report import NEW_REPORT_NODES
from ci_workflow.graph.definitions.refresh import REFRESH_NODES
from ci_workflow.graph.types import validate_typed_outputs

ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = ROOT / "skills" / "_internal" / "monitoring" / "SKILL.md"

MONITORING_PIPELINE_NODE_IDS: tuple[str, ...] = (
    "monitor_scope",
    "monitor_observe",
    "monitor_dedupe",
    "monitor_record",
    "monitor_await_disposition",
    "monitor_handoff",
)

# 每个节点合法类型化输出 fixture（handoff_digest 为 64 位十六进制摘要）
_TYPED_OUTPUT_FIXTURES: dict[str, dict[str, object]] = {
    "monitor_scope": {
        "scope_receipt_id": "monitor_scope_1",
        "observable_source_ids": ["src_reg_1", "src_ct_gov"],
        "last_cutoff": "2026-08-20",
    },
    "monitor_observe": {
        "observation_receipt_id": "observation_1",
        "changed_source_ids": ["src_ct_gov"],
        "unchanged_source_ids": ["src_reg_1"],
        "not_public_source_ids": [],
        "failed_source_ids": [],
    },
    "monitor_dedupe": {
        "dedupe_receipt_id": "dedupe_1",
        "new_candidate_ids": ["candidate_1"],
        "merged_candidate_ids": [],
    },
    "monitor_record": {
        "recorded_candidate_ids": ["candidate_1"],
        "diagnosis_categories": [OUTCOME_CHANGED],
        "user_guidance_zh": "发现来源信息变化，已记录变更候选，等待您选择处置。",
        "possibly_affected_reports": ["A"],
        "possibly_affected_page_ids": ["page_a_efficacy"],
    },
    "monitor_await_disposition": {
        "disposition": DISPOSITION_START_REFRESH,
        "disposition_receipt_id": "disposition_1",
    },
    "monitor_handoff": {
        "handoff_id": "handoff_1",
        "handoff_digest": "a" * 64,
        "bound_contract_version": "1.0",
    },
}

_INVALID_FLIPS: dict[str, object] = {
    "str": 5,
    "bool": "yes",
    "tuple[str]": ["ok", 5],
    "tuple[ReportKind]": ["X"],
    "dict[str, object]": [],
}


def _assert_complete_contract(contract: object) -> None:
    from ci_workflow.graph.types import NodeContract

    assert isinstance(contract, NodeContract)
    node = contract
    assert node.node_id
    assert node.version.startswith("1.")
    assert node.typed_inputs, f"{node.node_id} 缺少类型化输入"
    assert node.typed_outputs, f"{node.node_id} 缺少类型化输出"
    assert callable(node.completion_predicate), f"{node.node_id} 缺少完成谓词"
    assert node.completion_summary, f"{node.node_id} 缺少完成摘要"
    assert isinstance(node.reads, tuple) and isinstance(node.writes, tuple)
    assert node.retry_policy is not None
    assert node.retry_policy.max_attempts >= 1
    assert node.retry_policy.backoff_seconds >= 0.0
    assert node.retry_policy.retryable_errors, f"{node.node_id} 无可重试错误"
    assert node.declared_errors, f"{node.node_id} 缺少声明错误"
    assert node.idempotency_material, f"{node.node_id} 缺少幂等材料"
    assert node.side_effect_class == "none", f"{node.node_id} 监测节点不得有副作用"
    assert node.scope == "shared"
    for field in (*node.typed_inputs, *node.typed_outputs):
        assert field.name, f"{node.node_id} 字段名缺失"
        assert field.type, f"{node.node_id}.{field.name} 类型缺失"
        assert field.description, f"{node.node_id}.{field.name} 描述缺失"
    # 中文表达：节点摘要必须是中文句子，不得暴露后端状态名或英文术语
    assert any("\u4e00" <= ch <= "\u9fff" for ch in node.completion_summary)
    with pytest.raises(FrozenInstanceError):
        node.typed_inputs = ()  # type: ignore[misc]


def test_monitoring_graph_declares_six_node_pipeline_in_design_order() -> None:
    """管线恰为设计声明的六节点，顺序一致；未知节点失败关闭。"""
    assert MONITORING_NODE_IDS == MONITORING_PIPELINE_NODE_IDS
    assert len(MONITORING_NODES) == 6
    with pytest.raises(ValueError, match="未知监测图节点"):
        monitoring_node_contract("monitor_publish")
    with pytest.raises(ValueError, match="未知监测图节点"):
        monitoring_node_contract("ingest")


def test_monitoring_node_contracts_are_complete_typed_and_immutable() -> None:
    for node_id in MONITORING_PIPELINE_NODE_IDS:
        _assert_complete_contract(monitoring_node_contract(node_id))


def test_monitoring_outputs_pass_closed_type_vocabulary_and_completion_predicates() -> None:
    """合法 fixture 通过封闭类型校验与完成谓词；空/缺字段/逐字段翻转拒绝。"""
    for node_id in MONITORING_PIPELINE_NODE_IDS:
        node = monitoring_node_contract(node_id)
        fixture = _TYPED_OUTPUT_FIXTURES[node_id]
        assert set(fixture) == {field.name for field in node.typed_outputs}
        validate_typed_outputs(node, fixture)
        assert node.completion_predicate(fixture) is True
        assert node.completion_predicate({}) is False
        partial = dict(fixture)
        partial.pop(next(iter(partial)))
        assert node.completion_predicate(partial) is False
        for field in node.typed_outputs:
            flipped = dict(fixture)
            flipped[field.name] = _INVALID_FLIPS[field.type]
            with pytest.raises(ValueError, match="输出类型"):
                validate_typed_outputs(node, flipped)


def test_monitoring_nodes_never_write_core_truth_or_report_state() -> None:
    """只写 monitoring.* 键；证据/门槛/快照/质控/分析/产物与运行状态族一律不写。"""
    forbidden_writes = {
        "evidence",
        "project",
        "report_evidence",
        "format_artifact",
        "download_request",
        "revision_approval",
    }
    forbidden_writes.update(
        f"{family}.{{report_kind}}" for family in ("gate", "snapshot", "qc", "analysis", "artifact")
    )
    for node in MONITORING_NODES:
        assert node.writes, f"{node.node_id} 必须声明写集"
        for key in node.writes:
            assert key.startswith(MONITORING_STATE_PREFIX), f"{node.node_id} 越权写键: {key}"
            assert key not in forbidden_writes
        for key in node.reads:
            allowed = key.startswith(MONITORING_STATE_PREFIX) or key == "project"
            assert allowed, f"{node.node_id} 越权读键: {key}"


def test_monitoring_node_ids_do_not_collide_with_core_graphs() -> None:
    monitoring_ids = set(MONITORING_NODE_IDS)
    assert not monitoring_ids & {n.node_id for n in NEW_REPORT_NODES}
    assert not monitoring_ids & {n.node_id for n in REFRESH_NODES}


def test_monitoring_outcome_and_disposition_vocabularies_are_closed() -> None:
    """观察结果与用户处置词表封闭，且与域机器合同逐字对齐。"""
    from typing import get_args

    from ci_workflow.domain.monitoring import ObservationOutcome, UserDisposition

    assert MONITORING_OUTCOMES == (
        OUTCOME_CHANGED,
        OUTCOME_NO_CHANGE,
        OUTCOME_NOT_PUBLIC,
        OUTCOME_TECHNICAL_FAILURE,
        OUTCOME_NEEDS_USER,
    )
    # 图词表覆盖域合同全部五种观察结果（发现变化 + PRD §4 四类结果）
    assert set(MONITORING_OUTCOMES) == set(get_args(ObservationOutcome))
    assert {
        OUTCOME_NO_CHANGE,
        OUTCOME_NOT_PUBLIC,
        OUTCOME_TECHNICAL_FAILURE,
        OUTCOME_NEEDS_USER,
    } <= set(MONITORING_OUTCOMES)
    # 用户决定是域合同 UserDisposition 减去初始状态 pending
    assert MONITORING_DISPOSITIONS == (DISPOSITION_START_REFRESH, DISPOSITION_DEFER)
    assert set(MONITORING_DISPOSITIONS) == set(get_args(UserDisposition)) - {"pending"}
    assert HANDOFF_TARGET_NORMAL_REFRESH == "normal_refresh"
    # 交接节点声明"只读交接、不发布"：无 publish/move/approve 副作用
    handoff = monitoring_node_contract("monitor_handoff")
    assert handoff.side_effect_class == "none"
    assert "RefreshHandoffError" in handoff.declared_errors


def test_monitoring_skill_defines_content_version_and_locked_handoff_semantics() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "不可变的来源内容版本" in text
    assert "不得用抓取日期、运行编号或临时快照名" in text
    assert "不得把它改回\"暂不处理\"" in text


def test_monitor_observe_outputs_separate_four_outcome_source_sets() -> None:
    """观察节点在输出层面区分四类来源集合；无变化不创建空候选。"""
    observe = monitoring_node_contract("monitor_observe")
    output_names = {field.name for field in observe.typed_outputs}
    assert {
        "changed_source_ids",
        "unchanged_source_ids",
        "not_public_source_ids",
        "failed_source_ids",
    } <= output_names
    # 四类集合必须是四个不同字段，杜绝单一字段混报；回执也在场
    assert "observation_receipt_id" in output_names


# ── 内部监测 Skill 中文边界 ────────────────────────────────────────────────


def test_monitoring_skill_states_normal_refresh_boundary_in_chinese() -> None:
    """Skill 必须声明候选进入"正常刷新"而非直接进入修订批准流。"""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "name: monitoring" in text
    assert "正常刷新" in text
    assert "不得把候选直接送入修订批准流" in text
    assert "重新核验" in text
    # 旧版合同（Task 9.3 之前）要求候选"进入修订流程"，已被本任务推翻
    assert "进入修订流程" not in text


def test_monitoring_skill_covers_four_diagnosis_categories_with_user_actions() -> None:
    """Skill 必须给出四类诊断的中文提示边界与用户下一步动作。"""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "已完成但没有变化" in text
    assert "未发现公开信息变化" in text
    assert "来源确认未公开目标信息" in text
    assert "技术获取失败" in text
    assert "恢复尝试未穷尽前，不得要求用户协助" in text
    assert "需要用户协助" in text
    assert "穷尽配置的恢复尝试" in text


def test_monitoring_skill_binds_dispositions_and_forbidden_behaviors() -> None:
    """Skill 必须绑定两种处置、追加保存与不可自动接纳边界，及可卸载性声明。"""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "启动正常刷新" in text
    assert "暂不处理" in text
    assert "不得自动接纳事实或声明" in text
    assert "不得建立正式快照" in text
    assert "不得生成或发布报告" in text
    assert "不得把抓取时间误作首次披露时间" in text
    assert "监测 Skill 未安装或被移除" in text
    assert "手动刷新不受影响" in text
