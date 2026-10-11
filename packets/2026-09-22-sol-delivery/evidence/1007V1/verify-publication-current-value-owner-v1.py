"""Read-only actual source components through the current-value production helper.

This does not register product relationships, adopt normalized facts or commit
reports. The explicit reported-proportion metadata exercises the display contract.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.source_research_service import ResearchFact
from ci_workflow.application.user_fact_edit import FactTargetIdentity
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, numeric_value

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-current-value-owner-v1"


def main() -> None:
    assert not OUT.exists(), "Do not rerun or overwrite completed evidence"
    package = RUN / "source-package.json"
    assert hashlib.sha256(package.read_bytes()).hexdigest() == (
        "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0")
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 34
    versions = json.loads((RUN / "ingestion-return.json").read_bytes())["fact_version_by_ref"]
    rows = []
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for raw in json.loads(package.read_bytes())["facts"]:
            fact = ResearchFact.model_validate(raw)
            context = fact.result_context
            if not context or context.domain != "efficacy":
                continue
            version = versions[fact.fact_id]
            stored = db.execute("SELECT v.raw_value,v.normalized_value,v.primary_fragment_id,"
                "v.content_sha256,v.review_state,f.locator,f.content_text,f.source_version_id "
                "FROM fact_versions v JOIN evidence_fragments f "
                "ON f.fragment_id=v.primary_fragment_id WHERE v.fact_version_id=?", (version,)
            ).fetchone()
            assert stored and stored[0] == fact.raw_value and stored[1] is None
            assert stored[4] == "accepted" and stored[6] == fact.original_text
            active = ActiveFact.model_validate({**raw, "fact_version_id": version,
                "primary_fragment_id": stored[2], "source_locator": stored[5],
                "source_quote": stored[6], "source_version_id": stored[7],
                "statistical_form": "reported_proportion", "measure_object": "participants",
                "unit": "%", "normalized_unit": "%"})
            before = active.model_dump_json()
            value = numeric_value(active)
            target = FactTargetIdentity(fact_id=fact.fact_id, fact_version_id=version,
                                       entity_id=fact.entity_id, field_id=fact.field_id)
            assert target.fact_id == fact.fact_id and active.model_dump_json() == before
            rows.append({"fact_id": fact.fact_id, "fact_version_id": version,
                "source_version_id": stored[7], "source_content_sha256": stored[3],
                "original_raw": stored[0], "parent_normalized_value": stored[1],
                "printed_percent": value})
    assert len(rows) == 4 and sorted(row["printed_percent"] for row in rows) == [
        18.4, 22.0, 37.2, 60.0]
    assert read_current_delivery(PROJECT) == current
    OUT.mkdir()
    result = {"state": "REAL_SOURCE_CURRENT_VALUE_HELPER_ONLY_PASSED",
        "source_fact_current_writes": 0, "current_revision": current.revision,
        "generation": current_bundle_sha256(current), "rows": rows,
        "registered_consumers_actual_product_or_browser_acceptance": "NOT_RUN"}
    (OUT / "actual.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                                indent=1), encoding="utf-8")
    print(json.dumps({"state": result["state"], "rows": len(rows)}), flush=True)


if __name__ == "__main__":
    main()
