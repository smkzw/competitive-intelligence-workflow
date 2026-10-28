"""Official NLM fallback. Preserve ESearch/EFetch XML; search hits alone never bind a trial."""
from __future__ import annotations

import time
import urllib.request
from urllib.parse import urlencode

from lxml import etree

from ciw.models import stable_id
from ciw.sources.europepmc import _ID, excluded_publication
from ciw.store import now_iso

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
_last_request = 0.0


def parse_xml(raw):
    try:
        root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
    except etree.XMLSyntaxError:
        raise ValueError("PubMed XML无法解析") from None
    if any(isinstance(node, etree._Entity) for node in root.iter()):
        raise ValueError("PubMed XML包含未解析实体")
    return root


def abstract_text(node):
    return "\n".join(" ".join("".join(p.itertext()).split()) for p in node.findall("AbstractText"))


def _get(url):
    global _last_request
    # ponytail: per-process admission; CIW research acquisition runs serially.
    time.sleep(max(0, 0.35 - (time.monotonic() - _last_request)))
    _last_request = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "ciw/2.0 clinical research"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _store(ws, operation, parameters):
    url = BASE + operation + "?" + urlencode({"db": "pubmed", "tool": "ciw", **parameters})
    raw = _get(url)
    root = parse_xml(raw)
    expected = "eSearchResult" if operation == "esearch.fcgi" else "PubmedArticleSet"
    if root.tag != expected or root.find("ERROR") is not None:
        raise ValueError("PubMed未返回预期记录")
    source = ws.record_source(kind="pubmed", url=url, data=raw, ext="xml", publisher="NCBI PubMed")
    return root, source


def _fetch(ws, identifier):
    start, pmids, source_ids, total = 0, [], [], None
    while True:
        root, source = _store(ws, "esearch.fcgi", dict(term=identifier, retmode="xml", retstart=start, retmax=100))
        count = root.findtext("Count")
        page = root.findall("IdList/Id")
        if not count or not count.isdigit() or any(not (p.text or "").isdigit() for p in page):
            raise ValueError("PubMed检索数量或身份字段无效")
        if total is not None and int(count) != total:
            raise ValueError("PubMed分页期间检索集合变化")
        total = int(count)
        source_ids.append(source.source_id)
        ids = [p.text for p in page]
        if start + len(ids) > total:
            raise ValueError("PubMed检索数量与记录不一致")
        if (not ids and start < int(count)) or len(ids) != len(set(ids)) or set(ids).intersection(pmids):
            raise ValueError("PubMed分页不完整或重复")
        pmids.extend(ids)
        start += len(ids)
        if start >= int(count):
            break
    for index in range(0, len(pmids), 100):
        requested = pmids[index:index + 100]
        root, source = _store(ws, "efetch.fcgi", dict(id=",".join(requested), retmode="xml"))
        returned = (root.findall("PubmedArticle/MedlineCitation/PMID")
                    + root.findall("PubmedBookArticle/BookDocument/PMID"))
        if len(returned) != len(requested) or {p.text for p in returned} != set(requested):
            raise ValueError("PubMed原文记录与请求的PMID集合不一致")
        source_ids.append(source.source_id)
    return source_ids, sorted(set(pmids))


def discover(ws, registry_ids, *, offline=False, reuse=False):
    wanted = {s.upper() for s in registry_ids}
    if any(not _ID.fullmatch(s) for s in wanted):
        raise ValueError("PubMed检索仅接受明确登记号")
    state = ws.read_stage("pubmed-search") or {}
    known = {s.source_id for s in ws.sources() if s.kind == "pubmed"}
    if not offline:
        for identifier in sorted(wanted):
            old = state.get(identifier, {})
            if reuse and old.get("status") == "ok" and old.get("source_ids") and set(old["source_ids"]) <= known:
                continue
            try:
                source_ids, pmids = _fetch(ws, identifier)
                state[identifier] = dict(status="ok", checked_at=now_iso(), source_ids=source_ids, pmids=pmids)
            except (OSError, ValueError) as exc:
                state[identifier] = dict(status="failed", checked_at=now_iso(), error=type(exc).__name__,
                                         http_status=getattr(exc, "code", None))
            ws.write_stage("pubmed-search", state)
    failures = [dict(registry_id=k, **state[k]) for k in sorted(wanted) if state.get(k, {}).get("status") == "failed"]
    known = {s.source_id for s in ws.sources() if s.kind == "pubmed"}
    pending = sorted(k for k in wanted if state.get(k, {}).get("status") != "ok"
                     or not state[k].get("source_ids") or not set(state[k]["source_ids"]) <= known)
    papers = records(ws, wanted)
    return papers, dict(source="pubmed", status="partial" if pending else "ok", requested=len(wanted),
        records=len(papers), eligible=sum(not p["excluded_type"] for p in papers), failures=failures,
        pending_ids=pending, mode="offline" if offline else "reuse" if reuse else "online")


def records(ws, wanted):
    candidates = []
    for source in ws.sources():
        if source.kind != "pubmed":
            continue
        root = parse_xml(ws.read_source(source.source_id))
        for article in root.findall("PubmedArticle"):
            citation = article.find("MedlineCitation")
            pmid = citation.findtext("PMID") if citation is not None else None
            abstract = article.find("MedlineCitation/Article/Abstract")
            if not pmid or not pmid.isdigit() or abstract is None:
                continue
            text = abstract_text(abstract)
            ids = sorted(set(wanted) & {m.upper() for m in _ID.findall(text)})
            if not ids:
                continue
            title_node = article.find("MedlineCitation/Article/ArticleTitle")
            if title_node is None:
                raise ValueError("PubMed文章缺少标题")
            title = "".join(title_node.itertext())
            types = article.findall("MedlineCitation/Article/PublicationTypeList/PublicationType")
            doi = article.findtext("PubmedData/ArticleIdList/ArticleId[@IdType='doi']") or ""
            candidates.append(dict(source_id=source.source_id, source_sha=source.sha256, paper_id=pmid, doi=doi,
                path=f"xpath:./PubmedArticle[MedlineCitation/PMID='{pmid}']/MedlineCitation/Article/Abstract",
                title=title, text=text, registry_ids=ids,
                excluded_type=excluded_publication(title, [p.text for p in types]),
                version_conflict=False))
    return merge_records(ws, candidates)


def merge_records(ws, papers):
    """Choose the latest observed version; conflicting simultaneous versions remain excluded."""
    dates = {s.source_id: s.fetched_at for s in ws.sources()}
    current = {}
    for paper in papers:
        key, stamp = str(paper["paper_id"]), dates[paper["source_id"]]
        signature = stable_id("paper", paper["title"], paper["text"], paper["doi"], paper["excluded_type"])
        previous = current.get(key)
        if previous is None or stamp > previous["stamp"]:
            current[key] = dict(stamp=stamp, versions={signature: paper})
        elif stamp == previous["stamp"]:
            previous["versions"].setdefault(signature, paper)
    out = []
    for key in sorted(current):
        versions = current[key]["versions"]
        for signature in sorted(versions):
            item = dict(versions[signature])
            item["version_conflict"] |= len(versions) > 1
            item["excluded_type"] |= item["version_conflict"]
            out.append(item)
    return out
