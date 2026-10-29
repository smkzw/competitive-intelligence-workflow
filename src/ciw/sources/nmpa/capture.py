"""NMPA public catalogue → exact detail reader → literal certificate inbox."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ciw.config import IndicationConfig
from ciw.models import stable_id
from ciw.sources.browser import run_script
from ciw.sources.nmpa.parser import DOMESTIC, FOREIGN, content_key, parse_detail
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
        if "rows" not in row and path.exists():
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
            created = _save_detail(folder, pages[0])
            summary["details" if created else "resumed"] += 1
        except (ValueError, KeyError, TypeError) as exc:
            summary["failures"].append(dict(number=number, reason=str(exc), error_code=end.get("error_code")))
        if end.get("status") in {"user_control", "verification_required", "network_error"}:
            break
    return summary


def _save_detail(folder, raw):
    """Keep the first capture and every changed record; never overwrite historical or invalid bytes."""
    number, category = raw["registration_number"], raw["category"]
    if datetime.fromisoformat(raw["observed_at"]).tzinfo is None:
        raise ValueError("NMPA capture lacks a timezone")
    digest = content_key(raw)
    versions = []
    for path in folder.glob(f"certificate-{number}*.json"):
        try:
            old = json.loads(path.read_text())
            parse_detail(old, registration_number=number, category=category)
            observed = datetime.fromisoformat(old["observed_at"])
            if observed.tzinfo is not None:
                versions.append((observed, content_key(old)))
        except (ValueError, KeyError, TypeError):
            continue
    if versions:
        latest = max(v[0] for v in versions)
        if {key for time, key in versions if time == latest} == {digest}:
            return False
    path = folder / f"certificate-{number}.json"
    if path.exists():
        # Include the observation in the immutable file name: A→B→A is a new current version.
        suffix = stable_id("v", raw)
        path = folder / f"certificate-{number}-{suffix}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(raw, handle, ensure_ascii=False)
    return True


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
            result = dict(query=query, category=category, rows=rows, end=end, observed_at=now_iso())
            name = "list-" + datetime.now(UTC).isoformat(timespec="microseconds").replace(":", "") + ".json"
            with (folder / name).open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False)
            summary["queries"].append(dict(query=query, category=category, **end))
            for row in rows:
                links[(category, row["registration_number"])] = row
            if end.get("status") in {"user_control", "verification_required", "network_error"}:
                summary["blocked"] = end["status"]
                return
