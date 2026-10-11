"""Freeze six existing paper atoms and exact original witness byte pointers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-public-version-witness-slice-v1"
NATIVE = ROOT / ".artifacts/1007-publication-native-package-v1/source-package.json"
RECONCILED = ROOT / (
    "packets/2026-09-22-sol-delivery/evidence/1007V1/"
    "owner-publication-source-reconciliation-v1.json"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert digest(NATIVE) == "6909f03ab9f1c7b08b264ba31078a0dab62849937f5da059f99a72c6ab880e8e"
    package = json.loads(NATIVE.read_text())
    reconciliation = json.loads(RECONCILED.read_text())
    fields = {
        "definition.primary_measure", "population.entry_exposure_disposition",
        "efficacy.primary.prime.week24.contrast", "safety.any_teae.column_2",
        "safety.any_teae.column_3",
    }
    facts = [fact for fact in package["facts"] if fact["field_id"] in fields or (
        fact["field_id"] == "efficacy.primary.prime.week24.arm_cell"
        and fact["original_text"] == "45 (60.0)"
    )]
    assert len(facts) == 6 and len({fact["fact_id"] for fact in facts}) == 6
    sources = []
    for source in package["sources"]:
        copied = dict(source)
        text = copied.pop("content_text")
        copied["content_text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        # Original full XML remains in the frozen native package. Nothing is fetched,
        # rewritten, adopted, or assigned a replacement acquisition clock here.
        sources.append(copied)
    crossmarks = [row for row in reconciliation["raw_responses"]
                 if row["request_id"].startswith(("req-03-", "req-04-"))]
    assert len(crossmarks) == 2
    for row in crossmarks:
        path = ROOT / row["raw_root"] / row["cas_relative_path"]
        assert digest(path) == row["sha256"]
    OUT.mkdir()
    with (OUT / "packet.json").open("x", encoding="utf-8") as stream:
        json.dump({
            "state": "FROZEN_REVIEW_INPUT_NOT_PROOF_OR_ADOPTION",
            "cutoff": "2026-10-07T23:59:59.999999+08:00",
            "native_package_path": NATIVE.relative_to(ROOT).as_posix(),
            "native_package_sha256": digest(NATIVE),
            "sources": sources, "facts": facts, "crossmark_raw": crossmarks,
            "clock_policy": "Crossmark precise clocks were rejected; no backdating. "
                            "Native paper capture dates and all original bytes unchanged.",
            "current_source_fact_writes": 0,
        }, stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"facts": len(facts), "sources": len(sources),
                      "packet_sha256": digest(OUT / "packet.json")}))


if __name__ == "__main__":
    main()
