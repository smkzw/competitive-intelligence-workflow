"""Task 3.4 规范图状态：运行族/证据族注册、共享证据账本与按报告隔离写键。"""

from __future__ import annotations

from typing import Any

# 前四组证据状态族：不由控制图改写
EVIDENCE_STATE_FAMILIES: tuple[str, ...] = (
    "route_attempt",
    "route_completion",
    "fact_disclosure",
    "fact_review",
)

# 后五组运行状态族：由控制图迁移改写
RUNTIME_STATE_FAMILIES: tuple[str, ...] = (
    "project",
    "report_evidence",
    "format_artifact",
    "download_request",
    "revision_approval",
)

ALL_STATE_FAMILIES: tuple[str, ...] = EVIDENCE_STATE_FAMILIES + RUNTIME_STATE_FAMILIES

# 共享证据账本键：A/B/C 共同只读；控制图只记录引用，不拥有科学事实
EVIDENCE_LEDGER_KEY = "evidence"

# 按报告隔离的写键族：gate / 候选快照 / 分析 / 格式产物
REPORT_SCOPED_FAMILIES: tuple[str, ...] = ("gate", "snapshot", "analysis", "artifact")
REPORT_KINDS: tuple[str, ...] = ("A", "B", "C")

# 副作用账本键（规范状态内的幂等记录）
SIDE_EFFECT_LEDGER_KEY = "side_effects"

# 未见对象的固定类型化起始状态：调用方不得自行断言其他起始状态
FAMILY_DEFAULT_STATES: dict[str, str | None] = {
    "project": None,
    "report_evidence": "queued",
    "format_artifact": "queued",
    "download_request": "awaiting_user",
    "revision_approval": "submitted",
}


def report_scoped_key(family: str, report_kind: str) -> str:
    """按报告隔离的规范状态键：gate.A / snapshot.B / analysis.C / artifact.A 等。"""
    if family not in REPORT_SCOPED_FAMILIES:
        raise ValueError(f"非报告写键族: {family}")
    if report_kind not in REPORT_KINDS:
        raise ValueError(f"非法报告类型: {report_kind}")
    return f"{family}.{report_kind}"


def render_write_template(template: str, report_kind: str) -> str:
    """把写键模板（含 {report_kind}）渲染为具体报告状态键。"""
    if "{report_kind}" not in template:
        raise ValueError(f"写键模板必须含 report_kind 占位符: {template}")
    return template.replace("{report_kind}", report_kind)


def initial_state() -> dict[str, Any]:
    """规范图初始状态：五个运行族映射 + 共享证据账本 + 12 个按报告隔离写键。"""
    state: dict[str, Any] = {family: {} for family in RUNTIME_STATE_FAMILIES}
    state[EVIDENCE_LEDGER_KEY] = {}
    for family in REPORT_SCOPED_FAMILIES:
        for kind in REPORT_KINDS:
            state[report_scoped_key(family, kind)] = {}
    state[SIDE_EFFECT_LEDGER_KEY] = {}
    return state
