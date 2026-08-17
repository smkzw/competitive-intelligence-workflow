"""Task 4.4 兼容性合同：九类图形、可比性拆分、锁定快照入口与全行恰好一次。

反例冻结以下合同（假绿修复后必须 GREEN）：

1. **九类图形注册**：字段要求与中文显示合同。
2. **未知类型拒绝**：不在注册表中的类型失败关闭。
3. **缺失状态非零**：缺失类披露保留非数值状态，不得转 0。
4. **兼容组关键维度**：单位、量表、统计形式、方向、时间窗、分析人群触发拆图；
   ``control_role`` / ``denominator`` 仅为组内展示语境，不得拆图。
5. **稳定小多图拆分**：确定性、顺序无关、最小拆分。
6. **所有输入行恰好一次**：覆盖校验；原始重复 row_id 失败；组内不得改写内容。
7. **必需字段与可渲染性**：已披露行缺字段失败关闭；缺失行 ``renderable=False``；
   完整行 ``renderable=True``；森林上下限、气泡 size、雷达长度最小校验。
8. **锁定快照入口**：row_id 唯一非空、快照一致、disclosure 已知集合。
9. **小多图中文标题**：拆图标题不得泄漏 ASCII snake_case / 英枚举内部键；
   方向展示值冻结为「越高越有利」「越低越有利」（内部键仍可 higher_better/
   lower_better）；分析人群等已知内部枚举必须有中文显示映射；未知含下划线
   的维度值失败关闭，不得直出到 ``title_zh``。
"""

from __future__ import annotations

import re
from typing import Any

import pytest

# 用户可见标题禁止泄漏的内部枚举/程序员键（非穷尽；至少覆盖已知 stop 条件）
_FORBIDDEN_TITLE_TOKENS: tuple[str, ...] = (
    "higher_better",
    "lower_better",
    "reported_value",
    "reported_zero",
    "not_reported",
    "not_publicly_disclosed",
    "not_applicable",
    "unresolved_due_to_route",
    "below_reporting_threshold",
)
_SNAKE_CASE_TOKEN = re.compile(r"(?<![A-Za-z0-9_])[a-z]+(?:_[a-z0-9]+)+(?![A-Za-z0-9_])")

# 方向维度标题展示合同（内部键 → 中文临床语义；Codex 冻结）
_DIRECTION_TITLE_ZH: dict[str, str] = {
    "higher_better": "越高越有利",
    "lower_better": "越低越有利",
}

# 分析人群等已知内部枚举 → 标题中文（分组仍可用内部键）
_ANALYSIS_POPULATION_TITLE_ZH: dict[str, str] = {
    "intention_to_treat": "意向治疗人群",
    "modified_intention_to_treat": "改良意向治疗人群",
    "per_protocol": "符合方案人群",
}

_REQUIRED_API: tuple[str, ...] = (
    "ChartType",
    "ChartSpec",
    "COMPARABILITY_DIMS",
    "DISPLAY_CONTEXT_DIMS",
    "SmallMultipleGroup",
    "register_chart_type",
    "resolve_chart_type",
    "split_compatible_groups",
    "validate_all_rows_covered",
    "validate_chart_input_rows",
)

NINE_CHART_TYPE_VALUES: tuple[str, ...] = (
    "bar",
    "line",
    "forest",
    "heatmap",
    "bubble",
    "scatter_interval",
    "timeline",
    "radar",
    "status_matrix",
)

# 各图类型最小完整字段（已披露可渲染行）
_COMPLETE_FIELDS: dict[str, dict[str, Any]] = {
    "bar": {"category": "治疗组", "value": 1.2},
    "line": {"time": "第12周", "value": 1.2},
    "forest": {"effect": 0.8, "ci_lower": 0.5, "ci_upper": 1.1},
    "heatmap": {"event": "头痛", "value_matrix": [[0.1, 0.2]]},
    "bubble": {"x_value": 0.5, "y_value": 0.2, "size": 120},
    "scatter_interval": {"center": 1.0, "ci_lower": 0.8},
    "timeline": {"time": "2024-01", "status": "进行中"},
    "radar": {"dimensions": ["疗效", "安全性"], "scores": [0.8, 0.6]},
    "status_matrix": {"status": "已披露", "coverage": "完整"},
}


