"""Opt-in Ego public registry capture; no profile discovery or automatic claiming."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw2.harness.tools import ToolContext
from ciw2.sources.china_capture import CaptureError, parse_capture, parse_page
from ciw2.sources.http import register_text

SCRIPT = Path(__file__).with_suffix('.mjs')
CODE_HASH = hashlib.sha256(b''.join(path.read_bytes() for path in (
    Path(__file__),SCRIPT,Path(__file__).with_name('china_capture.py'),Path(__file__).with_name('http.py')))).hexdigest()


class BrowserBlocked(RuntimeError):
    pass


class BrowserFailed(RuntimeError):
    pass


def _markers(*streams: str | bytes | None) -> str:
    lines = []
    for stream in streams:
        value = stream.decode('utf-8',errors='replace') if isinstance(stream,bytes) else stream or ''
        lines.extend(line for line in value.splitlines() if line.startswith(('CIW_CHINA_PAGE:','CIW_CHINA_END:')))
    return '\n'.join(lines)


def _invoke(ctx: ToolContext, query: str, resume: dict[str, Any] | None = None, *,
            script_path: Path = SCRIPT, options: dict[str, Any] | None = None) -> tuple[str, bool]:
    space = ctx.settings.china_ego_space_id
    if isinstance(space, bool) or not isinstance(space, int) or space <= 0:
        raise BrowserBlocked('未配置专用Ego浏览器空间')
    executable = shutil.which('ego-browser')
    if not executable:
        raise BrowserBlocked('Ego浏览器工具不可用')
    if options and {'space','query'} & options.keys():
        raise BrowserFailed('浏览器配置不得覆盖授权空间或查询')
    config = {'space':space,'query':query,**(options or {})}
    if resume:
        parsed = [parse_page(page,query=query) for page in resume['pages']]
        config.update(skip_pages=[page['page'] for page in parsed],
                      expected_totals=[parsed[0]['total_pages'],parsed[0]['total_records']])
    script = 'const config = ' + json.dumps(config, ensure_ascii=False) + ';\n' + script_path.read_text()
    try:
        proc = subprocess.run([executable,'nodejs','-e',script],capture_output=True,text=True,
                              timeout=ctx.settings.china_browser_timeout_s,check=False)
        return _markers(proc.stdout,proc.stderr), proc.returncode == 0
    except subprocess.TimeoutExpired as exc:
        return _markers(exc.output,exc.stderr), False
    except OSError as exc:
        raise BrowserBlocked(f'浏览器调用失败（{type(exc).__name__}）') from None


def _read_output(stdout: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pages, end = [], {}
    try:
        for line in stdout.splitlines():
            if line.startswith('CIW_CHINA_PAGE:'):
                pages.append(json.loads(line.removeprefix('CIW_CHINA_PAGE:')))
            elif line.startswith('CIW_CHINA_END:'):
                if end:
                    raise ValueError('duplicate completion')
                end = json.loads(line.removeprefix('CIW_CHINA_END:'))
        if not isinstance(end,dict):
            raise TypeError('invalid completion')
    except (ValueError,TypeError) as exc:
        raise BrowserFailed(f'浏览器捕获格式无效（{type(exc).__name__}）') from None
    return pages,end


def _save(ctx: ToolContext, query: str, pages: list[dict[str, Any]], end: dict[str, Any],
          *, complete: bool, **metadata: Any) -> str:
    text = json.dumps({'query':query,'pages':pages},ensure_ascii=False)
    source_id = register_text(ctx,kind='chinadrugtrials',url=pages[0]['url'],text=text,
        title=f'中国药物临床试验登记检索：{query}',meta={'method':'ego_public_ui','complete':complete,
            **metadata,'observed_at':end.get('observed_at'),
            'request_context':{'method':'POST','registry':'chinadrugtrials','query':query}})
    ctx.db.log_step(ctx.run_id,ctx.stage,'source',0,'source_observation',{
        'project_id':ctx.project_id,'source_id':source_id,'mode':'browser_checked','url':pages[0]['url'],
        'http_status':None,'browser_checked_at':datetime.now(UTC).isoformat(),'complete':complete})
    return source_id


def _retain_valid_pages(ctx: ToolContext, query: str, pages: list[dict[str, Any]], end: dict[str, Any]) -> None:
    valid = []
    for page in pages:
        try:
            parse_page(page,query=query)
        except CaptureError:
            continue
        valid.append(page)
    if valid:
        _save(ctx,query,valid,end,complete=False,validation_failed=True,
              pages_read=[parse_page(page,query=query)['page'] for page in valid],
              rejected_page_count=len(pages)-len(valid))


def _resume_pages(ctx: ToolContext, query: str) -> dict[str, Any] | None:
    rows = ctx.db.query("SELECT s.* FROM agent_steps a JOIN sources s ON s.id=json_extract(a.content,'$.source_id') "
        "WHERE a.run_id=? AND a.role='source_observation' AND s.project_id=? AND s.kind='chinadrugtrials' "
        "AND json_extract(a.content,'$.mode')='browser_checked' ORDER BY a.id DESC",(ctx.run_id,ctx.project_id))
    for row in rows:
        metadata = json.loads(row['meta'])
        if metadata.get('request_context') != {'method':'POST','registry':'chinadrugtrials','query':query}:
            continue
        if metadata.get('complete') is not False:
            return None
        raw = ctx.cas.get(row['digest'])
        if hashlib.sha256(raw).hexdigest() != row['digest']:
            raise BrowserFailed('恢复来源字节不一致')
        pages = json.loads(raw)['pages']
        parsed = [parse_page(page,query=query) for page in pages]
        numbers = [page['page'] for page in parsed]
        ctrs = [item['ctr'] for page in parsed for item in page['results']]
        if len(numbers) != len(set(numbers)) or len(ctrs) != len(set(ctrs)):
            return None  # Conflicting captures need a fresh collection, not first-wins merging.
        return {'source_id':row['id'],'pages':pages}
    return None


def browser_search(ctx: ToolContext, query: str) -> dict[str, Any]:
    if not query.strip():
        raise BrowserFailed('检索词为空')
    resume = _resume_pages(ctx,query)
    stdout, process_ok = _invoke(ctx,query,resume)
    pages,end = _read_output(stdout)
    new_capture = pages
    if resume:
        pages = [*resume['pages'],*pages]
    if not pages:
        if end.get('status') in {'blocked','user_control'}:
            raise BrowserBlocked('浏览器空间不可用或需要用户交接')
        raise BrowserFailed('浏览器未取得可核验的登记页面')
    try:
        result = parse_capture(pages,query=query,allow_partial=True)
    except CaptureError:
        _retain_valid_pages(ctx,query,pages,end)
        raise BrowserFailed('浏览器来源页面校验失败') from None
    new_pages = [parse_page(page,query=query)['page'] for page in new_capture]
    complete = process_ok and end.get('status') == 'ok' and result['complete']
    source_id = _save(ctx,query,pages,end,complete=complete,pending_pages=result['pending_pages'],
        pages_read=result['pages_read'],total_records=result['total_records'],
        reused_source_ids=[resume['source_id']] if resume else [],
        reused_pages=[parse_page(page,query=query)['page'] for page in resume['pages']] if resume else [],
        new_pages_checked=new_pages)
    if not complete:
        raise BrowserFailed('浏览器检索未完成；已保存有效分页来源供复核')
    return {**result,'source_id':source_id,'results':[{**row,'source_id':source_id} for row in result['results']]}
