"""全网搜索 + 通用网页读取（会议摘要、企业管线页、新闻稿、监管公告）。
提供方可插拔：tavily | bing | serpapi。未配置时工具返回 blocked，覆盖率如实记为 blocked。
提供方请求失败抛 SearchFailed：只保留错误类别与实际 HTTP 状态码，不含请求 URL、凭据或响应正文；
失败与 blocked、空结果三者互不替代。
"""
from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import UA, fetch


class SearchBlocked(RuntimeError):
    """未配置或未知提供方：不是「查过无结果」，也不是请求失败。"""


class SearchFailed(RuntimeError):
    """提供方请求失败：消息可落库、可回传模型，但不得含请求 URL、凭据或响应正文。"""


def _failed(exc: Exception) -> SearchFailed:
    """把提供方异常压成安全摘要：只留异常类型名与真实 HTTP 状态码。"""
    if isinstance(exc, httpx.HTTPStatusError):
        return SearchFailed(f"搜索服务返回 HTTP {exc.response.status_code}（{type(exc).__name__}）")
    return SearchFailed(f"搜索服务请求失败（{type(exc).__name__}）")


def _search_rows(response: httpx.Response, path: str) -> list[dict[str, Any]]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise SearchFailed('搜索服务返回非对象结果')
    metadata, info = payload.get('search_metadata', {}), payload.get('search_information', {})
    if not isinstance(metadata, dict) or not isinstance(info, dict):
        raise SearchFailed('搜索服务返回无效结果状态')
    # SerpApi documents an error message even for a successful, fully empty search.
    if path == 'organic_results' and metadata.get('status') == 'Success' and (
            str(info.get('organic_results_state', '')).casefold() == 'fully empty'):
        if payload.get('organic_results', []) != []:
            raise SearchFailed('搜索服务的空结果状态与记录矛盾')
        return []
    if payload.get('error') or payload.get('errors') or metadata.get('status') in {'Error', 'Processing', 'Queued'}:
        raise SearchFailed('搜索服务未返回成功的检索结果')
    rows = payload
    for key in path.split('.'):
        if not isinstance(rows, dict) or key not in rows:
            raise SearchFailed('搜索服务缺少可核验的结果集合')
        rows = rows[key]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise SearchFailed('搜索服务结果集合格式无效')
    return rows


def web_search(settings: Any, query: str, n: int = 10) -> list[dict[str, Any]]:
    prov, key = settings.websearch_provider, settings.websearch_api_key
    if prov == "none" or not key:
        raise SearchBlocked("未配置全网搜索（CIW_WEBSEARCH_PROVIDER / CIW_WEBSEARCH_API_KEY）")
    try:
        with httpx.Client(timeout=settings.http_timeout_s, headers={"User-Agent": UA}) as c:
            if prov == "tavily":
                r = c.post("https://api.tavily.com/search",
                           json={"api_key": key, "query": query, "max_results": n, "search_depth": "advanced"})
                r.raise_for_status()
                return [{"title": x.get("title"), "url": x.get("url"), "snippet": x.get("content"),
                         "date": x.get("published_date")} for x in _search_rows(r, 'results')]
            if prov == "bing":
                r = c.get("https://api.bing.microsoft.com/v7.0/search", params={"q": query, "count": n},
                          headers={"Ocp-Apim-Subscription-Key": key})
                r.raise_for_status()
                return [{"title": x.get("name"), "url": x.get("url"), "snippet": x.get("snippet"),
                         "date": x.get("datePublished")} for x in _search_rows(r, 'webPages.value')]
            if prov == "serpapi":
                r = c.get("https://serpapi.com/search.json", params={"q": query, "num": n, "api_key": key})
                r.raise_for_status()
                return [{"title": x.get("title"), "url": x.get("link"), "snippet": x.get("snippet"),
                         "date": x.get("date")} for x in _search_rows(r, 'organic_results')]
    except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _failed(exc) from None  # 不链原始异常：其消息可能带请求 URL 与密钥
    raise SearchBlocked(f"未知搜索提供方：{prov}")


class WebSearchArgs(BaseModel):
    query: str = Field(description="搜索词；可用 site: 限定，如 site:cde.org.cn 伊普可泮")
    max_results: int = Field(default=10, ge=1, le=20)
    route_id: str = Field(description="检索路线 ID，如 china:web:company-pipeline")
    region: str = "global"


@REGISTRY.register("web_search", "全网搜索（会议摘要、企业管线、新闻稿、监管公告）。返回标题、URL、摘要。", WebSearchArgs)
def _web_search(ctx: ToolContext, a: WebSearchArgs) -> Any:
    try:
        rows = web_search(ctx.settings, a.query, a.max_results)
    except SearchBlocked as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, a.query, "blocked", note=str(exc))
        return {"status": "blocked", "error": str(exc)}
    except Exception as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, a.query, "failed", note=str(exc)[:300])
        raise
    if ctx.db and ctx.run_id:
        ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, a.query, "ok", hits=len(rows))
    return {"count": len(rows), "results": rows}


class FetchUrlArgs(BaseModel):
    url: str
    kind: str = Field(default="web", description="conference|company|regulator|news|web")
    offset: int = Field(default=0, ge=0)


@REGISTRY.register("fetch_url", "读取网页或文本PDF并登记原件与正文来源。PDF保留页码；长文用offset分页。", FetchUrlArgs)
def _fetch_url(ctx: ToolContext, a: FetchUrlArgs) -> Any:
    if not a.url.startswith(("http://", "https://")):
        raise ValueError("只支持 http(s) URL")
    f = fetch(ctx, a.url, kind=a.kind)
    return {"source_url": f.url, "source_id": f.source_id, "text": f.text[a.offset:a.offset + 12000],
            "offset":a.offset,"total_chars": len(f.text),
            "next_offset":a.offset+12000 if a.offset+12000<len(f.text) else None,
            "pages":f.meta.get('pages',[]),'text_parser_id':f.meta.get('text_parser_id')}
