"""C 终点实例阅读密度：同一研究内 definition/timepoint/description 按完整实例身份组合。

RED 前置：本文件先于 repair 编写，记录修复前真实失败；修复后同一行为族整体转绿。
验收对象：
- 生产投影 ``report_c._chart_row/_chart_groups/_table_rows`` 必须把 validated
  ``DesignObservation`` 上显式存在的 outcome/source-version/endpoint-role/group/
  cohort/period/raw-assessment 上下文逐行投影；完整性前提满足且领域十轴身份
  （含原始父路径）在同一研究内一致时给出实例键。不同组不是冲突，同身份
  同字段不同原文才标明待核，缺失上下文保持独立。
- 生产资产 ``report-c.js`` 的 ``renderCriteriaSources`` 设计模式路径按该实例键
  组合同一终点的三件套，检索按事实精确匹配：未命中的同实例兄弟事实以标记的
  上下文展示，不计入选中的事实数，也不进入完整表可见行。
- ``report-c.css`` 提供行长控制与滚动定位合同，不缩字号、不裁切、不堆 !important。

数据来源：``test_r24_ctgov_c_design_projection._fixed_capture/_project_fixed`` 的
固定登记采集投影（合成开发输入，不是已接受的真实来源证据），以及
``fixtures/positive/c-atopic-dermatitis`` 的旧口径观察（无 outcome_id，用于
缺失上下文保持独立的反例）。浏览器/视觉验收仍由父级在真实 Chromium/WebKit 执行。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from typing import Any

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.renderers.portal import report_c
from ci_workflow.renderers.portal.report_a import ProductRow, TrialRow
from ci_workflow.reports.c.contracts import DesignObservation
from tests.integration.test_r24_c_precedent_table import ASSET_CSS, HARNESS_JS, ROOT
from tests.integration.test_r24_ctgov_c_design_projection import _project_fixed

PAGE_ID = "endpoint-timepoint-matrix"
ASSET_JS = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js"

# 与 report-c.js searchableText 完全同源的检索字段（保持精确同一 Q 的可核对性）。
_SEARCHABLE_KEYS = (
    "product_zh",
    "trial_display_id",
    "trial_zh",
    "source_text",
    "original_text",
    "value",
    "element_zh",
    "time",
    "group_zh",
    "cohort_zh",
    "scale",
)
_ATTR_QUERY = "Thrombotic and Haemolytic Events will in"
_TRIAL_QUERY = "NCT02264639"
_EMPTY_QUERY = "no-endpoint-instance-matches-this-development-control"
_NOTE_INSTANCE_PHRASE = "同一研究"
_CONTEXT_NOTE_PHRASE = "未匹配当前检索"


_PRODUCTS = (
    ProductRow(
        id="pegcetacoplan",
        name="培戈塞塔科普兰（开发用）",
        target="C3",
        modality="peptide",
        phase="III期",
        status="开发中",
        regions=("United States",),
        route="皮下注射",
        developer="开发用申办方",
        mechanism="补体C3抑制剂",
    ),
    ProductRow(
        id="nomacopan",
        name="诺玛科潘（开发用）",
        target="C5",
        modality="protein",
        phase="II期",
        status="开发中",
        regions=("United Kingdom",),
        route="皮下注射",
        developer="开发用申办方",
        mechanism="补体C5抑制剂",
    ),
)
_TRIALS = (
    TrialRow(
        id="nct02264639",
        display_id="NCT02264639",
        product_id="pegcetacoplan",
        name="开发用研究 NCT02264639",
        phase="III期",
        region="United States",
        status="招募中",
        role="core",
    ),
    TrialRow(
        id="nct03829449",
        display_id="NCT03829449",
        product_id="nomacopan",
        name="开发用研究 NCT03829449",
        phase="II期",
        region="United Kingdom",
        status="招募中",
        role="core",
    ),
)


def _endpoint_data() -> report_c.ReportCPortalData:
    """固定登记投影 + 两条当前值状态行；不改动任何科学事实与来源绑定。"""
    projection = _project_fixed("NCT02264639", "NCT03829449")
    observations: list[DesignObservation] = list(projection.observations)
    modified = next(
        item for item in observations if item.row_id == "c-nct02264639-pri0-definition"
    )
    observations[observations.index(modified)] = modified.model_copy(
        update={
            "review_state": FactReviewState.USER_MODIFIED,
            "display_text": "研究者修订：开发用当前值",
        }
    )
    cleared = next(
        item for item in observations if item.row_id == "c-nct03829449-sec0-timepoint"
    )
    observations[observations.index(cleared)] = cleared.model_copy(
        update={"disclosure_state": FactDisclosureState.USER_CLEARED}
    )
    return report_c.ReportCPortalData(
        schema_version="1.0",
        report_version="r24-c-endpoint-instance-density-dev",
        indication_id="pnh",
        indication="阵发性睡眠性血红蛋白尿症",
        data_cutoff=datetime(2026, 9, 30),
        products=_PRODUCTS,
        trials=_TRIALS,
        observations=tuple(observations),
    )


def _page_rows(
    data: report_c.ReportCPortalData,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[DesignObservation, ...]]:
    observations = report_c._page_observations(data, PAGE_ID)
    groups = json.loads(report_c._json(report_c._chart_groups(
        data, observations, page_id=PAGE_ID, title="终点与评估时间",
    )))
    chart_rows = [row for group in groups for row in group["rows"]]
    table_rows = json.loads(report_c._json(report_c._table_rows(
        data, observations, page_id=PAGE_ID,
    )))
    return chart_rows, table_rows, observations


def _endpoint_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[DesignObservation]]:
    chart_rows, table_rows, observations = _page_rows(_endpoint_data())
    return chart_rows, table_rows, list(observations)


def _outcome_facts(observations: list[DesignObservation]) -> dict[str, list[str]]:
    """同一研究内同一 outcome_id 的全部事实行（页面顺序）；不含跨研究合并。"""
    grouped: dict[str, list[str]] = {}
    for observation in observations:
        if observation.field not in report_c._ENDPOINT_FIELDS:
            continue
        key = f"{observation.trial_id}|{observation.outcome_id}"
        grouped.setdefault(key, []).append(observation.row_id)
    return grouped


def _js_hits(rows: list[dict[str, Any]], query: str) -> list[str]:
    needle = query.strip().casefold()
    hits: list[str] = []
    for row in rows:
        blob = " ".join(
            str(row.get(key) or "") for key in _SEARCHABLE_KEYS
        ).casefold()
        if needle in blob:
            hits.append(str(row["row_id"]))
    return hits


def _block_ordinals(snapshot: dict[str, Any]) -> dict[str, str]:
    return {
        str(block["instance_id"]): str(block["ordinal"])
        for block in snapshot["blocks"]
        if block["instance_id"]
    }


def _harness_payload() -> dict[str, Any]:
    data = _endpoint_data()
    chart_rows, table_rows, observations = _page_rows(data)
    _, dimensions = report_c._filter_dimensions_for_rows(data, observations)
    payload = {
        "asset_path": str(ASSET_JS),
        "page_id": PAGE_ID,
        "chart_groups": json.loads(report_c._json(report_c._chart_groups(
            data, observations, page_id=PAGE_ID, title="终点与评估时间",
        ))),
        "table_rows": table_rows,
        "row_dimensions": dimensions,
        "filter_dimensions": tuple(report_c._FILTER_DIMENSION_LABELS),
        "trial_query": _TRIAL_QUERY,
        "attr_query": _ATTR_QUERY,
        "empty_query": _EMPTY_QUERY,
        "expected_attr_hits": _js_hits(chart_rows, _ATTR_QUERY),
        "expected_trial_hits": _js_hits(chart_rows, _TRIAL_QUERY),
        "row_trials": {str(row["row_id"]): str(row["trial_id"]) for row in chart_rows},
        "outcome_facts": _outcome_facts(observations),
        "source_texts": {
            str(row["row_id"]): str(row["source_text"]) for row in chart_rows
        },
    }
    return payload


# ---------------------------------------------------------------------------
# Node DOM harness：复用 precedent 的最小 DOM/选择器引擎，替换快照与驱动段
# ---------------------------------------------------------------------------

_ENGINE_JS = HARNESS_JS.split("/* ---------------- snapshot ---------------- */")[0].replace(
    'win.__C_PAGE_ID__ = "inclusion-criteria";',
    "win.__C_PAGE_ID__ = page.page_id;",
)

_ENDPOINT_HARNESS_JS = _ENGINE_JS + r"""
/* ---------------- endpoint-instance snapshot ---------------- */

