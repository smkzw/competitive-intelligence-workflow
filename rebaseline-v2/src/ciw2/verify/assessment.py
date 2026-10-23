"""当前引文规则下的核验裁决。

裁决是事件，不是科学观察：它只追加到 ``agent_steps(role='fact_verdict')``，
从不改写事实、引文、来源、修订链接或科学上下文。规则身份直接绑定实际
checker（``quote.py``）与本评估模块的字节，任何一边改变都会使旧回执失效；
不维护可手改的版本字符串，也不猜测旧事实当时使用的规则。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ciw2.verify.quote import check_quote, normalize

ROLE = 'fact_verdict'
COORDINATE = 'normalized'
PENDING_NOTE = '待按当前引文规则复核'
VERDICTS = frozenset({
    'confirmed', 'invalidated', 'missing_quote', 'source_unpinned', 'source_unavailable',
    'source_unreadable', 'source_digest_mismatch'})
RECEIPT_KEYS = ('project_id', 'fact_id', 'fact_digest', 'rule', 'stored_status', 'stored_rule', 'status',
                'verdict', 'reason', 'source_id', 'source_digest', 'text_digest', 'quote_sha256',
                'quote_len', 'quote_start', 'quote_end', 'coordinate')


def _identity() -> str:
    # Hash the real checker plus this contract, not a hand-maintained version.
    here = Path(__file__).resolve()
    checker = here.with_name('quote.py').read_bytes()
    return 'quote-' + hashlib.sha256(checker + b'\0' + here.read_bytes()).hexdigest()[:16]


_RULE = _identity()


def rule_identity() -> str:
    """动态读取，测试和规则升级可显式替换当前规则身份。"""
    return _RULE


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def fact_digest(fact: dict[str, Any]) -> str:
    """绑定已解码事实；保留JSON字符串与数值类型，不对临床字符串再次解码。"""
    payload = {key: fact.get(key) for key in
               ('id', 'project_id', 'entity_id', 'field', 'value', 'tier', 'source_id', 'quote', 'context')}
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()


def quote_digest(quote: Any) -> str | None:
    return hashlib.sha256(quote.encode()).hexdigest() if isinstance(quote, str) and quote else None


def effective_status(stored: str, verdict: str) -> str:
    """只降不升：stored verified 只有 confirmed 回执能继续认证。"""
    if stored != 'verified':
        return stored
    return 'verified' if verdict == 'confirmed' else 'unverified'


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in '0123456789abcdef' for char in value)


def _result(verdict: str, reason: str, *, source_id: str | None = None, source_digest: str | None = None,
            text_digest: str | None = None, quote: Any = None, start: int | None = None,
            end: int | None = None) -> dict[str, Any]:
    return {'verdict': verdict, 'reason': reason, 'source_id': source_id, 'source_digest': source_digest,
            'text_digest': text_digest, 'quote_sha256': quote_digest(quote),
            'quote_len': len(quote) if isinstance(quote, str) else 0,
            'quote_start': start, 'quote_end': end}


def inspect(db: Any, cas: Any, *, project_id: str, source_id: str | None, quote: Any,
            value: Any) -> dict[str, Any]:
    """按 pinned source_id 读取本项目 CAS 字节并重算 SHA；不按 URL 猜最新版本。"""
    if not source_id:
        return _result('source_unpinned', '来源版本未固定，无法复核', quote=quote)
    src = db.one('SELECT id, digest, text_digest FROM sources WHERE project_id=? AND id=?',
                 (project_id, source_id))
    if src is None or not _is_digest(src['digest']) or not _is_digest(src['text_digest']):
        return _result('source_unavailable', '来源版本未在本项目中读取，无法复核', source_id=source_id, quote=quote)
    try:
        raw = cas.get(src['digest'])
        text_bytes = cas.get(src['text_digest'])
    except OSError:
        return _result('source_unreadable', '来源原文不可读，未能复核', source_id=source_id,
                       source_digest=src['digest'], text_digest=src['text_digest'], quote=quote)
    if (hashlib.sha256(raw).hexdigest() != src['digest']
            or hashlib.sha256(text_bytes).hexdigest() != src['text_digest']):
        return _result('source_digest_mismatch', '来源摘要与固定字节不一致，未能复核', source_id=source_id,
                       source_digest=src['digest'], text_digest=src['text_digest'], quote=quote)
    evidence = {'source_id': source_id, 'source_digest': src['digest'], 'text_digest': src['text_digest']}
    if not isinstance(quote, str) or not quote.strip():
        return _result('missing_quote', '缺少原文片段', quote=quote, **evidence)
    check = check_quote(text_bytes.decode('utf-8', errors='replace'), quote, value)
    return _result('confirmed' if check.ok else 'invalidated', check.reason, quote=quote,
                   start=check.start, end=check.end, **evidence)


def make_receipt(fact: dict[str, Any], *, rule: str, stored_status: str,
                 result: dict[str, Any]) -> dict[str, Any]:
    verdict = result['verdict']
    return {
        'project_id': fact['project_id'], 'fact_id': fact['id'], 'fact_digest': fact_digest(fact),
        'rule': rule, 'stored_status': stored_status, 'stored_rule': 'unknown',
        'status': effective_status(stored_status, verdict), 'verdict': verdict,
        'reason': result.get('reason') or '',
        'source_id': result.get('source_id') or fact.get('source_id'),
        'source_digest': result.get('source_digest'), 'text_digest': result.get('text_digest'),
        'quote_sha256': result.get('quote_sha256'), 'quote_len': result.get('quote_len', 0),
        'quote_start': result.get('quote_start'), 'quote_end': result.get('quote_end'),
        'coordinate': COORDINATE,
    }


def receipt_matches(receipt: Any, fact: dict[str, Any]) -> bool:
    """只有结构完整、事实/来源/引文/规则全部匹配的回执才能认证。"""
    if not isinstance(receipt, dict):
        return False
    if not all(key in receipt for key in RECEIPT_KEYS):
        return False
    if not str(fact.get('extracted_by') or '').startswith('llm:') or fact.get('status') != 'verified':
        return False
    if (receipt.get('project_id') != fact.get('project_id') or receipt.get('fact_id') != fact.get('id')
            or receipt.get('rule') != rule_identity()):
        return False
    if receipt.get('fact_digest') != fact_digest(fact):
        return False
    verdict = receipt.get('verdict')
    if not isinstance(verdict,str) or verdict not in VERDICTS or receipt.get('stored_status') != 'verified':
        return False
    if receipt.get('status') != effective_status('verified', verdict):
        return False
    if receipt.get('coordinate') != COORDINATE:
        return False
    if receipt.get('source_id') != fact.get('source_id'):
        return False
    if receipt.get('quote_sha256') != quote_digest(fact.get('quote')):
        return False
    quote=fact.get('quote')
    if receipt.get('quote_len') != (len(quote) if isinstance(quote,str) else 0):
        return False
    if verdict=='confirmed':
        start,end=receipt.get('quote_start'),receipt.get('quote_end')
        if (type(start) is not int or type(end) is not int or start<0 or end<=start
                or not isinstance(quote,str) or end-start!=len(normalize(quote))):
            return False
    if verdict in {'confirmed', 'invalidated'}:
        return _is_digest(receipt.get('source_digest')) and _is_digest(receipt.get('text_digest'))
    return True


def same_receipt(left: Any, right: Any) -> bool:
    """同一事实/规则/证据/结果的幂等判定；不含写入时间。"""
    return isinstance(left, dict) and isinstance(right, dict) and all(
        left.get(key) == right.get(key) for key in RECEIPT_KEYS)
