"""Replay pinned CT.gov inventories into a unique, still-unreviewed study ledger.

Raw content variants and every discovery route survive. This is not eligibility,
alias adoption, regulator verification, a report, or competitor-universe closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.build_ctgov_source_inventory import (
    InventoryError,
    _canonical_json,
    _load_pinned_bundle,
    _write_exclusive,
    build_inventory,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_union(inventories: list[Path]) -> dict[str, Any]:
    if not inventories:
        raise InventoryError("At least one pinned inventory is required")
    if any(p.is_symlink() for p in inventories):
        raise InventoryError("Inventory must be a regular, pinned file")
    sources: list[dict[str, Any]] = []
    grouped: dict[str, dict[str, Any]] = {}
    memberships = 0
    for path in sorted({p.resolve() for p in inventories}):
        if path.is_symlink():
            raise InventoryError("Inventory must be a regular, pinned file")
        raw = path.read_bytes()
        inv = json.loads(raw)
        cas = Path(inv["source"]["cas_dir"])
        capture_path = Path(inv["source"]["capture_receipt"]["relative_path"])
        rebuilt = build_inventory(cas_dir=cas, capture_receipt=capture_path)
        if any(inv.get(k) != v for k, v in rebuilt.items() if k != "replay_command"):
            raise InventoryError("Inventory projection differs from its pinned raw source")
        receipt, _, _, records = _load_pinned_bundle(cas, capture_path)
        source_id = inv["source"]["source_set_sha256"]
        source = {
            "source_id": source_id, "inventory_path": str(path), "inventory_sha256": _sha(raw),
            "cas_dir": str(cas), "capture_receipt": inv["source"]["capture_receipt"],
            "condition": inv["source"]["condition"], "count": len(records),
            "pages": receipt["acquisition"]["pages"],
            "request_urls_available": all(
                bool(p.get("request_url")) for p in receipt["acquisition"]["pages"]
            ),
        }
        if any(s["source_id"] == source_id for s in sources):
            # A copied inventory is not another acquisition/discovery route.
            continue
        sources.append(source)
        for row in records:
            study = row["study"]
            protocol = study["protocolSection"]
            nct = protocol["identificationModule"]["nctId"]
            entry = grouped.setdefault(nct, {"nct_id": nct, "versions": {}})
            digest = _sha(_canonical_json(study))
            version = entry["versions"].setdefault(digest, {
                "record_sha256": digest,
                "title": protocol["identificationModule"].get("briefTitle"),
                "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
                "memberships": [],
            })
            version["memberships"].append({
                "source_id": source_id, "page_number": row["page_number"],
                "page_sha256": row["page_sha256"],
                "page_relative_path": row["page_relative_path"],
                "study_path": f"$.studies[{row['study_index']}]",
            })
            memberships += 1
    studies = []
    for nct in sorted(grouped):
        entry = grouped[nct]
        versions = []
        for digest in sorted(entry["versions"]):
            version = entry["versions"][digest]
            version["memberships"].sort(key=lambda m: (m["source_id"], m["study_path"]))
            versions.append(version)
        studies.append({"nct_id": nct, "versions": versions,
                        "version_conflict": len(versions) > 1, "decision": "review_pending"})
    return {
        "schema_version": "1.0", "accepted": False, "universe_closed": False,
        "scientific_acceptance": "not_accepted", "unique_studies": len(studies),
        "query_memberships": memberships,
        "source_version_conflicts": sum(s["version_conflict"] for s in studies),
        "sources": sorted(sources, key=lambda s: s["source_id"]), "studies": studies,
        "limitations": ["Discovery membership is not indication/innovation eligibility",
                        "Different record versions retained; no active version chosen",
                        "Targets, aliases, China and required publications "
                        "remain separate reviews"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_union(args.inventory)
    _write_exclusive(args.output, result)
    print(json.dumps({"output": str(args.output), "unique_studies": result["unique_studies"],
                      "source_version_conflicts": result["source_version_conflicts"],
                      "accepted": False, "universe_closed": False}))


if __name__ == "__main__":
    main()
