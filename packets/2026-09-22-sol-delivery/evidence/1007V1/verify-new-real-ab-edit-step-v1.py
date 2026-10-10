"""Read-only postconditions on the normal UI result; never replay a save."""

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
OUT = ROOT / ".artifacts/1007-current14-real-ab-edit-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", required=True, type=int, choices=(1, 2, 3, 4))
    step = parser.parse_args().step
    destination = OUT / f"step-{step}-verified.json"
    if destination.exists():
        raise SystemExit("Existing verification: reopen it, not the UI operation")
    pre = json.loads((OUT / "prewrite.json").read_bytes())
    ui = json.loads((OUT / f"step-{step}-ui-return.json").read_bytes())
    result = ui["result"]
    fact_id = pre["selected_fact"]["fact_id"]
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == result["revision"] == 14 + step
    assert current_bundle_sha256(current) == result["current_generation_sha256"]
    assert set(result["rebuilt_reports"]) == {"A", "B"}
    assert result["derived_crude_rate"] is None
    assert result["independent_scientific_acceptance"] == "not_inherited"
    facts = UserFactEditService(PROJECT).current_facts()
    before = pre["all_public_facts_before"]
    assert facts.keys() == before.keys()
    assert all(facts[key] == value for key, value in before.items() if key != fact_id)
    fact = facts[fact_id]
    expected = ("-67.4", "-67.5", None, "-67.5")[step-1]
    assert fact["normalized_value"] == expected and fact["raw_value"] == expected
    assert fact["fact_version_id"] == result["fact_version_id"]
    assert fact["review_state"] == "user_modified"
    assert fact["original_text"] == fact["source_quote"] == "-67.5"
    for key in ("source_version_id", "source_id", "source_locator", "result_context",
                "consumer_bindings", "statistical_form", "measure_object"):
        assert fact[key] == pre["selected_fact"][key], key
    c = next(report for report in current.reports if report.report == "C")
    assert c.model_dump(mode="json") == next(
        report for report in pre["current"]["reports"] if report["report"] == "C"
    )
    projected = {}
    for report in current.reports:
        if report.report == "C":
            continue
        assert report.revision == current.revision and report.builder_input_relative_path
        source = PROJECT / report.builder_input_relative_path
        assert sha(source) == report.builder_input_sha256
        original_data = json.loads(source.read_bytes())
        original_row = next(item for item in original_data["efficacy"]
                            if item["row_id"] == "eff-b0b587971df19e9d9cde")
        assert original_row["value"] == -67.5, "Immutable builder input is not current UI"
        rendered = PROJECT / report.site_relative_path / "data/report.js"
        assert sha(rendered) == report.file_hashes["data/report.js"]
        # The first production assignment is pure JSON; decode data, never execute JS.
        data, _ = json.JSONDecoder().raw_decode(rendered.read_text().split("=", 1)[1])
        row = next(item for item in data["efficacy"]
                   if item["row_id"] == "eff-b0b587971df19e9d9cde")
        assert row["value"] == (None if expected is None else float(expected))
        assert row["source_text"] == "-67.5"
        # Clear removes current numeric axes; the immutable source N remains39.
        assert original_row["denominator"] == 39
        assert row["denominator"] == (None if step == 3 else 39)
        assert row["disclosure_state"] == ("user_cleared" if step == 3 else "reported_value")
        projected[report.report] = row
    assert all(sha(PROJECT / path) == digest for path, digest in pre["protected_files"].items())
    with (sqlite3.connect((PROJECT / "state/project.sqlite").as_uri()+"?mode=ro", uri=True) as db,
          sqlite3.connect((OUT / "database-before.sqlite").as_uri()+"?mode=ro", uri=True) as old):
        for table in ("source_versions", "evidence_fragments", "source_portal_consumer_bindings"):
            assert list(db.execute(f"SELECT * FROM {table} ORDER BY 1")) == list(
                old.execute(f"SELECT * FROM {table} ORDER BY 1"))
        original = list(old.execute("SELECT * FROM fact_versions ORDER BY 1"))
        now = set(db.execute("SELECT * FROM fact_versions ORDER BY 1"))
        assert all(row in now for row in original)
    payload = {
        "state": "NORMAL_UI_AB_SYNC_READONLY_POSTCONDITIONS_PASSED_NOT_RELEASE",
        "step": step, "revision": current.revision,
        "generation": current_bundle_sha256(current), "editable_facts_count": len(facts),
        "other_public_facts_exact": len(facts)-1, "source_tables_exact": True,
        "original_fact_versions_preserved": len(original),
        "protected_old_files_exact": len(pre["protected_files"]), "c_current_exact": True,
        "target_current": fact, "report_rows": projected,
        "current": current.model_dump(mode="json"),
        "ui_return_sha256": sha(OUT / f"step-{step}-ui-return.json"),
        "limits": "Actual estimate edit, not n/N derivation or clinical/whole-report acceptance",
    }
    with destination.open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"step": step, "revision": current.revision, "source_exact": True}))


if __name__ == "__main__":
    main()
