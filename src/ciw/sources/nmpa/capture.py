"""NMPA public catalogue → exact detail reader → literal certificate inbox."""

from __future__ import annotations

import json

from ciw.config import IndicationConfig
from ciw.sources.browser import run_script
from ciw.sources.nmpa.parser import DOMESTIC, FOREIGN, parse_detail
from ciw.store import Workspace, now_iso


def capture(
    ws: Workspace, cfg: IndicationConfig, space: int, *, max_details: int | None = None, resume_only: bool = False
) -> dict:
    folder = ws.root / "captures/nmpa"
    folder.mkdir(parents=True, exist_ok=True)
    summary = {"queries": [], "details": 0, "resumed": 0, "failures": []}
    links = {}
    if resume_only:
        for path in sorted(folder.glob("list-*.json")):
            doc = json.loads(path.read_text())
            if doc["query"] in cfg.china.nmpa_queries and doc["end"].get("status") == "ok":
                for row in doc["rows"]:
                    links[(doc["category"], row["registration_number"])] = row
        summary["queries"] = [{"status": "reused", "records": len(links)}]
    else:
        _discover(folder, cfg, space, summary, links)
    if summary.get("blocked"):
        return summary
    for (category, number), row in list(links.items())[:max_details]:
        path = folder / f"certificate-{number}.json"
        if path.exists():
            try:
                parse_detail(json.loads(path.read_text()), registration_number=number, category=category)
                summary["resumed"] += 1
                continue
            except (ValueError, KeyError, TypeError):
                pass
        config = dict(space=space, category=category, query=number, url=row["url"])
        if "rows" in row:
            pages, end = [row], {"status": "ok"}
        else:
            pages, end = run_script("detail.mjs", config, 120, package="ciw.sources.nmpa", helpers=("record.mjs",))
        try:
            if end.get("status") != "ok" or len(pages) != 1:
                raise ValueError(end.get("status", "missing_response"))
            parse_detail(pages[0], registration_number=number, category=category)
            path.write_text(json.dumps(pages[0], ensure_ascii=False), encoding="utf-8")
            summary["details"] += 1
        except (ValueError, KeyError, TypeError) as exc:
            summary["failures"].append(dict(number=number, reason=str(exc)))
        if end.get("status") in {"user_control", "verification_required"}:
            break
    return summary


def _discover(folder, cfg, space, summary, links):
    for query in cfg.china.nmpa_queries:
        for category in (DOMESTIC, FOREIGN):
            rows, end = run_script(
                "browser.mjs",
                dict(space=space, query=query, category=category),
                600,
                package="ciw.sources.nmpa",
                helpers=("record.mjs",),
            )
            result = dict(query=query, category=category, rows=rows, end=end)
            name = "list-" + now_iso().replace(":", "") + ".json"
            (folder / name).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            summary["queries"].append(dict(query=query, category=category, **end))
            for row in rows:
                links[(category, row["registration_number"])] = row
            if end.get("status") in {"user_control", "verification_required"}:
                summary["blocked"] = end["status"]
                return
