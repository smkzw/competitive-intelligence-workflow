"""PubMed / PMC（NCBI E-utilities）。读取题录/摘要与 PMC 开放全文；全文仅存本地 CAS，不入 git。"""
from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import FetchError, fetch, register_text

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



@REGISTRY.register("pubmed_fetch", "获取 PubMed 记录或 PMC 开放全文，返回固定来源与实际内容层级。", PubFetchArgs)
def _pubmed_fetch(ctx: ToolContext, a: PubFetchArgs) -> Any:
    if not re.fullmatch(r"\d{4,9}", a.pmid):
        raise ValueError("PMID 不合法")
    pmcid = None
    status = "not_requested"
    if a.full_text:
        rows = esummary(ctx, [a.pmid])
        if rows and (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
                     or str(rows[0].get("pmid", "")) != a.pmid):
            raise FetchError("esummary 未能唯一对应请求的 PMID")
        pmcid = rows[0].get("pmcid") if rows else None
        status = "not_in_pmc" if rows else "metadata_unresolved"
    if pmcid:
        match = re.fullmatch(r"(?:PMC)?([0-9]+)", str(pmcid).strip())
        if not match:
            raise FetchError("esummary 中的 PMCID 无效")
        pmcid = "PMC" + match[1]
        f = fetch(ctx, f"{EUTILS}/efetch.fcgi", kind="pmc", title=pmcid, register=False,
                  params={"db": "pmc", "id": pmcid, "rettype": "xml", **_key(ctx)})
        try:
            root = ElementTree.fromstring(f.content)
        except ElementTree.ParseError as exc:
            raise FetchError("PMC XML 无法解析") from exc
        articles = ([root] if root.tag == "article" else list(root.findall("article"))
                    if root.tag == "pmc-articleset" else [])
        if len(articles) != 1:
            raise FetchError("PMC XML 没有唯一 article")
        article = articles[0]
        ids = article.findall("front/article-meta/article-id")
        pmcs = [(n.text or "").strip() for n in ids if n.get("pub-id-type") in {"pmcid", "pmc"}]
        pmids = [(n.text or "").strip() for n in ids if n.get("pub-id-type") == "pmid"]
        if not pmcs or any(value not in {pmcid, match[1]} for value in pmcs):
            raise FetchError("PMC XML 的 PMCID 与请求不一致")
        if any(value != a.pmid for value in pmids):
            raise FetchError("PMC XML 的 PMID 与请求不一致")
        body = article.find("body")
        if body is None or not "".join(body.itertext()).strip():
            raise FetchError("PMC XML 缺少正文")
        text = re.sub(r"<[^>]+>", " ", f.text)
        text = re.sub(r"\s+", " ", text)
        kind, title, level, status = "pmc", pmcid, "pmc_full_text", "available"
        url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    else:
        f = fetch(ctx, f"{EUTILS}/efetch.fcgi", kind="pubmed", title=a.pmid, register=False,
                  params={"db": "pubmed", "id": a.pmid, "rettype": "abstract", "retmode": "text", **_key(ctx)})
        markers = re.findall(r"(?m)^PMID:[ \t]*([0-9]+)(?=[ \t\r\n]|$)", f.text)
        if not f.text.strip() or markers != [a.pmid]:
            raise FetchError("PubMed 记录缺少唯一 PMID 标记")
        text, kind, title, level = f.text, "pubmed", a.pmid, "pubmed_record"
        url = f"https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/"
    sid = register_text(ctx, kind=kind, url=url, text=text, raw=f.content,
                        title=title, meta={"fetched_url": f.url})
    return {"source_url": url, "source_id": sid, "text": text[a.offset:a.offset + 12000],
            "total_chars": len(text), "pmid": a.pmid, "content_level": level,
            "full_text_requested": a.full_text, "full_text_status": status}
