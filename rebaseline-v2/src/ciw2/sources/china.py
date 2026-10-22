"""中国注册/监管来源：药物临床试验登记与信息公示平台（chinadrugtrials）、CDE、NMPA。
实测（rebaseline 时）：chinadrugtrials 搜索接口对普通 HTTP 客户端返回 202 + JS 挑战页，
无法用 httpx 直接抓取；CDE/NMPA 列表页大量依赖前端渲染。因此：
- M0（本包）：`china_registry_search` 先尝试直连；识别到反爬/挑战页 → 记为 blocked，
  并自动退回到 site: 限定的全网搜索（需配置搜索提供方），结果标注为「线索」。
- M2：实现 PlaywrightAdapter（真实浏览器渲染，限速 + 本地缓存），登记号 CTR/受理号 CXSL/CXHL 解析为结构化事实。
任何时候都不得把 blocked 当成「中国无此药/无试验」。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import FetchError, fetch
from ciw2.sources.websearch import SearchBlocked, web_search

REGISTRIES = {
    "chinadrugtrials": {"site": "chinadrugtrials.org.cn", "label": "药物临床试验登记与信息公示平台",
                        "search_url": "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml"},
    "cde": {"site": "cde.org.cn", "label": "国家药监局药品审评中心（受理/优先审评/突破性治疗公示）",
            "search_url": None},
    "nmpa": {"site": "nmpa.gov.cn", "label": "国家药监局（药品批准证明文件/上市批准）", "search_url": None},
}


class RegistryBlocked(RuntimeError):
    pass


def looks_like_challenge(status: int, text: str) -> bool:
    t = text[:3000].lower()
    return status == 202 or ("<meta" in t and "content=" in t and len(text) < 40000 and "ctr" not in t
                             and "登记号" not in text)


def direct_search(ctx: ToolContext, registry: str, query: str) -> list[dict[str, Any]]:
    url = REGISTRIES[registry]["search_url"]
    if not url:
        raise RegistryBlocked(f"{registry} 无可用直连检索接口（M2 Playwright 适配器）")
    try:
        f = fetch(ctx, url, kind=registry, params={"keywords": query}, register=False, retries=0)
    except FetchError as exc:
        raise RegistryBlocked(str(exc)) from exc
    if looks_like_challenge(f.status, f.text):
        raise RegistryBlocked(f"{registry} 返回 JS 挑战页（HTTP {f.status}），需 M2 浏览器适配器")
    raise RegistryBlocked(f"{registry} 列表解析器未实现（M2）")


class ChinaArgs(BaseModel):
    registry: Literal["chinadrugtrials", "cde", "nmpa"]
    query: str = Field(description="中文或英文关键词：适应症中文名、药物中文名/代号、企业名、靶点")
    route_id: str = Field(description="如 china:cde:indication")


@REGISTRY.register("china_registry_search",
                   "检索中国注册/监管来源（登记平台 / CDE / NMPA）。直连被拦截时自动退回 site: 限定全网搜索，"
                   "返回 mode=direct|site_search|blocked；blocked 不代表无结果。", ChinaArgs)
def _china(ctx: ToolContext, a: ChinaArgs) -> Any:
    reg = REGISTRIES[a.registry]
    try:
        rows = direct_search(ctx, a.registry, a.query)
        mode = "direct"
    except RegistryBlocked as blocked:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, "china", a.query, "blocked", note=str(blocked)[:300])
        try:
            rows = web_search(ctx.settings, f"site:{reg['site']} {a.query}", 10)
            mode = "site_search"
        except SearchBlocked as exc:
            return {"mode": "blocked", "registry": reg["label"], "error": f"{blocked}；且 {exc}"}
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, f"{a.route_id}:site", "china", a.query, "ok", hits=len(rows))
    return {"mode": mode, "registry": reg["label"], "count": len(rows), "results": rows}
