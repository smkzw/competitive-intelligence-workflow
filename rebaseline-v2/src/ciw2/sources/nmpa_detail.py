"""One already-discovered public NMPA certificate; literal source, never adoption.

The caller must already hold the official public detail URL and the exact
registration number. This module only reads that visible public record, stores
raw bytes and literal text, and verifies same-run reuse. It does not crawl a
catalogue, create drugs/trials/facts, merge legal roles, or infer indication
approval from a certificate date.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources import china_browser, nmpa_capture
from ciw2.sources.http import register_text

SCRIPT = Path(__file__).with_suffix('.mjs')
KIND = 'nmpa'
CATEGORY_TYPE = Literal['境内生产药品', '境外生产药品']
NUMBER = r'国药准字[A-Z]{1,3}[0-9]{8}'


def code_hash() -> str:
    return hashlib.sha256(b''.join(path.read_bytes() for path in (
        Path(__file__), SCRIPT, Path(china_browser.__file__),
        Path(nmpa_capture.__file__)))).hexdigest()


def _record(url: Any) -> str:
    """Public link identity (id/itemId), using the existing exact parser guard."""
    try:
        nmpa_capture._url(url)
        token = parse_qs(urlsplit(url).query, strict_parsing=True)['nmpa'][0]
        return base64.b64decode(token, validate=True).decode('ascii')
    except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error):
        raise ValueError('NMPA公开详情来源绑定无效') from None


def _source_text(captured: dict[str, Any]) -> str:
    """Literal visible labels/values, not JSON punctuation."""
    rows = '\n'.join(f'{label.strip()}\t{value}' for label, value in captured['rows'])
    return captured['heading'] + '\n' + rows


def parse_capture(raw: Any, *, url: str, registration_number: str,
                  category: str) -> dict[str, Any]:
    expected = {'url', 'category', 'registration_number', 'heading', 'rows', 'observed_at'}
    if not isinstance(raw, dict) or set(raw) != expected:
        raise ValueError('NMPA详情捕获结构不符')
    if raw['category'] != category or raw['registration_number'] != registration_number:
        raise ValueError('NMPA详情捕获与请求类别或注册证号不符')
    if _record(raw['url']) != _record(url):
        raise ValueError('NMPA详情实际地址与所请求公开记录不一致')
    observed = raw['observed_at']
    if not isinstance(observed, str) or datetime.fromisoformat(observed).tzinfo is None:
        raise ValueError('NMPA详情无有效实际获取时间')
    parsed = nmpa_capture.parse_detail(raw, registration_number=registration_number, category=category)
    return {**parsed, 'observed_at': observed, 'source_text': _source_text(raw)}


def _capture(ctx: ToolContext, url: str, registration_number: str, category: str) -> dict[str, Any]:
    stdout, ok = china_browser._invoke(ctx, registration_number, script_path=SCRIPT,
                                       options={'url': url, 'category': category})
    pages, end = china_browser._read_output(stdout)
    if end.get('status') in {'blocked', 'user_control'}:
        raise china_browser.BrowserBlocked('NMPA公开详情浏览器空间不可用或需要用户交接')
    if not ok or end.get('status') != 'ok' or len(pages) != 1:
        code = end.get('error_code')
        reason = f'（{code}）' if isinstance(code, str) and re.fullmatch(r'certificate_[a-z_]+', code) else ''
        raise china_browser.BrowserFailed(f'NMPA公开详情未完成{reason}，不能作为空资料')
    return pages[0]


def _require(ctx: ToolContext) -> int:
    space = getattr(ctx.settings, 'china_ego_space_id', None) if ctx.settings is not None else None
    if isinstance(space, bool) or not isinstance(space, int) or space <= 0:
        raise china_browser.BrowserBlocked('未配置专用Ego浏览器空间')
    if ctx.db is None or ctx.cas is None or not ctx.project_id or not ctx.run_id:
        raise ValueError('NMPA详情请求缺少当前项目或运行')
    if ctx.db.one('SELECT id FROM runs WHERE id=? AND project_id=?', (ctx.run_id, ctx.project_id)) is None:
        raise ValueError('NMPA详情请求运行不属于当前项目')
    return space


def _scope(ctx: ToolContext, space: int, url: str, category: str, registration_number: str) -> dict[str, Any]:
    return {'tool': 'nmpa_product_detail', 'project_id': ctx.project_id, 'run_id': ctx.run_id,
            'space': space, 'url': url, 'category': category, 'registration_number': registration_number}


def _reuse(ctx: ToolContext, source_id: str, scope: dict[str, Any], url: str,
           registration_number: str, category: str) -> tuple[dict[str, Any], dict[str, Any]]:
    source = ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                        (source_id, ctx.project_id, KIND))
    if source is None or not source['text_digest']:
        raise ValueError('NMPA详情缓存来源不属于当前项目')
    try:
        meta = json.loads(source['meta'])
    except (TypeError, ValueError):
        raise ValueError('NMPA详情缓存元数据不符') from None
    if meta.get('request_context') != scope or meta.get('extractor_version') != code_hash():
        raise ValueError('NMPA详情缓存请求范围或抽取版本不符')
    try:
        raw = ctx.cas.get(source['digest'])
        stored = ctx.cas.get(source['text_digest'])
    except (OSError, KeyError, TypeError):
        raise ValueError('NMPA详情缓存字节不可读') from None
    if hashlib.sha256(raw).hexdigest() != source['digest']:
        raise ValueError('NMPA详情缓存原始字节不符')
    try:
        captured = json.loads(raw)
    except (TypeError, ValueError):
        raise ValueError('NMPA详情缓存捕获格式不符') from None
    parsed = parse_capture(captured, url=url, registration_number=registration_number, category=category)
    if hashlib.sha256(stored).hexdigest() != source['text_digest'] or stored != parsed['source_text'].encode():
        raise ValueError('NMPA详情缓存原文与原始字节不符')
    return parsed, source


def _payload(parsed: dict[str, Any], source: dict[str, Any], mode: str) -> dict[str, Any]:
    return {'source_id': source['id'], 'source_url': source['url'], 'observation_mode': mode,
            'category': parsed['category'], 'registration_number': parsed['registration_number'],
            'drug_name': parsed['drug_name'], 'drug_name_en': parsed['drug_name_en'],
            'strength': parsed['strength'], 'holder_name': parsed['holder_name'],
            'holder_name_zh': parsed['holder_name_zh'], 'holder_name_en': parsed['holder_name_en'],
            'manufacturer_name': parsed['manufacturer_name'],
            'manufacturer_name_zh': parsed['manufacturer_name_zh'],
            'manufacturer_name_en': parsed['manufacturer_name_en'],
            'domestic_responsible_person': parsed['domestic_responsible_person'],
            'issue_date': parsed['issue_date'], 'valid_until': parsed['valid_until'],
            'approval_date': parsed['approval_date'], 'field_locators': parsed['field_locators'],
            'source_digest': source['digest'], 'text_digest': source['text_digest'],
            'published_date': None, 'source_text': parsed['source_text'],
            'observed_at': parsed['observed_at']}


def browser_detail(ctx: ToolContext, url: str, registration_number: str, category: str) -> dict[str, Any]:
    space = _require(ctx)
    if category not in nmpa_capture.FIELDS:
        raise ValueError('当前已观察合同仅支持境内或境外生产药品详情')
    if not re.fullmatch(NUMBER, registration_number):
        raise ValueError('待核对的注册证号格式不符')
    _record(url)  # Validate before any browser launch.
    scope = _scope(ctx, space, url, category, registration_number)
    if ctx.extra is None:
        ctx.extra = {}
    cache = ctx.extra.setdefault('fetch_cache', {})
    key = ('nmpa_detail', ctx.project_id, ctx.run_id, space, url, category, registration_number, code_hash())
    if key in cache:
        parsed, source = _reuse(ctx, cache[key], scope, url, registration_number, category)
        mode = 'cache_reused'
    else:
        captured = _capture(ctx, url, registration_number, category)
        parsed = parse_capture(captured, url=url, registration_number=registration_number, category=category)
        source_id = register_text(ctx, kind=KIND, url=captured['url'], text=parsed['source_text'],
            raw=json.dumps(captured, ensure_ascii=False).encode(), title=captured['heading'],
            meta={'method': 'ego_public_ui', 'request_context': scope,
                  'extractor_version': code_hash(), 'observation': 'browser_checked'})
        if not source_id:
            raise china_browser.BrowserFailed('NMPA详情来源未登记')
        cache[key] = source_id
        source = ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=?', (source_id, ctx.project_id))
        mode = 'browser_checked'
    if source is None:
        raise ValueError('NMPA详情来源不属于当前项目')
    ctx.extra.setdefault('source_ids_read', set()).add(source['id'])
    ctx.db.log_step(ctx.run_id, ctx.stage, 'source', 0, 'source_observation', {
        'project_id': ctx.project_id, 'source_id': source['id'], 'mode': mode,
        'url': source['url'], 'category': category, 'registration_number': registration_number,
        'browser_checked': mode == 'browser_checked', 'cache_reused': mode == 'cache_reused',
        'browser_checked_at': datetime.now(UTC).isoformat() if mode == 'browser_checked' else None,
        'cache_reused_at': datetime.now(UTC).isoformat() if mode == 'cache_reused' else None})
    return _payload(parsed, source, mode)


class DetailArgs(BaseModel):
    url: str = Field(description='已发现的NMPA公开药品详情URL（datasearch.search-info.html?nmpa=…）')
    registration_number: str = Field(pattern=r'^国药准字[A-Z]{1,3}[0-9]{8}$',
        description='该公开详情标题中的完整注册证号/批准文号，不猜别名')
    category: CATEGORY_TYPE = Field(description='必须与公开详情标题的药品类别完全一致')


@REGISTRY.register('nmpa_product_detail',
    '读取已定位到确切注册证号的NMPA药品批准证明文件公开详情原文；只登记来源，'
    '不创建药物/试验/事实，不推断适应症获批或首次公开日期。', DetailArgs)
def _detail(ctx: ToolContext, a: DetailArgs) -> dict[str, Any]:
    return browser_detail(ctx, a.url, a.registration_number, a.category)
