"""Resolve 14 missing adopted primaries to existing candidates, without adoption.

The original source snapshot and fragment paths are checked, never a value-only
or row-order join. Exact candidate existence is not scientific acceptance.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
PREP = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
OUT = ROOT / ".artifacts/1007-safety-primary-gap-v1"
SNAPSHOT = PROJECT / "snapshots/evidence/evidence-snapshot_70170bf126764571d59faba8.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Existing diagnosis: collect original, never overwrite/replay"
    assert sha(SNAPSHOT) == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    database = PROJECT / "state/project.sqlite"
    before = sha(database)
    mapping = json.loads((PREP / "direct-consumer-candidates.json").read_bytes())
    unresolved = {item["row_ref"] for item in mapping["not_direct"]
                  if item["reason"] == "no_adopted_snapshot_primary_for_this_row"}
    assert len(unresolved) == 14
    a = json.loads((PREP / "a-preliminary.json").read_bytes())
    snapshot = json.loads(SNAPSHOT.read_bytes())
    sources = {s["source_version_id"]: s["capture"] for s in snapshot["closure"]["sources"]}
    found = []
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for row in a["safety"]:
            ref = f"safety:{row['row_id']}"
            if ref not in unresolved:
                continue
            matches = list(db.execute(
                "SELECT v.fact_version_id,v.raw_value,v.review_state,v.scientific_context_json,"
                "v.content_sha256,f.locator,f.content_text,f.content_sha256 "
                "FROM fact_versions v JOIN evidence_fragments f "
                "ON f.fragment_id=v.primary_fragment_id WHERE f.source_version_id=? "
                "AND json_extract(f.locator,'$.field_path')=?",
                (row["source_version_id"], row["source_field_path"]),
            ))
            assert len(matches) == 1, (ref, len(matches))
            version, raw, state, encoded, digest, locator, quote, fragment_digest = matches[0]
            assert state == "candidate" and version not in snapshot["fact_version_ids"]
            assert hashlib.sha256(encoded.encode()).hexdigest() == digest
            context = json.loads(encoded)
            capture = sources[row["source_version_id"]]
            exact = extract_locator_quote(capture["content_text"], media_type=capture["media_type"],
                                          locator=EvidenceLocator.model_validate_json(locator))
            assert exact == quote and hashlib.sha256(quote.encode()).hexdigest() == fragment_digest
            observation = context["result_context"]
            assert (float(raw) == row["value"] and observation["domain"] == "adverse_events"
                    and observation["trial_id"].casefold() == row["trial_id"]
                    and observation["group_id"] == row["group_id"]
                    and observation["group_title"] == row["arm"])
            found.append({"row_ref": ref, "report_row": row, "fact_version_id": version,
                          "fact_context": context, "fact_content_sha256": digest,
                          "review_state": state, "source_version_id": row["source_version_id"],
                          "source_locator": json.loads(locator), "original_quote": quote,
                          "fragment_sha256": fragment_digest,
                          "source_title": capture["title"], "source_url": capture["url"],
                          "source_capture_text_sha256": hashlib.sha256(
                              capture["content_text"].encode()).hexdigest(),
                          "bound_snapshot_member": False})
    assert len(found) == 14 and sha(database) == before
    OUT.mkdir()
    result = {"state": "EXACT_EXISTING_CANDIDATES_RECOVERED_NOT_ACCEPTED_NOT_BOUND",
              "source_snapshot_sha256": sha(SNAPSHOT), "source_commit":
              "3069e00187f7ac24a0b2bad68010a69f5e5d6e67", "script_sha256": sha(Path(__file__)),
              "database_sha256_unchanged": before, "rows": found,
              "by_study": dict(Counter(r["report_row"]["trial_id"] for r in found)),
              "source_versions": sorted({r["source_version_id"] for r in found}),
              "independent_source_review": "NOT_RUN", "adoptions": 0, "registrations": 0,
              "source_writes": 0, "renders": 0, "saves": 0,
              "limits": "Existing candidate/precise original retrieval is not medical acceptance, "
                        "user-current binding, clinical comparability or universe proof"}
    with (OUT / "actual.json").open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=1)
    print(json.dumps({"state": result["state"], "candidates": len(found),
                      "by_study": result["by_study"]}))


if __name__ == "__main__":
    main()
