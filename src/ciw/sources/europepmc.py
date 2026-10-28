"""Europe PMC discovery: literal registration IDs, source bytes, and explicit failures."""

from __future__ import annotations

import json
import re
import urllib.request
from urllib.parse import parse_qs, urlencode, urlparse

from lxml import html

from ciw.models import stable_id
from ciw.store import Workspace, now_iso

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_ID = re.compile(r"\b(?:NCT|CTR)[0-9]{8}\b", re.I)
_EXCLUDE = re.compile(
    r"systematic review|meta[- ]analysis|post[- ]hoc|secondary analysis|subgroup analysis|study protocol|"
    r"rationale and design|design and rationale",
    re.I,
)


def is_registry_id(text: str) -> bool:
    return bool(_ID.fullmatch(text))


def plain_abstract(paper: dict) -> str:
    text = paper.get("abstractText") or ""
    if not text:
        return ""
    return " ".join(html.fragment_fromstring(text, create_parent="div").text_content().split())


def discover(ws: Workspace, registry_ids: list[str], *, offline: bool = False,
             reuse: bool = False) -> tuple[list[dict], dict]:
    wanted = {s.upper() for s in registry_ids}
    if any(not _ID.fullmatch(s) for s in wanted):
        raise ValueError("论文发现仅接受明确NCT或CTR号")
    state = ws.read_stage("publication-search") or {}
    completed = {
        parse_qs(urlparse(s.url).query).get("query", [""])[0].strip('"') for s in ws.sources() if s.kind == "europepmc"
    }
    if not offline:
        for identifier in sorted(wanted):
            if reuse and identifier in completed and state.get(identifier, {}).get("status") == "ok":
                continue
            try:
                _fetch(ws, identifier)
                state[identifier] = {"status": "ok", "checked_at": now_iso()}
            except (OSError, ValueError) as exc:
                state[identifier] = {
                    "status": "failed",
                    "checked_at": now_iso(),
                    "error": type(exc).__name__,
                    "http_status": getattr(exc, "code", None),
                }
        ws.write_stage("publication-search", state)
    failures = [
        {"registry_id": key, **value}
        for key, value in sorted(state.items())
        if key in wanted and value["status"] == "failed"
    ]
    completed = {
        parse_qs(urlparse(s.url).query).get("query", [""])[0].strip('"') for s in ws.sources() if s.kind == "europepmc"
    }
    pending = sorted(wanted - completed)
    records = _records(ws, wanted)
    eligible = [r for r in records if not r["excluded_type"] and r["text"]]
    conflicts = sum(r["version_conflict"] for r in records)
    coverage = {
        "source": "publications",
        "status": "partial" if failures or conflicts or pending else "ok",
        "records": len(records),
        "eligible": len(eligible),
        "failures": failures,
        "version_conflicts": conflicts,
        "mode": "offline" if offline else "reuse" if reuse else "online",
        "requested": len(wanted),
        "pending_ids": pending,
    }
    return records, coverage


def _fetch(ws: Workspace, identifier: str) -> None:
    cursor, seen = "*", set()
    while cursor:
        if cursor in seen:
            raise ValueError("Europe PMC pagination repeated its cursor")
        seen.add(cursor)
        url = (
            SEARCH
            + "?"
            + urlencode(
                {
                    "query": f'"{identifier}"',
                    "format": "json",
                    "resultType": "core",
                    "pageSize": 100,
                    "cursorMark": cursor,
                }
            )
        )
        request = urllib.request.Request(url, headers={"User-Agent": "ciw/2.0 clinical research"})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
        doc = json.loads(raw)
        if not isinstance(doc.get("resultList", {}).get("result"), list):
            raise ValueError("Europe PMC response lacks resultList.result")
        ws.record_source(
            kind="europepmc", url=url, data=raw, ext="json", title=f"论文检索：{identifier}", publisher="Europe PMC"
        )
        if not doc["resultList"]["result"]:
            break
        next_cursor = doc.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor


def _records(ws: Workspace, wanted: set[str]) -> list[dict]:
    current = {}
    for source in sorted(ws.sources(), key=lambda s: s.source_id):
        if source.kind != "europepmc":
            continue
        doc = json.loads(ws.read_source(source.source_id))
        for index, paper in enumerate(doc.get("resultList", {}).get("result", [])):
            text = plain_abstract(paper)
            ids = sorted(wanted & {m.upper() for m in _ID.findall(text)})
            if not ids:
                continue  # A search hit/citation alone does not bind a publication to a trial.
            title = paper.get("title", "")
            types = paper.get("pubTypeList", {}).get("pubType", [])
            excluded = paper.get("source") != "MED" or any(
                str(t).casefold() in {"review", "meta-analysis", "clinical trial protocol"} for t in types
            )
            key = (paper.get("source"), paper.get("id"))
            version = stable_id("paper", title, text, types, paper.get("doi", ""))
            candidate = {
                "source_id": source.source_id,
                "source_sha": source.sha256,
                "path": f"$.resultList.result[{index}].abstractText",
                "paper_id": paper.get("id"),
                "doi": paper.get("doi", ""),
                "title": title,
                "text": text,
                "registry_ids": ids,
                "excluded_type": excluded or bool(_EXCLUDE.search(title)),
            }
            previous = current.get(key)
            if previous is None or source.fetched_at > previous["fetched_at"]:
                current[key] = {"fetched_at": source.fetched_at, "versions": {version: candidate}}
            elif source.fetched_at == previous["fetched_at"]:
                previous["versions"].setdefault(version, candidate)
    records = []
    for key in sorted(current):
        versions = current[key]["versions"]
        for version in sorted(versions):
            record = versions[version]
            record["version_conflict"] = len(versions) > 1
            record["excluded_type"] |= record["version_conflict"]
            records.append(record)
    return records