def _api() -> Any:
    """按名拉取 Task 4.4 API；缺任一符号即 ImportError（精确 RED）。"""
    from ci_workflow.reports.common import chart_specs as mod

    missing = [name for name in _REQUIRED_API if not hasattr(mod, name)]
    if missing:
        raise ImportError("Task 4.4 图表兼容性 API 尚未实现（Worker 02）：" + ", ".join(missing))
    return mod


def _identity(
    *,
    product: str = "product-01",
    trial: str = "trial-01",
    group: str = "group-01",
    endpoint: str = "endpoint-01",
    event: str | None = None,
    timepoint: str = "tp-01",
) -> dict[str, str]:
    identity: dict[str, str] = {
        "product_id": product,
        "trial_id": trial,
        "group_id": group,
        "endpoint_id": endpoint,
        "timepoint_id": timepoint,
    }
    if event is not None:
        identity["event_id"] = event
        del identity["endpoint_id"]
        del identity["timepoint_id"]
    return identity


def _base_row(**overrides: Any) -> dict[str, Any]:
    """最小合规科学行：可比性维度 + 展示语境 + 锁定快照绑定。"""
    defaults: dict[str, Any] = {
        "row_id": "row-auto",
        "display_label_zh": "第3组治疗组主要终点",
        "page_responsibility_id": "efficacy",
        "report_snapshot_id": "snapshot-01",
        "disclosure_state": "reported_value",
        "unit": "mg/dL",
        "scale": "原始",
        "statistical_form": "均值差",
        "direction": "higher_better",
        "time_window": "12周",
        "analysis_population": "ITT",
        "control_role": "安慰剂",
        "denominator": 120,
        **_identity(),
    }
    defaults.update(overrides)
    return defaults


def _rows(*specs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, spec in enumerate(specs):
        rows.append(_base_row(row_id=f"row-{i:03d}", **spec))
    return rows


def _complete_row(chart_type: str, **overrides: Any) -> dict[str, Any]:
    fields = dict(_COMPLETE_FIELDS[chart_type])
    fields.update(overrides)
    return _base_row(**fields)


# ══════════════════════════════════════════════════════════════════════════════
# 1. 九类图形注册
# ══════════════════════════════════════════════════════════════════════════════


class TestChartTypeRegistration:
    """九类图形必须全部注册，每类有明确字段要求与中文显示合同。"""

    @pytest.mark.parametrize("chart_type_value", NINE_CHART_TYPE_VALUES)
    def test_each_chart_type_has_registered_spec(self, chart_type_value: str) -> None:
        api = _api()
        chart_type = api.ChartType(chart_type_value)
        spec = api.ChartSpec.for_type(chart_type)
        assert spec is not None, f"{chart_type_value} 缺少注册 ChartSpec"
        assert spec.chart_type == chart_type
        assert isinstance(spec.required_fields, tuple)
        assert len(spec.required_fields) > 0, f"{chart_type_value} 的 required_fields 不得为空"
        assert spec.display_contract_zh, f"{chart_type_value} 缺少中文显示合同"

    def test_chart_type_enum_has_exactly_nine_members(self) -> None:
        api = _api()
        members = list(api.ChartType)
        assert len(members) == 9
        assert {m.value for m in members} == set(NINE_CHART_TYPE_VALUES)

    def test_all_nine_specs_are_distinct(self) -> None:
        api = _api()
        specs = [api.ChartSpec.for_type(t) for t in api.ChartType]
        field_sets = [frozenset(s.required_fields) for s in specs]
        assert len(set(field_sets)) == 9, "存在图形类型的 required_fields 重复"

    def test_bar_spec_requires_category_and_value(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.BAR)
        assert "category" in spec.required_fields
        assert "value" in spec.required_fields

    def test_line_spec_requires_time_and_value(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.LINE)
        assert "time" in spec.required_fields
        assert "value" in spec.required_fields

    def test_forest_spec_requires_effect_and_ci(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.FOREST)
        assert "effect" in spec.required_fields
        assert "ci_lower" in spec.required_fields
        assert "ci_upper" in spec.required_fields

    def test_heatmap_spec_requires_event_and_value_matrix(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.HEATMAP)
        assert "event" in spec.required_fields
        assert "value_matrix" in spec.required_fields

    def test_bubble_spec_requires_x_and_y_and_size(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.BUBBLE)
        assert "x_value" in spec.required_fields
        assert "y_value" in spec.required_fields
        assert "size" in spec.required_fields

    def test_scatter_interval_spec_requires_center_and_range(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.SCATTER_INTERVAL)
        assert "center" in spec.required_fields
        assert any(
            f in spec.required_fields
            for f in ("ci_lower", "ci_upper", "range_lower", "range_upper")
        )

    def test_timeline_spec_requires_time_and_status(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.TIMELINE)
        assert "time" in spec.required_fields
        assert "status" in spec.required_fields

    def test_radar_spec_requires_dimensions_and_scores(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.RADAR)
        assert "dimensions" in spec.required_fields
        assert "scores" in spec.required_fields

    def test_status_matrix_spec_requires_status_and_coverage(self) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType.STATUS_MATRIX)
        assert "status" in spec.required_fields
        assert "coverage" in spec.required_fields