function endpointSnapshot(ctx) {
  const doc = ctx.doc;
  const blocks = doc.querySelectorAll("[data-endpoint-instance]").map(function (node) {
    const heading = node.querySelector(".kz-c-endpoint-instance__heading");
    const reason = node.querySelector(".kz-c-endpoint-instance__reason");
    return {
      instance_id: node.getAttribute("data-endpoint-instance-id") || "",
      standalone: node.getAttribute("data-endpoint-standalone") === "true",
      ordinal: node.getAttribute("data-endpoint-ordinal"),
      role_zh: node.getAttribute("data-endpoint-role-zh") || "",
      complete: node.getAttribute("data-endpoint-complete"),
      conflict: node.getAttribute("data-endpoint-conflict") === "true",
      reason_text: reason ? reason.textContent : "",
      heading_text: heading ? heading.textContent : "",
      fact_row_ids: node.querySelectorAll("[data-criterion-row-id]").map(function (fact) {
        return fact.getAttribute("data-criterion-row-id");
      }),
    };
  });
  const facts = doc.querySelectorAll("[data-criterion-row-id]").map(function (node) {
    const block = node.closest("[data-endpoint-instance]");
    const evidence = node.querySelectorAll("[data-evidence-open]");
    const original = node.querySelector(".kz-c-criteria-original");
    const revision = node.querySelector(".kz-c-criteria-revision");
    const contextNote = node.querySelector(".kz-c-criteria-context-note");
    const current = node.querySelector(".kz-c-design-source-value");
    return {
      row_id: node.getAttribute("data-criterion-row-id"),
      ordinal: node.getAttribute("data-criterion-ordinal"),
      instance_id: block ? (block.getAttribute("data-endpoint-instance-id") || "") : null,
      context_only: node.getAttribute("data-criterion-context-only") === "true",
      context_note: contextNote ? contextNote.textContent : null,
      trial_id: node.getAttribute("data-criterion-trial-id"),
      current_state: node.getAttribute("data-criterion-current-state") || "",
      original_text: original ? original.textContent : null,
      revision_text: revision ? revision.textContent : null,
      preview_text: current ? current.textContent : null,
      evidence_count: evidence.length,
      evidence_row_id: evidence.length ? evidence[0].getAttribute("data-evidence-open") : null,
    };
  });
  const visibleTableRows = doc.querySelectorAll(".kz-chart-table__row[data-row-id]")
    .filter((node) => node.style.display !== "none")
    .map((node) => node.getAttribute("data-row-id"));
  const status = doc.querySelector(".kz-c-criteria-status");
  const search = doc.getElementById("kz-c-criteria-search");
  return {
    table_present: doc.querySelectorAll("table.kz-c-criteria-table").length === 1,
    role_row_headers: doc.querySelectorAll("table.kz-c-criteria-table th[scope=row]")
      .map((node) => node.textContent),
    blocks: blocks,
    facts: facts,
    matched_facts: facts.filter((fact) => !fact.context_only).map((fact) => fact.row_id),
    context_facts: facts.filter((fact) => fact.context_only).map((fact) => fact.row_id),
    visible_table_rows: visibleTableRows,
    status_text: status ? status.textContent : "",
    study_columns: doc.querySelectorAll("th[data-criteria-study]")
      .map((node) => node.getAttribute("data-criteria-study")),
    unmatched_selected: doc.querySelector("[data-criteria-unmatched-selected]")
      ? doc.querySelector("[data-criteria-unmatched-selected]").textContent : "",
    method_folded: !!doc.querySelector("details.kz-c-criteria-method")
      && doc.querySelector("details.kz-c-criteria-method").getAttribute("open") === null,
    method_in_toolbar: doc.querySelector("details.kz-c-criteria-method")
      ? doc.querySelector("details.kz-c-criteria-method").parentNode.className : null,
    choices_in_toolbar: doc.querySelector("details.kz-c-criteria-choose")
      ? doc.querySelector("details.kz-c-criteria-choose").parentNode.className : null,
    search_value: search ? search.value : null,
    checkboxes: doc.querySelectorAll(".kz-c-criteria-choices input").map(function (node) {
      return { value: node.value, checked: node.checked };
    }),
    url_search: ctx.win.location.search,
  };
}

