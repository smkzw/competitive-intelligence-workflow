"""Task 7.5：C 类真实正例、登记优先阻断和多路径验收 RED。"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.reports.c import (
    DesignFieldFamily,
    DesignGateDecision,
    DesignObservation,
    evaluate_design_gate,
)

ROOT = Path(__file__).resolve().parents[2]

FIXTURE_ROOT = ROOT / "fixtures/positive/c-atopic-dermatitis"
REPORT_DATA = FIXTURE_ROOT / "inputs/report-data.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def _raw_string_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for child in value.values() for text in _raw_string_values(child))
    if isinstance(value, list):
        return tuple(text for child in value for text in _raw_string_values(child))
    return ()


def _observations(payload: dict[str, Any]) -> tuple[DesignObservation, ...]:
    return tuple(DesignObservation.model_validate(row) for row in payload["observations"])


def test_real_c_fixture_contains_declared_registry_facts_not_synthetic_placeholders() -> None:
    payload = _load(REPORT_DATA)
    assert payload["indication"] == "中重度特应性皮炎"
    assert {row["display_id"] for row in payload["trials"]} == {
        "NCT02260986",
        "NCT04178967",
        "NCT03985943",
        "NCT05149313",
    }
    assert len(payload["products"]) == 3
    assert len(payload["observations"]) == 48
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in ("示例", "占位", "synthetic", "fake", "TODO"):
        assert marker not in serialized

    expected_counts = {
        "NCT02260986": 740,
        "NCT04178967": 445,
        "NCT03985943": 941,
        "NCT05149313": 331,
    }
    for trial in payload["trials"]:
        assert trial["sample_size"] == expected_counts[trial["display_id"]]


def test_normalized_observations_are_bound_to_raw_registry_fields() -> None:
    payload = _load(REPORT_DATA)
    observations = _observations(payload)
    for trial in payload["trials"]:
        nct = trial["display_id"]
        raw = json.loads(
            (FIXTURE_ROOT / "sources/clinicaltrials" / f"{nct}.json").read_text(encoding="utf-8")
        )
        raw_text = json.dumps(raw, ensure_ascii=False)
        raw_string_text = "\n".join(_raw_string_values(raw))
        trial_rows = tuple(item for item in observations if item.trial_id == trial["id"])
        assert trial_rows
        assert all(
            item.source_locator.url and nct in item.source_locator.url for item in trial_rows
        )
        assert all(
            item.source_version_id.startswith(f"ctgov-{nct.lower()}-") for item in trial_rows
        )
        for item in trial_rows:
            if item.disclosure_state is FactDisclosureState.NOT_PUBLICLY_DISCLOSED:
                continue
            if item.field_family is DesignFieldFamily.GROUPING:
                assert "RANDOMIZED" in raw_text
                assert "PARALLEL" in raw_text
                blind_token = {"三盲": "TRIPLE", "四盲": "QUADRUPLE"}.get(item.blinding)
                assert blind_token is not None
                assert blind_token in raw_text
            elif item.field_family is DesignFieldFamily.SAMPLE_SIZE:
                assert item.threshold_value in raw_text
            elif item.field_family is DesignFieldFamily.STATISTICAL:
                continue
            else:
                source_text = item.source_text
                variants = {
                    source_text,
                    source_text.rstrip(".;"),
                    source_text.replace(">=", "\\>="),
                    source_text.replace("<", "\\<"),
                    source_text.replace(">=", "\\>=").replace("<", "\\<"),
                }
                assert any(
                    variant in raw_text or variant in raw_string_text for variant in variants
                ), (
                    nct,
                    item.field,
                    item.source_text,
                )


def test_positive_c_design_gate_and_source_bound_design_alternatives() -> None:
    """关键登记设计可通过，并保留至少两类真实终点路径证据。"""
    payload = _load(REPORT_DATA)
    observations = _observations(payload)
    trial_ids = tuple(trial["id"] for trial in payload["trials"])
    result = evaluate_design_gate(observations, core_trial_ids=trial_ids)
    assert result.decision is DesignGateDecision.PASSED
    assert result.failures == ()
    assert result.nonblocking_gaps
    assert {gap.disclosure_state for gap in result.nonblocking_gaps} == {
        FactDisclosureState.NOT_PUBLICLY_DISCLOSED
    }

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
    assert not any(
        token in json.dumps(payload, ensure_ascii=False)
        for token in ("排名", "唯一最佳", '"rank"', '"score"')
    )


def test_missing_critical_registry_design_blocks_negative_case() -> None:
    payload = _load(REPORT_DATA)
    negative = deepcopy(payload)
    negative["observations"] = [
        row
        for row in negative["observations"]
        if not (row["trial_id"] == "nct05149313" and row["field"] == "primary_endpoint_timepoint")
    ]
    observations = _observations(negative)
    result = evaluate_design_gate(
        observations,
        core_trial_ids=tuple(trial["id"] for trial in negative["trials"]),
    )
    assert result.decision is DesignGateDecision.BLOCKED
    assert result.allows_draft is False
    failure = next(
        item
        for item in result.failures
        if item.trial_id == "nct05149313" and item.field_family is DesignFieldFamily.TIMEPOINT
    )
    assert failure.failure_code == "c_missing_timepoint"
    assert "时间点" in failure.user_note_zh
    assert failure.trial_id in failure.user_note_zh


def test_adversarial_portal_visible_copy_avoids_raw_enums_and_label_doubling() -> None:
    """医学经理可见文案：不出现登记枚举拼串，路径卡片不重复“前提：/权衡：”。"""
    import tempfile

    from ci_workflow.renderers.portal.report_c import (  # noqa: WPS433
        ReportCPortalData,
        render_report_c_site,
    )

    payload = _load(REPORT_DATA)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "html"
        render_report_c_site(ReportCPortalData.model_validate(payload), root)
        treatment = (root / "treatment-arms.html").read_text(encoding="utf-8")
        patterns = (root / "design-patterns.html").read_text(encoding="utf-8")
        visible_treatment = re.sub(
            r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
            "",
            treatment,
            flags=re.S | re.I,
        )
        visible_patterns = re.sub(
            r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
            "",
            patterns,
            flags=re.S | re.I,
        )
        for token in (
            "allocation=",
            "interventionModel=",
            "masking=",
            "RANDOMIZED",
            "PARALLEL",
            "TRIPLE",
            "Two subcutaneous injections of",
            "once weekly",
        ):
            assert token not in visible_treatment, token
        assert "前提：前提：" not in visible_patterns
        assert "权衡：权衡：" not in visible_patterns
        for trial in payload["trials"]:
            dossier = (root / "trials" / f"{trial['id']}.html").read_text(encoding="utf-8")
            visible_dossier = re.sub(
                r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
                "",
                dossier,
                flags=re.S | re.I,
            )
            assert not re.search(r"(?:group|cohort)-nct\d+", visible_dossier, re.I)
            assert "None" not in visible_dossier


def test_eligibility_pages_use_native_chinese_clinical_wording() -> None:
    import tempfile

    from ci_workflow.renderers.portal.report_c import (  # noqa: WPS433
        ReportCPortalData,
        render_report_c_site,
    )

    payload = _load(REPORT_DATA)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "html"
        render_report_c_site(ReportCPortalData.model_validate(payload), root)
        visible = "\n".join(
            re.sub(
                r"<script\b.*?</script>|<style\b.*?</style>|<[^>]+>",
                "",
                (root / page).read_text(encoding="utf-8"),
                flags=re.S | re.I,
            )
            for page in ("inclusion-criteria.html", "exclusion-criteria.html")
        )
        assert not re.search(
            r"\b(?:participants?|subjects?|screening|baseline|treatment|history)\b",
            visible,
            re.I,
        )


def test_adversarial_filter_panel_default_does_not_bury_chart_marker() -> None:
    """静态模板不得默认 open 大筛选面板却把核心图模块压到首屏之外。"""
    template = (ROOT / "src/ci_workflow/renderers/portal/templates/c/page.html.j2").read_text(
        encoding="utf-8"
    )
    # Default-open details is only acceptable if chart precedes the panel.
    chart_idx = template.find('id="kz-chart-module"')
    panel_idx = template.find('id="kz-filter-panel"')
    assert chart_idx > 0 and panel_idx > 0
    if 'id="kz-filter-panel" class="kz-c-filter-panel" open>' in template or (
        'id="kz-filter-panel"' in template and " open>" in template[panel_idx : panel_idx + 80]
    ):
        assert chart_idx < panel_idx, (
            "默认展开筛选时，核心图标记必须出现在筛选面板之前，否则医学经理首屏只能看到筛选。"
        )


def test_c_overview_exposes_full_research_design_matrix_and_detail_links() -> None:
    """首页矩阵按研究横向展开全部已提取字段，并保留每条事实下钻入口。"""
    import tempfile

    from ci_workflow.renderers.portal.report_c import (  # noqa: WPS433
        ReportCPortalData,
        render_report_c_site,
    )

    payload = _load(REPORT_DATA)
    fields = tuple(dict.fromkeys(row["field"] for row in payload["observations"]))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "html"
        render_report_c_site(ReportCPortalData.model_validate(payload), root)
        overview = (root / "overview.html").read_text(encoding="utf-8")
        design_map = (root / "design-map.html").read_text(encoding="utf-8")
        matrix_headers = re.findall(
            r"<th[^>]*data-matrix-trial=\"([^\"]+)\"",
            overview,
        )
        assert matrix_headers == [trial["id"] for trial in payload["trials"]]
        assert 'id="kz-c-design-matrix"' in overview
        assert "研究 × 设计要素横向矩阵" in overview
        assert "研究 × 设计要素横向矩阵" in design_map
        assert "人群与标准" in overview
        assert "分组设计" in overview
        assert "统计分析" in overview
        for field in fields:
            assert f'data-matrix-field="{field}"' in overview
        for observation in payload["observations"]:
            row_id = observation["row_id"]
            assert f'data-evidence-open="{row_id}"' in overview
            assert row_id in overview
        assert 'data-filter-dimension="scale"' in overview
        assert 'data-filter-dimension="timepoint"' in overview

        trial_detail = (root / "trials" / f"{payload['trials'][0]['id']}.html").read_text(
            encoding="utf-8"
        )
        assert "来源位置" in trial_detail
        assert "ClinicalTrials.gov · 目标人群" in trial_detail
        assert ">登记字段<" not in trial_detail
        assert ">target_population<" not in trial_detail
        assert ">inclusion_criterion<" not in trial_detail

        client = (ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js").read_text(
            encoding="utf-8"
        )
        assert "coreDesignRows" not in client
        assert "compactFact" not in client
        assert "elements.length > 6" not in client
        assert '"core-design-matrix": "核心设计事实比较"' in client
        assert "compactCoverage" not in client
        assert "compactTrialAxis ? trialId : trialLabel" in client
        assert 'return p.data.value[2] ? matrixLabel(p.data.row) : "未公开";' in client