# ══════════════════════════════════════════════════════════════════════════════
# 2. 未知类型拒绝
# ══════════════════════════════════════════════════════════════════════════════


class TestUnknownChartTypeRejection:
    def test_register_rejects_unknown_string(self) -> None:
        api = _api()
        with pytest.raises(ValueError, match="未知图形类型|不在注册范围"):
            api.register_chart_type(
                "waterfall",
                api.ChartSpec(
                    chart_type="waterfall",  # type: ignore[arg-type]
                    required_fields=("x",),
                    display_contract_zh="瀑布图",
                ),
            )

    def test_resolve_rejects_unregistered_type(self) -> None:
        api = _api()
        rows = _rows({**_COMPLETE_FIELDS["bar"], "unit": "mg/dL"})
        with pytest.raises((ValueError, KeyError), match="未知|未注册|不支持"):
            api.resolve_chart_type(rows, "waterfall")  # type: ignore[arg-type]

    def test_chart_type_enum_rejects_invalid_name(self) -> None:
        api = _api()
        with pytest.raises((ValueError, AttributeError)):
            api.ChartType("waterfall")


# ══════════════════════════════════════════════════════════════════════════════
# 3. 缺失状态非零
# ══════════════════════════════════════════════════════════════════════════════


class TestMissingDisclosureNonZero:
    @pytest.mark.parametrize(
        "disclosure_state",
        [
            "not_reported",
            "not_publicly_disclosed",
            "not_applicable",
            "unresolved_due_to_route",
            "below_reporting_threshold",
        ],
        ids=[
            "not_reported",
            "not_publicly_disclosed",
            "not_applicable",
            "unresolved_due_to_route",
            "below_reporting_threshold",
        ],
    )
    def test_missing_state_preserved_not_zeroed(self, disclosure_state: str) -> None:
        api = _api()
        row = _base_row(disclosure_state=disclosure_state, unit="mg/dL")
        result = api.resolve_chart_type([row], api.ChartType.BAR)
        assert len(result) == 1
        assert result[0]["disclosure_state"] == disclosure_state
        assert result[0]["renderable"] is False
        for key in ("value", "display_value", "numeric_value"):
            if key in result[0]:
                assert result[0][key] is None or result[0][key] == "", (
                    f"缺失状态 {disclosure_state} 的行不得将 {key} 转为数值"
                )

    def test_missing_rows_not_dropped_from_chart(self) -> None:
        api = _api()
        rows = _rows(
            {**_COMPLETE_FIELDS["bar"], "disclosure_state": "reported_value"},
            {"disclosure_state": "not_reported", "unit": "mg/dL"},
            {"disclosure_state": "not_publicly_disclosed", "unit": "mg/dL"},
        )
        result = api.resolve_chart_type(rows, api.ChartType.BAR)
        result_ids = {r["row_id"] for r in result}
        input_ids = {r["row_id"] for r in rows}
        assert input_ids == result_ids, "缺失行在图形结果中丢失"

    def test_zero_only_when_explicitly_reported_zero(self) -> None:
        api = _api()
        zero_row = _complete_row("bar", disclosure_state="reported_zero", value=0)
        zero_result = api.resolve_chart_type([zero_row], api.ChartType.BAR)
        assert len(zero_result) == 1
        assert zero_result[0]["disclosure_state"] == "reported_zero"
        assert zero_result[0]["renderable"] is True
        for key in ("value", "display_value", "numeric_value"):
            if key in zero_result[0] and zero_result[0][key] not in (None, ""):
                assert zero_result[0][key] == 0, (
                    f"reported_zero 的 {key} 若存在必须为 0，不得估算其他值"
                )

        missing_row = _base_row(
            disclosure_state="not_reported",
            unit="mg/dL",
            row_id="row-missing-vs-zero",
        )
        missing_result = api.resolve_chart_type([missing_row], api.ChartType.BAR)
        assert len(missing_result) == 1
        assert missing_result[0]["disclosure_state"] == "not_reported"
        assert missing_result[0]["renderable"] is False
        for key in ("value", "display_value", "numeric_value"):
            if key in missing_result[0]:
                assert missing_result[0][key] not in (0, 0.0), f"not_reported 不得将 {key} 转为 0"