function endpointSearch(ctx, value) {
  const input = ctx.doc.getElementById("kz-c-criteria-search");
  if (!input) throw new Error("缺少检索输入框 #kz-c-criteria-search");
  input.value = value;
  dispatch(input, { type: "input" });
  ctx.win._flushTimers();
}

function endpointCheck(ctx, trialId, checked) {
  const boxes = ctx.doc.querySelectorAll(".kz-c-criteria-choices input");
  const box = boxes.find((item) => item.value === trialId);
  if (!box) throw new Error("缺少研究勾选框：" + trialId);
  box.checked = checked;
  dispatch(box, { type: "change" });
  ctx.win._flushTimers();
}

/* ---------------- driver ---------------- */

const out = { ok: true, snapshots: {} };
try {
  if (!fs.existsSync(data.asset_path)) {
    throw new Error("缺少生产资产：" + data.asset_path);
  }
  const A = runContext("", data);
  out.snapshots.initial = endpointSnapshot(A);
  endpointSearch(A, data.attr_query);
  out.snapshots.attr = endpointSnapshot(A);
  endpointSearch(A, "");
  out.snapshots.attr_clear = endpointSnapshot(A);
  endpointSearch(A, data.trial_query);
  out.snapshots.trial = endpointSnapshot(A);
  endpointSearch(A, "");
  out.snapshots.trial_clear = endpointSnapshot(A);
  endpointCheck(A, data.trial_query, false);
  out.snapshots.unchecked = endpointSnapshot(A);
  endpointCheck(A, data.trial_query, true);
  endpointSearch(A, "");
  out.snapshots.rechecked = endpointSnapshot(A);
  endpointSearch(A, data.empty_query);
  out.snapshots.empty = endpointSnapshot(A);
  endpointSearch(A, "");
  out.snapshots.empty_clear = endpointSnapshot(A);
  const B = runContext(
    "?criteria_q=" + encodeURIComponent(data.attr_query)
      + "&criteria_hide=" + encodeURIComponent(data.trial_query),
    data
  );
  out.snapshots.restore = endpointSnapshot(B);
} catch (error) {
  out.ok = false;
  out.error = String(error && error.stack ? error.stack : error);
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    return _harness_payload()


@pytest.fixture(scope="module")
def harness(
    tmp_path_factory: pytest.TempPathFactory, payload: dict[str, Any]
) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("需要 Node.js 执行 C 终点实例密度最小 DOM 行为测试")
    work = tmp_path_factory.mktemp("r24-c-endpoint-instance-density")
    harness_path = work / "harness.cjs"
    harness_path.write_text(_ENDPOINT_HARNESS_JS, encoding="utf-8")
    payload_path = work / "payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [node, str(harness_path), str(payload_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        "Node DOM 沙箱异常退出：\n" + completed.stderr + "\n" + completed.stdout[:2000]
    )
    result = json.loads(completed.stdout)
    if not result.get("ok"):
        pytest.fail("加载生产 report-c.js 失败：" + str(result.get("error")), pytrace=False)
    return result


