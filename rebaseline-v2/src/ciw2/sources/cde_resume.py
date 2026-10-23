"""CDE 同次运行部分来源读取；只复用已捕获分页，不触发新的浏览器检查。

本模块不重新解释栏目、筛选或监管含义：范围以元数据和负载逐字匹配，分页
是否闭合由调用方传入的生产校验器（allow_partial=True）裁决。返回的原始
分页不构成新的来源观察、新鲜度声明、来源采纳、缓存或事实。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources import china_browser

_MISSING = object()


def _object(value: Any, reason: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise china_browser.BrowserFailed(reason)
    return value


def _loads(raw: Any, reason: str) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        raise china_browser.BrowserFailed(reason) from None


def _page_numbers(value: Any, field: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise china_browser.BrowserFailed(f'部分恢复校验结果缺少{field}')
    numbers: list[int] = []
    for item in value:
        if type(item) is not int or item < 1:
            raise china_browser.BrowserFailed(f'部分恢复校验结果{field}不是有效页号')
        numbers.append(item)
    if len(set(numbers)) != len(numbers):
        raise china_browser.BrowserFailed(f'部分恢复校验结果{field}包含重复页')
    return numbers


def _validated(pages: list[dict[str, Any]], validate: Callable[[list], dict]) -> dict[str, Any] | None:
    """调用生产校验器；返回 None 表示捕获已完整，否则返回可复用的缺口摘要。"""
    if not callable(validate):
        raise china_browser.BrowserFailed('部分恢复缺少来源校验器')
    try:
        result = validate(pages)
    except Exception as exc:  # noqa: BLE001 - 校验失败必须闭合为来源失败，不做兜底解析
        raise china_browser.BrowserFailed(f'部分恢复来源校验失败（{type(exc).__name__}）') from None
    parsed = _object(result, '部分恢复校验结果不是对象')
    complete = parsed.get('complete', _MISSING)
    if type(complete) is not bool:
        raise china_browser.BrowserFailed('部分恢复校验结果缺少完成标记')
    if complete:
        return None
    read = _page_numbers(parsed.get('pages_read'), '已读页')
    pending = _page_numbers(parsed.get('pending_pages'), '待读页')
    if set(read) & set(pending):
        raise china_browser.BrowserFailed('部分恢复校验结果的已读页与待读页重叠')
    total = parsed.get('total_records', _MISSING)
    if type(total) is not int or total < 1:
        raise china_browser.BrowserFailed('部分恢复校验结果缺少有效记录总数')
    if len(read) != len(pages):
        raise china_browser.BrowserFailed('部分恢复校验结果与原始分页数量不符')
    return {'pages_read': read, 'pending_pages': pending, 'total_records': total}


def _capture_pages(ctx: ToolContext, source: dict[str, Any], *, section: str,
                   filters: dict[str, Any]) -> list[dict[str, Any]]:
    """按摘要重读原始分页；任何字节、范围或结构异常都失败闭合。"""
    try:
        raw = ctx.cas.get(source['digest'])
    except (OSError, TypeError):
        raise china_browser.BrowserFailed('部分恢复来源字节缺失') from None
    if hashlib.sha256(raw).hexdigest() != source['digest']:
        raise china_browser.BrowserFailed('恢复来源字节不一致')
    capture = _object(_loads(raw, '部分恢复来源内容不是有效JSON'), '部分恢复来源内容不是对象')
    if capture.get('section') != section or capture.get('filters') != filters:
        raise china_browser.BrowserFailed('部分恢复来源范围不符')
    pages = capture.get('pages')
    if not isinstance(pages, list) or not pages:
        raise china_browser.BrowserFailed('部分恢复来源缺少有效分页')
    return pages


def load_partial(ctx: ToolContext, *, section: str, filters: dict[str, Any],
                 validate: Callable[[list], dict]) -> dict[str, Any] | None:
    """读取本次运行中最新且完全匹配的未完成 CDE 来源分页。

    返回 None 表示无需部分恢复（无匹配、最新匹配已完整或校验后已闭合）。
    返回分页仅为原始捕获内容；本函数不写来源、事件、缓存或事实。
    """
    if not isinstance(section, str) or not section.strip():
        raise china_browser.BrowserFailed('部分恢复栏目无效')
    if not isinstance(filters, dict):
        raise china_browser.BrowserFailed('部分恢复筛选无效')
    if (ctx.db is None or ctx.cas is None or not isinstance(ctx.project_id, str) or not ctx.project_id
            or not isinstance(ctx.run_id, str) or not ctx.run_id):
        raise china_browser.BrowserFailed('部分恢复缺少项目或运行上下文')
    run = ctx.db.one('SELECT project_id FROM runs WHERE id=?', (ctx.run_id,))
    if run is None or run['project_id'] != ctx.project_id:
        raise china_browser.BrowserFailed('部分恢复运行不属于当前项目')
    expected = {'registry': 'cde', 'section': section, 'filters': filters}
    for step in ctx.db.query("SELECT id, content FROM agent_steps WHERE run_id=? "
                             "AND role='source_observation' ORDER BY id DESC", (ctx.run_id,)):
        observation = _object(_loads(step['content'], '来源观察记录无法解析'),
                              '来源观察记录不是对象')
        if observation.get('mode') != 'browser_checked':
            continue
        source = ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                            (observation.get('source_id'), ctx.project_id, 'cde'))
        if source is None:
            continue
        metadata = _object(_loads(source['meta'], '部分恢复来源元数据无法解析'),
                           '部分恢复来源元数据不是对象')
        scope = metadata.get('request_context')
        if not isinstance(scope, dict):
            raise china_browser.BrowserFailed('部分恢复来源缺少查询范围')
        identity = {key: value for key, value in scope.items() if key != 'method'}
        if identity != expected:
            continue
        method = scope.get('method')
        if method is not None and not (section == 'acceptance' and method == 'browser_form'):
            raise china_browser.BrowserFailed('部分恢复来源查询方法不符')
        if metadata.get('complete') is True:
            return None  # 最新匹配来源已完成：不回退到更早的未完成来源。
        if metadata.get('complete') is not False:
            raise china_browser.BrowserFailed('部分恢复来源完成标记不合法')
        if observation.get('complete') is not False:
            raise china_browser.BrowserFailed('部分恢复观察记录与来源完成状态不一致')
        pages = _capture_pages(ctx, source, section=section, filters=filters)
        result = _validated(pages, validate)
        if result is None:
            return None
        return {'source_id': source['id'], 'pages': pages, **result}
    return None
