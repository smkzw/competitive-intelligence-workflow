"""Task 7.5：C 类真实设计门户的路由、事实和证据下钻 RED 合同。"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.qc.browser import enumerate_site_routes, route_to_site_path
from ci_workflow.reports.c import (
    DesignFieldFamily,
    DesignGateDecision,
    DesignObservation,
    evaluate_design_gate,
    project_eligibility_drilldown,
    project_endpoint_definition_timepoint,
    project_trial_dossier,
)
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "fixtures/positive/c-atopic-dermatitis"
REPORT_DATA = FIXTURE_ROOT / "inputs/report-data.json"
RECEIPTS = FIXTURE_ROOT / "source-receipts.json"
REGISTRY_DIR = FIXTURE_ROOT / "sources/clinicaltrials"

C_STATIC_PAGE_IDS = (
    "overview",
    "design-map",
    "trial-profile",
    "population-disease-definition",
    "inclusion-criteria",
    "exclusion-criteria",
    "treatment-arms",
    "endpoint-timepoint-matrix",
    "visit-duration-followup",
    "sample-analysis-statistics",
    "design-patterns",
)
C_CORE_FAMILIES = {
    DesignFieldFamily.POPULATION,
    DesignFieldFamily.GROUPING,
    DesignFieldFamily.ENDPOINT,
    DesignFieldFamily.TIMEPOINT,
}
_INTERNAL_LEAKS = (
    "field_family",
    "source_role",
    "not_publicly_disclosed",
    "registry_result_or_primary_report",
    "c_missing_",
    "candidate_paths",
    "__CHART_GROUPS__",
    "__EVIDENCE_VIEWS__",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _observations(payload: dict[str, Any]) -> tuple[DesignObservation, ...]:
    rows = payload.get("observations")
    assert isinstance(rows, list)
    return tuple(DesignObservation.model_validate(row) for row in rows)


def _renderer() -> ModuleType:
    """延迟导入待实现的 C 门户；缺失时精确失败而非收集期导入崩溃。"""
    try:
        module = importlib.import_module("ci_workflow.renderers.portal.report_c")
    except ModuleNotFoundError as exc:
        if exc.name != "ci_workflow.renderers.portal.report_c":
            raise
        pytest.fail(f"C 类门户渲染器尚未实现：{exc}", pytrace=False)
    return module


def _render_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    module = _renderer()
    data_type = getattr(module, "ReportCPortalData", None)
    render = getattr(module, "render_report_c_site", None)
    if data_type is None or not callable(render):
        pytest.fail("C 类门户必须公开 ReportCPortalData 与 render_report_c_site", pytrace=False)
    root = tmp_path_factory.mktemp("c-report-portal") / "html"
    data = data_type.model_validate(_load(REPORT_DATA))
    render(data, root)
    return root


@pytest.fixture(scope="module")
def c_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _render_site(tmp_path_factory)


def _text(site: Path, relative: str) -> str:
    return (site / relative).read_text(encoding="utf-8")


def _json_assignment(html: str, name: str) -> Any:
    match = re.search(rf"window\.{re.escape(name)}\s*=\s*", html)
    assert match is not None, name
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(html[match.end() :].lstrip())
    return value


def _page_json_assignment(site: Path, relative: str, name: str) -> Any:
    return _json_assignment(_text(site, relative), name)


def _sitemap(site: Path) -> dict[str, Any]:
    return _load(site / "data/sitemap.json")


def _report_literal(site: Path) -> dict[str, Any]:
    source = _text(site, "data/report.js")
    marker = "window.REPORT_C="
    assert marker in source
    value, _ = json.JSONDecoder().raw_decode(source.split(marker, 1)[1].lstrip())
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def test_real_registry_sources_and_receipts_are_complete_and_byte_bound() -> None:
    """四个声明研究必须来自官方登记，原文文件和回执摘要逐一对应。"""
    payload = _load(REPORT_DATA)
    receipts = _load(RECEIPTS)
    records = receipts.get("records")
    assert isinstance(records, list)
    assert {item["record_id"] for item in records} == {
        "NCT02260986",
        "NCT04178967",
        "NCT03985943",
        "NCT05149313",
    }
    assert len(records) == 4

    trial_ids = {trial["display_id"] for trial in payload["trials"]}
    assert trial_ids == {item["record_id"] for item in records}
    for receipt in records:
        raw_path = FIXTURE_ROOT / receipt["relative_path"]
        assert raw_path.is_file(), receipt["record_id"]
        content = raw_path.read_bytes()
        assert len(content) == receipt["byte_size"], receipt["record_id"]
        assert hashlib.sha256(content).hexdigest() == receipt["sha256"], receipt["record_id"]
        raw = json.loads(content)
        assert raw["protocolSection"]["identificationModule"]["nctId"] == receipt["record_id"]
        assert receipt["source_url"].startswith("https://clinicaltrials.gov/api/v2/studies/")

    raw_titles = {
        json.loads(path.read_text(encoding="utf-8"))["protocolSection"]["identificationModule"]["nctId"]
        for path in REGISTRY_DIR.glob("*.json")
    }
    assert raw_titles == trial_ids


def test_real_fixture_has_multiple_innovative_products_and_registry_design_facts() -> None:
    """正例不是空壳：三种干预、四项登记试验且每项覆盖四类关键设计。"""
    payload = _load(REPORT_DATA)
    products = payload["products"]
    trials = payload["trials"]
    observations = _observations(payload)
    assert len(products) >= 2
    assert len(trials) == 4
    assert {trial["product_id"] for trial in trials} == {
        "dupilumab",
        "lebrikizumab",
        "nemolizumab",
    }
    assert {item.source_role.value for item in observations} == {"clinical_trial_registry"}
    assert {item.review_state.value for item in observations} == {"accepted"}
    assert {item.trial_id for item in observations} == {
        trial["id"] for trial in trials
    }
    for trial in trials:
        trial_families = {
            item.field_family
            for item in observations
            if item.trial_id == trial["id"]
        }
        assert trial_families >= C_CORE_FAMILIES, trial["id"]
    assert {item.field for item in observations} >= {
        "inclusion_criterion",
        "exclusion_criterion",
        "dosing_regimen",
        "visit_schedule",
    }


def test_positive_design_gate_and_source_bound_design_alternatives() -> None:
    """关键登记设计可通过；真实终点事实保留至少两类可选路径。"""
    payload = _load(REPORT_DATA)
    observations = _observations(payload)
    trial_ids = tuple(trial["id"] for trial in payload["trials"])
    gate = evaluate_design_gate(observations, core_trial_ids=trial_ids)
    assert gate.decision is DesignGateDecision.PASSED
    assert gate.failures == ()
    assert gate.nonblocking_gaps
    assert all(
        gap.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED
        for gap in gate.nonblocking_gaps
    )

    endpoint_rows = tuple(
        item
        for item in observations
        if item.field_family is DesignFieldFamily.ENDPOINT
        and item.field == "primary_endpoint_definition"
    )
    assert len(endpoint_rows) == len(trial_ids)
    path_trials: dict[str, set[str]] = {}
    for item in endpoint_rows:
        source = f"{item.source_field_name} {item.source_text}".casefold()
        family = "EASI" if "easi" in source else "IGA" if "iga" in source else ""
        assert family, item.observation_id
        assert item.source_locator.url
        path_trials.setdefault(family, set()).add(item.trial_id)
    assert set(path_trials) == {"EASI", "IGA"}
    assert set().union(*path_trials.values()) == set(trial_ids)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert not any(
        token in serialized for token in ("排名", "唯一最佳", '"rank"', '"score"')
    )


def test_projection_surfaces_share_stable_facts_and_trial_dossiers_are_complete() -> None:
    """图/表/抽屉和逐试验档案必须由同一观察身份集合投影。"""
    payload = _load(REPORT_DATA)
    observations = _observations(payload)
    endpoint_view = project_endpoint_definition_timepoint(observations)
    assert tuple(row.endpoint_identity for row in endpoint_view.chart_rows) == tuple(
        row.endpoint_identity for row in endpoint_view.table_rows
    )
    assert len(endpoint_view.chart_rows) == 4
    assert all(row.endpoint_source_locator.url for row in endpoint_view.chart_rows)

    eligibility_view = project_eligibility_drilldown(
        observations,
        indication_id=payload["indication_id"],
    )
    assert eligibility_view.table_rows
    assert tuple(row.drilldown_chain_id for row in eligibility_view.chart_rows) == tuple(
        row.drilldown_chain_id for row in eligibility_view.table_rows
    )
    assert set(eligibility_view.evidence_by_chain_id) == {
        row.drilldown_chain_id for row in eligibility_view.table_rows
    }

    for trial in payload["trials"]:
        trial_rows = tuple(item for item in observations if item.trial_id == trial["id"])
        dossier = project_trial_dossier(observations, trial_id=trial["id"])
        assert set(dossier.observation_ids) == {item.observation_id for item in trial_rows}
        assert tuple(row.observation_id for row in dossier.chart_rows) == tuple(
            row.observation_id for row in dossier.table_rows
        )


def test_c_sitemap_expands_all_twelve_static_pages_and_every_trial_detail(
    c_site: Path,
) -> None:
    payload = _load(REPORT_DATA)
    trial_ids = tuple(trial["id"] for trial in payload["trials"])
    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.C)
    expected = registry.sitemap(ReportKind.C, trial_ids=trial_ids)

    sitemap = _sitemap(c_site)
    listed = tuple(item["route"] for item in sitemap["routes"])
    assert set(listed) == set(expected)
    assert len(listed) == len(C_STATIC_PAGE_IDS) + len(trial_ids)
    assert len(catalog.pages) == len(C_STATIC_PAGE_IDS)
    assert {page.id for page in catalog.pages} == set(C_STATIC_PAGE_IDS)
    assert len(set(listed)) == len(listed)

    physical = tuple(enumerate_site_routes(c_site, ReportKind.C))
    assert set(physical) == set(expected)
    for route in expected:
        assert (c_site / route_to_site_path(route)).is_file(), route


def test_c_static_pages_bind_chart_table_and_evidence_to_one_fact_set(c_site: Path) -> None:
    """每页图表先于完整表格；图表行必须全部可从证据抽屉回溯。"""
    for page_id in C_STATIC_PAGE_IDS:
        html = _text(c_site, f"{page_id}.html")
        assert 'lang="zh-CN"' in html
        assert 'id="kz-chart-module"' in html, page_id
        assert "window.__CHART_GROUPS__" in html, page_id
        assert "window.__EVIDENCE_VIEWS__" in html, page_id
        assert html.index("kz-chart-module") < html.index("kz-chart-table"), page_id
        groups = _page_json_assignment(c_site, f"{page_id}.html", "__CHART_GROUPS__")
        evidence = _page_json_assignment(c_site, f"{page_id}.html", "__EVIDENCE_VIEWS__")
        assert isinstance(groups, list) and groups, page_id
        assert isinstance(evidence, list) and evidence, page_id
        chart_ids = {
            row["row_id"]
            for group in groups
            for row in group.get("rows", [])
            if isinstance(row, dict) and row.get("row_id")
        }
        evidence_ids = {
            view["row"]["row_id"]
            for view in evidence
            if isinstance(view, dict)
            and isinstance(view.get("row"), dict)
            and view["row"].get("row_id")
        }
        assert chart_ids
        assert chart_ids <= evidence_ids, page_id
        if page_id == "design-patterns":
            path_ids = set(re.findall(r'data-path-id="([^"]+)"', html))
            assert len(path_ids) >= 2
            assert "唯一最佳" not in re.sub(
                r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
                "",
                html,
                flags=re.S | re.I,
            )


def test_c_trial_detail_pages_preserve_each_trial_observation_set(c_site: Path) -> None:
    payload = _load(REPORT_DATA)
    observations = _observations(payload)
    index = _text(c_site, "trial-profile.html")
    for trial in payload["trials"]:
        trial_id = trial["id"]
        href = f'trials/{trial_id}.html'
        assert href in index
        html = _text(c_site, href)
        assert f'data-trial-id="{trial_id}"' in html
        assert trial["display_id"] in html
        groups = _json_assignment(html, "__CHART_GROUPS__")
        evidence = _json_assignment(html, "__EVIDENCE_VIEWS__")
        chart_ids = {
            row["row_id"]
            for group in groups
            for row in group.get("rows", [])
            if isinstance(row, dict) and row.get("row_id")
        }
        expected_ids = {
            item.row_id for item in observations if item.trial_id == trial_id
        }
        evidence_ids = {
            view["row"]["row_id"]
            for view in evidence
            if isinstance(view, dict)
            and isinstance(view.get("row"), dict)
            and view["row"].get("row_id")
        }
        assert chart_ids == expected_ids
        assert chart_ids <= evidence_ids


def test_c_pages_use_local_assets_and_scoped_external_sources(
    c_site: Path,
) -> None:
    for html_path in sorted(c_site.rglob("*.html")):
        html = html_path.read_text(encoding="utf-8")
        source_match = re.search(
            r'<section[^>]+id="external-sources"[^>]*>.*?</section>',
            html,
            flags=re.S | re.I,
        )
        for src in re.findall(r'(?:src|href)="([^"]+)"', html):
            if src.startswith(("http:", "https:", "//")):
                assert source_match is not None
                assert src in source_match.group(0)
            else:
                assert not src.startswith(("http:", "https:", "//")), (html_path, src)
        visible = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
        visible = re.sub(r"<style\b.*?</style>", "", visible, flags=re.S | re.I)
        visible = re.sub(r"<[^>]+>", "", visible)
        assert "康哲药业" in visible
        for token in _INTERNAL_LEAKS:
            assert token not in visible, (html_path, token)



def test_adversarial_c_user_visible_pages_reject_raw_design_enums(c_site: Path) -> None:
    """攻击：完整表可见区不得残留 ClinicalTrials 设计枚举拼串或重复前提标签。"""
    treatment = _text(c_site, "treatment-arms.html")
    visible = re.sub(
        r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
        "",
        treatment,
        flags=re.S | re.I,
    )
    for token in (
        "allocation=",
        "interventionModel=",
        "masking=",
        "RANDOMIZED",
        "PARALLEL",
        "TRIPLE",
    ):
        assert token not in visible, token

    patterns = _text(c_site, "design-patterns.html")
    visible_patterns = re.sub(
        r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
        "",
        patterns,
        flags=re.S | re.I,
    )
    assert "前提：前提：" not in visible_patterns
    assert "权衡：权衡：" not in visible_patterns

    overview = _text(c_site, "overview.html")
    assert 'id="kz-filter-panel"' in overview
    # 医学经理首屏：筛选面板默认 open 时，不得把核心图压到面板之后的远距离。
    panel_open = bool(
        re.search(
            r'id="kz-filter-panel"[^>]*\sopen(?:\s|>|/)',
            overview,
        )
    )
    chart_pos = overview.find('id="kz-chart-module"')
    panel_pos = overview.find('id="kz-filter-panel"')
    assert chart_pos > 0 and panel_pos > 0
    if panel_open:
        assert chart_pos < panel_pos

def test_missing_critical_registry_fact_blocks_draft_portal_generation(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """负例：移除一项核心试验的终点时间点，不能生成貌似完整的门户。"""
    payload = _load(REPORT_DATA)
    payload["observations"] = [
        row
        for row in payload["observations"]
        if not (
            row["trial_id"] == "nct05149313"
            and row["field"] == "primary_endpoint_timepoint"
        )
    ]
    module = _renderer()
    data_type = getattr(module, "ReportCPortalData", None)
    render = getattr(module, "render_report_c_site", None)
    assert data_type is not None and callable(render)
    data = data_type.model_validate(payload)
    with pytest.raises(ValueError, match="终点|时间点|关键|阻断|证据"):
        render(data, tmp_path_factory.mktemp("c-report-negative") / "html")
