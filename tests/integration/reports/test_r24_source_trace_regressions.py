"""R24-29 逐事实来源追溯回归族（生产调用负例与边界正例）。

独立会商 R24-25（冻结提交 155eca6）判 FAIL 的可复现缺陷在此固化为生产调用回归：

1. 本机路径形状（绝对路径、家目录、UNC、Windows 盘符、``file:``、上跳相对路径）
   不得晋级来源定位；同一位置对象里若有可用的精确锚点，只移除脏字段；
2. 粗 JSON 容器（``$.``、``$.resultsSection``）与仅链接/仅章节不足以构成
   精确定位；
3. 已定位必须同时具备来源版本、逐字原文与精确非本机锚点；待核视图不得残留
   来源版本、定位、原文、冲突或历史；
4. 已报告数值（含真零与不可绘图值）必须保留原始报告值，数值披露与来源追溯
   状态分离；C 必须保留来源自身的 URL 与字段路径，不得改写成登记链接。

全部断言只走生产入口（``render_report_b_site``、``render_report_c_site``、
``validate_evidence_view_payload`` 与序列化边界断言），不访问外部来源。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.renderers.portal.evidence_drawer import serialize_evidence_views
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site
from ci_workflow.reports.common.evidence_view import (
    EvidenceViewBoundaryError,
    assert_evidence_trace_contract,
    validate_evidence_view_payload,
)
from ci_workflow.reports.common.view_state import derive_row_id

ROOT = Path(__file__).resolve().parents[3]
B_FIXTURE = ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json"
C_FIXTURE = ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
DRAWER_ASSET = (
    ROOT / "src/ci_workflow/renderers/portal/assets/evidence-drawer.js"
)

LOCAL_ABSOLUTE = "/Users/example/internal.json"
LOCAL_UNC = r"\\server\share\internal.json"
LOCAL_RELATIVE = "../secrets/internal.json"
PUBLICATION_URL = "https://example.org/articles/123"


def _b_payload() -> dict[str, Any]:
    return json.loads(B_FIXTURE.read_text(encoding="utf-8"))


def _fact(payload: dict[str, Any], index: int, **fields: Any) -> dict[str, Any]:
    return {**payload["efficacy"][index], **fields}


def _render_b_site(tmp_path: Path, payload: dict[str, Any]) -> Path:
    site = tmp_path / "b-site"
    render_report_b_site(ReportBPortalData.model_validate(payload), site)
    return site


def _views_by_row(site: Path, relative: str) -> dict[str, dict[str, Any]]:
    html = (site / relative).read_text(encoding="utf-8")
    match = re.search(r"window\.__EVIDENCE_VIEWS__\s*=\s*", html)
    assert match is not None, relative
    views, _ = json.JSONDecoder().raw_decode(html[match.end() :].lstrip())
    assert isinstance(views, list) and views, relative
    return {view["row"]["row_id"]: view for view in views}


def _render_c_views(tmp_path: Path, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """渲染 C 站点，汇总全部物理页嵌入的证据视图（按 row_id 去重）。"""
    site = tmp_path / "c-site"
    render_report_c_site(ReportCPortalData.model_validate(payload), site)
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(site.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        match = re.search(r"window\.__EVIDENCE_VIEWS__\s*=\s*", html)
        if match is None:
            continue
        views, _ = json.JSONDecoder().raw_decode(html[match.end() :].lstrip())
        for view in views:
            result[view["row"]["row_id"]] = view
    return result


# ─── B：精确定位必须是精确、非本机、带原文的锚点 ──────────────────────────────


def test_b_local_path_shapes_cannot_become_located_anchors(tmp_path: Path) -> None:
    payload = _b_payload()
    payload["efficacy_views"] = {
        "coverage_mode": "partial",
        "facts": [
            # 好锚点 + 本机路径链接：保留精确字段路径，移除脏链接
            _fact(
                payload,
                0,
                source_version_id="sv-mixed",
                source_text="68.4",
                source_locator={
                    "document_role": "registry",
                    "field_path": "$.results.efficacy[0].value",
                    "url": LOCAL_ABSOLUTE,
                },
            ),
            _fact(
                payload,
                1,
                source_version_id="sv-absolute",
                source_text="31.2",
                source_locator={"document_role": "registry", "url": LOCAL_ABSOLUTE},
            ),
            _fact(
                payload,
                2,
                source_version_id="sv-unc",
                source_text="12.3",
                source_locator={"document_role": "registry", "table": LOCAL_UNC},
            ),
            _fact(
                payload,
                3,
                source_version_id="sv-relative",
                source_text="9.9",
                source_locator={"document_role": "registry", "field_path": LOCAL_RELATIVE},
            ),
            _fact(
                payload,
                4,
                source_version_id="sv-file-url",
                source_text="8.8",
                source_locator={"document_role": "registry", "url": f"file://{LOCAL_ABSOLUTE}"},
            ),
            _fact(
                payload,
                5,
                source_version_id="sv-drive",
                source_text="7.7",
                source_locator={"document_role": "registry", "table": r"C:\reports\study.json"},
            ),
        ],
    }
    site = _render_b_site(tmp_path, payload)
    views = _views_by_row(site, "efficacy.html")
    rows = payload["efficacy"]

    mixed = views[rows[0]["row_id"]]
    assert mixed["source_trace_state"] == "located"
    assert mixed["locator"]["field_path"] == "$.results.efficacy[0].value"
    assert mixed["locator"]["url"] is None, "本机路径链接不得随视图输出"
    assert mixed["original_text"] == "68.4"

    for index in (1, 2, 3, 4, 5):
        view = views[rows[index]["row_id"]]
        assert view["source_trace_state"] == "unverified", index
        assert view["source_version_id"] is None, index
        assert view["locator"] is None, index
        assert view["original_text"] is None, index
        assert view["source_version_label_zh"] == "逐事实来源待核", index

    serialized = (site / "efficacy.html").read_text(encoding="utf-8")
    assert LOCAL_ABSOLUTE not in serialized
    assert LOCAL_RELATIVE not in serialized
    assert "internal.json" not in serialized


def test_b_coarse_container_and_weak_locators_do_not_claim_located(tmp_path: Path) -> None:
    payload = _b_payload()
    payload["efficacy_views"] = {
        "coverage_mode": "partial",
        "facts": [
            _fact(
                payload,
                0,
                source_version_id="sv-coarse",
                source_text="68.4",
                source_field_path="$.resultsSection",
            ),
            _fact(
                payload,
                1,
                source_version_id="sv-root",
                source_text="31.2",
                source_field_path="$.",
            ),
            _fact(
                payload,
                2,
                source_version_id="sv-url-only",
                source_text="12.3",
                source_locator={
                    "document_role": "registry",
                    "url": "https://example.org/study/1",
                },
            ),
            _fact(
                payload,
                3,
                source_version_id="sv-heading-only",
                source_text="9.9",
                source_locator={"document_role": "registry", "heading": "登记结果"},
            ),
            _fact(
                payload,
                4,
                source_version_id="sv-leaf",
                source_text="8.8",
                source_field_path="$.results.efficacy[4].value",
            ),
        ],
    }
    site = _render_b_site(tmp_path, payload)
    views = _views_by_row(site, "efficacy.html")
    rows = payload["efficacy"]

    leaf = views[rows[4]["row_id"]]
    assert leaf["source_trace_state"] == "located"
    assert leaf["locator"]["field_path"] == "$.results.efficacy[4].value"
    assert leaf["locator"]["url"] is None

    for index in (0, 1, 2, 3):
        view = views[rows[index]["row_id"]]
        assert view["source_trace_state"] == "unverified", index
        assert view["locator"] is None, index
        assert view["source_version_id"] is None, index


def test_b_located_requires_verbatim_text_not_only_version_and_anchor(tmp_path: Path) -> None:
    payload = _b_payload()
    payload["safety_views"] = {
        "coverage_mode": "partial",
        "facts": [
            {**payload["safety"][0], "source_version_id": "sv-no-quote",
             "source_locator": {"document_role": "registry",
                                "field_path": "$.results.safety[0].value"}},
        ],
    }
    site = _render_b_site(tmp_path, payload)
    views = _views_by_row(site, "safety.html")
    view = views[payload["safety"][0]["row_id"]]
    assert view["source_trace_state"] == "unverified"
    assert view["source_version_id"] is None
    assert view["locator"] is None
    assert view["original_text"] is None
    assert view["original_text_status"] == "not_provided"


def test_b_located_quote_preserves_original_whitespace(tmp_path: Path) -> None:
    payload = _b_payload()
    quote = "  Reported  68.4\n"
    payload["efficacy_views"] = {
        "coverage_mode": "partial",
        "facts": [_fact(
            payload, 0, source_version_id="sv-verbatim", source_text=quote,
            source_field_path="$.results.efficacy[0].value",
        )],
    }
    site = _render_b_site(tmp_path, payload)
    view = _views_by_row(site, "efficacy.html")[payload["efficacy"][0]["row_id"]]
    assert view["source_trace_state"] == "located"
    assert view["original_text"] == quote


# ─── B：已报告数值必须保留原始报告值，真零不得当作缺失 ────────────────────────


def test_b_reported_number_survives_plot_ineligible_projection(tmp_path: Path) -> None:
    payload = _b_payload()
    payload["safety"][1] = {
        **payload["safety"][1],
        "value": 92.7,
        "unit": "Proportion of participants",
        "disclosure_state": "已公开",
    }
    site = _render_b_site(tmp_path, payload)
    views = _views_by_row(site, "safety.html")
    view = views[payload["safety"][1]["row_id"]]

    assert view["value"]["value"] == "92.7", "不可绘图不得抹掉已报告原始数值"
    assert view["value"]["state"] is None
    assert view["row"]["disclosure_state"] == "reported_value"
    assert view["source_trace_state"] == "unverified"
    assert view["locator"] is None


def test_b_true_zero_is_reported_zero_and_missing_is_not_zero(tmp_path: Path) -> None:
    payload = _b_payload()
    payload["safety"][0] = {
        **payload["safety"][0],
        "value": 0,
        "disclosure_state": "已公开",
    }
    payload["safety"][2] = {
        **payload["safety"][2],
        "value": None,
        "disclosure_state": "未公开",
    }
    site = _render_b_site(tmp_path, payload)
    views = _views_by_row(site, "safety.html")

    zero = views[payload["safety"][0]["row_id"]]
    assert zero["value"]["state"] is None
    assert float(zero["value"]["value"]) == 0.0
    assert zero["row"]["disclosure_state"] == "reported_zero"

    missing = views[payload["safety"][2]["row_id"]]
    assert missing["value"]["value"] is None, "真实缺失不得重新标成 0"
    assert missing["value"]["state"] == "not_yet_disclosed"


# ─── 序列化边界：model_construct/model_copy 不能绕过追溯合同 ──────────────────


def _located_payload() -> dict[str, Any]:
    identity = {
        "product_id": "product-01",
        "trial_id": "trial-01",
        "group_id": "group-treat",
        "endpoint_id": "endpoint-hba1c",
    }
    return {
        "report_kind": "A",
        "observation_kind": "general",
        "row": {
            "row_id": derive_row_id(**identity),
            "display_label_zh": "第3组治疗组主要终点",
            "page_responsibility_id": "efficacy",
            "report_snapshot_id": "report-snapshot-r2429",
            "disclosure_state": "reported_value",
            **identity,
        },
        "product_zh": "产品甲",
        "trial_zh": "试验一",
        "group_zh": {"value": "治疗组"},
        "element_zh": "主要终点 HbA1c 变化值",
        "scale": {"value": "原始"},
        "timepoint": {"value": "第12周"},
        "value": {"value": "5.2"},
        "threshold": {"state": "not_applicable"},
        "unit": {"value": "mg/dL"},
        "numerator": {"state": "not_applicable"},
        "denominator": {"value": "120"},
        "source_trace_state": "located",
        "source_version_id": "source-version-01",
        "source_version_label_zh": "ClinicalTrials.gov 登记版本（2026年5月1日）",
        "locator": {
            "document_role": "primary_registry",
            "field_path": "$.results.efficacy[0].value",
        },
        "original_text": "Mean change from baseline: 5.2",
        "original_text_status": "provided",
        "explanation": {"value": "直接取自来源报告值，未做换算"},
    }


def test_serialization_boundary_rejects_bypassed_local_path_locator() -> None:
    view = validate_evidence_view_payload(_located_payload())
    forged = view.model_copy(
        update={
            "locator": view.locator.model_copy(update={"url": LOCAL_ABSOLUTE}),
        }
    )
    with pytest.raises(EvidenceViewBoundaryError, match="本机路径|定位"):
        assert_evidence_trace_contract(forged)


def test_serialization_boundary_rejects_bypassed_quote_less_located() -> None:
    payload = _located_payload()
    payload["report_kind"] = "B"
    view = validate_evidence_view_payload(payload)
    forged = view.model_copy(update={"original_text": None})
    with pytest.raises(EvidenceViewBoundaryError, match="原文"):
        assert_evidence_trace_contract(forged)
    with pytest.raises(EvidenceViewBoundaryError, match="原文"):
        serialize_evidence_views([forged])


def test_model_rejects_local_path_and_coarse_anchor_shapes() -> None:
    dirty = _located_payload()
    dirty["locator"] = {"document_role": "primary_registry", "url": LOCAL_ABSOLUTE}
    with pytest.raises(EvidenceViewBoundaryError, match="本机路径|定位"):
        validate_evidence_view_payload(dirty)

    unc = _located_payload()
    unc["locator"] = {"document_role": "primary_registry", "table": LOCAL_UNC}
    with pytest.raises(EvidenceViewBoundaryError, match="本机路径|定位"):
        validate_evidence_view_payload(unc)

    coarse = _located_payload()
    coarse["locator"] = {"document_role": "primary_registry", "field_path": "$.resultsSection"}
    with pytest.raises(EvidenceViewBoundaryError, match="粗|定位"):
        validate_evidence_view_payload(coarse)

    url_only = _located_payload()
    url_only["locator"] = {
        "document_role": "primary_registry",
        "url": "https://example.org/study/1",
    }
    with pytest.raises(EvidenceViewBoundaryError, match="定位"):
        validate_evidence_view_payload(url_only)

    heading_only = _located_payload()
    heading_only["locator"] = {"document_role": "primary_registry", "heading": "登记结果"}
    with pytest.raises(EvidenceViewBoundaryError, match="定位"):
        validate_evidence_view_payload(heading_only)


def test_model_rejects_unverified_leftovers() -> None:
    for field_name, value in (
        ("conflicts", [{
            "conflicting_source_version_id": "source-version-02",
            "conflicting_value_zh": "105/120",
            "conflict_note_zh": "登记结果页与主要报告完成人数不一致",
            "locator": {"document_role": "primary_registry", "table": "基线特征表"},
        }]),
        ("historical_versions", [{
            "source_version_id": "source-version-00",
            "previous_value": {"value": "99"},
            "supersession_note_zh": "2026年3月登记版本已被5月版本取代，仅留历史",
            "locator": {"document_role": "primary_registry", "table": "基线特征表"},
        }]),
    ):
        payload = _located_payload()
        payload.update(
            source_trace_state="unverified",
            source_version_id=None,
            locator=None,
            original_text=None,
            original_text_status="not_provided",
            **{field_name: value},
        )
        with pytest.raises(EvidenceViewBoundaryError, match="来源待核|待核"):
            validate_evidence_view_payload(payload)



def test_omitted_trace_state_defaults_to_unverified_and_rejects_leftovers() -> None:
    """缺省待核：省略 source_trace_state 不得晋级已定位，版本/定位残留必须拒绝。"""
    payload = _located_payload()
    payload.pop("source_trace_state", None)
    with pytest.raises(EvidenceViewBoundaryError, match="来源待核|残留"):
        validate_evidence_view_payload(payload)


def test_a_shaped_located_view_without_quote_stays_compatible() -> None:
    """A 类调用方（页、表、段锚点）继续兼容：不因缺引文被改写为伪造或崩溃。"""
    view = validate_evidence_view_payload(_located_payload())
    assert view.source_trace_state == "located"
    assert view.source_version_id == "source-version-01"
    assert view.locator.table is None


# ─── C：保留来源自身 URL/字段路径与显式追溯状态 ──────────────────────────────


def test_c_publication_source_keeps_its_own_url_and_field_path(tmp_path: Path) -> None:
    payload = json.loads(C_FIXTURE.read_text(encoding="utf-8"))
    target = payload["observations"][0]
    quote = "  Publication  result\n"
    target["source_text"] = quote
    target["source_locator"] = {
        "document_role": "publication",
        "field_path": "results.outcomes[0].measure",
        "heading": "Results",
        "url": PUBLICATION_URL,
    }
    views = _render_c_views(tmp_path, payload)
    view = views[target["row_id"]]

    assert view["source_trace_state"] == "located"
    assert view["locator"]["url"] == PUBLICATION_URL, "论文/外部来源 URL 不得改写成登记链接"
    assert view["locator"]["field_path"] == "results.outcomes[0].measure"
    assert view["source_version_id"] == target["source_version_id"]
    assert view["original_text"] == quote
    assert "clinicaltrials.gov" not in json.dumps(view["locator"], ensure_ascii=False).lower()
    assert "ClinicalTrials.gov" not in view["source_version_label_zh"]


def test_c_weak_or_local_locator_is_not_located_and_keeps_good_anchor(tmp_path: Path) -> None:
    payload = json.loads(C_FIXTURE.read_text(encoding="utf-8"))
    observations = payload["observations"]
    url_only = observations[1]
    url_only["source_locator"] = {
        "document_role": "publication",
        "url": PUBLICATION_URL,
    }
    local_with_row = observations[2]
    local_with_row["source_locator"] = {
        "document_role": "clinical-trial-registry",
        "field_path": LOCAL_ABSOLUTE,
        "row": "2",
        "url": f"file://{LOCAL_ABSOLUTE}",
    }
    views = _render_c_views(tmp_path, payload)

    weak = views[url_only["row_id"]]
    assert weak["source_trace_state"] == "unverified"
    assert weak["source_version_id"] is None
    assert weak["locator"] is None
    assert weak["original_text"] is None
    assert weak["source_version_label_zh"] == "逐事实来源待核"

    kept = views[local_with_row["row_id"]]
    assert kept["source_trace_state"] == "located"
    assert kept["locator"]["row"] == "2"
    assert kept["locator"]["field_path"] is None
    assert kept["locator"]["url"] is None


# ─── 数据依据面板：显式追溯状态、不得复用「来源未列示」 ──────────────────────


def test_drawer_asset_renders_explicit_trace_state() -> None:
    source = DRAWER_ASSET.read_text(encoding="utf-8")
    assert '["_source_trace", "来源追溯"]' in source
    assert '"逐事实来源待核"' in source
    assert "已定位" in source
    assert "来源待核，未提供精确定位" in source
    assert "isLocalPathShape" in source
    assert "FALLBACK_ROLE_LABELS" in source
    assert "source_record" in source


def test_drawer_asset_does_not_reuse_not_listed_for_pending_trace() -> None:
    source = DRAWER_ASSET.read_text(encoding="utf-8")
    body = source.split("function renderLocatorInto", 1)[1].split("\n  }", 1)[0]
    assert "pendingText" in body, "待核定位回退必须由来源追溯状态决定"
    assert "container.textContent = pendingText || NOT_LISTED;" in body
    view_body = source.split("function renderView", 1)[1].split("\n  }", 1)[0]
    assert "traceIsPending(view) ? TRACE_PENDING_LOCATOR : NOT_LISTED" in view_body
