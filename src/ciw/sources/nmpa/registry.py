"""Deterministic ingestion of exact public certificate captures; no model calls."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ciw.models import Event, stable_id
from ciw.normalize.products import ProductResolver
from ciw.sources.nmpa.parser import parse_detail
from ciw.store import Workspace


def ingest(ws: Workspace, resolver: ProductResolver) -> tuple[list[Event], list[dict], dict[str, Any]]:
    paths = sorted((ws.root / "captures/nmpa").glob("certificate-*.json"))
    events, issues = [], []
    for path in paths:
        try:
            raw = json.loads(path.read_text())
            parsed = parse_detail(raw, registration_number=raw["registration_number"], category=raw["category"])
            fetched_at = raw["observed_at"]
            if datetime.fromisoformat(fetched_at).tzinfo is None:
                raise ValueError("NMPA capture lacks a timezone")
            source = ws.record_source(
                kind="nmpa",
                url=parsed["url"],
                data=path.read_bytes(),
                ext="json",
                title=raw["heading"],
                publisher="国家药品监督管理局",
                fetched_at=fetched_at,
            )
            name = " / ".join(filter(None, [parsed["drug_name"], parsed["drug_name_en"]]))
            product = resolver.find_in_text(name) or resolver.resolve_intervention(name)
            if product is None:
                raise ValueError("NMPA产品未唯一匹配当前配置")
            quote = raw["heading"] + "\n" + "\n".join(f"{k}\t{v}" for k, v in raw["rows"])
            events.append(
                Event(
                    event_id=stable_id("ev", source.source_id, parsed["registration_number"]),
                    product_id=product,
                    product_mention=name,
                    event_type="approval",
                    region="中国",
                    date=parsed["approval_date"],
                    indication="",
                    detail="药品许可记录：" + parsed["registration_number"],
                    quote=quote,
                    status="registry",
                    source_id=source.source_id,
                )
            )
        except (ValueError, KeyError, TypeError) as exc:
            issues.append({"kind": "nmpa_capture_invalid", "ref": path.name, "note": str(exc)})
    coverage = {
        "source": "nmpa",
        "status": "not_captured" if not paths else "partial" if issues else "ok",
        "records": len(paths),
        "adopted": len(events),
        "failed": len(issues),
    }
    return events, issues, coverage
