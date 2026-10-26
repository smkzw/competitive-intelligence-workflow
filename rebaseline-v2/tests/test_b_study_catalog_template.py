"""B 相关研究目录模板：未发表与未知记录保留，不访问网络，不判定临床结论。"""
from __future__ import annotations

import re

import pytest

from ciw2.render.portal import _env

_COUNTS = {"all": 3, "with_results": 1, "without_results": 1, "unknown": 1, "adopted": 1}
_ATTACK_URL = 'https://example.org/src?a=1&b="><script>alert(1)</script>'
_ESCAPED_URL = "https://example.org/src?a=1&amp;b=&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"


def _identity(registry_id: str, *, drug: str = "合成药物甲", company: str = "合成公司甲") -> dict:
    label = f"{drug} · 合成适应症 · III期 · 申办方 {company}"
    return {
        "registry_id": registry_id,
        "drug_label": drug,
        "drugs": [drug],
        "drug_names_original": [drug],
        "name_refs": [],
        "targets": ["靶点甲"],
        "profile_refs": [],
        "indication": "合成适应症",
        "conditions_original": ["合成适应症"],
        "phase_label": "III期",
        "companies": [{"role": "申办方", "name": company}],
        "label": label,
        "axis_label": f"{drug} · III期",
    }


def _catalog_row(entity_id: str, registry_id: str, published_results: bool | None, published_label: str,
                 result_count: int, source_url: str | None) -> dict:
    return {
        "entity_id": entity_id,
        "registry_id": registry_id,
        "identity": _identity(registry_id),
        "result_count": result_count,
        "published_results": published_results,
        "published_label": published_label,
        "source_url": source_url,
        "source_id": "src-synthetic" if source_url else None,
    }


def _result(fact_id: str, entity_id: str, registry_id: str) -> dict:
    return {
        "id": fact_id,
        "entity_id": entity_id,
        "entity": registry_id,
        "domain": "clinical",
        "display_drugs": ["合成药物甲"],
        "identity": _identity(registry_id),
        "endpoint": "合成终点",
        "class_title": None,
        "category": None,
        "timepoint": "Week 16",
        "population": "合成人群",
        "arm": "合成组别",
        "value": 1,
        "unit": "%",
        "stat_type": "proportion",
        "denominator": 10,
        "status": "verified",
        "source_url": "https://example.org/fact",
        "quote": "合成原文片段",
        "verdict_note": None,
    }


def _safety(fact_id: str, entity_id: str, registry_id: str) -> dict:
    return {
        "id": fact_id,
        "entity_id": entity_id,
        "entity": registry_id,
        "display_drugs": ["合成药物甲"],
        "identity": _identity(registry_id),
        "arm": "合成组别",
        "field": "safety.sae.any",
        "value": 0,
        "denominator": 10,
        "proportion": None,
        "timepoint": "Week 16",
        "status": "verified",
        "source_url": "https://example.org/safety",
        "quote": "合成安全性原文",
        "verdict_note": None,
    }


def _data(*, catalog: dict | None = None, include_catalog: bool = True, results: list | None = None,
          safety: list | None = None, groups: list | None = None) -> dict:
    data = {
        "results": results if results is not None else [_result("fact-pub", "study-pub", "REG-PUB")],
        "safety": safety if safety is not None else [_safety("fact-safety", "study-unpub", "REG-UNPUB")],
        "analyses": [],
        "charts": {"groups": [{"id": "g1", "label": "合成指标"}] if groups is None else groups},
        "domain_counts": {"clinical": 1},
        "domain_labels": {"clinical": "临床"},
        "default_domain": "clinical",
    }
    if include_catalog:
        data["study_catalog"] = catalog
    return data


def _catalog() -> dict:
    return {
        "rows": [
            _catalog_row("study-pub", "REG-PUB", True, "已有公开结果<script>", 4, _ATTACK_URL),
            _catalog_row("study-unpub", "REG-UNPUB", False, "尚无公开结果", 0, None),
            _catalog_row("study-unk", "REG-UNK", None, "登记结果状态未知", 0, "https://example.org/unknown"),
        ],
        "counts": dict(_COUNTS),
    }


def _render(data: dict) -> str:
    return _env.get_template("b.html").render(
        project={"indication": "合成适应症", "cutoff_date": None, "focus": None},
        report="B",
        report_title="B 疗效安全",
        data=data,
        findings=[],
        charts_json=data.get("charts", {}),
        static="/static",
        assets=None,
        reports=["B"],
    )


def _slice(html: str, start: str, end: str) -> str:
    return html.split(start, 1)[1].split(end, 1)[0]


def _options(html: str) -> list[tuple[str, str, bool]]:
    select = re.search(r'<select id="result-study">(.*?)</select>', html, re.DOTALL)
    assert select is not None
    found = re.findall(r'<option value="([^"]*)"([^>]*)>(.*?)</option>', select.group(1), re.DOTALL)
    return [(value, re.sub(r"\s+", " ", text).strip(), "selected" in attrs) for value, attrs, text in found]


