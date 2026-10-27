"""ClinicalTrials.gov v2：按条件检索介入性研究，逐条入 CAS。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from ciw.http import get_json
from ciw.models import Source
from ciw.store import Workspace

API = "https://clinicaltrials.gov/api/v2/studies"
STUDY_URL = "https://clinicaltrials.gov/study/{nct}"


def _paged(params: dict[str, Any]) -> Iterable[dict[str, Any]]:
    token = None
    while True:
        q = dict(params, pageSize=100, format="json")
        if token:
            q["pageToken"] = token
        page = get_json(API, q, timeout=120)
        yield from page.get("studies", [])
        token = page.get("nextPageToken")
        if not token:
            return


def search_and_store(
    ws: Workspace, *, conditions: list[str], intervention_queries: list[str] = ()
) -> dict[str, tuple[Source, dict[str, Any]]]:
    """返回 {NCT: (Source, study_json)}；同一 NCT 多次命中只存一次，并记录命中原因。"""
    found: dict[str, tuple[Source, dict[str, Any]]] = {}
    queries = [("query.cond", c) for c in conditions] + [("query.intr", q) for q in intervention_queries]
    for key, value in queries:
        params = {key: value, "filter.advanced": "AREA[StudyType]INTERVENTIONAL"}
        for study in _paged(params):
            nct = study["protocolSection"]["identificationModule"]["nctId"]
            if nct in found:
                continue
            data = json.dumps(study, ensure_ascii=False, sort_keys=True).encode()
            ident = study["protocolSection"]["identificationModule"]
            src = ws.record_source(
                kind="ctgov",
                url=STUDY_URL.format(nct=nct),
                data=data,
                ext="json",
                title=ident.get("briefTitle", ""),
                publisher="ClinicalTrials.gov",
                published_at=study["protocolSection"]
                .get("statusModule", {})
                .get("lastUpdatePostDateStruct", {})
                .get("date"),
            )
            found[nct] = (src, study)
    return found


def load_from_sources(ws: Workspace) -> dict[str, tuple[Source, dict[str, Any]]]:
    """离线重跑：从 CAS 里取每个 NCT 最新获取的记录。"""
    latest: dict[str, tuple[Source, dict[str, Any]]] = {}
    for src in sorted((s for s in ws.sources() if s.kind == "ctgov"), key=lambda s: s.fetched_at):
        study = json.loads(ws.read_source(src.source_id))
        nct = study["protocolSection"]["identificationModule"]["nctId"]
        latest[nct] = (src, study)
    return latest
