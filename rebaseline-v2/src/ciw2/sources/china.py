"""中国注册/监管来源：药物临床试验登记与信息公示平台（chinadrugtrials）、CDE、NMPA。
实测（rebaseline 时）：chinadrugtrials 搜索接口对普通 HTTP 客户端返回 202 + JS 挑战页，
无法用 httpx 直接抓取；CDE/NMPA 列表页大量依赖前端渲染。因此：
- M0（本包）：`china_registry_search` 先尝试直连；识别到反爬/挑战页 → 记为 blocked，
  并自动退回到 site: 限定的全网搜索（需配置搜索提供方），结果标注为「线索」。
- M2：专用空间已接登记列表/详情、CDE受理及已观察的新报序列、NMPA证书；其他栏目未闭合。
任何时候都不得把 blocked 当成「中国无此药/无试验」。
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.china_browser import BrowserBlocked, BrowserFailed, browser_search
from ciw2.sources.http import FetchError, fetch
from ciw2.sources.websearch import SearchBlocked, SearchFailed, web_search

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
        raise RegistryBlocked(f"{registry} 无可用直连检索接口，按已配置浏览器能力或site备用继续")
    try:
        f = fetch(ctx, url, kind=registry, params={"keywords": query}, register=False, retries=0)
    except FetchError as exc:
        raise RegistryBlocked(str(exc)) from exc
    if looks_like_challenge(f.status, f.text):
        raise RegistryBlocked(f"{registry} 返回 JS 挑战页（HTTP {f.status}），需 M2 浏览器适配器")
    raise RegistryBlocked(f"{registry} 列表解析器未实现（M2）")


def _persist_browser_candidates(ctx: ToolContext, captured: dict[str, Any], route: str) -> None:
    """Adopt explicit registry labels as provisional candidates, never clinical/MAH facts."""
    source_id = captured['source_id']
    if not ctx.db.one('SELECT id FROM sources WHERE id=? AND project_id=?',(source_id,ctx.project_id)):
        raise BrowserFailed('浏览器来源不属于当前项目')
    existing = {drug['name']:drug for drug in ctx.db.entities(ctx.project_id,'drug')}
    with ctx.db.tx():
        for row in captured['results']:
            name = row['drug_name']
            refs = list(existing.get(name,{}).get('attrs',{}).get('registry_list_refs',[]))
            reference = {'ctr':row['ctr'],'source_id':source_id}
            if reference not in refs:
                refs.append(reference)
            drug_id,_ = ctx.db.upsert_entity(ctx.project_id,'drug',name,route_id=route,
                attrs={'registry_list_refs':refs})
            existing.setdefault(name,{'attrs':{}})['attrs']['registry_list_refs'] = refs
            trial_id,_ = ctx.db.upsert_entity(ctx.project_id,'trial',row['ctr'],route_id=route,
                attrs={'registry_title':row['title'],'registry_indication':row['indication'],
                    'registry_status_text':row['status_text'],'registry_source_id':source_id,
                    'registry_detail_id':row['detail_id']})
            ctx.db.link(ctx.project_id,drug_id,'drug-trial',trial_id,attrs={'source_id':source_id,
                'relation':'explicit_registry_drug_label','page':row['page'],'row_number':row['row_number']})


class ChinaArgs(BaseModel):
    registry: Literal["chinadrugtrials", "cde", "nmpa"]
    query: str = Field(description="中文或英文关键词：适应症中文名、药物中文名/代号、企业名、靶点")
    route_id: str = Field(description="如 china:cde:indication")
    query_kind: Literal['keyword','drug_name','company','acceptance_number','indication','target'] = Field(
        default='keyword',description='CDE公开目录需明确药名、企业或受理号；不能将适应症/靶点误作药名')
    cde_section: Literal['acceptance','new_review_task_chemical_ind','new_review_task_biological_trial'] = Field(
        default='acceptance',description='CDE受理目录或化药IND/生物临床试验申请新报序列；新报需精确受理号')


@REGISTRY.register("china_registry_search",
                   "检索中国注册/监管来源（登记平台 / CDE / NMPA）。直连被拦截时自动退回 site: 限定全网搜索，"
                   "返回 mode=direct|browser|site_search|blocked；blocked 不代表无结果。", ChinaArgs)
def _china(ctx: ToolContext, a: ChinaArgs) -> Any:
    reg = REGISTRIES[a.registry]
    try:
        rows = direct_search(ctx, a.registry, a.query)
        mode = "direct"
    except RegistryBlocked as blocked:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, "china", a.query, "blocked", note=str(blocked)[:300])
        if a.registry == 'chinadrugtrials' and ctx.settings.china_ego_space_id is not None:
            try:
                captured = browser_search(ctx,a.query)
            except (BrowserBlocked,BrowserFailed) as exc:
                if ctx.db and ctx.run_id:
                    status = 'blocked' if isinstance(exc,BrowserBlocked) else 'failed'
                    ctx.db.log_coverage(ctx.run_id,f'{a.route_id}:browser','china',a.query,status,note=str(exc))
            else:
                _persist_browser_candidates(ctx,captured,a.route_id)
                if ctx.db and ctx.run_id:
                    ctx.db.log_coverage(ctx.run_id,f'{a.route_id}:browser','china',a.query,'ok',hits=len(captured['results']))
                return {**captured,'mode':'browser','persisted':True,'registry':reg['label'],'count':len(captured['results'])}
        if a.registry == 'cde' and ctx.settings.china_ego_space_id is not None:
            from ciw2.sources import cde_browser, cde_review_browser
            adapter=cde_browser if a.cde_section=='acceptance' else cde_review_browser
            try:
                captured = (adapter.browser_search(ctx,a.query,a.query_kind,section=a.cde_section)
                            if a.cde_section=='new_review_task_biological_trial'
                            else adapter.browser_search(ctx,a.query,a.query_kind))
            except (BrowserBlocked,BrowserFailed) as exc:
                status = 'blocked' if isinstance(exc,BrowserBlocked) else 'failed'
                ctx.db.log_coverage(ctx.run_id,f'{a.route_id}:browser','china',a.query,status,note=str(exc))
            else:
                if a.cde_section=='acceptance':
                    cde_browser.persist_candidates(ctx,captured,a.route_id)
                else:
                    captured['linked_refs']=cde_review_browser.persist_refs(ctx,captured,a.route_id)
                ctx.db.log_coverage(ctx.run_id,f'{a.route_id}:browser','china',a.query,'ok',hits=len(captured['results']))
                persisted=a.cde_section=='acceptance' or captured['linked_refs']>0
                return {**captured,'mode':'browser','persisted':persisted,'registry':reg['label'],'count':len(captured['results'])}
        try:
            rows = web_search(ctx.settings, f"site:{reg['site']} {a.query}", 10)
            mode = "site_search"
        except SearchBlocked as exc:
            if ctx.db and ctx.run_id:
                ctx.db.log_coverage(ctx.run_id, f'{a.route_id}:site', 'china', a.query, 'blocked', note=str(exc))
            return {"mode": "blocked", "registry": reg["label"], "error": f"{blocked}；且 {exc}"}
        except SearchFailed as exc:
            if ctx.db and ctx.run_id:
                ctx.db.log_coverage(ctx.run_id, f'{a.route_id}:site', 'china', a.query, 'failed', note=str(exc))
            raise
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, f"{a.route_id}:site", "china", a.query, "ok", hits=len(rows))
    return {"mode": mode, "registry": reg["label"], "count": len(rows), "results": rows}
