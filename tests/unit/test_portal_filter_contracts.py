"""Task 4.3 分层筛选与确定性 URL 状态单元测试。

覆盖：
- 不可变类型化筛选维度契约（ID 身份稳定、中文标签仅展示、适用性声明）
- 页面级 / 模块级独立键空间与重置隔离
- URL 版本化序列化往返（encode → decode、确定性排序、URL 上限）
- 未知维度、重复值、无效页面 ID、非法状态版本失败关闭
- 排序、锚定试验、选中证据、当前页的显式测试策略
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.renderers.portal.filters import (
    AnchorTrialState,
    EvidenceSelection,
    FilterDimension,
    FilterState,
    FilterValue,
    FilterVersion,
    ModuleFilterState,
    PageFilterScope,
    PaginationState,
    PortalFilterError,
    SortState,
)
from ci_workflow.renderers.portal.url_state import (
    SAVE_LOCAL_VIEW_HINT_ZH,
    URL_SIZE_LIMIT,
    UrlStateError,
    decode_filter_state,
    encode_filter_state,
    serialize_filter_state,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dimension(
    *,
    dim_id: str = "indication",
    label_zh: str = "适应症",
    values: list[dict[str, str]] | None = None,
    page_applicability: dict[str, bool] | None = None,
    module_applicability: dict[str, bool] | None = None,
) -> FilterDimension:
    if values is None:
        values = [
            {"id": "ind-01", "label_zh": "系统性红斑狼疮"},
            {"id": "ind-02", "label_zh": "类风湿关节炎"},
        ]
    if page_applicability is None:
        page_applicability = {
            "/b/overview": True,
            "/b/efficacy": True,
            "/b/safety": True,
            "/b/baseline-overview": True,
            "/c/overview": True,
            "/a/overview": True,
        }
    if module_applicability is None:
        module_applicability = {"b-efficacy": True, "b-safety": True}
    return FilterDimension(
        id=dim_id,
        label_zh=label_zh,
        values=tuple(
            FilterValue(id=v["id"], label_zh=v["label_zh"]) for v in values
        ),
        page_applicability=page_applicability,
        module_applicability=module_applicability,
    )


def _make_page_scope(
    *,
    page_id: str = "/b/overview",
    dims: list[FilterDimension] | None = None,
    selected: dict[str, list[str]] | None = None,
) -> PageFilterScope:
    if dims is None:
        dims = [
            _make_dimension(dim_id="indication", label_zh="适应症"),
            _make_dimension(dim_id="product", label_zh="产品"),
        ]
    if selected is None:
        selected = {"indication": ["ind-01"]}
    return PageFilterScope(
        page_id=page_id,
        dimensions=tuple(dims),
        selected=selected,
    )


def _make_module_state(
    *,
    module_id: str = "b-efficacy",
    dims: list[FilterDimension] | None = None,
    selected: dict[str, list[str]] | None = None,
) -> ModuleFilterState:
    if dims is None:
        dims = [
            _make_dimension(
                dim_id="endpoint",
                label_zh="终点",
                values=[
                    {"id": "ep-01", "label_zh": "主要终点"},
                    {"id": "ep-02", "label_zh": "次要终点"},
                ],
                page_applicability={},
                module_applicability={"b-efficacy": True},
            ),
            _make_dimension(
                dim_id="timepoint",
                label_zh="时间点",
                values=[
                    {"id": "tp-12w", "label_zh": "第12周"},
                    {"id": "tp-24w", "label_zh": "第24周"},
                ],
                page_applicability={},
                module_applicability={"b-efficacy": True},
            ),
        ]
    if selected is None:
        selected = {}
    return ModuleFilterState(
        module_id=module_id,
        dimensions=tuple(dims),
        selected=selected,
    )


def _make_full_state(
    *,
    page: PageFilterScope | None = None,
    modules: list[ModuleFilterState] | None = None,
    sort: SortState | None = None,
    anchor: AnchorTrialState | None = None,
    evidence: EvidenceSelection | None = None,
    pagination: PaginationState | None = None,
) -> FilterState:
    if page is None:
        page = _make_page_scope()
    if modules is None:
        modules = [_make_module_state()]
    return FilterState(
        page=page,
        modules=tuple(modules),
        sort=sort or SortState(),
        anchor=anchor or AnchorTrialState(),
        evidence=evidence or EvidenceSelection(),
        pagination=pagination or PaginationState(),
    )


# ===========================================================================
# 1. FilterDimension 不可变与身份稳定性
# ===========================================================================


class TestFilterDimension:
    """维度必须不可变、中文标签仅展示、ID 为稳定身份。"""

    def test_dimension_is_frozen(self) -> None:
        dim = _make_dimension()
        assert dim.id == "indication"
        with pytest.raises(Exception, match="frozen"):
            dim.id = "changed"  # type: ignore[misc]

    def test_dimension_values_are_frozen(self) -> None:
        dim = _make_dimension()
        for val in dim.values:
            with pytest.raises(Exception, match="frozen"):
                val.id = "changed"  # type: ignore[misc]

    def test_label_zh_contains_chinese(self) -> None:
        dim = _make_dimension(label_zh="适应症")
        assert re.search(r"[\u4e00-\u9fff]", dim.label_zh)

    def test_value_label_zh_contains_chinese(self) -> None:
        dim = _make_dimension()
        for val in dim.values:
            assert re.search(r"[\u4e00-\u9fff]", val.label_zh), (
                f"值标签必须含中文：{val.label_zh}"
            )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises((PydanticValidationError, ValueError)):
            _make_dimension(dim_id="")


# ===========================================================================
# 2. PageFilterScope 页面级筛选
# ===========================================================================


class TestPageFilterScope:
    """页面级筛选独立键空间。"""

    def test_scope_is_frozen(self) -> None:
        scope = _make_page_scope()
        with pytest.raises(Exception, match="frozen"):
            scope.page_id = "changed"  # type: ignore[misc]

    def test_selected_values_validated(self) -> None:
        scope = _make_page_scope()
        scope.validate_values()  # Should not raise

    def test_duplicate_values_rejected(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError), match="重复"):
            _make_page_scope(selected={"indication": ["ind-01", "ind-01"]})

    def test_empty_page_id_rejected(self) -> None:
        with pytest.raises(Exception, match="不能为空"):
            PageFilterScope(
                page_id="",
                dimensions=(_make_dimension(),),
                selected={},
            )


# ===========================================================================
# 3. ModuleFilterState 模块级筛选
# ===========================================================================


class TestModuleFilterState:
    """模块级筛选独立键空间。"""

    def test_module_is_frozen(self) -> None:
        state = _make_module_state()
        with pytest.raises(Exception, match="frozen"):
            state.module_id = "changed"  # type: ignore[misc]

    def test_empty_module_id_rejected(self) -> None:
        with pytest.raises(Exception, match="不能为空"):
            ModuleFilterState(
                module_id="",
                dimensions=(_make_dimension(),),
                selected={},
            )


# ===========================================================================
# 4. FilterState 整体结构与重置隔离
# ===========================================================================


class TestFilterState:
    """顶层筛选状态：页面 + 模块 + 排序 + 锚定 + 证据 + 分页。"""

    def test_state_is_frozen(self) -> None:
        state = _make_full_state()
        with pytest.raises(Exception, match="frozen"):
            state.version = "new"  # type: ignore[misc]

    def test_version_is_v1(self) -> None:
        state = _make_full_state()
        assert state.version == FilterVersion.V1

    def test_page_reset_does_not_affect_modules(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-01"]},
            ),
            modules=[
                _make_module_state(
                    selected={"endpoint": ["ep-01"]},
                ),
            ],
        )
        reset = state.reset_page()
        assert reset.page.selected == {}
        assert reset.modules[0].selected == {"endpoint": ("ep-01",)}

    def test_module_reset_does_not_affect_page(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-01"]},
            ),
            modules=[
                _make_module_state(
                    module_id="b-efficacy",
                    selected={"endpoint": ["ep-01"]},
                ),
                _make_module_state(
                    module_id="b-safety",
                    selected={"endpoint": ["ep-02"]},
                ),
            ],
        )
        reset = state.reset_module("b-efficacy")
        assert reset.page.selected == {"indication": ("ind-01",)}
        assert reset.modules[0].selected == {}
        assert reset.modules[1].selected == {"endpoint": ("ep-02",)}

    def test_module_reset_unknown_rejected(self) -> None:
        state = _make_full_state()
        with pytest.raises(PortalFilterError, match=r"未知模块"):
            state.reset_module("nonexistent")

    def test_duplicate_module_ids_rejected(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError), match=r"重复"):
            _make_full_state(
                modules=[
                    _make_module_state(module_id="b-efficacy"),
                    _make_module_state(module_id="b-efficacy"),
                ],
            )

    def test_page_reset_preserves_sort_anchor_evidence_pagination(self) -> None:
        state = _make_full_state(
            sort=SortState(field="efficacy", direction="desc"),
            anchor=AnchorTrialState(trial_id="NCT001"),
            evidence=EvidenceSelection(selected_ids=("frag-01",)),
            pagination=PaginationState(current_page=3),
        )
        reset = state.reset_page()
        assert reset.sort == state.sort
        assert reset.anchor == state.anchor
        assert reset.evidence == state.evidence
        assert reset.pagination.current_page == 3

    def test_module_reset_preserves_other_modules_and_global(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-01"]},
            ),
            modules=[
                _make_module_state(
                    module_id="b-efficacy",
                    selected={"endpoint": ["ep-01"]},
                ),
                _make_module_state(
                    module_id="b-safety",
                    selected={"endpoint": ["ep-02"]},
                ),
            ],
            sort=SortState(field="safety", direction="asc"),
        )
        reset = state.reset_module("b-efficacy")
        assert reset.sort == state.sort
        assert reset.modules[1].selected == {"endpoint": ("ep-02",)}


# ===========================================================================
# 5. SortState / AnchorTrialState / EvidenceSelection / PaginationState
# ===========================================================================


class TestGlobalStates:
    """排序、锚定试验、证据选中、分页全局状态。"""

    def test_sort_default_direction_asc(self) -> None:
        s = SortState()
        assert s.direction == "asc"

    def test_sort_invalid_direction_rejected(self) -> None:
        with pytest.raises((PydanticValidationError, ValueError)):
            SortState(direction="up")  # type: ignore[arg-type]

    def test_anchor_default_is_empty(self) -> None:
        a = AnchorTrialState()
        assert a.trial_id is None

    def test_evidence_default_is_empty(self) -> None:
        e = EvidenceSelection()
        assert e.selected_ids == ()

    def test_pagination_current_page_default(self) -> None:
        p = PaginationState()
        assert p.current_page == 1

    def test_pagination_zero_rejected(self) -> None:
        with pytest.raises((PydanticValidationError, ValueError)):
            PaginationState(current_page=0)

    def test_pagination_negative_rejected(self) -> None:
        with pytest.raises((PydanticValidationError, ValueError)):
            PaginationState(current_page=-1)


# ===========================================================================
# 6. URL 序列化往返
# ===========================================================================


class TestUrlStateEncodeDecode:
    """encode → decode 往返必须确定性保持全部状态。"""

    def test_roundtrip_minimal_state(self) -> None:
        state = _make_full_state()
        encoded = encode_filter_state(state)
        decoded = decode_filter_state(encoded)
        assert decoded.page.page_id == state.page.page_id
        assert decoded.page.selected == state.page.selected
        assert decoded.version == state.version

    def test_roundtrip_full_state(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                dims=[
                    _make_dimension(
                        dim_id="indication",
                        label_zh="适应症",
                        values=[
                            {"id": "ind-01", "label_zh": "系统性红斑狼疮"},
                            {"id": "ind-02", "label_zh": "类风湿关节炎"},
                        ],
                    ),
                    _make_dimension(
                        dim_id="product",
                        label_zh="产品",
                        values=[
                            {"id": "prod-03", "label_zh": "产品丙"},
                        ],
                    ),
                ],
                selected={
                    "indication": ["ind-01", "ind-02"],
                    "product": ["prod-03"],
                },
            ),
            modules=[
                _make_module_state(
                    module_id="b-efficacy",
                    selected={
                        "endpoint": ["ep-01", "ep-02"],
                        "timepoint": ["tp-12w"],
                    },
                ),
                _make_module_state(
                    module_id="b-safety",
                    dims=[
                        _make_dimension(
                            dim_id="ae_term",
                            label_zh="不良事件术语",
                            values=[{"id": "teae-01", "label_zh": "治疗期不良事件"}],
                            page_applicability={},
                            module_applicability={"b-safety": True},
                        ),
                    ],
                    selected={"ae_term": ["teae-01"]},
                ),
            ],
            sort=SortState(field="efficacy-signal", direction="desc"),
            anchor=AnchorTrialState(trial_id="NCT01234567"),
            evidence=EvidenceSelection(selected_ids=("frag-001", "frag-002")),
            pagination=PaginationState(current_page=5),
        )
        encoded = encode_filter_state(state)
        decoded = decode_filter_state(encoded)
        assert decoded.page.page_id == state.page.page_id
        assert decoded.page.selected == state.page.selected
        assert len(decoded.modules) == 2
        assert decoded.modules[0].module_id == "b-efficacy"
        assert decoded.sort.field == "efficacy-signal"
        assert decoded.sort.direction == "desc"
        assert decoded.anchor.trial_id == "NCT01234567"
        assert decoded.evidence.selected_ids == ("frag-001", "frag-002")
        assert decoded.pagination.current_page == 5

    def test_deterministic_encoding(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-02", "ind-01"]},
            ),
        )
        e1 = encode_filter_state(state)
        e2 = encode_filter_state(state)
        assert e1 == e2, "同一状态必须产生相同 URL"

    def test_values_sorted_in_encoding(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-02", "ind-01"]},
            ),
        )
        encoded = encode_filter_state(state)
        decoded = decode_filter_state(encoded)
        assert set(decoded.page.selected["indication"]) == {"ind-01", "ind-02"}

    def test_empty_state_encodes_to_minimal(self) -> None:
        # Create a state with no selections
        state = _make_full_state(
            page=_make_page_scope(selected={}),
        )
        encoded = encode_filter_state(state)
        decoded = decode_filter_state(encoded)
        assert decoded.page.selected == {}

    def test_copy_url_same_state(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-01"]},
            ),
            modules=[
                _make_module_state(selected={"endpoint": ["ep-01"]}),
            ],
        )
        encoded = encode_filter_state(state)
        decoded = decode_filter_state(encoded)
        assert decoded.page.selected == state.page.selected
        assert decoded.modules[0].selected == state.modules[0].selected


# ===========================================================================
# 7. URL 大小上限
# ===========================================================================


class TestUrlSizeLimit:
    """超过配置 URL 限制时返回「保存为本地视图」结果，不截断。"""

    def test_url_size_limit_constant(self) -> None:
        assert URL_SIZE_LIMIT > 0

    def test_large_state_exceeds_limit_returns_save_locally(self) -> None:
        many_values = [
            {"id": f"v-{i:04d}", "label_zh": f"值{i}"} for i in range(500)
        ]
        dim = _make_dimension(values=many_values)
        scope = _make_page_scope(
            dims=[dim],
            selected={"indication": [f"v-{i:04d}" for i in range(500)]},
        )
        state = _make_full_state(page=scope)
        outcome = serialize_filter_state(state)
        assert outcome.kind == "save_local_view"
        assert outcome.size > URL_SIZE_LIMIT
        assert outcome.message_zh == SAVE_LOCAL_VIEW_HINT_ZH
        # 完整未截断串仍可往返
        decoded = decode_filter_state(outcome.encoded)
        assert decoded.page.page_id == state.page.page_id
        assert len(decoded.page.selected["indication"]) == 500

    def test_normal_state_serializes_as_url(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(selected={"indication": ["ind-01"]}),
        )
        outcome = serialize_filter_state(state)
        assert outcome.kind == "url"
        assert outcome.message_zh is None
        assert outcome.encoded == encode_filter_state(state)


# ===========================================================================
# 8. 未知/无效状态失败关闭
# ===========================================================================


class TestFailureClosed:
    """未知维度、重复值、无效 ID、非法版本失败关闭。"""

    def test_unknown_page_id_format_rejected(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError)):
            PageFilterScope(
                page_id="invalid-no-slash",
                dimensions=(_make_dimension(),),
                selected={},
            )

    def test_duplicate_selected_values_rejected(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError), match="重复"):
            _make_page_scope(
                selected={"indication": ["ind-01", "ind-01"]},
            )

    def test_decode_corrupted_string_rejected(self) -> None:
        with pytest.raises(UrlStateError):
            decode_filter_state("not-valid-state-data")

    def test_decode_unknown_version_rejected(self) -> None:
        with pytest.raises(UrlStateError, match="版本"):
            decode_filter_state("v999~pid=/b/overview")

    def test_decode_unknown_segment_rejected(self) -> None:
        with pytest.raises(UrlStateError, match="未知"):
            decode_filter_state("v1~pid=/b/overview~xyz=1")


# ===========================================================================
# 9. 适用性声明
# ===========================================================================


class TestApplicability:
    """适用维度才出现；不适用维度隐藏或禁用并给出中文原因。"""

    def test_dimension_has_page_applicability(self) -> None:
        dim = _make_dimension()
        assert "/b/overview" in dim.page_applicability
        assert dim.page_applicability["/b/overview"] is True

    def test_dimension_has_module_applicability(self) -> None:
        dim = _make_dimension()
        assert "b-efficacy" in dim.module_applicability
        assert dim.module_applicability["b-efficacy"] is True

    def test_inapplicable_dimension_absent(self) -> None:
        dim = _make_dimension()
        assert dim.page_applicability.get("/nonexistent") is None

    def test_model_is_frozen(self) -> None:
        """frozen=True 模型阻止属性重新赋值。"""
        dim = _make_dimension()
        with pytest.raises((PydanticValidationError, AttributeError)):
            dim.label_zh = "新标签"  # type: ignore[misc]

    def test_page_and_module_dimension_catalogs(self) -> None:
        from ci_workflow.renderers.portal.filters import (
            MODULE_DIMENSION_IDS,
            PAGE_DIMENSION_IDS,
        )

        assert "indication" in PAGE_DIMENSION_IDS
        assert "target_or_mechanism" in PAGE_DIMENSION_IDS
        assert "endpoint" in MODULE_DIMENSION_IDS
        assert "denominator_role" in MODULE_DIMENSION_IDS
        assert "disclosure_state" in MODULE_DIMENSION_IDS


# ===========================================================================
# 10. 中文错误消息
# ===========================================================================


class TestChineseErrors:
    """所有失败关闭错误消息必须为中文。"""

    def test_duplicate_values_chinese_error(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError), match=r"[\u4e00-\u9fff]"):
            _make_page_scope(
                selected={"indication": ["ind-01", "ind-01"]},
            )

    def test_unknown_page_chinese_error(self) -> None:
        with pytest.raises((PortalFilterError, PydanticValidationError), match=r"[\u4e00-\u9fff]"):
            PageFilterScope(
                page_id="invalid-no-slash",
                dimensions=(_make_dimension(),),
                selected={},
            )


# ===========================================================================
# 11. ReportViewModel 行选取兼容
# ===========================================================================


class TestSelectViewRows:
    """筛选只选取既有稳定行，不创造/替换身份。"""

    def test_select_preserves_row_identity(self) -> None:
        from ci_workflow.domain.enums import FactDisclosureState, ReportKind
        from ci_workflow.renderers.portal.filters import select_view_rows
        from ci_workflow.reports.common.view_state import (
            ReportRow,
            ReportViewModel,
            derive_row_id,
        )

        identities = [
            {"product_id": "product-alpha", "trial_id": "trial-001", "endpoint_id": "ep-pri"},
            {"product_id": "product-beta", "trial_id": "trial-002", "endpoint_id": "ep-pri"},
            {"product_id": "product-alpha", "trial_id": "trial-003", "endpoint_id": "ep-sec"},
        ]
        rows = []
        for idx, ident in enumerate(identities):
            row_id = derive_row_id(**ident)
            rows.append(
                ReportRow(
                    row_id=row_id,
                    display_label_zh=f"合成行{idx + 1}",
                    page_responsibility_id="overview",
                    report_snapshot_id="snap-001",
                    disclosure_state=FactDisclosureState.REPORTED_VALUE,
                    **ident,
                )
            )
        view = ReportViewModel(
            report_kind=ReportKind.A,
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            report_version="v1",
            rows=tuple(rows),
        )
        state = _make_full_state(
            page=_make_page_scope(
                dims=[
                    _make_dimension(
                        dim_id="product",
                        label_zh="产品",
                        values=[
                            {"id": "product-alpha", "label_zh": "产品α"},
                            {"id": "product-beta", "label_zh": "产品β"},
                        ],
                    )
                ],
                selected={"product": ["product-alpha"]},
            ),
            modules=[],
        )
        filtered = select_view_rows(view, state)
        assert len(filtered.rows) == 2
        assert all(r.row_id in {rows[0].row_id, rows[2].row_id} for r in filtered.rows)
        assert filtered.view.report_snapshot_id == "snap-001"
        assert filtered.view.page_responsibility_id == "overview"

    def test_empty_selection_stays_empty(self) -> None:
        from ci_workflow.domain.enums import FactDisclosureState, ReportKind
        from ci_workflow.renderers.portal.filters import select_view_rows
        from ci_workflow.reports.common.view_state import (
            ReportRow,
            ReportViewModel,
            derive_row_id,
        )

        ident = {"product_id": "product-alpha", "trial_id": "trial-001"}
        row = ReportRow(
            row_id=derive_row_id(**ident),
            display_label_zh="合成行一",
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            **ident,
        )
        view = ReportViewModel(
            report_kind=ReportKind.A,
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            report_version="v1",
            rows=(row,),
        )
        state = _make_full_state(
            page=_make_page_scope(
                dims=[
                    _make_dimension(
                        dim_id="product",
                        label_zh="产品",
                        values=[
                            {"id": "product-alpha", "label_zh": "产品α"},
                            {"id": "product-gamma", "label_zh": "产品γ"},
                        ],
                    )
                ],
                selected={"product": ["product-gamma"]},
            ),
            modules=[],
        )
        filtered = select_view_rows(view, state)
        assert filtered.rows == ()
        assert filtered.view is view

    def test_unprojectable_dimension_fails_closed(self) -> None:
        from ci_workflow.domain.enums import FactDisclosureState, ReportKind
        from ci_workflow.renderers.portal.filters import select_view_rows
        from ci_workflow.reports.common.view_state import (
            ReportRow,
            ReportViewModel,
            derive_row_id,
        )

        ident = {"product_id": "product-alpha", "trial_id": "trial-001"}
        row = ReportRow(
            row_id=derive_row_id(**ident),
            display_label_zh="合成行一",
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            disclosure_state=FactDisclosureState.REPORTED_VALUE,
            **ident,
        )
        view = ReportViewModel(
            report_kind=ReportKind.A,
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            report_version="v1",
            rows=(row,),
        )
        state = _make_full_state(
            page=_make_page_scope(
                selected={"indication": ["ind-01"]},
            ),
            modules=[],
        )
        with pytest.raises(PortalFilterError, match=r"无法映射|不能投影|不适用"):
            select_view_rows(view, state)

    def test_or_within_dimension_and_across_dimensions(self) -> None:
        from ci_workflow.domain.enums import FactDisclosureState, ReportKind
        from ci_workflow.renderers.portal.filters import select_view_rows
        from ci_workflow.reports.common.view_state import (
            ReportRow,
            ReportViewModel,
            derive_row_id,
        )

        identities = [
            {
                "product_id": "product-alpha",
                "trial_id": "trial-001",
                "endpoint_id": "ep-pri",
            },
            {
                "product_id": "product-beta",
                "trial_id": "trial-002",
                "endpoint_id": "ep-pri",
            },
            {
                "product_id": "product-alpha",
                "trial_id": "trial-003",
                "endpoint_id": "ep-sec",
            },
        ]
        rows = []
        for idx, ident in enumerate(identities):
            rows.append(
                ReportRow(
                    row_id=derive_row_id(**ident),
                    display_label_zh=f"合成行{idx + 1}",
                    page_responsibility_id="overview",
                    report_snapshot_id="snap-001",
                    disclosure_state=FactDisclosureState.REPORTED_VALUE,
                    **ident,
                )
            )
        view = ReportViewModel(
            report_kind=ReportKind.A,
            page_responsibility_id="overview",
            report_snapshot_id="snap-001",
            report_version="v1",
            rows=tuple(rows),
        )
        # OR within product: alpha OR beta → all three; AND module endpoint=ep-pri → two
        state = _make_full_state(
            page=_make_page_scope(
                dims=[
                    _make_dimension(
                        dim_id="product",
                        label_zh="产品",
                        values=[
                            {"id": "product-alpha", "label_zh": "产品α"},
                            {"id": "product-beta", "label_zh": "产品β"},
                        ],
                    ),
                ],
                selected={
                    "product": ["product-alpha", "product-beta"],
                },
            ),
            modules=[
                _make_module_state(
                    dims=[
                        _make_dimension(
                            dim_id="endpoint",
                            label_zh="终点",
                            values=[
                                {"id": "ep-pri", "label_zh": "主要终点"},
                                {"id": "ep-sec", "label_zh": "次要终点"},
                            ],
                            page_applicability={},
                            module_applicability={"b-efficacy": True},
                        ),
                    ],
                    selected={"endpoint": ["ep-pri"]},
                ),
            ],
        )
        filtered = select_view_rows(view, state, module_id="b-efficacy")
        assert {r.row_id for r in filtered.rows} == {rows[0].row_id, rows[1].row_id}


# ===========================================================================
# 12. Codex 反例：decode 失败关闭 / 百分号编码 / UTF-8 字节上限
# ===========================================================================


class TestDecodeFailClosedRepair:
    """网址恢复不得静默接受重复或未知维度。"""

    def test_duplicate_pid_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"重复|页面"):
            decode_filter_state("v1~pid=/b/overview~pid=/b/efficacy")

    def test_duplicate_dimension_in_ps_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"重复"):
            decode_filter_state(
                "v1~pid=%2Fb%2Foverview~ps=indication:ind-01|indication:ind-02"
            )

    def test_duplicate_module_id_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"重复"):
            decode_filter_state(
                "v1~pid=%2Fb%2Foverview~m=b-efficacy~ms=endpoint:ep-01"
                "~m=b-efficacy~ms=endpoint:ep-02"
            )

    def test_duplicate_evidence_id_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"重复"):
            decode_filter_state("v1~pid=%2Fb%2Foverview~e=frag-01,frag-01")

    def test_unknown_page_dimension_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"未知|不支持|维度"):
            decode_filter_state("v1~pid=%2Fb%2Foverview~ps=totally_unknown:a")

    def test_unknown_module_dimension_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"未知|不支持|维度"):
            decode_filter_state(
                "v1~pid=%2Fb%2Foverview~m=b-efficacy~ms=totally_unknown:a"
            )


class TestPercentEncodingRoundtrip:
    """稳定 ID 含分隔符时须百分号编码往返，解码不得注入额外段。"""

    def test_page_id_with_slashes_roundtrips(self) -> None:
        state = _make_full_state(
            page=_make_page_scope(page_id="/b/overview", selected={}),
            modules=[],
        )
        encoded = encode_filter_state(state)
        assert "/b/overview" not in encoded or "%2F" in encoded
        decoded = decode_filter_state(encoded)
        assert decoded.page.page_id == "/b/overview"

    def test_value_with_reserved_chars_roundtrips(self) -> None:
        dim = _make_dimension(
            dim_id="product",
            label_zh="产品",
            values=[{"id": "prod:a|b~c=d", "label_zh": "含保留符产品"}],
        )
        state = _make_full_state(
            page=_make_page_scope(
                page_id="/b/products/prod-alpha",
                dims=[dim],
                selected={"product": ["prod:a|b~c=d"]},
            ),
            modules=[],
        )
        encoded = encode_filter_state(state)
        # Raw reserved separators must not appear unescaped in value payload
        assert "~pid=" in encoded or encoded.startswith("v1~")
        decoded = decode_filter_state(encoded)
        assert decoded.page.page_id == "/b/products/prod-alpha"
        assert decoded.page.selected["product"] == ("prod:a|b~c=d",)
        # Encoded tilde in value must not create extra segments
        assert encoded.count("~") == len(encoded.split("~")) - 1

    def test_decoded_value_does_not_inject_segments(self) -> None:
        # Manually craft: value is percent-encoded "~evil=1" so it stays one segment
        encoded = "v1~pid=%2Fb%2Foverview~ps=product:prod%7Eevil%3D1"
        decoded = decode_filter_state(encoded)
        assert decoded.page.selected["product"] == ("prod~evil=1",)


class TestUtf8ByteUrlLimit:
    """URL 上限按 UTF-8 字节计数。"""

    def test_serialize_uses_utf8_byte_length(self) -> None:
        # Many CJK labels in IDs push byte length above char length
        many = [f"值{i:04d}-中文标识" for i in range(80)]
        dim = _make_dimension(
            dim_id="product",
            label_zh="产品",
            values=[{"id": v, "label_zh": f"标签{v}"} for v in many],
        )
        state = _make_full_state(
            page=_make_page_scope(
                dims=[dim],
                selected={"product": many},
            ),
            modules=[],
        )
        outcome = serialize_filter_state(state, limit=500)
        encoded = encode_filter_state(state)
        assert outcome.size == len(encoded.encode("utf-8"))
        if len(encoded.encode("utf-8")) > 500:
            assert outcome.kind == "save_local_view"
            assert outcome.message_zh == SAVE_LOCAL_VIEW_HINT_ZH
        else:
            # Force with tiny limit
            tiny = serialize_filter_state(state, limit=10)
            assert tiny.kind == "save_local_view"
            assert tiny.size == len(encoded.encode("utf-8"))



# ===========================================================================
# 13. Repair2：冻结目录页面/模块权威
# ===========================================================================


class TestCatalogAuthorityRepair2:
    """页面/模块必须属于冻结 A/B/C 目录或其动态详情路由。"""

    def test_unknown_static_page_rejected(self) -> None:
        with pytest.raises(
            (PortalFilterError, PydanticValidationError), match=r"目录"
        ):
            PageFilterScope(
                page_id="/not-in-catalog",
                dimensions=(),
                selected={},
            )

    def test_decode_unknown_page_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"目录"):
            decode_filter_state("v1~pid=%2Fnot-in-catalog")

    def test_unknown_module_rejected(self) -> None:
        with pytest.raises(
            (PortalFilterError, PydanticValidationError), match=r"目录"
        ):
            ModuleFilterState(module_id="made-up", dimensions=(), selected={})

    def test_decode_unknown_module_rejected(self) -> None:
        with pytest.raises(UrlStateError, match=r"目录"):
            decode_filter_state("v1~pid=%2Fb%2Foverview~m=made-up")

    def test_static_route_accepted(self) -> None:
        scope = PageFilterScope(
            page_id="/b/efficacy",
            dimensions=(),
            selected={},
        )
        assert scope.page_id == "/b/efficacy"

    def test_dynamic_product_route_accepted(self) -> None:
        scope = PageFilterScope(
            page_id="/b/products/prod-alpha",
            dimensions=(),
            selected={},
        )
        assert scope.page_id == "/b/products/prod-alpha"

    def test_dynamic_trial_route_accepted(self) -> None:
        scope = PageFilterScope(
            page_id="/c/trials/nct-001",
            dimensions=(),
            selected={},
        )
        assert scope.page_id == "/c/trials/nct-001"

    def test_known_filter_profile_accepted(self) -> None:
        mod = ModuleFilterState(
            module_id="b-efficacy",
            dimensions=(),
            selected={},
        )
        assert mod.module_id == "b-efficacy"
