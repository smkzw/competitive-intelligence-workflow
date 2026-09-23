"""Task 4.5 同页数据依据面板：右侧面板宿主、数据嵌入与中文标签权威。

合同（§15.5）：
- 面板在**同一页面**右侧打开，不整页跳转、不改变滚动与筛选；用户可见
  名称使用「数据依据」「固定对照」「来源版本」「原文定位」，禁止出现
  「证据抽屉」或任何工程标签（row_id、gate、signal、prompt、log）。
- 展示层只渲染已通过 ``validate_evidence_view_payload`` 验证的不可变
  ``EvidenceView``；空字段由互斥中文状态呈现（不适用/尚未公开/来源未列示/
  技术暂不可用），不得留白，也不得把缺失当作 0。
- 固定多条后以并列对照表核对定义、时间点、分母与冲突；来源定位无有效
  http(s) 链接时不生成伪链接。
- 本模块只负责渲染与基础交互的数据契约；图/表触发、筛选同步、网址恢复、
  Esc 与焦点返回由门户联动层调用 ``window.__EVIDENCE_DRAWER__`` 公开 API。

公开 API：
- ``serialize_evidence_views`` — 验证后的视图集 → 确定性 JSON 嵌入字面量。
- ``render_evidence_drawer_embed`` — ``window.__EVIDENCE_VIEWS__`` +
  ``window.__EVIDENCE_DRAWER_LABELS__`` 脚本块（数据只读嵌入）。
- ``render_evidence_drawer_host`` — 面板宿主标记（静态、无数据）。
- ``evidence_drawer_css_link_tag`` / ``evidence_drawer_script_tag`` — 资产标签。
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.reports.common.evidence_view import (
    EVIDENCE_FIELD_STATE_LABELS_ZH,
    EvidenceView,
)

EVIDENCE_DRAWER_CSS_ASSET = "evidence-drawer.css"
EVIDENCE_DRAWER_JS_ASSET = "evidence-drawer.js"

# 披露状态 → 中文标签。与 Task 4.4 完整表既有表达一致：
# 「未公开/未报告/不适用/低于报告阈值/路径未解析/来源冲突」不另立措辞；
# 已报告值/已报告零值沿用确定值语义。
DISCLOSURE_STATE_LABELS_ZH: dict[str, str] = {
    FactDisclosureState.REPORTED_VALUE.value: "已报告值",
    FactDisclosureState.REPORTED_ZERO.value: "已报告零值",
    FactDisclosureState.NOT_REPORTED.value: "未报告",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD.value: "低于报告阈值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED.value: "未公开",
    FactDisclosureState.NOT_APPLICABLE.value: "不适用",
    FactDisclosureState.CONFLICTING.value: "来源冲突",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE.value: "路径未解析",
    FactDisclosureState.USER_CLEARED.value: "用户清除，待重新核实",
}

# 已知来源文档角色 → 中文标签；未知角色不渲染英文角色名（定位行回落到
# 「来源未列示」，不补造角色）。
DOCUMENT_ROLE_LABELS_ZH: dict[str, str] = {
    "registry": "登记记录",
    "primary_registry": "主要登记记录",
    "registry_result": "登记结果记录",
    "primary_trial_report": "主要试验报告",
    "publication": "论文",
    "supplementary_material": "补充材料",
    "protocol": "研究方案",
    "protocol_sap": "研究方案与统计分析计划",
    "company_disclosure": "企业披露",
    "conference_disclosure": "会议披露",
    "designated_industry_source": "行业指定来源",
    "source_primary": "原始来源",
}

# 原文携带状态 → 中文表达：已提供渲染逐字原文；未提供/不允许时确定性呈现。
ORIGINAL_TEXT_STATUS_LABELS_ZH: dict[str, str] = {
    "not_provided": "原文未提供",
    "not_permitted": "技术暂不可用",
}

_FIELD_STATE_LABELS_JSON: dict[str, str] = {
    state.value: label for state, label in EVIDENCE_FIELD_STATE_LABELS_ZH.items()
}


def _label_payload() -> dict[str, dict[str, str]]:
    return {
        "field_states": _FIELD_STATE_LABELS_JSON,
        "disclosure_states": DISCLOSURE_STATE_LABELS_ZH,
        "document_roles": DOCUMENT_ROLE_LABELS_ZH,
        "original_text_states": ORIGINAL_TEXT_STATUS_LABELS_ZH,
    }


def serialize_evidence_views(views: Sequence[EvidenceView]) -> str:
    """验证后的视图集 → 确定性 JSON 字面量（``model_dump(mode="json")``）。"""
    payloads = [view.model_dump(mode="json") for view in views]
    return json.dumps(payloads, ensure_ascii=False, separators=(",", ":"))


def render_evidence_drawer_embed(views: Sequence[EvidenceView]) -> str:
    """数据只读嵌入：视图集 + 中文标签权威（展示层只读，禁止拼出事实）。"""
    views_json = serialize_evidence_views(views)
    labels_json = json.dumps(_label_payload(), ensure_ascii=False, separators=(",", ":"))
    return (
        "<script>\n"
        f"window.__EVIDENCE_VIEWS__ = {views_json};\n"
        f"window.__EVIDENCE_DRAWER_LABELS__ = {labels_json};\n"
        "</script>"
    )


def render_evidence_drawer_host() -> str:
    """面板宿主标记：静态结构，内容全部由 evidence-drawer.js 渲染。"""
    return """<aside class="kz-evidence-drawer" id="kz-evidence-drawer" hidden>
  <div class="kz-evidence-drawer__panel" id="kz-evidence-drawer-panel"
       role="dialog" aria-modal="true" aria-labelledby="kz-evidence-drawer-title"
       tabindex="-1">
    <header class="kz-evidence-drawer__header">
      <h2 class="kz-evidence-drawer__title" id="kz-evidence-drawer-title">数据依据</h2>
      <button type="button" class="kz-evidence-drawer__close"
              id="kz-evidence-drawer-close" aria-label="关闭数据依据">
        <span aria-hidden="true">×</span>
      </button>
    </header>
    <p class="kz-evidence-drawer__status" id="kz-evidence-drawer-status"
       role="status" hidden></p>
    <div class="kz-evidence-drawer__body" id="kz-evidence-drawer-body">
      <section class="kz-evidence-view" id="kz-evidence-view"
               aria-label="当前数据依据" hidden>
        <h3 class="kz-evidence-view__subject" id="kz-evidence-view-subject"></h3>
        <dl class="kz-evidence-view__fields" id="kz-evidence-view-fields"></dl>
        <section class="kz-evidence-view__conflicts"
                 id="kz-evidence-view-conflicts" hidden>
          <h4 class="kz-evidence-view__subhead">冲突</h4>
          <ul class="kz-evidence-view__conflict-list"
              id="kz-evidence-view-conflict-list"></ul>
        </section>
        <section class="kz-evidence-view__history"
                 id="kz-evidence-view-history" hidden>
          <h4 class="kz-evidence-view__subhead">历史版本</h4>
          <ul class="kz-evidence-view__history-list"
              id="kz-evidence-view-history-list"></ul>
        </section>
        <div class="kz-evidence-view__actions">
          <button type="button" class="kz-evidence-pin-btn" id="kz-evidence-pin-btn"
                  aria-pressed="false">固定此条</button>
        </div>
      </section>
      <section class="kz-evidence-pinned" id="kz-evidence-pinned"
               aria-label="固定对照" hidden>
        <h3 class="kz-evidence-pinned__title">固定对照</h3>
        <p class="kz-evidence-pinned__hint" id="kz-evidence-pinned-hint"></p>
        <div class="kz-evidence-compare" id="kz-evidence-compare" hidden></div>
      </section>
    </div>
  </div>
</aside>"""


def evidence_drawer_css_link_tag(assets_rel: str) -> str:
    return f'  <link rel="stylesheet" href="{assets_rel}/{EVIDENCE_DRAWER_CSS_ASSET}">'


def evidence_drawer_script_tag(assets_rel: str) -> str:
    return f'  <script src="{assets_rel}/{EVIDENCE_DRAWER_JS_ASSET}"></script>'
