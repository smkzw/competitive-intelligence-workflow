"""全网搜索 + 通用网页读取（会议摘要、企业管线页、新闻稿、监管公告）。
提供方可插拔：tavily | bing | serpapi。未配置时工具返回 blocked，覆盖率如实记为 blocked。
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import UA, fetch


class SearchBlocked(RuntimeError):
    pass


def web_search(settings: Any, query: str, n: int = 10) -> list[dict[str, Any]]:
    prov, key = settings.websearch_provider, settings.websearch_api_key
    if prov == "none" or not key:
        raise SearchBlocked("未配置全网搜索（CIW_WEBSEARCH_PROVIDER / CIW_WEBSEARCH_API_KEY）")
    with httpx.Client(timeout=settings.http_timeout_s, headers={"User-Agent": UA}) as c:
        if prov == "tavily":
            r = c.post("https://api.tavily.com/search",
                       json={"api_key": key, "query": query, "max_results": n, "search_depth": "advanced"})
            r.raise_for_status()
            return [{"title": x.get("title"), "url": x.get("url"), "snippet": x.get("content"),
                     "date": x.get("published_date")} for x in r.json().get("results", [])]
        if prov == "bing":
            r = c.get("https://api.bing.microsoft.com/v7.0/search", params={"q": query, "count": n},
                      headers={"Ocp-Apim-Subscription-Key": key})
            r.raise_for_status()
            return [{"title": x.get("name"), "url": x.get("url"), "snippet": x.get("snippet"),
                     "date": x.get("datePublished")} for x in r.json().get("webPages", {}).get("value", [])]
        if prov == "serpapi":
            r = c.get("https://serpapi.com/search.json", params={"q": query, "num": n, "api_key": key})
            r.raise_for_status()
            return [{"title": x.get("title"), "url": x.get("link"), "snippet": x.get("snippet"),
                     "date": x.get("date")} for x in r.json().get("organic_results", [])]
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


@REGISTRY.register("fetch_url", "读取网页正文并登记为来源（抽取事实前必须先读取原文）。长文用 offset 分页。", FetchUrlArgs)
def _fetch_url(ctx: ToolContext, a: FetchUrlArgs) -> Any:
    if not a.url.startswith(("http://", "https://")):
        raise ValueError("只支持 http(s) URL")
    f = fetch(ctx, a.url, kind=a.kind)
    if "pdf" in f.content_type:
        return {"status": "unsupported", "error": "PDF 解析在 M4 实现（pdfplumber），当前请改用 HTML/摘要页",
                "source_url": f.url}
    return {"source_url": f.url, "source_id": f.source_id, "text": f.text[a.offset:a.offset + 12000],
            "total_chars": len(f.text)}
