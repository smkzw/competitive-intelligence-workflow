"""Task 4.1 共用报告视图模型、行集合同与页面注册表单元测试。

覆盖：稳定 row ID 由科学身份字段（含字段名）确定（标签/排序/筛选/格式
变化不变）、身份不足与重复失败关闭、字段名限定避免跨身份字段同值碰撞、
单行集图表/完整表行 ID 完全一致、空筛选保持为空且不扩宽作用域、筛选行
必须是规范视图行本体（模型级全等，披露状态/标签/快照/页面漂移拒绝）、
冻结 A/B/C 页面目录加载（源码树与包内数据布局）与确定性站点地图。
生产边界验证器（``validate_*_payload``）是唯一入口并强制冻结目录页面
责任权威；Pydantic 模型层错误统一包装为对应 ``BoundaryError``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ci_workflow.domain.enums import ReportKind
from ci_workflow.reports.common.chart_specs import (
    ChartTableBoundaryError,
    ChartTableModule,
    validate_chart_table_module_payload,
    validate_filtered_row_set_payload,
)
from ci_workflow.reports.common.page_registry import (
    PageRegistry,
    PageRegistryError,
    StaticPage,
)
from ci_workflow.reports.common.view_state import (
    ViewStateBoundaryError,
    derive_row_id,
    validate_report_row_payload,
    validate_report_view_model_payload,
)

PAGE = "efficacy"
SNAPSHOT = "report-snapshot-01"


def row(
    *,
    label: str = "第3组治疗组主要终点",
    state: str = "reported_value",
    page: str = PAGE,
    snapshot: str = SNAPSHOT,
    **identity: str,
) -> dict[str, Any]:
    return {
        "row_id": derive_row_id(**identity),
        "display_label_zh": label,
        "page_responsibility_id": page,
        "report_snapshot_id": snapshot,
        "disclosure_state": state,
        **identity,
    }


def view(
    rows: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    *,
    page: str = PAGE,
    snapshot: str = SNAPSHOT,
) -> dict[str, Any]:
    return {
        "report_kind": "A",
        "page_responsibility_id": page,
        "report_snapshot_id": snapshot,
        "report_version": "1.0",
        "rows": list(rows),
    }


# 三组科学身份字段集合：行重建（换页/换快照攻击）时保持身份不变。
_IDENTITY_SET: tuple[dict[str, str], ...] = (
    {
        "product_id": "product-01", "trial_id": "trial-01",
        "group_id": "group-01", "endpoint_id": "endpoint-01", "timepoint_id": "timepoint-01",
    },
    {
        "product_id": "product-01", "trial_id": "trial-01",
        "group_id": "group-01", "event_id": "event-01",
    },
    {
        "product_id": "product-01", "trial_id": "trial-01",
        "group_id": "group-02", "endpoint_id": "endpoint-01", "timepoint_id": "timepoint-01",
    },
)


def identity_rows() -> tuple[dict[str, Any], ...]:
    return (
        row(**_IDENTITY_SET[0]),
        row(
            label="第3组严重不良事件发生率",
            **_IDENTITY_SET[1],
        ),
        row(
            label="第2组治疗组主要终点",
            state="not_reported",
            **_IDENTITY_SET[2],
        ),
    )


def filtered_row_set(rows: tuple[dict[str, Any], ...]) -> Any:
    payload = {"view": view(rows), "rows": list(rows)}
    return validate_filtered_row_set_payload(payload)


# ─── ReportRow / ReportViewModel：稳定身份 ───────────────────────────────────


def test_row_id_derived_from_scientific_identity_not_label_or_order() -> None:
    first = validate_report_row_payload(
        row(
            product_id="product-01", trial_id="trial-01",
            group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-01",
        ),
        report_kind=ReportKind.A,
    )
    relabeled = validate_report_row_payload(
        row(
            label="中文标签变化不影响身份",
            product_id="product-01", trial_id="trial-01",
            group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-01",
        ),
        report_kind=ReportKind.A,
    )
    different = validate_report_row_payload(
        row(
            product_id="product-02", trial_id="trial-01",
            group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-01",
        ),
        report_kind=ReportKind.A,
    )
    assert first.row_id == relabeled.row_id
    assert first.row_id != different.row_id


def test_row_id_stable_across_sorting_filtering_and_format() -> None:
    rows = identity_rows()
    model = validate_report_view_model_payload(view(rows))
    original = tuple(r.row_id for r in model.rows)
    reversed_model = validate_report_view_model_payload(view(tuple(reversed(rows))))
    filtered = validate_report_view_model_payload(view([rows[0], rows[2]]))
    assert {r.row_id for r in reversed_model.rows} == set(original)
    assert {r.row_id for r in filtered.rows} == {original[0], original[2]}
    # 格式投影不改变行身份：同一个行集进入图表模块后 ID 原样保留。
    row_set = filtered_row_set(tuple(reversed(rows)))
    module = ChartTableModule(row_set=row_set)
    assert set(module.chart_row_ids) == set(original)


def test_row_requires_at_least_one_scientific_identity_field() -> None:
    with pytest.raises(ViewStateBoundaryError, match="身份不足"):
        validate_report_row_payload(
            row(label="只有中文标签没有科学身份"),
            report_kind=ReportKind.A,
        )


def test_row_rejects_free_form_row_id() -> None:
    free_form = row(product_id="product-01")
    free_form["row_id"] = "自由文本行ID"
    with pytest.raises(ViewStateBoundaryError, match="身份"):
        validate_report_row_payload(free_form, report_kind=ReportKind.A)


def test_standalone_row_validator_requires_frozen_page_in_report_catalog() -> None:
    """负例：独立行验证器必须携带报告上下文并强制冻结目录。

    公开行验证器不得绕过注册表：B/C 专属或目录外页面责任在任何报告
    上下文下都失败关闭；同一页面在不同报告上下文中按各自目录判定。
    """
    for page_id in ("baseline-demographics", "design-map", "自由文本页"):
        with pytest.raises(ViewStateBoundaryError, match="目录"):
            validate_report_row_payload(
                row(page=page_id, product_id="product-01", trial_id="trial-01"),
                report_kind=ReportKind.A,
            )
    # 正例：A 目录页面 + A 报告上下文通过。
    validated = validate_report_row_payload(
        row(product_id="product-01", trial_id="trial-01"),
        report_kind=ReportKind.A,
    )
    assert validated.page_responsibility_id == PAGE
    # A 的独立疗效－安全性矩阵责任页在 B 目录中不存在。
    with pytest.raises(ViewStateBoundaryError, match="目录"):
        validate_report_row_payload(
            row(page="matrix", product_id="product-01", trial_id="trial-01"),
            report_kind=ReportKind.B,
        )


def test_duplicate_scientific_identity_fails_closed() -> None:
    """负例：同一科学身份即使披露状态不同也是重复，失败关闭。"""
    rows = identity_rows()
    duplicated = row(
        label="同一身份的重复行",
        state="reported_zero",
        product_id="product-01", trial_id="trial-01",
        group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-01",
    )
    with pytest.raises(ViewStateBoundaryError, match="重复"):
        validate_report_view_model_payload(view((*rows, duplicated)))


def test_view_model_binds_rows_to_one_locked_snapshot_and_page() -> None:
    rows = identity_rows()
    model = validate_report_view_model_payload(view(rows))
    assert all(r.report_snapshot_id == model.report_snapshot_id for r in model.rows)
    assert all(r.page_responsibility_id == model.page_responsibility_id for r in model.rows)
    other_snapshot = row(
        snapshot="report-snapshot-其他快照",
        product_id="product-01", trial_id="trial-01",
        group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-09",
    )
    with pytest.raises(ViewStateBoundaryError, match="快照"):
        validate_report_view_model_payload(view((*rows, other_snapshot)))
    other_page = row(
        page="product-overview",
        product_id="product-01", trial_id="trial-01",
        group_id="group-01", endpoint_id="endpoint-01", timepoint_id="timepoint-09",
    )
    with pytest.raises(ViewStateBoundaryError, match="页面"):
        validate_report_view_model_payload(view((*rows, other_page)))


# ─── 字段限定行身份：事实字段名参与身份材料 ─────────────────────────────────


def test_row_id_qualifies_identity_field_names() -> None:
    """负例：仅按值推导会让 fact_id 与 claim_id 同值碰撞；字段名必须参与身份。"""
    assert derive_row_id(fact_id="x") != derive_row_id(claim_id="x")
    assert derive_row_id(product_id="x") != derive_row_id(trial_id="x")
    assert derive_row_id(group_id="x") != derive_row_id(endpoint_id="x")
    assert derive_row_id(event_id="x") != derive_row_id(timepoint_id="x")
    assert derive_row_id(fact_id="x") != derive_row_id(fact_id="x", claim_id="x")
    assert derive_row_id(fact_id="x") != derive_row_id(fact_id="y")
    assert derive_row_id(product_id="a", trial_id="b") != derive_row_id(
        product_id="b", trial_id="a"
    )


def test_row_id_is_stable_regardless_of_argument_order() -> None:
    """关键字顺序不是身份材料：字段按规范顺序拼接。"""
    first = derive_row_id(product_id="product-01", trial_id="trial-01")
    second = derive_row_id(trial_id="trial-01", product_id="product-01")
    assert first == second


# ─── 冻结目录页面责任权威（生产边界强制） ───────────────────────────────────


def test_view_model_requires_page_responsibility_in_frozen_catalog() -> None:
    """负例：A 视图使用 B/C 专属或目录外页面责任，即使不传注册表也必须失败。

    行与视图的页面责任保持一致（行内一致不构成绕过），只攻击目录权威。
    """
    for page_id in ("baseline-demographics", "design-map", "participant-flow", "自由文本页"):
        payload = view(
            tuple(row(page=page_id, **identity) for identity in _IDENTITY_SET)
        )
        payload["page_responsibility_id"] = page_id
        with pytest.raises(ViewStateBoundaryError, match="目录"):
            validate_report_view_model_payload(payload)


def test_view_model_rejects_cross_report_page_labels_without_registry_argument() -> None:
    """负例：A 报告行集被标成 B/C 专属页面（攻击不传注册表参数）。"""
    b_rows = tuple(row(page="baseline-demographics", **identity) for identity in _IDENTITY_SET)
    b_view = {
        "report_kind": "A",
        "page_responsibility_id": "baseline-demographics",
        "report_snapshot_id": SNAPSHOT,
        "report_version": "1.0",
        "rows": list(b_rows),
    }
    with pytest.raises(ViewStateBoundaryError, match="目录"):
        validate_report_view_model_payload(b_view)
    # 经生产行集边界：嵌入视图的页面责任同样必须属于冻结目录。
    payload = {"view": b_view, "rows": list(b_rows)}
    with pytest.raises(ChartTableBoundaryError, match="目录"):
        validate_filtered_row_set_payload(payload)


def test_view_model_accepts_every_frozen_a_page() -> None:
    """正例：A 冻结目录的全部静态页面责任都可作为 A 视图页面。"""
    from ci_workflow.reports.common.page_registry import PageRegistry

    registry = PageRegistry.load()
    for page in sorted(registry.catalog(ReportKind.A).pages, key=lambda p: p.id):
        page_id = page.id
        payload = view(
            tuple(row(page=page_id, **identity) for identity in _IDENTITY_SET)
        )
        payload["page_responsibility_id"] = page_id
        model = validate_report_view_model_payload(payload)
        assert model.page_responsibility_id == page_id


# ─── ChartTableModule / FilteredRowSet：单行集合同 ───────────────────────────


def test_chart_and_table_row_ids_derive_from_single_filtered_row_set() -> None:
    rows = identity_rows()
    row_set = filtered_row_set(rows)
    module = ChartTableModule(row_set=row_set)
    expected = tuple(sorted(r["row_id"] for r in rows))
    assert module.chart_row_ids == expected
    assert module.table_row_ids == expected
    assert module.chart_row_ids == module.table_row_ids


def test_module_accepts_only_one_row_set_and_rejects_separate_injection() -> None:
    """调用方不能分别注入图表行与完整表行：模型只接受唯一行集。"""
    assert set(ChartTableModule.model_fields) == {"row_set"}
    rows = identity_rows()
    payload = {
        "row_set": {
            "view": view(rows),
            "rows": list(rows),
        },
        "chart_rows": [r["row_id"] for r in rows],
        "table_rows": [r["row_id"] for r in rows],
    }
    with pytest.raises(ChartTableBoundaryError, match="Extra inputs"):
        validate_chart_table_module_payload(payload)


def test_filtered_row_set_must_stay_within_view_rows() -> None:
    rows = identity_rows()
    foreign = row(
        product_id="product-99", trial_id="trial-99",
        group_id="group-99", endpoint_id="endpoint-99", timepoint_id="timepoint-99",
    )
    payload = {"view": view(rows), "rows": [*rows, foreign]}
    with pytest.raises(ChartTableBoundaryError, match="作用域"):
        validate_filtered_row_set_payload(payload)


def test_empty_filtered_row_set_stays_empty_and_does_not_widen() -> None:
    row_set = filtered_row_set(())
    module = ChartTableModule(row_set=row_set)
    assert module.chart_row_ids == ()
    assert module.table_row_ids == ()
    assert row_set.row_set_digest is not None


def test_disclosed_missing_rows_are_preserved_in_both_sets() -> None:
    rows = identity_rows()
    assert {r["disclosure_state"] for r in rows} & {
        "not_reported",
        "not_publicly_disclosed",
        "below_reporting_threshold",
    }
    module = ChartTableModule(row_set=filtered_row_set(rows))
    assert len(module.chart_row_ids) == len(rows)
    assert len(module.table_row_ids) == len(rows)
    assert module.chart_row_ids == module.table_row_ids


def test_row_set_digest_is_order_independent() -> None:
    rows = identity_rows()
    first = filtered_row_set(rows)
    second = filtered_row_set(tuple(reversed(rows)))
    assert first.row_set_digest == second.row_set_digest


@pytest.mark.parametrize(
    "mutate,view_kwargs",
    [
        (lambda r: {**r, "disclosure_state": "reported_zero"}, {}),
        (lambda r: {**r, "disclosure_state": "not_publicly_disclosed"}, {}),
        (lambda r: {**r, "display_label_zh": "中文标签变化必须改变行集摘要"}, {}),
        (
            lambda r: {**r, "page_responsibility_id": "product-overview"},
            {"page": "product-overview"},
        ),
        (
            lambda r: {**r, "report_snapshot_id": "report-snapshot-另一锁定快照"},
            {"snapshot": "report-snapshot-另一锁定快照"},
        ),
    ],
    ids=["disclosure-zero", "disclosure-missing", "label", "page", "snapshot"],
)
def test_row_set_digest_covers_complete_canonical_row_content(
    mutate: Any, view_kwargs: dict[str, str]
) -> None:
    """负例：行集摘要必须覆盖完整规范行内容；任何内容变化都改变摘要。

    row_id 只由科学身份决定，因此只哈希 row ID 会放过标签/披露状态/
    页面/快照漂移——摘要必须哈希按行 ID 排序的完整规范行模型。
    """
    rows = identity_rows()
    base = filtered_row_set(rows)
    changed = tuple(mutate(dict(r)) for r in rows)
    payload = {"view": view(changed, **view_kwargs), "rows": list(changed)}
    other = validate_filtered_row_set_payload(payload)
    assert other.row_set_digest != base.row_set_digest
    # 图与表仍来自同一行集、模型级全等。
    module = ChartTableModule(row_set=other)
    assert module.chart_row_ids == module.table_row_ids


def test_filtered_row_set_rejects_drift_from_canonical_view_row() -> None:
    """负例：row_id 相同但披露状态/中文标签/快照/页面漂移的"重建行"必须拒绝。

    筛选行必须是规范视图行本体（模型级全等），不能只凭 row_id 通过；
    这是"行只引用身份、值必须经锁定快照查找"边界的关键机械绑定。
    """
    rows = identity_rows()
    canonical = rows[0]
    view_payload = view(rows)

    def drifted(**overrides: Any) -> dict[str, Any]:
        row_payload = dict(canonical)
        row_payload.update(overrides)
        return row_payload

    for mutation in (
        {"disclosure_state": "not_reported"},
        {"disclosure_state": "not_publicly_disclosed"},
        {"display_label_zh": "被篡改的中文标签"},
        {"report_snapshot_id": "report-snapshot-被替换快照"},
        {"page_responsibility_id": "product-overview"},
    ):
        payload = {"view": view_payload, "rows": [drifted(**mutation), rows[1], rows[2]]}
        with pytest.raises(ChartTableBoundaryError, match="全等"):
            validate_filtered_row_set_payload(payload)


def test_filtered_row_set_keeps_genuine_reorder_filter_and_empty() -> None:
    """正例：真实的重排/筛选/空筛选仍被允许，只有内容漂移被拒绝。"""
    rows = identity_rows()
    reordered = filtered_row_set(tuple(reversed(rows)))
    assert [r.row_id for r in reordered.rows] == [
        r["row_id"] for r in reversed(rows)
    ]
    subset = filtered_row_set((rows[0], rows[2]))
    assert [r.row_id for r in subset.rows] == [rows[0]["row_id"], rows[2]["row_id"]]
    assert filtered_row_set(()).rows == ()


# ─── PageRegistry：冻结目录与站点地图 ───────────────────────────────────────


def _catalog_yaml(report: str, pages: list[dict[str, Any]]) -> str:
    return yaml.safe_dump(
        {
            "contract_version": "1.0",
            "report": report,
            "pages": pages,
        },
        allow_unicode=True,
        sort_keys=False,
    )


def _page(
    page_id: str,
    *,
    route: str | None = None,
    title: str = "中文页面标题",
    navigation_group: str = "总览",
    responsibility: str = "呈现核心内容",
) -> dict[str, Any]:
    return {
        "id": page_id,
        "route": route or f"/a/{page_id}",
        "title": title,
        "navigation_group": navigation_group,
        "responsibility": responsibility,
        "visuals": ["结构分布图"],
        "complete_table": True,
        "filter_profiles": ["a-overview"],
        "evidence_drawer_profile": "common-clinical",
    }


def test_registry_loads_frozen_abc_catalogs_preserving_chinese_labels() -> None:
    registry = PageRegistry.load()
    expected_counts = {ReportKind.A: 11, ReportKind.B: 20, ReportKind.C: 12}
    for kind, count in expected_counts.items():
        catalog = registry.catalog(kind)
        assert len(catalog.pages) == count
        for page in catalog.pages:
            assert page.title_zh
            assert any("\u4e00" <= ch <= "\u9fff" for ch in page.title_zh)
            assert page.route == f"/{kind.value.casefold()}/{page.id}"


def test_registry_loads_packaged_catalog_layout_without_repo_docs() -> None:
    """包内数据布局（随轮分发，位于模块同目录）可直接加载全部三个报告。

    安装布局中不存在仓库根 ``docs/architecture``，注册表必须能从模块
    目录解析同一组冻结目录；该目录与仓库根目录逐字一致由合同测试保证。
    """
    from pathlib import Path

    packaged_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "ci_workflow" / "reports" / "common" / "page-catalogs"
    )
    registry = PageRegistry._load_from_dir(packaged_dir)
    assert [c.report.value for c in registry.catalogs] == ["A", "B", "C"]
    assert len(registry.catalog(ReportKind.A).pages) == 11
    assert len(registry.catalog(ReportKind.B).pages) == 20
    assert len(registry.catalog(ReportKind.C).pages) == 12
    sitemap = registry.sitemap(
        ReportKind.A, product_ids=("product-01",), trial_ids=("trial-01",)
    )
    assert "/a/products/product-01" in sitemap


def test_load_rejects_caller_selected_root_and_helper_is_private() -> None:
    """负例/API：公开 ``PageRegistry.load`` 不接受调用方选择目录。

    任意 root 选择从公开生产 API 移除；测试用目录只经私有
    ``_load_from_dir`` 加载，该辅助不导出且生产验证器不调用。
    """
    import inspect

    from ci_workflow.reports import common as reports_common

    assert "root" not in inspect.signature(PageRegistry.load).parameters
    with pytest.raises(TypeError):
        PageRegistry.load(root=Path("."))
    assert "_load_from_dir" not in reports_common.__all__
    assert not hasattr(reports_common, "_load_from_dir")
    # 私有辅助仍能加载包内数据目录（内部/测试专用）。
    packaged_dir = (
        Path(__file__).resolve().parents[3]
        / "src" / "ci_workflow" / "reports" / "common" / "page-catalogs"
    )
    loaded = PageRegistry._load_from_dir(packaged_dir)
    assert [c.report.value for c in loaded.catalogs] == ["A", "B", "C"]


def test_production_load_and_validators_never_touch_test_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """负例/隔离：monkeypatch 测试辅助 ``_load_from_dir`` 使其抛错。

    生产 ``PageRegistry.load()`` 与公开生产验证器必须仍从冻结目录正常
    工作——证明生产调用链（load → 生产专用私有路径）不经过测试覆盖点。
    """

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("测试辅助 _load_from_dir 被生产路径调用")

    monkeypatch.setattr(PageRegistry, "_load_from_dir", classmethod(_boom))
    registry = PageRegistry.load()
    assert [c.report.value for c in registry.catalogs] == ["A", "B", "C"]
    # 公开生产验证器（视图模型/行集/图表模块）全部工作。
    model = validate_report_view_model_payload(view(identity_rows()))
    assert model.page_responsibility_id == PAGE
    rows = identity_rows()
    row_set = validate_filtered_row_set_payload(
        {"view": view(rows), "rows": list(rows)}
    )
    module = validate_chart_table_module_payload(
        {"row_set": row_set.model_dump(mode="json")}
    )
    assert module.chart_row_ids == module.table_row_ids


def _catalog_dir(tmp_path: Path) -> Path:
    target = tmp_path / "docs" / "architecture" / "page-catalogs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_minimal_b_c(tmp_path: Path) -> None:
    """B/C 最小合法目录：动态详情责任引用的页面必须存在。"""
    target = _catalog_dir(tmp_path)
    (target / "B.yaml").write_text(
        _catalog_yaml(
            "B",
            [
                _page("overview", route="/b/overview"),
                _page("product-trial-profiles", route="/b/product-trial-profiles"),
            ],
        ),
        encoding="utf-8",
    )
    (target / "C.yaml").write_text(
        _catalog_yaml(
            "C",
            [
                _page("overview", route="/c/overview"),
                _page("trial-profile", route="/c/trial-profile"),
            ],
        ),
        encoding="utf-8",
    )


def test_registry_rejects_unknown_report_kind(tmp_path: Path) -> None:
    target = _catalog_dir(tmp_path)
    (target / "D.yaml").write_text(
        _catalog_yaml("D", [_page("overview", route="/d/overview")]),
        encoding="utf-8",
    )
    with pytest.raises(PageRegistryError, match="报告类型"):
        PageRegistry._load_from_dir(target)


def test_registry_rejects_duplicate_or_free_form_routes(tmp_path: Path) -> None:
    target = _catalog_dir(tmp_path)
    _write_minimal_b_c(tmp_path)
    pages = [
        _page("overview", route="/a/overview"),
        _page("overview", route="/a/overview", title="重复页面"),
    ]
    (target / "A.yaml").write_text(_catalog_yaml("A", pages), encoding="utf-8")
    with pytest.raises(PageRegistryError, match="重复"):
        PageRegistry._load_from_dir(target)
    pages = [_page("overview", route="/a/自定义路由")]
    (target / "A.yaml").write_text(_catalog_yaml("A", pages), encoding="utf-8")
    with pytest.raises(PageRegistryError, match="路由"):
        PageRegistry._load_from_dir(target)


def test_registry_rejects_catalog_report_mismatch(tmp_path: Path) -> None:
    target = _catalog_dir(tmp_path)
    (target / "A.yaml").write_text(
        _catalog_yaml("B", [_page("overview", route="/b/overview")]),
        encoding="utf-8",
    )
    with pytest.raises(PageRegistryError, match="目录"):
        PageRegistry._load_from_dir(target)


def test_registry_separates_static_and_dynamic_responsibilities() -> None:
    registry = PageRegistry.load()
    for kind in ReportKind:
        catalog = registry.catalog(kind)
        static_ids = {p.id for p in catalog.pages}
        assert catalog.dynamic_routes
        for spec in catalog.dynamic_routes:
            assert spec.page_responsibility_id in static_ids
            assert spec.identity_field in spec.route_template
            assert (
                spec.route_template
                != next(p.route for p in catalog.pages if p.id == spec.page_responsibility_id)
            )
    a = registry.catalog(ReportKind.A)
    assert {s.route_kind for s in a.dynamic_routes} == {"product_detail"}
    c = registry.catalog(ReportKind.C)
    assert {s.route_kind for s in c.dynamic_routes} == {"trial_detail"}


def test_sitemap_expands_every_supplied_product_and_trial_deterministically() -> None:
    registry = PageRegistry.load()
    products = ("product-03", "product-01", "product-02")
    trials = ("trial-02", "trial-01")
    sitemap = registry.sitemap(ReportKind.A, product_ids=products, trial_ids=trials)
    static = tuple(
        p.route
        for p in sorted(registry.catalog(ReportKind.A).pages, key=lambda p: p.id)
    )
    assert sitemap[: len(static)] == static
    assert "/a/products/product-01" in sitemap
    assert "/a/products/product-02" in sitemap
    assert "/a/products/product-03" in sitemap
    assert "/a/trials/trial-01" not in sitemap
    assert "/a/trials/trial-02" not in sitemap
    assert len(sitemap) == len(static) + 3
    assert sitemap == registry.sitemap(ReportKind.A, product_ids=products, trial_ids=trials)
    # C 只有试验详情动态责任：提供的产品不产生产品路由。
    c_sitemap = registry.sitemap(ReportKind.C, product_ids=products, trial_ids=trials)
    assert "/c/products/product-01" not in c_sitemap
    assert "/c/trials/trial-01" in c_sitemap


def test_sitemap_rejects_duplicate_or_unsafe_slugs() -> None:
    registry = PageRegistry.load()
    with pytest.raises(PageRegistryError, match="重复"):
        registry.sitemap(ReportKind.A, product_ids=("product-01", "product-01"))
    with pytest.raises(PageRegistryError, match="路径"):
        registry.sitemap(ReportKind.A, product_ids=("product/../01",))


def test_static_page_model_rejects_empty_chinese_title() -> None:
    with pytest.raises(ValueError, match="中文"):
        StaticPage(
            id="overview",
            route="/a/overview",
            title_zh="",
            navigation_group_zh="总览",
            responsibility_zh="呈现核心内容",
            visuals=("结构分布图",),
            complete_table=True,
            filter_profiles=("a-overview",),
            evidence_drawer_profile="common-clinical",
        )