# ---------------------------------------------------------------------------
# 根行为族 A：投影层把显式实例上下文逐行带出，并只在完整同研究身份下组合
# ---------------------------------------------------------------------------


def test_reading_controls_share_toolbar_without_removing_methods_or_study_choices(
    harness: dict[str, Any],
) -> None:
    initial = harness["snapshots"]["initial"]
    assert initial["method_in_toolbar"] == "kz-c-criteria-toolbar"
    assert initial["choices_in_toolbar"] == "kz-c-criteria-toolbar"
    assert initial["method_folded"]
    assert all(item["checked"] for item in initial["checkboxes"])


def test_endpoint_rows_project_explicit_instance_context() -> None:
    chart_rows, table_rows, observations = _endpoint_rows()
    assert len(chart_rows) == len(observations)
    assert len(table_rows) == len(observations)

    by_row_id = {str(row["row_id"]): row for row in chart_rows}
    for observation in observations:
        row = by_row_id[observation.row_id]
        if observation.field not in report_c._ENDPOINT_FIELDS:
            continue
        # 显式上下文逐行投影；outcome_id 缺失必须显式为空，不得用角色/序号顶替。
        assert row["outcome_id"] == observation.outcome_id
        assert row["endpoint_role_key"] == observation.endpoint_key
        assert row["assessment_timepoint_raw"] == (
            " ".join(str(observation.assessment_timepoint or "").split()) or None
        )
        assert row["source_version_id"] == observation.source_version_id
        assert "endpoint_instance" in row

    # 同一 outcome_id 的 definition/description/timepoint 共享同一实例键。
    seen_pairs: set[tuple[str, str]] = set()
    for observation in observations:
        if observation.field not in report_c._ENDPOINT_FIELDS:
            continue
        instance = by_row_id[observation.row_id]["endpoint_instance"]
        scope = (str(observation.trial_id), str(observation.outcome_id))
        if scope in seen_pairs:
            prior = next(
                by_row_id[prior_id]["endpoint_instance"]["instance_id"]
                for prior_id, prior_scope in (
                    (item.row_id, (str(item.trial_id), str(item.outcome_id)))
                    for item in observations
                    if item.field in report_c._ENDPOINT_FIELDS
                )
                if prior_scope == scope
            )
            assert instance["instance_id"] == prior
            assert instance["complete"] is True
        seen_pairs.add(scope)

    # 多条主要终点保持独立实例：nct02264639 有 4 条 primary outcome。
    primary_ids = {
        by_row_id[observation.row_id]["endpoint_instance"]["instance_id"]
        for observation in observations
        if observation.trial_id == "nct02264639"
        and observation.field == "primary_endpoint_definition"
    }
    assert len(primary_ids) == 4

    # 跨研究绝不因序号或标题相似共享实例键。
    cross = {
        str(trial): {
            by_row_id[observation.row_id]["endpoint_instance"]["instance_id"]
            for observation in observations
            if observation.trial_id == trial and observation.field.endswith("_definition")
        }
        for trial in ("nct02264639", "nct03829449")
    }
    assert cross["nct02264639"].isdisjoint(cross["nct03829449"])