# ══════════════════════════════════════════════════════════════════════════════
# 4. 兼容组关键维度（拆图）与展示语境（不拆图）
# ══════════════════════════════════════════════════════════════════════════════


class TestCompatibilityDimensions:
    """可比性拆图维度：单位、量表、统计形式、方向、时间窗、分析人群。
    control_role / denominator 为组内展示语境，不得触发拆图。"""

    def test_comparability_dims_tuple_exists(self) -> None:
        api = _api()
        expected = {
            "unit",
            "scale",
            "statistical_form",
            "direction",
            "time_window",
            "analysis_population",
        }
        assert set(api.COMPARABILITY_DIMS) == expected, (
            f"COMPARABILITY_DIMS 必须恰好为拆图维度，当前={api.COMPARABILITY_DIMS}"
        )
        assert "control_role" not in api.COMPARABILITY_DIMS
        assert "denominator" not in api.COMPARABILITY_DIMS

    def test_display_context_dims_are_not_split_triggers(self) -> None:
        api = _api()
        assert set(api.DISPLAY_CONTEXT_DIMS) == {"control_role", "denominator"}
        assert set(api.DISPLAY_CONTEXT_DIMS).isdisjoint(set(api.COMPARABILITY_DIMS))

    def test_same_dimensions_grouped_together(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "scale": "原始", "time_window": "12周"},
            {"unit": "mg/dL", "scale": "原始", "time_window": "12周"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1
        assert len(groups[0].rows) == 2

    def test_different_unit_splits(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同单位未拆分"

    def test_different_scale_splits(self) -> None:
        api = _api()
        rows = _rows({"scale": "原始"}, {"scale": "对数"})
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同量表未拆分"

    def test_different_statistical_form_splits(self) -> None:
        api = _api()
        rows = _rows(
            {"statistical_form": "均值差"},
            {"statistical_form": "风险比"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同统计形式未拆分"

    def test_different_direction_splits(self) -> None:
        """相反 direction 必须拆成 ≥2 组（治疗/对照同图不得掩盖方向不可比）。"""
        api = _api()
        rows = _rows(
            {"direction": "higher_better"},
            {"direction": "lower_better"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同方向未拆分"
        assert len(groups) == 2, "仅方向不同时应恰好拆成 2 组"

    def test_fixture_equivalent_opposite_direction_splits(self) -> None:
        """与浏览器夹具等价：同单位同量表下相反 direction 不得共轴一图。"""
        api = _api()
        rows = _rows(
            {
                "unit": "mg/dL",
                "scale": "原始",
                "statistical_form": "均值差",
                "direction": "higher_better",
                "time_window": "12周",
                "analysis_population": "ITT",
                "control_role": "治疗组",
                "denominator": 120,
            },
            {
                "unit": "mg/dL",
                "scale": "原始",
                "statistical_form": "均值差",
                "direction": "lower_better",
                "time_window": "12周",
                "analysis_population": "ITT",
                "control_role": "治疗组",
                "denominator": 118,
                "disclosure_state": "not_publicly_disclosed",
            },
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "夹具等价相反方向行被错误共轴"

    def test_different_time_window_splits(self) -> None:
        api = _api()
        rows = _rows({"time_window": "12周"}, {"time_window": "24周"})
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同时间窗未拆分"

    def test_time_window_normalized_bucket_does_not_split(self) -> None:
        """时间窗规范化桶一致时不得拆分（空白差异）。"""
        api = _api()
        rows = _rows({"time_window": "12周"}, {"time_window": "12 周"})
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1, "规范化后相同的时间窗被错误拆分"

    def test_different_analysis_population_splits(self) -> None:
        api = _api()
        rows = _rows(
            {"analysis_population": "ITT"},
            {"analysis_population": "mITT"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2, "不同分析人群未拆分"

    def test_treatment_and_control_roles_stay_same_group(self) -> None:
        """治疗组与安慰剂/活性对照同列展示，不得因 control_role 拆图。"""
        api = _api()
        rows = _rows(
            {"control_role": "治疗组", "denominator": 120},
            {"control_role": "安慰剂", "denominator": 120},
            {"control_role": "活性对照", "denominator": 120},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1, "治疗/对照角色差异不得拆图"
        assert len(groups[0].rows) == 3
        roles = {r["control_role"] for r in groups[0].rows}
        assert roles == {"治疗组", "安慰剂", "活性对照"}

    def test_different_denominators_stay_same_group(self) -> None:
        """跨试验样本量/分母不同仍须同图展示，不得因 denominator 拆图。"""
        api = _api()
        rows = _rows(
            {"control_role": "治疗组", "denominator": 120, "trial_id": "t-a"},
            {"control_role": "治疗组", "denominator": 240, "trial_id": "t-b"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1, "分母差异不得拆图"
        dens = {r["denominator"] for r in groups[0].rows}
        assert dens == {120, 240}

    def test_roles_and_denominators_mixed_stay_same_group(self) -> None:
        """治疗/对照角色不同且分母不同时仍在同一兼容图组。"""
        api = _api()
        rows = _rows(
            {"control_role": "治疗组", "denominator": 118},
            {"control_role": "安慰剂", "denominator": 120},
            {"control_role": "活性对照", "denominator": 240},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1
        assert {r["row_id"] for r in groups[0].rows} == {r["row_id"] for r in rows}

    def test_group_title_must_be_chinese(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        groups = api.split_compatible_groups(rows)
        for g in groups:
            assert g.title_zh, "小多图组缺少中文标题"
            assert any("\u4e00" <= ch <= "\u9fff" for ch in g.title_zh), f"标题非中文: {g.title_zh}"

    def test_group_title_rejects_english_enum_and_snake_case(self) -> None:
        """拆图标题不得出现 ASCII snake_case 或已知英枚举内部键（用户可见 stop 条件）。"""
        api = _api()
        rows = _rows(
            {"direction": "higher_better", "unit": "mg/dL"},
            {"direction": "lower_better", "unit": "mg/dL"},
            {"direction": "higher_better", "unit": "nmol/L"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) >= 2
        for g in groups:
            title = g.title_zh
            for token in _FORBIDDEN_TITLE_TOKENS:
                assert token not in title, f"标题泄漏内部键 {token!r}: {title}"
            snake = _SNAKE_CASE_TOKEN.search(title)
            assert snake is None, f"标题含 ASCII snake_case 令牌 {snake.group(0)!r}: {title}"

    def test_direction_split_titles_use_native_clinical_zh(self) -> None:
        """direction 触发拆分时，标题必须用「越高越有利」「越低越有利」，不得回显英枚举。"""
        api = _api()
        rows = _rows(
            {"direction": "higher_better"},
            {"direction": "lower_better"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 2
        titles = {g.title_zh for g in groups}
        for zh in _DIRECTION_TITLE_ZH.values():
            assert any(zh in t for t in titles), f"缺少「{zh}」: {titles}"
        for eng in _DIRECTION_TITLE_ZH:
            for title in titles:
                assert eng not in title, f"标题仍含英枚举 {eng!r}: {title}"
        for title in titles:
            assert "越高越好" not in title and "越低越好" not in title

    def test_analysis_population_snake_case_titles_use_zh_mapping(self) -> None:
        """分析人群内部 snake_case 触发拆分时，title_zh 必须用中文映射，不得直出内部键。"""
        api = _api()
        rows = _rows(
            {"analysis_population": "intention_to_treat"},
            {"analysis_population": "per_protocol"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 2
        titles = {g.title_zh for g in groups}
        expected = {
            k: _ANALYSIS_POPULATION_TITLE_ZH[k] for k in ("intention_to_treat", "per_protocol")
        }
        for eng, zh in expected.items():
            assert any(zh in t for t in titles), f"标题缺少分析人群中文「{zh}」: {titles}"
            for title in titles:
                assert eng not in title, f"标题泄漏分析人群内部键 {eng!r}: {title}"
        for title in titles:
            snake = _SNAKE_CASE_TOKEN.search(title)
            assert snake is None, f"分析人群标题含 snake_case {snake.group(0)!r}: {title}"

    def test_unknown_underscore_dim_value_fails_closed_not_passthrough(self) -> None:
        """未知含下划线的可比维度值必须失败关闭，不得写入 title_zh。"""
        api = _api()
        rows = _rows(
            {"analysis_population": "ITT"},
            {"analysis_population": "mystery_population_bucket"},
        )
        with pytest.raises(ValueError, match="未知|不支持|未映射|失败"):
            api.split_compatible_groups(rows)

    def test_unknown_direction_underscore_value_fails_closed(self) -> None:
        """未知方向内部键（含下划线）失败关闭，不得直出标题。"""
        api = _api()
        rows = _rows(
            {"direction": "higher_better"},
            {"direction": "sideways_neutral"},
        )
        with pytest.raises(ValueError, match="未知|不支持|未映射|失败"):
            api.split_compatible_groups(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 5. 稳定小多图拆分
# ══════════════════════════════════════════════════════════════════════════════


class TestStableSmallMultipleSplit:
    def test_split_is_deterministic(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "scale": "原始"},
            {"unit": "mg/dL", "scale": "对数"},
            {"unit": "nmol/L", "scale": "原始"},
        )
        first = api.split_compatible_groups(rows)
        second = api.split_compatible_groups(rows)
        assert len(first) == len(second)
        for g1, g2 in zip(first, second, strict=True):
            assert g1.title_zh == g2.title_zh
            assert [r["row_id"] for r in g1.rows] == [r["row_id"] for r in g2.rows]

    def test_split_input_order_independence(self) -> None:
        import itertools

        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"}, {"unit": "mg/dL"})
        groups_by_order: list[list[Any]] = []
        for perm in itertools.permutations(range(len(rows))):
            reordered = [rows[i] for i in perm]
            groups_by_order.append(api.split_compatible_groups(reordered))
        ref = groups_by_order[0]
        for g in groups_by_order[1:]:
            assert len(g) == len(ref)
            for group_ref, group_cur in zip(ref, g, strict=True):
                assert sorted(r["row_id"] for r in group_ref.rows) == sorted(
                    r["row_id"] for r in group_cur.rows
                )

    def test_split_minimal_dimensions(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "scale": "原始", "direction": "higher_better"},
            {"unit": "nmol/L", "scale": "原始", "direction": "higher_better"},
        )
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 2, "最小拆分应为 2 组"

    def test_no_group_is_empty(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        groups = api.split_compatible_groups(rows)
        for g in groups:
            assert len(g.rows) > 0, "小多图组不得为空"

    def test_group_rows_are_from_input(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"}, {"unit": "mg/dL"})
        input_ids = {r["row_id"] for r in rows}
        groups = api.split_compatible_groups(rows)
        for g in groups:
            for r in g.rows:
                assert r["row_id"] in input_ids, f"组 {g.title_zh} 包含输入外的行 {r['row_id']}"


# ══════════════════════════════════════════════════════════════════════════════
# 6. 所有输入行恰好一次 + 内容保真
# ══════════════════════════════════════════════════════════════════════════════


class TestAllRowsExactlyOnce:
    def test_all_rows_covered_no_loss(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "disclosure_state": "reported_value"},
            {"unit": "nmol/L", "disclosure_state": "not_reported"},
            {"unit": "mg/dL", "disclosure_state": "not_publicly_disclosed"},
        )
        groups = api.split_compatible_groups(rows)
        api.validate_all_rows_covered(rows, groups)

    def test_no_duplicate_rows(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        groups = api.split_compatible_groups(rows)
        all_ids = [r["row_id"] for g in groups for r in g.rows]
        assert len(all_ids) == len(set(all_ids)), "行在组间重复出现"

    def test_validate_fails_on_lost_row(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        groups = api.split_compatible_groups(rows)
        incomplete_groups = groups[:1]
        with pytest.raises((ValueError, AssertionError), match="丢失|缺失|覆盖"):
            api.validate_all_rows_covered(rows, incomplete_groups)

    def test_validate_fails_on_duplicate_row(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"})
        groups = api.split_compatible_groups(rows)
        duplicate_groups = [
            api.SmallMultipleGroup(
                title_zh=groups[0].title_zh,
                split_dims=groups[0].split_dims,
                rows=groups[0].rows + groups[0].rows,
            )
        ]
        with pytest.raises((ValueError, AssertionError), match="重复|覆盖"):
            api.validate_all_rows_covered(rows, duplicate_groups)

    def test_validate_fails_on_duplicate_original_row_id(self) -> None:
        """原始输入自身重复 row_id 必须失败关闭（不能只靠 Counter 对齐放过）。"""
        api = _api()
        row = _base_row(row_id="dup-row", unit="mg/dL")
        original = [row, dict(row)]
        groups = [
            api.SmallMultipleGroup(
                title_zh="全部指标",
                split_dims=(),
                rows=(dict(row), dict(row)),
            )
        ]
        with pytest.raises((ValueError, AssertionError), match="重复"):
            api.validate_all_rows_covered(original, groups)

    def test_validate_fails_when_group_rewrites_row_content(self) -> None:
        """组内行不得改写原始科学内容；仅 row_id 对齐不算覆盖通过。"""
        api = _api()
        rows = _rows({"unit": "mg/dL", "denominator": 120})
        groups = api.split_compatible_groups(rows)
        rewritten = dict(groups[0].rows[0])
        rewritten["unit"] = "nmol/L"
        rewritten["display_label_zh"] = "被改写标签"
        bad_groups = [
            api.SmallMultipleGroup(
                title_zh=groups[0].title_zh,
                split_dims=groups[0].split_dims,
                rows=(rewritten,),
            )
        ]
        with pytest.raises((ValueError, AssertionError), match="改写|内容|摘要|全等"):
            api.validate_all_rows_covered(rows, bad_groups)

    def test_empty_input_no_groups(self) -> None:
        api = _api()
        groups = api.split_compatible_groups([])
        api.validate_all_rows_covered([], groups)

    def test_single_row_single_group(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"})
        groups = api.split_compatible_groups(rows)
        assert len(groups) == 1
        api.validate_all_rows_covered(rows, groups)

    def test_all_rows_exact_once_with_complex_mix(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "scale": "原始", "direction": "higher_better"},
            {"unit": "mg/dL", "scale": "对数", "direction": "higher_better"},
            {"unit": "nmol/L", "scale": "原始", "direction": "higher_better"},
            {"unit": "nmol/L", "scale": "原始", "direction": "lower_better"},
        )
        groups = api.split_compatible_groups(rows)
        api.validate_all_rows_covered(rows, groups)
        total = sum(len(g.rows) for g in groups)
        assert total == len(rows), f"行数不守恒: {total} != {len(rows)}"

    def test_disclosed_and_missing_rows_all_exactly_once(self) -> None:
        api = _api()
        rows = _rows(
            {"unit": "mg/dL", "disclosure_state": "reported_value"},
            {"unit": "mg/dL", "disclosure_state": "not_reported"},
            {"unit": "nmol/L", "disclosure_state": "reported_value"},
            {"unit": "nmol/L", "disclosure_state": "not_publicly_disclosed"},
        )
        groups = api.split_compatible_groups(rows)
        api.validate_all_rows_covered(rows, groups)
        total = sum(len(g.rows) for g in groups)
        assert total == len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 7. 必需字段校验与可渲染性
# ══════════════════════════════════════════════════════════════════════════════


class TestRequiredFieldsAndRenderability:
    @pytest.mark.parametrize("chart_type_value", NINE_CHART_TYPE_VALUES)
    def test_complete_disclosed_row_is_renderable(self, chart_type_value: str) -> None:
        api = _api()
        row = _complete_row(chart_type_value)
        result = api.resolve_chart_type([row], chart_type_value)
        assert result[0]["renderable"] is True
        assert result[0]["_chart_type"] == chart_type_value

    @pytest.mark.parametrize("chart_type_value", NINE_CHART_TYPE_VALUES)
    def test_disclosed_row_missing_required_field_fails(self, chart_type_value: str) -> None:
        api = _api()
        spec = api.ChartSpec.for_type(api.ChartType(chart_type_value))
        missing_field = spec.required_fields[0]
        row = _complete_row(chart_type_value)
        del row[missing_field]
        with pytest.raises(ValueError, match="必需|必填|缺少|缺失"):
            api.resolve_chart_type([row], chart_type_value)

    @pytest.mark.parametrize("chart_type_value", NINE_CHART_TYPE_VALUES)
    def test_missing_disclosure_row_not_renderable_without_fail(
        self, chart_type_value: str
    ) -> None:
        """缺失行即使无图形字段也保留，且明确不可渲染、不生成数值点。"""
        api = _api()
        row = _base_row(disclosure_state="not_reported")
        result = api.resolve_chart_type([row], chart_type_value)
        assert len(result) == 1
        assert result[0]["renderable"] is False
        assert result[0]["disclosure_state"] == "not_reported"
        for key in ("value", "display_value", "numeric_value"):
            if key in result[0]:
                assert result[0][key] not in (0, 0.0)

    def test_forest_ci_order_must_be_valid(self) -> None:
        api = _api()
        row = _complete_row("forest", ci_lower=1.5, ci_upper=0.5)
        with pytest.raises(ValueError, match="置信区间|上下限|次序"):
            api.resolve_chart_type([row], api.ChartType.FOREST)

    def test_bubble_size_must_be_positive(self) -> None:
        api = _api()
        row = _complete_row("bubble", size=0)
        with pytest.raises(ValueError, match="size|气泡"):
            api.resolve_chart_type([row], api.ChartType.BUBBLE)

    def test_radar_dimensions_scores_length_must_match(self) -> None:
        api = _api()
        row = _complete_row(
            "radar",
            dimensions=["疗效", "安全性", "依从性"],
            scores=[0.8, 0.6],
        )
        with pytest.raises(ValueError, match="长度|dimensions|scores"):
            api.resolve_chart_type([row], api.ChartType.RADAR)


# ══════════════════════════════════════════════════════════════════════════════
# 8. 锁定快照统一入口校验
# ══════════════════════════════════════════════════════════════════════════════


class TestLockedSnapshotIngress:
    def test_validate_accepts_consistent_locked_rows(self) -> None:
        api = _api()
        rows = _rows({"unit": "mg/dL"}, {"unit": "nmol/L"})
        validated = api.validate_chart_input_rows(rows)
        assert len(validated) == 2
        assert {r["row_id"] for r in validated} == {r["row_id"] for r in rows}

    def test_empty_row_id_fails(self) -> None:
        api = _api()
        rows = [_base_row(row_id="  ")]
        with pytest.raises(ValueError, match="row_id"):
            api.validate_chart_input_rows(rows)

    def test_duplicate_row_id_fails(self) -> None:
        api = _api()
        rows = [
            _base_row(row_id="same"),
            _base_row(row_id="same", unit="nmol/L"),
        ]
        with pytest.raises(ValueError, match="重复"):
            api.validate_chart_input_rows(rows)

    def test_missing_snapshot_id_fails(self) -> None:
        api = _api()
        row = _base_row()
        del row["report_snapshot_id"]
        with pytest.raises(ValueError, match="snapshot|快照"):
            api.validate_chart_input_rows([row])

    def test_mixed_snapshot_ids_fail(self) -> None:
        api = _api()
        rows = _rows(
            {"report_snapshot_id": "snapshot-a"},
            {"report_snapshot_id": "snapshot-b"},
        )
        with pytest.raises(ValueError, match="混合|不一致|快照"):
            api.validate_chart_input_rows(rows)

    def test_unknown_disclosure_state_fails(self) -> None:
        api = _api()
        rows = [_base_row(disclosure_state="invented_state")]
        with pytest.raises(ValueError, match="disclosure|披露"):
            api.validate_chart_input_rows(rows)

    def test_resolve_and_split_reject_mixed_snapshots(self) -> None:
        api = _api()
        rows = _rows(
            {**_COMPLETE_FIELDS["bar"], "report_snapshot_id": "snap-1"},
            {**_COMPLETE_FIELDS["bar"], "report_snapshot_id": "snap-2"},
        )
        with pytest.raises(ValueError, match="混合|不一致|快照"):
            api.resolve_chart_type(rows, api.ChartType.BAR)
        with pytest.raises(ValueError, match="混合|不一致|快照"):
            api.split_compatible_groups(rows)
