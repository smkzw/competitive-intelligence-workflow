"""Task 4.3 URL 状态序列化：版本化、确定性、可往返。

encode_filter_state / decode_filter_state 实现：
- 版本化 URL hash 参数序列化
- 组件级 percent-encoding（稳定 ID 可含 ``/ ~ | , : =``）
- 确定性键排序
- 超限按 UTF-8 字节返回类型化「保存为本地视图」，不截断
- 重复/未知维度/未知字段失败关闭，中文错误
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import quote, unquote

from pydantic import BaseModel, ConfigDict

from ci_workflow.renderers.portal.filters import (
    MODULE_DIMENSION_IDS,
    PAGE_DIMENSION_IDS,
    AnchorTrialState,
    EvidenceSelection,
    FilterState,
    FilterVersion,
    ModuleFilterState,
    PageFilterScope,
    PaginationState,
    SortState,
)

URL_SIZE_LIMIT = 2048
_SEGMENT_SEP = "~"
SAVE_LOCAL_VIEW_HINT_ZH = "当前选择过多，请保存为本地视图"
_PAGE_DIM_SET = frozenset(PAGE_DIMENSION_IDS)
_MODULE_DIM_SET = frozenset(MODULE_DIMENSION_IDS)


class UrlStateError(ValueError):
    """URL 状态解析失败：数据损坏或格式错误。"""


class UrlSerializeOutcome(BaseModel):
    """URL 序列化结果：成功写入 hash，或因超限建议本地视图（从不截断）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["url", "save_local_view"]
    encoded: str
    size: int
    message_zh: str | None = None


def _enc(value: str) -> str:
    """Percent-encode 一个稳定 ID 组件（含 ``/`` 与 ``~``）。

    ``urllib.parse.quote`` 默认不编码 ``~``（RFC 3986 unreserved），
    但 ``~`` 是本协议的段分隔符，必须强制编码。
    """
    return quote(value, safe="").replace("~", "%7E")


def _dec(value: str) -> str:
    return unquote(value)


def _encode_selected(selected: dict[str, tuple[str, ...]]) -> str:
    parts: list[str] = []
    for key in sorted(selected.keys()):
        vals = sorted(selected[key])
        if not vals:
            continue
        encoded_vals = ",".join(_enc(v) for v in vals)
        parts.append(f"{_enc(key)}:{encoded_vals}")
    return "|".join(parts)


def _decode_selected(
    data: str,
    *,
    allowed_dims: frozenset[str],
    scope_zh: str,
) -> dict[str, tuple[str, ...]]:
    if not data:
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for part in data.split("|"):
        if ":" not in part:
            raise UrlStateError(f"筛选状态格式无效：{part}")
        key_raw, vals_str = part.split(":", 1)
        key = _dec(key_raw.strip())
        if not key:
            raise UrlStateError("筛选维度 ID 不能为空")
        if key in result:
            raise UrlStateError(f"{scope_zh}维度「{key}」重复")
        if key not in allowed_dims:
            raise UrlStateError(f"未知{scope_zh}维度：{key}")
        raw_vals = [v for v in vals_str.split(",") if v]
        vals = [_dec(v) for v in raw_vals]
        if len(vals) != len(set(vals)):
            raise UrlStateError(f"筛选值在维度「{key}」中重复")
        result[key] = tuple(sorted(vals))
    return result


def encode_filter_state(state: FilterState) -> str:
    """将筛选状态确定性序列化为 URL hash 字符串（组件已编码）。"""
    segments: list[str] = [str(state.version.value), f"pid={_enc(state.page.page_id)}"]

    page_sel = _encode_selected(state.page.selected)
    if page_sel:
        segments.append(f"ps={page_sel}")

    for mod in sorted(state.modules, key=lambda m: m.module_id):
        mod_sel = _encode_selected(mod.selected)
        segments.append(f"m={_enc(mod.module_id)}")
        if mod_sel:
            segments.append(f"ms={mod_sel}")

    if state.sort.field:
        segments.append(
            f"s={_enc(state.sort.field)}:{_enc(state.sort.direction)}"
        )

    if state.anchor.trial_id:
        segments.append(f"a={_enc(state.anchor.trial_id)}")

    if state.evidence.open_id:
        segments.append(f"eo={_enc(state.evidence.open_id)}")

    if state.evidence.selected_ids:
        sorted_ids = sorted(state.evidence.selected_ids)
        segments.append("e=" + ",".join(_enc(i) for i in sorted_ids))

    if state.pagination.current_page != 1:
        segments.append(f"pg={state.pagination.current_page}")

    return _SEGMENT_SEP.join(segments)


def serialize_filter_state(
    state: FilterState,
    *,
    limit: int = URL_SIZE_LIMIT,
) -> UrlSerializeOutcome:
    """序列化并以 UTF-8 字节检查 URL 上限。"""
    encoded = encode_filter_state(state)
    size = len(encoded.encode("utf-8"))
    if size > limit:
        return UrlSerializeOutcome(
            kind="save_local_view",
            encoded=encoded,
            size=size,
            message_zh=SAVE_LOCAL_VIEW_HINT_ZH,
        )
    return UrlSerializeOutcome(
        kind="url",
        encoded=encoded,
        size=size,
        message_zh=None,
    )