def test_endpoint_instance_projection_consistent_between_chart_and_table() -> None:
    chart_rows, table_rows, observations = _endpoint_rows()
    chart_by_id = {str(row["row_id"]): row for row in chart_rows}
    table_by_id = {str(row["row_id"]): row for row in table_rows}
    for observation in observations:
        chart = chart_by_id[observation.row_id]
        table = table_by_id[observation.row_id]
        if observation.field not in report_c._ENDPOINT_FIELDS:
            continue
        assert chart["endpoint_instance"] == table["endpoint_instance"]
        assert table["source_version_id"] == observation.source_version_id


def test_endpoint_rows_without_outcome_id_stay_separate_with_reason() -> None:
    data = report_c.ReportCPortalData.model_validate_json(
        (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
    )
    observations = report_c._page_observations(data, PAGE_ID)
    assert observations
    rows = [
        row
        for group in report_c._chart_groups(
            data, observations, page_id=PAGE_ID, title="终点与评估时间"
        )
        for row in group["rows"]
    ]
    by_row_id = {str(row["row_id"]): row for row in rows}
    assert len(rows) == len(observations)
    for observation in observations:
        instance = by_row_id[observation.row_id]["endpoint_instance"]
        assert instance["instance_id"] is None
        assert instance["complete"] is False
        assert instance["conflict"] is False
        assert "终点实例标识" in instance["reason_zh"]


def test_conflicting_scope_stays_separate_with_reason() -> None:
    data = _endpoint_data()
    target = next(
        item for item in data.observations if item.row_id == "c-nct03829449-sec0-definition"
    )
    conflicting_row = target.model_copy(
        update={
            "row_id": "c-nct03829449-sec0-definition-conflict",
            "source_row_id": "conflict-seed",
            "observation_id": "conflict-seed",
            "source_text": "Synthetic contrary source endpoint within the same complete context",
        }
    )
    data = data.model_copy(
        update={"observations": (*data.observations, conflicting_row)}
    )
    rows = [
        row
        for group in report_c._chart_groups(
            data, data.observations, page_id=PAGE_ID, title="终点与评估时间"
        )
        for row in group["rows"]
    ]
    by_row_id = {str(row["row_id"]): row for row in rows}
    for row_id in (
        "c-nct03829449-sec0-definition",
        "c-nct03829449-sec0-timepoint",
        "c-nct03829449-sec0-description",
        "c-nct03829449-sec0-definition-conflict",
    ):
        instance = by_row_id[row_id]["endpoint_instance"]
        assert instance["conflict"] is True
        assert instance["reason_zh"]
    # 同一科学实例保留全部矛盾原文，不假造新语境或取第一条。
    assert (
        by_row_id["c-nct03829449-sec0-definition"]["endpoint_instance"]["instance_id"]
        == by_row_id["c-nct03829449-sec0-definition-conflict"]["endpoint_instance"][
            "instance_id"
        ]
    )
    assert len(rows) == len(data.observations)


def test_duplicate_observation_keeps_both_facts_under_same_instance() -> None:
    data = _endpoint_data()
    target = next(
        item for item in data.observations if item.row_id == "c-nct02264639-pri1-definition"
    )
    duplicate = target.model_copy(
        update={
            "row_id": "c-nct02264639-pri1-definition-duplicate",
            "source_row_id": "duplicate-seed",
            "observation_id": "duplicate-seed",
        }
    )
    data = data.model_copy(update={"observations": (*data.observations, duplicate)})
    rows = [
        row
        for group in report_c._chart_groups(
            data, data.observations, page_id=PAGE_ID, title="终点与评估时间"
        )
        for row in group["rows"]
    ]
    by_row_id = {str(row["row_id"]): row for row in rows}
    assert (
        by_row_id["c-nct02264639-pri1-definition"]["endpoint_instance"]["instance_id"]
        == by_row_id["c-nct02264639-pri1-definition-duplicate"]["endpoint_instance"][
            "instance_id"
        ]
    )
    # 重复观察保持两条独立事实，不拼接、不聚合。
    assert len(rows) == len(data.observations)
    assert by_row_id["c-nct02264639-pri1-definition"]["source_text"] == (
        by_row_id["c-nct02264639-pri1-definition-duplicate"]["source_text"]
    )


def test_same_outcome_id_across_trials_never_pairs() -> None:
    data = _endpoint_data()
    target = next(
        item for item in data.observations if item.row_id == "c-nct02264639-pri0-definition"
    )
    cross_trial = target.model_copy(
        update={
            "row_id": "c-cross-trial-definition",
            "source_row_id": "cross-seed",
            "observation_id": "cross-seed",
            "trial_id": "nct03829449",
        }
    )
    data = data.model_copy(update={"observations": (*data.observations, cross_trial)})
    rows = [
        row
        for group in report_c._chart_groups(
            data, data.observations, page_id=PAGE_ID, title="终点与评估时间"
        )
        for row in group["rows"]
    ]
    by_row_id = {str(row["row_id"]): row for row in rows}
    assert (
        by_row_id["c-nct02264639-pri0-definition"]["endpoint_instance"]["instance_id"]
        != by_row_id["c-cross-trial-definition"]["endpoint_instance"]["instance_id"]
    )


def test_distinct_legitimate_group_contexts_are_not_declared_a_scientific_conflict() -> None:
    original = [o for o in _endpoint_data().observations
                if o.outcome_id == "outcome-nct03829449-sec-0"]
    other_group = [o.model_copy(update={
        "row_id": o.row_id + "-other-group", "group_id": "explicit-second-group",
    }) for o in original]
    projection = report_c._endpoint_instance_projection((*original, *other_group))
    assert all(not p["conflict"] for p in projection.values())
    assert projection[original[0].row_id]["instance_id"] != (
        projection[other_group[0].row_id]["instance_id"]
    )


def test_same_complete_instance_and_field_with_different_source_quotes_is_a_conflict() -> None:
    original = next(o for o in _endpoint_data().observations
                    if o.row_id == "c-nct03829449-sec0-definition")
    contradictory = original.model_copy(update={
        "row_id": original.row_id + "-different-source-value",
        "source_text": "Synthetic contradictory endpoint, not the original source value",
    })
    projection = report_c._endpoint_instance_projection((original, contradictory))
    assert all(p["conflict"] and p["reason_zh"] for p in projection.values())


def test_same_claimed_outcome_id_does_not_merge_different_protocol_parent_paths() -> None:
    original = next(o for o in _endpoint_data().observations
                    if o.row_id == "c-nct03829449-sec0-definition")
    other_parent = original.model_copy(update={
        "row_id": original.row_id + "-other-parent",
        "source_locator": original.source_locator.model_copy(update={
            "field_path": "$.protocolSection.outcomesModule.secondaryOutcomes[1].measure",
        }),
    })
    projection = report_c._endpoint_instance_projection((original, other_parent))
    assert projection[original.row_id]["instance_id"] != (
        projection[other_parent.row_id]["instance_id"]
    )


def test_user_modified_and_cleared_states_survive_projection() -> None:
    chart_rows, _, _ = _endpoint_rows()
    by_row_id = {str(row["row_id"]): row for row in chart_rows}
    assert by_row_id["c-nct02264639-pri0-definition"]["review_state"] == "user_modified"
    assert by_row_id["c-nct03829449-sec0-timepoint"]["disclosure_state"] == "user_cleared"
    # 原文与来源绑定不被当前值状态改写。
    assert by_row_id["c-nct02264639-pri0-definition"]["source_text"]
    assert (
        by_row_id["c-nct03829449-sec0-timepoint"]["endpoint_instance"]["complete"] is True
    )


# ---------------------------------------------------------------------------
# 根行为族 B：真实 report-c.js 的实例组合、精确检索与完整表同步
# ---------------------------------------------------------------------------


def test_endpoint_blocks_compose_within_study_instances(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    initial = harness["snapshots"]["initial"]
    assert initial["table_present"] is True
    expected_facts = payload["outcome_facts"]

    complete_blocks = [block for block in initial["blocks"] if not block["standalone"]]
    assert len(complete_blocks) == len(expected_facts)
    blocks_by_facts = {
        tuple(sorted(block["fact_row_ids"])): block for block in complete_blocks
    }
    for key, row_ids in expected_facts.items():
        block = blocks_by_facts.get(tuple(sorted(row_ids)))
        assert block is not None, key
        assert block["complete"] == "true"
        assert block["conflict"] is False
        assert block["role_zh"] in {"主要终点", "次要终点"}
        assert block["heading_text"]

    # 每条事实独立可达来源，原文逐字保留。
    facts_by_id = {fact["row_id"]: fact for fact in initial["facts"]}
    assert set(facts_by_id) == set(payload["source_texts"])
    for row_id, fact in facts_by_id.items():
        assert fact["evidence_count"] == 1
        assert fact["evidence_row_id"] == row_id
        assert fact["original_text"] == payload["source_texts"][row_id]
    # 完整表同步：无检索时全部事实可见，无上下文标记。
    assert sorted(initial["matched_facts"]) == sorted(payload["source_texts"])
    assert initial["context_facts"] == []
    assert sorted(initial["visible_table_rows"]) == sorted(payload["source_texts"])
    # 修改/清除的当前值状态在实例块内可见。
    assert "当前修订" in str(facts_by_id["c-nct02264639-pri0-definition"]["revision_text"])
    assert "用户清除" in str(facts_by_id["c-nct03829449-sec0-timepoint"]["revision_text"])
    # 角色行表头保留研究列对照表合同。
    assert any("主要终点" in header for header in initial["role_row_headers"])
    assert any("次要终点" in header for header in initial["role_row_headers"])


def test_attribute_search_keeps_instance_context_labelled_and_uncounted(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    snapshots = harness["snapshots"]
    attr = snapshots["attr"]
    expected_hits = payload["expected_attr_hits"]
    assert len(expected_hits) == 1
    assert sorted(attr["matched_facts"]) == sorted(expected_hits)
    # 命中一个属性时，同实例兄弟事实作为带标记的上下文展示。
    assert sorted(attr["context_facts"]) == sorted(
        row_id
        for row_id in payload["outcome_facts"]["nct03829449|outcome-nct03829449-sec-0"]
        if row_id not in expected_hits
    )
    facts_by_id = {fact["row_id"]: fact for fact in attr["facts"]}
    for row_id in attr["context_facts"]:
        assert facts_by_id[row_id]["context_note"] is not None
        assert _CONTEXT_NOTE_PHRASE in facts_by_id[row_id]["context_note"]
        assert facts_by_id[row_id]["evidence_row_id"] == row_id
        assert facts_by_id[row_id]["original_text"] == payload["source_texts"][row_id]
    # 精确同一 Q：完整表可见行 == 命中事实，上下文不进入完整表与计数。
    assert sorted(attr["visible_table_rows"]) == sorted(expected_hits)
    assert str(len(expected_hits)) in attr["status_text"]
    # 实例序号不因检索重排。
    assert _block_ordinals(attr) == {
        key: ordinal
        for key, ordinal in _block_ordinals(snapshots["initial"]).items()
        if key in {block["instance_id"] for block in attr["blocks"] if block["instance_id"]}
    }
    # 清空检索：上下文标记消失，全部事实回到命中集合。
    cleared = snapshots["attr_clear"]
    assert sorted(cleared["matched_facts"]) == sorted(payload["source_texts"])
    assert cleared["context_facts"] == []


def test_trial_search_choice_and_restore_preserve_exact_query(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    snapshots = harness["snapshots"]
    trial = snapshots["trial"]
    expected_trial_hits = payload["expected_trial_hits"]
    assert sorted(trial["matched_facts"]) == sorted(expected_trial_hits)
    assert sorted(trial["visible_table_rows"]) == sorted(expected_trial_hits)
    trial_ids = {fact["trial_id"] for fact in trial["facts"]}
    assert trial_ids == {"nct02264639"}

    trial_clear = snapshots["trial_clear"]
    assert sorted(trial_clear["matched_facts"]) == sorted(payload["source_texts"])

    unchecked = snapshots["unchecked"]
    remaining = [
        row_id
        for row_id, trial_id in payload["row_trials"].items()
        if trial_id != "nct02264639"
    ]
    assert sorted(unchecked["matched_facts"]) == sorted(remaining)
    assert sorted(unchecked["visible_table_rows"]) == sorted(remaining)
    assert "criteria_hide=" + _TRIAL_QUERY in unchecked["url_search"]
    # 取消勾选不重排其余研究的实例序号。
    initial_ordinals = _block_ordinals(snapshots["initial"])
    for block in unchecked["blocks"]:
        if block["instance_id"]:
            assert _block_ordinals(unchecked)[block["instance_id"]] == (
                initial_ordinals[block["instance_id"]]
            )

    rechecked = snapshots["rechecked"]
    assert sorted(rechecked["matched_facts"]) == sorted(payload["source_texts"])
    boxes = {item["value"]: item["checked"] for item in rechecked["checkboxes"]}
    assert all(boxes.values())
    assert "criteria_hide=" not in rechecked["url_search"]

    restore = snapshots["restore"]
    assert restore["search_value"] == _ATTR_QUERY
    assert sorted(restore["matched_facts"]) == sorted(payload["expected_attr_hits"])
    assert sorted(restore["visible_table_rows"]) == sorted(payload["expected_attr_hits"])
    restore_boxes = {item["value"]: item["checked"] for item in restore["checkboxes"]}
    assert restore_boxes[_TRIAL_QUERY] is False


def test_empty_query_shows_no_blocks_and_zero_count(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    empty = harness["snapshots"]["empty"]
    assert empty["blocks"] == []
    assert empty["facts"] == []
    assert empty["visible_table_rows"] == []
    assert "0" in empty["status_text"]
    cleared = harness["snapshots"]["empty_clear"]
    assert sorted(cleared["matched_facts"]) == sorted(payload["source_texts"])
    assert len(cleared["blocks"]) == len(payload["outcome_facts"])


def test_sparse_search_omits_empty_columns_without_deselecting_studies(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    sparse = harness["snapshots"]["attr"]
    assert sparse["study_columns"] == ["NCT03829449"]
    assert "NCT02264639" in sparse["unmatched_selected"]
    assert "保留选择" in sparse["unmatched_selected"]
    assert all(box["checked"] for box in sparse["checkboxes"])
    assert sorted(sparse["matched_facts"]) == sorted(payload["expected_attr_hits"])
    assert "criteria_hide=" not in sparse["url_search"]


def test_clear_search_restores_all_selected_columns_and_empty_search_accounts_for_them(
    harness: dict[str, Any],
) -> None:
    snapshots = harness["snapshots"]
    initial = snapshots["initial"]
    restored = snapshots["attr_clear"]
    assert restored["study_columns"] == initial["study_columns"]
    assert restored["unmatched_selected"] == ""
    empty = snapshots["empty"]
    assert empty["study_columns"] == []
    for trial in initial["study_columns"]:
        assert trial in empty["unmatched_selected"]
    assert all(box["checked"] for box in empty["checkboxes"])


# ---------------------------------------------------------------------------
# 相关 GREEN 组：样式合同与既有消费者标记
# ---------------------------------------------------------------------------


def _css_block(css: str, selector: str) -> str:
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, f"report-c.css 缺少样式块：{selector}"
    return match.group(1)


def test_endpoint_density_css_contract() -> None:
    css = ASSET_CSS.read_text(encoding="utf-8")

    wrap = _css_block(css, ".kz-c-criteria-table-wrap")
    assert "scroll-margin-top" in wrap

    for selector in (
        ".kz-c-design-source-value",
        ".kz-c-criteria-original",
        ".kz-c-endpoint-instance__heading",
        ".kz-c-endpoint-instance__reason",
    ):
        assert "max-width: 72ch" in _css_block(css, selector), selector

    instance = _css_block(css, ".kz-c-endpoint-instance")
    assert "!important" not in instance
    note = _css_block(css, ".kz-c-criteria-context-note")
    assert "!important" not in note

    # 全文件字号地板：px 不低于 16、rem 不低于 1（KZ6 TYPE-01 站点合同）。
    for value, unit in re.findall(r"font-size:\s*([0-9.]+)(px|rem)", css):
        assert float(value) >= (16 if unit == "px" else 1), (value, unit)


def test_endpoint_surface_keeps_existing_consumers_wired() -> None:
    source = ASSET_JS.read_text(encoding="utf-8")
    for token in (
        "data-endpoint-instance",
        "kz-c-endpoint-instance",
        "kz-c-criteria-context-note",
        "endpoint_instance",
        _NOTE_INSTANCE_PHRASE,
        _CONTEXT_NOTE_PHRASE,
        "renderCriteriaSources",
        "criteria_q",
        "criteria_hide",
    ):
        assert token in source, token


def test_original_description_is_reachable_without_duplicating_full_text_in_preview(
    payload: dict[str, Any], harness: dict[str, Any]
) -> None:
    facts = {fact["row_id"]: fact for fact in harness["snapshots"]["initial"]["facts"]}
    for row_id, original in payload["source_texts"].items():
        if row_id.endswith("-description") and facts[row_id]["current_state"] != "user_modified":
            assert facts[row_id]["original_text"] == original
            assert facts[row_id]["evidence_row_id"] == row_id
            assert "展开" in facts[row_id]["preview_text"]
            assert original not in facts[row_id]["preview_text"]


def test_long_explanation_is_keyboard_reachable_but_collapsed_initially(
    harness: dict[str, Any]
) -> None:
    assert harness["snapshots"]["initial"]["method_folded"]
