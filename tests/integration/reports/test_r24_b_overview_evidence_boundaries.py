"""The ordinary B entry may describe supplied data, not certify unseen research."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site


@pytest.mark.parametrize("case", ("ordinary", "no_denominator", "partial_sources", "subset"))
def test_overview_does_not_invent_closure_or_complete_provenance(
    tmp_path: Path, case: str,
) -> None:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    if case == "no_denominator":
        for row in payload["safety"]:
            row["denominator"] = None
    elif case == "partial_sources":
        payload["efficacy_views"] = {"coverage_mode": "partial", "facts": []}
        payload["safety_views"] = {"coverage_mode": "partial", "facts": []}
    elif case == "subset":
        payload["efficacy"] = payload["efficacy"][:1]
        payload["safety"] = payload["safety"][:1]
    data = ReportBPortalData.model_validate(payload)
    site = tmp_path / case
    render_report_b_site(data, site)
    html = (site / "overview.html").read_text(encoding="utf-8")
    intro = html.split('aria-label="核心结论">', 1)[1].split("</section>", 1)[0]
    assert "本资料包列示" in intro
    assert f"{len(data.products)} 个产品" in intro
    assert f"{len(data.trials)} 项研究" in intro
    assert "不能据此认定竞品检索已完整" in intro
    assert "逐条显示来源定位状态" in intro
    assert "分母缺失时不补算比例" in intro
    assert "描述性对照不等于头对头研究" in intro
    for unsupported in (
        "全闭包", "基线信息完整", "数值可回溯登记来源", "并附登记的同组风险人数分母",
    ):
        assert unsupported not in intro