def test_catalog_keeps_unpublished_unknown_and_wires_study_ids():
    html = _render(_data(catalog=_catalog()))
    assert html.index('id="studies"') < html.index('id="comparison"')
    assert '<a href="#studies">相关研究</a>' in html
    studies = _slice(html, 'id="studies"', 'id="comparison"')
    assert "<h2>相关研究</h2>" in studies
    assert 'id="study-catalog-count">3<' in studies
    assert "登记已发布 1" in studies and "尚无登记结果 1" in studies and "未知 1" in studies
    details = re.search(r"<details([^>]*)>", studies)
    assert details is not None and "open" not in details.group(1)
    table = _slice(studies, 'id="tbl-b-studies"', "</table>")
    assert "已收录数据点" in table
    assert "样本量" not in table and "事件数" not in table
    assert "data-fact-id=" not in table
    for entity_id, label in (
        ("study-pub", "已有公开结果&lt;script&gt;"),
        ("study-unpub", "尚无公开结果"),
        ("study-unk", "登记结果状态未知"),
    ):
        assert f'data-study-id="{entity_id}"' in table
        assert label in table
    assert ">0<" in table
    assert _ESCAPED_URL in table
    assert "<script>" not in html
    assert "合成药物甲" in table and "合成适应症" in table and "III期" in table
    assert "申办方" in table and "合成公司甲" in table and "REG-UNPUB" in table
    controls = _slice(html, '<div class="result-controls">', "</div>")
    assert 'id="result-query"' in controls and 'id="result-domain"' in controls and 'id="result-group"' in controls
    options = _options(html)
    assert [item[0] for item in options] == ["all", "study-pub", "study-unpub", "study-unk"]
    assert options[0][1:] == ("全部研究", True)
    assert options[1][1].endswith(" · REG-PUB")
    assert "合成药物甲 · 合成适应症 · III期 · 申办方 合成公司甲" in options[1][1]
    assert 'value=""' not in controls
    results = _slice(html, 'id="tbl-b">', "</table>")
    assert 'data-fact-id="fact-pub" data-domain="clinical"' in results
    assert 'data-study-id="study-pub"' in results
    assert "https://example.org/fact" in results and "合成原文片段" in results
    safety = _slice(html, 'id="tbl-b-safety"', "</table>")
    assert 'data-fact-id="fact-safety"' in safety and 'data-study-id="study-unpub"' in safety
    assert "https://example.org/safety" in safety and "合成安全性原文" in safety


def test_blank_study_id_does_not_create_blank_option_and_zero_stays_zero():
    catalog = _catalog()
    catalog["rows"].append({
        "entity_id": "",
        "registry_id": "REG-BLANK",
        "identity": _identity("REG-BLANK"),
        "result_count": 0,
        "published_results": False,
        "published_label": "无标识未发表",
        "source_url": None,
        "source_id": None,
    })
    catalog["counts"] = {"all": 4, "with_results": 1, "without_results": 2, "unknown": 1, "adopted": 1}
    html = _render(_data(catalog=catalog))
    assert 'id="study-catalog-count">4<' in html
    assert [item[0] for item in _options(html)] == ["all", "study-pub", "study-unpub", "study-unk"]
    table = _slice(html, 'id="tbl-b-studies"', "</table>")
    assert "无标识未发表" in table and "REG-BLANK" in table
    assert 'data-study-id=""' not in table


def test_empty_results_remain_empty_beside_catalog():
    html = _render(_data(catalog=_catalog(), results=[], safety=[], groups=[]))
    assert 'id="tbl-b-studies"' in html and "登记结果状态未知" in html
    assert 'id="result-empty"' in html and "暂无匹配的数值结果。" in html
    assert "hidden" not in _slice(html, 'id="result-empty"', ">")
    assert 'id="result-panel"' not in html


@pytest.mark.parametrize("mode", ["missing", "none", "empty"])
def test_absent_catalog_renders_without_study_controls(mode: str):
    catalog = None
    include = True
    if mode == "missing":
        include = False
    elif mode == "empty":
        catalog = {"rows": [], "counts": {"all": 0, "with_results": 0, "without_results": 0, "unknown": 0, "adopted": 0}}
    html = _render(_data(catalog=catalog, include_catalog=include))
    assert 'id="result-query"' in html and 'data-fact-id="fact-pub"' in html
    assert "https://example.org/fact" in html and "合成原文片段" in html
    assert 'id="studies"' not in html and 'id="result-study"' not in html and 'id="tbl-b-studies"' not in html
    assert 'href="#studies"' not in html
    assert '<option value=""' not in html and "value=\"\"" not in html
    results = _slice(html, 'id="tbl-b">', "</table>")
    safety = _slice(html, 'id="tbl-b-safety"', "</table>")
    assert 'data-study-id="study-pub"' in results
    assert 'data-study-id="study-unpub"' in safety
