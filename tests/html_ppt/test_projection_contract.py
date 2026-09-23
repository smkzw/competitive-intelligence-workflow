"""Task 8.5：A/B/C HTML-PPT 结构映射与失败关闭合同。"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_MD = ROOT / "docs/acceptance/runs/8.5/projection-contract.md"
CATALOG_DIR = ROOT / "docs/architecture/page-catalogs"
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
EASI75_FAMILY_RE = re.compile(r"EASI[- ]?75", re.IGNORECASE)
REMOTE_ATTR = re.compile(r"""(?:src|href)\s*=\s*['"](?:https?|wss?):""", re.IGNORECASE)
FORBIDDEN_VISIBLE = (
    "schema_version",
    "gate_status",
    "route_attempts",
    "snapshot-",
    "v-fixture",
    "reported_value",
    "not_publicly_disclosed",
    "higher_is_better",
    "workflow",
    "prompt",
    "playwright",
    "chromium",
    "RENDERER_",
    "traceback",
    "TODO",
    "fixture run",
    "scientific_review",
    "content_text",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_contract() -> dict[str, Any]:
    text = CONTRACT_MD.read_text(encoding="utf-8")
    match = re.search(r"```json\n(\{.*?\n\})\n```", text, re.DOTALL)
    assert match, "projection-contract.md 必须包含机器可读 JSON 块"
    payload = json.loads(match.group(1))
    assert payload["schema_version"] == "8.5-projection-contract-v1"
    return payload


def han_count(text: str) -> int:
    return len(HAN_RE.findall(text))


def notes_is_valid(html: str) -> bool:
    if "<strong>" not in html.lower():
        return False
    return 150 <= han_count(re.sub(r"<[^>]+>", "", html)) <= 300

def audience_text_is_clean(text: str) -> bool:
    lowered = text.lower()
    return not any(token.lower() in lowered for token in FORBIDDEN_VISIBLE)


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return _load_contract()


def test_locked_input_and_asset_hashes(contract: Mapping[str, Any]) -> None:
    for spec in contract["inputs"].values():
        path = ROOT / spec["path"]
        assert path.is_file(), spec["path"]
        assert _sha256(path) == spec["sha256"], spec["path"]
    for spec in contract["assets"].values():
        path = ROOT / spec["path"]
        assert path.is_file(), spec["path"]
        assert _sha256(path) == spec["sha256"], spec["path"]


def test_slide_counts_and_coverage_match_catalogs(contract: Mapping[str, Any]) -> None:
    assert len(contract["A_slide_ids"]) >= 15
    assert contract["A_slide_expansion"] == {
        "efficacy": {
            "prefix": "a-efficacy-",
            "responsibility": "efficacy",
            "max_series_per_slide": 8,
        },
        "matrix": {
            "prefix": "a-matrix-",
            "responsibility": "matrix",
            "max_points_per_slide": 10,
        },
        "minimum_total_slides": 15,
    }
    assert len(contract["B_slide_ids"]) == 24
    assert len(contract["C_slide_ids"]) == 18
    for report, ids_key in (("A", "A_slide_ids"), ("B", "B_slide_ids"), ("C", "C_slide_ids")):
        catalog = yaml.safe_load((CATALOG_DIR / f"{report}.yaml").read_text(encoding="utf-8"))
        page_ids = {page["id"] for page in catalog["pages"]}
        mapped = set(contract["coverage"][report].values())
        non_portal = set(contract["non_portal_responsibilities"][report])
        assert not (page_ids & non_portal), f"{report} 非门户责任不得进入真实页面 catalog"
        portal_mapped = mapped - non_portal
        missing = page_ids - portal_mapped
        assert not missing, f"{report} 未覆盖页面责任: {sorted(missing)}"
        extra = portal_mapped - page_ids
        assert not extra, f"{report} 出现未知页面责任: {sorted(extra)}"
        assert mapped - page_ids == non_portal
        slides = contract[ids_key]
        assert list(contract["coverage"][report]) == slides
        assert catalog["pages"][0]["id"] == "overview"


def test_report_a_payload_shape_and_easi_family(contract: Mapping[str, Any]) -> None:
    raw = json.loads((ROOT / contract["inputs"]["A"]["path"]).read_text(encoding="utf-8"))
    payload = raw["report_data"]
    assert payload["indication"] == "特应性皮炎"
    assert len(payload["products"]) == 38
    assert len(payload["trials"]) == 49
    names = {row["name"] for row in payload["products"]}
    assert "度普利尤单抗" in names
    literal = [row for row in payload["efficacy"] if row.get("endpoint") == "EASI-75"]
    family = [
        row
        for row in payload["efficacy"]
        if EASI75_FAMILY_RE.search(str(row.get("endpoint") or ""))
    ]
    assert len(family) > len(literal)
    family_names = {
        next(p["name"] for p in payload["products"] if p["id"] == row["product_id"])
        for row in family
    }
    assert "度普利尤单抗" in family_names
    assert "度普利尤单抗" not in {
        next(p["name"] for p in payload["products"] if p["id"] == row["product_id"])
        for row in literal
    }
    assert contract["fail_close"]["A_easi75_literal_endpoint_forbidden"] is True


def test_report_b_modules_and_unpublished_gaps(contract: Mapping[str, Any]) -> None:
    data = json.loads((ROOT / contract["inputs"]["B"]["path"]).read_text(encoding="utf-8"))
    assert data["indication"] == "阵发性睡眠性血红蛋白尿"
    assert data["products"][0]["name"] == "伊普可泮"
    timepoints = {row["timepoint"] for row in data["efficacy"]}
    assert timepoints == {"第24周"}
    domains = {row["variable_domain"] for row in data["baseline_views"]["facts"]}
    assert "demographics" in domains
    assert "baseline_severity" in domains
    assert "disease_context" not in domains
    assert not any(
        row.get("field_family") == "subgroup" for row in data["disposition_views"]["facts"]
    )
    assert "efficacy_views" not in data or all(
        "亚组" not in str(row.get("endpoint_role") or "")
        for row in data["efficacy_views"]["facts"]
    )
    matrix_rows = data["matrix_view"]["rows"]
    assert all(row["trial_id"] != "nct04820530" for row in matrix_rows)
    assert matrix_rows[0]["treatment_projection"]["facet_key"] == (
        matrix_rows[0]["control_projection"]["facet_key"]
    )
    unpublished = [
        row
        for row in data["disposition_views"]["facts"]
        if row["disclosure_state"] == "not_publicly_disclosed"
    ]
    assert len(unpublished) == 40
    adherence = [
        row
        for row in data["disposition_views"]["facts"]
        if row["field"] == "adherence"
    ]
    assert adherence and all(row["value"] is None for row in adherence)
    assert "b-disease-context" in contract["B_slide_ids"]
    assert "b-adherence" in contract["B_slide_ids"]
    assert "b-subgroups" in contract["B_slide_ids"]
    assert contract["fail_close"]["B_missing_disease_context_domain"] is True
    assert contract["fail_close"]["B_missing_subgroup_rows"] is True
    assert contract["fail_close"]["B_longitudinal_only_week_24"] is True
    assert contract["fail_close"]["B_appoint_matrix_not_applicable"] is True


def test_report_c_observation_families_and_paths(contract: Mapping[str, Any]) -> None:
    data = json.loads((ROOT / contract["inputs"]["C"]["path"]).read_text(encoding="utf-8"))
    assert data["indication"] == "中重度特应性皮炎"
    assert len(data["products"]) == 3
    assert len(data["trials"]) == 4
    fields = {row["field"] for row in data["observations"]}
    required = {
        "target_population",
        "inclusion_criterion",
        "exclusion_criterion",
        "arm_randomization_blinding",
        "experimental_arm",
        "control_arm",
        "dosing_regimen",
        "primary_endpoint_definition",
        "primary_endpoint_timepoint",
        "visit_schedule",
        "planned_or_actual_sample_size",
        "analysis_population",
    }
    assert required <= fields
    assert contract["fail_close"]["C_min_design_paths"] == 1
    assert contract["fail_close"]["C_unique_best_forbidden"] is True
    path_slides = [
        slide_id
        for slide_id, page_id in contract["coverage"]["C"].items()
        if page_id == "design-patterns"
    ]
    assert path_slides == ["c-patterns", "c-path-1", "c-path-2"]
    assert contract["compatibility"]["C_second_path_slide_is_not_a_render_gate"] is True
    identity_rows = [
        row
        for row in data["observations"]
        if row["field"] == "inclusion_criterion"
        and str(row.get("threshold_value")) == "16"
    ]
    assert identity_rows, "C 试验定位页必须能读到 EASI 16 分阈值"


def test_notes_and_forbidden_helpers() -> None:
    valid = (
        "本页说明"
        + ("疗效对照" * 40)
        + "<strong>关键数字</strong>"
        + ("需要连同时间点一起读" * 8)
    )
    assert notes_is_valid(valid)
    assert not notes_is_valid("太短<strong>信号</strong>")
    assert not notes_is_valid("汉字" * 80)
    assert audience_text_is_clean("伊普可泮在 APPLY-PNH 第24周的血红蛋白应答率为 82.3%。")
    assert not audience_text_is_clean("disclosure reported_value")
    assert REMOTE_ATTR.search('<img src="https://example.com/x.png">')
    assert not REMOTE_ATTR.search('<img src="data:image/svg+xml;base64,AAA">')


def test_contract_forbids_portal_pdf_screenshot_generation() -> None:
    text = CONTRACT_MD.read_text(encoding="utf-8")
    assert "不得用门户 DOM、PDF 布局或截图生成幻灯片" in text
    assert "本步不代替 Task 8.6" in text
    assert "viewport" in text
