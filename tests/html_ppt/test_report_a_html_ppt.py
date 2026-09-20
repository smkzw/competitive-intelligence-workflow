"""Task 8.5：A 类 HTML-PPT 单文件组装与投影合同。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ci_workflow.renderers.html_ppt.assets import (
    ASSET_SPECS,
    INPUT_SPECS,
    load_locked_json,
    sha256_file,
)
from ci_workflow.renderers.html_ppt.notes import (
    FORBIDDEN,
    NOTES_PADDING,
    audience_is_clean,
    han_count,
)
from ci_workflow.renderers.html_ppt.projections.a import (
    REQUIRED_IDS,
    build_report_a_html_ppt,
    build_report_a_slides,
)

pytestmark = [pytest.mark.retained_legacy_format]

ROOT = Path(__file__).resolve().parents[2]
REMOTE_ATTR = re.compile(r"""(?:src|href)\s*=\s*['"](?:https?|wss?):""", re.IGNORECASE)
NOTES_RE = re.compile(r'<aside class="notes">(.*?)</aside>', re.S)
SLIDE_RE = re.compile(r"<section class=\"slide[\s\S]*?</section>", re.S)
ID_RE = re.compile(r'data-slide-id="([^"]+)"')


def test_report_a_html_ppt_contract(tmp_path: Path) -> None:
    path = build_report_a_html_ppt(output_path=tmp_path / "report-a.html", root=ROOT)
    html = path.read_text(encoding="utf-8")
    manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_sha256"] == INPUT_SPECS["A"][1]
    assert manifest["assets"]["runtime_js"] == ASSET_SPECS["runtime_js"][1]
    runtime_js = (ROOT / ASSET_SPECS["runtime_js"][0]).read_text(encoding="utf-8")
    fx_js = (ROOT / ASSET_SPECS["gx_fx_js"][0]).read_text(encoding="utf-8")
    assert runtime_js[:80] in html
    assert fx_js[:80] in html
    assert "data:image/svg+xml;base64," in html
    assert REMOTE_ATTR.search(html) is None
    assert "width: 1280px" in html and "height: 720px" in html
    assert "tpl-kangzhe" in html
    assert ".gx-env" in html
    slides = SLIDE_RE.findall(html)
    ids = [match.group(1) for block in slides if (match := ID_RE.search(block))]
    for required in REQUIRED_IDS:
        assert required in ids
    assert ids[0] == "a-cover" and ids[-1] == "a-ending"
    assert any(item.startswith("a-efficacy") for item in ids)
    assert "a-matrix-2" in ids
    assert "is-active" in slides[0]
    for block in slides:
        notes = NOTES_RE.search(block)
        assert notes is not None
        note_html = notes.group(1)
        assert "<strong>" in note_html.lower()
        assert 150 <= han_count(re.sub(r"<[^>]+>", "", note_html)) <= 300
        for token in NOTES_PADDING:
            assert token not in note_html
        audience = re.sub(r'<aside class="notes">.*?</aside>', "", block, flags=re.S)
        audience_text = re.sub(r"<[^>]+>", "", audience)
        audience_is_clean(audience_text, slide_id="a")
        lowered = audience_text.lower()
        for token in FORBIDDEN:
            assert token.lower() not in lowered
    assert "度普利尤单抗" in html
    assert "特应性皮炎" in html
    assert "竞争格局" in html
    assert "疗效与安全性矩阵" in html
    assert html.count('responsibility="matrix"') == 2
    assert "中国与全球监管" in html
    assert "研究依据与局限" in html
    assert 'aria-label="乐德奇拜单抗（Rademikibart / SIM0718）"' in html
    for label in (
        "Eblasakimab",
        "Rocatinlimab",
        "Amlitelimab",
        "Tezepelumab",
        "Rezpegaldesleukin",
    ):
        assert f">{label}</text>" in html
    assert "scientific_review" not in html
    assert not re.search(r"font-size:\s*[\d.]+vw", html)
    assert sha256_file(ROOT / ASSET_SPECS["logo"][0]) == ASSET_SPECS["logo"][1]


def test_report_a_responsibilities_cover_catalog() -> None:
    raw, _digest = load_locked_json("A", root=ROOT)
    slides = build_report_a_slides(raw["report_data"])
    by_id = {slide.slide_id: slide.responsibility for slide in slides}
    assert by_id["a-landscape"] == "landscape"
    assert by_id["a-efficacy"] == "efficacy"
    assert all(
        slide.responsibility == "efficacy"
        for slide in slides
        if slide.slide_id.startswith("a-efficacy")
    )
    assert len(slides) >= 15
    clinical = next(slide for slide in slides if slide.slide_id == "a-clinical")
    assert "试验项数" in clinical.body_html
    assert "治疗组" not in clinical.body_html
    assert "对照组" not in clinical.body_html
    efficacy = next(slide for slide in slides if slide.slide_id == "a-efficacy")
    assert "应答率（%）" in efficacy.body_html
