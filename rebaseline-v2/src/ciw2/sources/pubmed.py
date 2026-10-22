"""PubMed / PMC（NCBI E-utilities）。只取摘要与 PMC 开放全文；全文仅存本地 CAS，不入 git。"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import fetch, register_text

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _key(ctx: ToolContext) -> dict[str, str]:
    k = getattr(getattr(ctx, "settings", None), "ncbi_api_key", "")
    return {"api_key": k} if k else {}


def esearch(ctx: ToolContext, query: str, retmax: int = 20) -> list[str]:
    f = fetch(ctx, f"{EUTILS}/esearch.fcgi", kind="pubmed", register=False,
              params={"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json", "sort": "relevance",
                      **_key(ctx)})
    return f.json().get("esearchresult", {}).get("idlist", [])


def esummary(ctx: ToolContext, pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []
    f = fetch(ctx, f"{EUTILS}/esummary.fcgi", kind="pubmed", register=False,
              params={"db": "pubmed", "id": ",".join(pmids), "retmode": "json", **_key(ctx)})
    res = f.json().get("result", {})
    out = []
    for pid in res.get("uids", []):
        r = res[pid]
        ids = {i.get("idtype"): i.get("value") for i in r.get("articleids", [])}
        out.append({"pmid": pid, "title": r.get("title"), "journal": r.get("fulljournalname"),
                    "pubdate": r.get("pubdate"), "pmcid": ids.get("pmc"), "doi": ids.get("doi"),
                    "pubtypes": r.get("pubtype", []), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"})
    return out


class PubSearchArgs(BaseModel):
    query: str = Field(description="PubMed 检索式，如 (iptacopan) AND (paroxysmal nocturnal hemoglobinuria)")
    max_results: int = Field(default=20, ge=1, le=100)
    route_id: str = "global:pubmed"
    region: str = "global"


@REGISTRY.register("pubmed_search", "检索 PubMed，返回 PMID、题目、期刊、日期、PMCID。", PubSearchArgs)
def _pubmed_search(ctx: ToolContext, a: PubSearchArgs) -> Any:
    try:
        rows = esummary(ctx, esearch(ctx, a.query, a.max_results))
    except Exception as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, a.query, "failed", note=str(exc)[:300])
        raise
    if ctx.db and ctx.run_id:
        ctx.db.log_coverage(ctx.run_id, a.route_id, a.region, a.query, "ok", hits=len(rows))
    return {"count": len(rows), "articles": rows}


class PubFetchArgs(BaseModel):
    pmid: str
    full_text: bool = Field(default=False, description="有 PMCID 时尝试获取 PMC 开放全文")
    offset: int = Field(default=0, ge=0, description="长文分页读取的起始字符")


@REGISTRY.register("pubmed_fetch", "获取 PubMed 摘要（或 PMC 开放全文），登记为来源，返回 source_url 与文本。", PubFetchArgs)
def _pubmed_fetch(ctx: ToolContext, a: PubFetchArgs) -> Any:
    if not re.fullmatch(r"\d{4,9}", a.pmid):
        raise ValueError("PMID 不合法")
    url = f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/"
    if a.full_text:
        meta = esummary(ctx, [a.pmid])
        pmcid = meta[0].get("pmcid") if meta else None
        if pmcid:
            f = fetch(ctx, f"{EUTILS}/efetch.fcgi", kind="pmc", title=pmcid,
                      params={"db": "pmc", "id": pmcid, "rettype": "xml", **_key(ctx)})
            text = re.sub(r"<[^>]+>", " ", f.text)
            text = re.sub(r"\s+", " ", text)
            canonical = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
            sid = register_text(ctx, kind='pmc', url=canonical, text=text, raw=f.content,
                                title=pmcid, meta={'fetched_url': f.url})
            return {"source_url": canonical, "source_id": sid,
                    "text": text[a.offset:a.offset + 12000], "total_chars": len(text)}
    f = fetch(ctx, f"{EUTILS}/efetch.fcgi", kind="pubmed", title=a.pmid,
              params={"db": "pubmed", "id": a.pmid, "rettype": "abstract", "retmode": "text", **_key(ctx)})
    sid = register_text(ctx, kind='pubmed', url=url, text=f.text, raw=f.content,
                        title=a.pmid, meta={'fetched_url': f.url})
    return {"source_url": url, "source_id": sid, "text": f.text[a.offset:a.offset + 12000],
            "total_chars": len(f.text)}