def decode_filter_state(data: str) -> FilterState:
    """从 URL hash 字符串解码筛选状态；失败关闭。"""
    if not data or not data.strip():
        raise UrlStateError("URL 状态为空")

    data = data.strip().lstrip("#")
    segments = data.split(_SEGMENT_SEP)
    if not segments:
        raise UrlStateError("URL 状态格式无效")

    version_str = segments[0]
    try:
        version = FilterVersion(version_str)
    except ValueError as exc:
        raise UrlStateError(f"不支持的 URL 状态版本：{version_str}") from exc

    page_id: str | None = None
    page_selected: dict[str, tuple[str, ...]] = {}
    saw_ps = False
    modules: list[ModuleFilterState] = []
    seen_module_ids: set[str] = set()
    sort_field: str | None = None
    sort_direction: str = "asc"
    anchor_trial_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    evidence_open_id: str | None = None
    saw_evidence = False
    saw_evidence_open = False
    current_page = 1
    saw_pg = False
    saw_sort = False
    saw_anchor = False

    for seg in segments[1:]:
        if seg.startswith("pid="):
            if page_id is not None:
                raise UrlStateError("页面标识重复")
            page_id = _dec(seg[4:])
        elif seg.startswith("ps="):
            if saw_ps:
                raise UrlStateError("页面筛选段重复")
            saw_ps = True
            page_selected = _decode_selected(
                seg[3:],
                allowed_dims=_PAGE_DIM_SET,
                scope_zh="页面",
            )
        elif seg.startswith("m="):
            mid = _dec(seg[2:])
            if not mid:
                raise UrlStateError("模块 ID 不能为空")
            if mid in seen_module_ids:
                raise UrlStateError(f"模块标识「{mid}」重复")
            seen_module_ids.add(mid)
            try:
                modules.append(
                    ModuleFilterState(module_id=mid, dimensions=(), selected={})
                )
            except Exception as exc:
                raise UrlStateError(f"URL 状态解析失败：{exc}") from exc
        elif seg.startswith("ms="):
            if not modules:
                raise UrlStateError("模块筛选缺少模块标识")
            if modules[-1].selected:
                raise UrlStateError("同一模块的筛选段重复")
            try:
                modules[-1] = ModuleFilterState(
                    module_id=modules[-1].module_id,
                    dimensions=(),
                    selected=_decode_selected(
                        seg[3:],
                        allowed_dims=_MODULE_DIM_SET,
                        scope_zh="模块",
                    ),
                )
            except UrlStateError:
                raise
            except Exception as exc:
                raise UrlStateError(f"URL 状态解析失败：{exc}") from exc
        elif seg.startswith("s="):
            if saw_sort:
                raise UrlStateError("排序段重复")
            saw_sort = True
            sort_part = seg[2:]
            if ":" in sort_part:
                field_raw, dir_raw = sort_part.split(":", 1)
                sort_field = _dec(field_raw)
                sort_direction = _dec(dir_raw)
            else:
                sort_field = _dec(sort_part)
        elif seg.startswith("a="):
            if saw_anchor:
                raise UrlStateError("锚定试验段重复")
            saw_anchor = True
            anchor_trial_id = _dec(seg[2:])
        elif seg.startswith("eo="):
            if saw_evidence_open:
                raise UrlStateError("打开的数据依据段重复")
            saw_evidence_open = True
            evidence_open_id = _dec(seg[3:])
            if not evidence_open_id:
                raise UrlStateError("打开的数据依据标识不能为空")
        elif seg.startswith("e="):
            if saw_evidence:
                raise UrlStateError("证据选择段重复")
            saw_evidence = True
            raw_ids = [_dec(v) for v in seg[2:].split(",") if v]
            if len(raw_ids) != len(set(raw_ids)):
                raise UrlStateError("证据标识重复")
            evidence_ids = tuple(sorted(raw_ids))
        elif seg.startswith("pg="):
            if saw_pg:
                raise UrlStateError("页码段重复")
            saw_pg = True
            try:
                current_page = int(seg[3:])
            except ValueError as exc:
                raise UrlStateError(f"无效页码：{seg[3:]}") from exc
        elif seg:
            raise UrlStateError(f"未知 URL 状态字段：{seg}")

    if page_id is None or not page_id:
        raise UrlStateError("URL 状态缺少页面标识")

    try:
        return FilterState(
            version=version,
            page=PageFilterScope(
                page_id=page_id,
                dimensions=(),
                selected=page_selected,
            ),
            modules=tuple(modules),
            sort=SortState(
                field=sort_field,
                direction=sort_direction,  # type: ignore[arg-type]
            ),
            anchor=AnchorTrialState(trial_id=anchor_trial_id),
            evidence=EvidenceSelection(
                selected_ids=evidence_ids,
                open_id=evidence_open_id,
            ),
            pagination=PaginationState(current_page=current_page),
        )
    except UrlStateError:
        raise
    except Exception as exc:
        raise UrlStateError(f"URL 状态解析失败：{exc}") from exc
