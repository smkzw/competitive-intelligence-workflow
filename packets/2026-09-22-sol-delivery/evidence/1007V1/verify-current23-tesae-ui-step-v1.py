"""Read actual TESAE UI transaction; no UI/API mutation or blind save retry."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-current23-tesae-ui-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=int, required=True, choices=(1, 2, 3, 4))
    step = parser.parse_args().step
    destination = OUT / f"step-{step}-verified.json"
    assert not destination.exists(), "Read original postconditions; do not replay"
    pre = json.loads((OUT / "prewrite.json").read_bytes())
    ui = json.loads((OUT / f"step-{step}-ui-return.json").read_bytes())
    result = ui["result"]
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == result["revision"] == 23 + step
    assert current_bundle_sha256(current) == result["current_generation_sha256"]
    assert set(result["rebuilt_reports"]) == {"A", "B"}
    assert result["independent_scientific_acceptance"] == "not_inherited"
    facts = UserFactEditService(PROJECT).current_facts()
    before = pre["all_public_facts_before"]
    fact_id = pre["selected_fact"]["fact_id"]
    expected = ("3", "2", None, "2")[step - 1]
    assert len(facts) == len(before) == 1505 and facts.keys() == before.keys()
    assert all(facts[k] == v for k, v in before.items() if k != fact_id)
    fact = facts[fact_id]
    assert fact["normalized_value"] == fact["raw_value"] == expected
    assert fact["fact_version_id"] == result["fact_version_id"]
    assert fact["source_quote"] == "2" and fact["review_state"] == "user_modified"
    assert fact["numerator"] == (None if expected is None else int(expected))
    assert fact["denominator"] == (None if expected is None else 77)
    for field in ("source_version_id", "source_id", "source_locator", "consumer_bindings",
                  "result_context", "statistical_form", "measure_object"):
        assert fact[field] == pre["selected_fact"][field], field
    c = next(r for r in current.reports if r.report == "C")
    assert c.model_dump(mode="json") == next(r for r in pre["current"]["reports"]
                                            if r["report"] == "C")
    projected = {}
    for report in current.reports:
        if report.report == "C":
            continue
        assert report.revision == current.revision and report.builder_input_relative_path
        builder = PROJECT / report.builder_input_relative_path
        assert sha(builder) == report.builder_input_sha256
        original = next(r for r in json.loads(builder.read_bytes())["safety"]
                        if r["row_id"] == "safe-e5e0b4524553ae12affb")
        assert original["value"] == 2 and original["denominator"] == 77
        rendered = PROJECT / report.site_relative_path / "data/report.js"
        assert sha(rendered) == report.file_hashes["data/report.js"]
        data, _ = json.JSONDecoder().raw_decode(rendered.read_text().split("=", 1)[1])
        row = next(r for r in data["safety"] if r["row_id"] == "safe-e5e0b4524553ae12affb")
        assert row["value"] == (None if expected is None else int(expected))
        assert row["source_text"] == "2"
        assert row["disclosure_state"] == (
            "用户清除，待重新核实" if step == 3 else original["disclosure_state"]
        )
        projected[report.report] = row
    assert all(sha(PROJECT / p) == d for p, d in pre["protected_files"].items())
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri() + "?mode=ro",
                         uri=True) as db,
          sqlite3.connect((OUT / "database-before.sqlite").as_uri() + "?mode=ro",
                         uri=True) as old):
        for table in ("source_versions", "evidence_fragments", "source_portal_consumer_bindings"):
            assert list(db.execute(f"SELECT * FROM {table} ORDER BY 1")) == list(
                old.execute(f"SELECT * FROM {table} ORDER BY 1"))
        original_versions = list(old.execute("SELECT * FROM fact_versions ORDER BY 1"))
        assert set(original_versions) <= set(db.execute("SELECT * FROM fact_versions ORDER BY 1"))
    with destination.open("x") as stream:
        json.dump({"state": "NORMAL_UI_AB_TESAE_SYNC_READONLY_POSTCONDITIONS_PASSED",
                   "step": step, "revision": current.revision,
                   "generation": current_bundle_sha256(current), "facts": len(facts),
                   "other_public_facts_exact": 1504, "source_tables_exact": True,
                   "old_versions_exact": len(original_versions),
                   "protected_files_exact": len(pre["protected_files"]),
                   "target_current": fact, "report_rows": projected,
                   "current": current.model_dump(mode="json"),
                   "ui_return_sha256": sha(OUT / f"step-{step}-ui-return.json"),
                   "limits": "Temporary user-layer test; no clinical acceptance or RC"},
                  stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"step": step, "revision": current.revision, "facts": len(facts)}))


if __name__ == "__main__":
    main()
