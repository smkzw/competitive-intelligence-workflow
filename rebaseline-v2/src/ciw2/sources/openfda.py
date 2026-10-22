"""Drugs@FDA（openFDA）。获批状态、申请号、审评文件链接（Letter / Label / Review）。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import FetchError, fetch

API = "https://api.fda.gov/drug/drugsfda.json"


def lookup(ctx: ToolContext, name: str, limit: int = 10) -> list[dict[str, Any]]:
    q = f'openfda.generic_name:"{name}" OR openfda.brand_name:"{name}" OR products.active_ingredients.name:"{name}"'
    try:
        f = fetch(ctx, API, kind="fda", params={"search": q, "limit": limit}, title=f"drugsfda {name}")
    except FetchError as exc:
        if "HTTP 404" in str(exc):   # openFDA 无结果返回 404：这是「查过且无记录」，不是失败
            return []
        raise
    out = []
    for app in f.json().get("results", []):
        subs = app.get("submissions", [])
        orig = [s for s in subs if s.get("submission_type") == "ORIG"]
        out.append({
            "application_number": app.get("application_number"),
            "sponsor": app.get("sponsor_name"),
            "brand_names": sorted({p.get("brand_name") for p in app.get("products", []) if p.get("brand_name")}),
            "marketing_status": sorted({p.get("marketing_status") for p in app.get("products", [])
                                        if p.get("marketing_status")}),
            "original_approval": next((s.get("submission_status_date") for s in orig
                                       if s.get("submission_status") == "AP"), None),
            "documents": [{"type": d.get("type"), "date": d.get("date"), "url": d.get("url")}
                          for s in subs for d in s.get("application_docs", []) or []][:30],
            "source_url": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process"
                          f"&ApplNo={(app.get('application_number') or '')[3:]}",
        })
    return out


class FdaArgs(BaseModel):
    name: str = Field(description="INN 或商品名（英文）")
    route_id: str = "global:fda"


@REGISTRY.register("fda_drugsfda", "查询 Drugs@FDA：申请号、申请人、首次批准日期、审评文件链接。无记录返回空列表。", FdaArgs)
def _fda(ctx: ToolContext, a: FdaArgs) -> Any:
    try:
        rows = lookup(ctx, a.name)
    except Exception as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, "global", a.name, "failed", note=str(exc)[:300])
        raise
    if ctx.db and ctx.run_id:
        ctx.db.log_coverage(ctx.run_id, a.route_id, "global", a.name, "ok", hits=len(rows))
    return {"count": len(rows), "applications": rows}
