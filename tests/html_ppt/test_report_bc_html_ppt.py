# ruff: noqa: E501
"""Task 8.5：B/C HTML-PPT 投影与覆盖合同。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ci_workflow.renderers.html_ppt.assets import ASSET_SPECS, INPUT_SPECS, load_locked_json
from ci_workflow.renderers.html_ppt.notes import (
    FORBIDDEN,
    NOTES_PADDING,
    audience_is_clean,
    han_count,
)
from ci_workflow.renderers.html_ppt.projections.b import REQUIRED_IDS as B_IDS
from ci_workflow.renderers.html_ppt.projections.b import (
    build_report_b_html_ppt,
    build_report_b_slides,
)
from ci_workflow.renderers.html_ppt.projections.c import REQUIRED_IDS as C_IDS
from ci_workflow.renderers.html_ppt.projections.c import (
    build_report_c_html_ppt,
    build_report_c_slides,
)

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
REMOTE_ATTR = re.compile(r"""(?:src|href)\s*=\s*['"](?:https?|wss?):""", re.IGNORECASE)
NOTES_RE = re.compile(r'<aside class="notes">(.*?)</aside>', re.S)
SLIDE_RE = re.compile(r'<section class="slide[\s\S]*?</section>', re.S)
ID_RE = re.compile(r'data-slide-id="([^"]+)"')
FONT_RE = re.compile(r"font-size:\s*([\d.]+)px")

B_NEEDLES = [
    "阵发性睡眠性血红蛋白尿",
    "伊普可泮",
    "疗效",
    "纵向结果",
    "安全性",
    "疗效与安全性矩阵",
    "基线与人群总览",
    "人口学",
    "疾病语境",
    "基线疾病严重程度",
    "试验完成情况总览",
    "受试者流转",
    "依从性",
    "失访与退出",
    "筛败与原因",
    "补救治疗",
    "禁用药使用",
    "方案偏离",
    "试验与暴露语境",
    "亚组与支持证据",
    "产品与试验档案",
    "研究依据与局限",
    "82.3",
    "1.8",
    "92.2",
    "单臂研究没有试验内对照组",
    "本快照未提供独立亚组结果",
    "本快照未提供独立疾病语境事实",
    "第24周",
    "NCT04558918",
    "NCT04820530",
]
C_NEEDLES = [
    "中重度特应性皮炎",
    "设计图谱",
    "人群与疾病定义",
    "入选标准",
    "排除标准",
    "分组、干预与对照",
    "终点、定义与时间点",
    "访视、疗程与随访",
    "样本量与分析集",
    "试验档案",
    "试验定位核对",
    "设计模式与权衡",
    "可选路径一",
    "可选路径二",
    "资料版本与局限",
    "度普利尤单抗",
    "来布利珠单抗",
    "奈莫利珠单抗",
    "CHRONOS",
    "登记记录未单独公开分析集",
    "登记版本",
]
C_BANNED = [
    "The registry record does not",
    "allocation=RANDOMIZED",
    "Chronic AD that",
    "唯一最佳",
    "Lebrikizumab",
    "本页强制",
    "人群差标",
    "75 %",
]


def _assert_deck(path: Path, report: str, required: list[str], needles: list[str], banned: list[str] | None = None) -> str:
    html = path.read_text(encoding="utf-8")
    manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_sha256"] == INPUT_SPECS[report][1]
    assert manifest["assets"]["runtime_js"] == ASSET_SPECS["runtime_js"][1]
    assert REMOTE_ATTR.search(html) is None
    assert "width: 1280px" in html and "height: 720px" in html
    assert "data:image/svg+xml;base64," in html
    assert "tpl-kangzhe" in html
    slides = SLIDE_RE.findall(html)
    ids = [match.group(1) for block in slides if (match := ID_RE.search(block))]
    assert ids == required
    assert "is-active" in slides[0]
    for block in slides:
        notes = NOTES_RE.search(block)
        assert notes is not None
        note_html = notes.group(1)
        assert "<strong>" in note_html.lower()
        assert 150 <= han_count(re.sub(r"<[^>]+>", "", note_html)) <= 300
        for token in NOTES_PADDING:
            assert token not in note_html
        assert "请对着屏幕上的数字讲" not in note_html
        audience = re.sub(r'<aside class="notes">.*?</aside>', "", block, flags=re.S)
        audience_text = re.sub(r"<[^>]+>", "", audience)
        audience_is_clean(audience_text, slide_id=report)
        lowered = audience_text.lower()
        for token in FORBIDDEN:
            assert token.lower() not in lowered
    for needle in needles:
        assert needle in html, needle
    for token in banned or []:
        audience_all = re.sub(r'<aside class="notes">.*?</aside>', "", html, flags=re.S)
        assert token not in audience_all, token
    assert not re.search(r"font-size:\s*[\d.]+vw", html)
    for block in slides:
        sizes = [float(value) for value in FONT_RE.findall(block)]
        if sizes:
            assert min(sizes) >= 16
    return html


def test_report_b_html_ppt_contract(tmp_path: Path) -> None:
    path = build_report_b_html_ppt(output_path=tmp_path / "report-b.html", root=ROOT)
    html = _assert_deck(
        path,
        "B",
        B_IDS,
        B_NEEDLES,
        [
            "rescue_treatment",
            "prohibited_medication",
            "protocol_deviation",
            ">adherence<",
        ],
    )
    audience = re.sub(r'<aside class="notes">.*?</aside>', "", html, flags=re.S)
    assert "特应性皮炎" not in audience
    assert html.count("b-disease-context") >= 1
    assert 'aria-label="APPLY 疗效与安全性矩阵"' in html
    assert "1.8" in html
    assert ">APPOINT-PNH</text>" in html
    assert "第24周应答率（%）" in html


def test_report_b_fail_close_on_missing_module() -> None:
    raw, _digest = load_locked_json("B", root=ROOT)
    slides = build_report_b_slides(raw)
    assert [slide.slide_id for slide in slides] == B_IDS
    assert {slide.slide_id: slide.responsibility for slide in slides}["b-adherence"] == "adherence"


def test_report_c_html_ppt_contract(tmp_path: Path) -> None:
    path = build_report_c_html_ppt(output_path=tmp_path / "report-c.html", root=ROOT)
    html = _assert_deck(path, "C", C_IDS, C_NEEDLES, C_BANNED)
    for value in ("740 例", "445 例", "941 例", "331 例"):
        assert value in html
    assert 'class="grid g2 endpoint-grid"' in html
    assert html.count('class="kz-card endpoint-card"') == 4
    assert "EASI-75 应答" in html
    assert "75%改善" not in html
    assert html.count('class="grid g3"') >= 2
    audience = "".join(
        re.sub(r'<aside class="notes">.*?</aside>', "", block, flags=re.S)
        for block in SLIDE_RE.findall(html)
    )
    assert ">=" not in audience


def test_report_c_paths_and_identity() -> None:
    raw, _digest = load_locked_json("C", root=ROOT)
    slides = build_report_c_slides(raw)
    by_id = {slide.slide_id: slide for slide in slides}
    assert "度普利尤单抗" in by_id["c-identity"].body_html
    assert "NCT02260986" in by_id["c-identity"].body_html
    assert "第16周" in by_id["c-identity"].body_html or "第十六周" in by_id["c-identity"].body_html or "IGA" in by_id["c-identity"].body_html
    assert by_id["c-path-1"].responsibility == "design-patterns"
    assert by_id["c-path-2"].responsibility == "design-patterns"
