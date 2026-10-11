"""Exact replay of six frozen atoms against two official dated PMC objects; no adoption."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[4]
SLICE = ROOT / ".artifacts/1007-public-version-witness-slice-v1/packet.json"
OBJECTS = ROOT / ".artifacts/1007-pmc-object-witness-v2"
OUT = ROOT / ".artifacts/1007-pmc-object-six-fact-replay-v1"


def main() -> None:
    original = SLICE.read_bytes()
    assert hashlib.sha256(original).hexdigest() == (
        "a5cb55ffb40a1fbdcaa2298c1b18259d5ff93f3fbecbb657043f4d7d9c0822a5"
    )
    packet = json.loads(original)
    capture = json.loads((OBJECTS / "actual.json").read_text())
    cutoff = datetime.fromisoformat(packet["cutoff"])
    bindings = {}
    for record in capture["records"]:
        source_id = {"PMC10202800": "pubmed-record-37142763",
                     "PMC13308661": "pubmed-record-41405008"}[record["pmcid"]]
        raw = (OBJECTS / record["xml"]["relative_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record["xml"]["sha256"]
        assert hashlib.md5(raw, usedforsecurity=False).hexdigest() == record["metadata_xml_md5"]
        assert record["xml"]["headers"]["ETag"].strip('"') == record["metadata_xml_md5"]
        modified = parsedate_to_datetime(record["xml"]["headers"]["Last-Modified"])
        assert modified <= cutoff
        bindings[source_id] = (raw.decode("utf-8"), record, modified.isoformat())
    facts = []
    for fact in packet["facts"]:
        xml, record, modified = bindings[fact["source_id"]]
        references = [{"source_id": fact["source_id"], "locator": fact["locator"],
                       "original_text": fact["original_text"], "label_zh": "事实原子"},
                      *fact.get("source_clause_context", {}).get("continuations", [])]
        replays = []
        for reference in references:
            assert reference["source_id"] == fact["source_id"]
            locator = EvidenceLocator.model_validate(reference["locator"])
            observed = extract_locator_quote(xml, media_type="text/xml", locator=locator)
            replays.append({"field_path": locator.field_path,
                            "label_zh": reference.get("label_zh"),
                            "matches_original": observed == reference["original_text"],
                            "observed_sha256": hashlib.sha256(observed.encode()).hexdigest(),
                            "declared_sha256": hashlib.sha256(
                                reference["original_text"].encode()).hexdigest()})
        facts.append({"fact_id": fact["fact_id"], "field_id": fact["field_id"],
                      "source_id": fact["source_id"], "pmcid": record["pmcid"],
                      "object_sha256": record["xml"]["sha256"],
                      "server_object_last_modified": modified, "references": replays,
                      "all_references_exact": all(item["matches_original"] for item in replays)})
    assert hashlib.sha256(SLICE.read_bytes()).hexdigest() == hashlib.sha256(original).hexdigest()
    OUT.mkdir()
    receipt = {"state": "READ_ONLY_OBJECT_REPLAY_NOT_FACT_ADOPTION", "facts": facts,
               "cutoff": packet["cutoff"],
               "frozen_slice_sha256": hashlib.sha256(original).hexdigest(),
               "object_receipt_sha256": hashlib.sha256(
                   (OBJECTS / "actual.json").read_bytes()).hexdigest(),
               "source_current_fact_writes": 0}
    with (OUT / "actual.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True, indent=1)
    print(json.dumps({"state": receipt["state"], "facts": len(facts),
                      "exact_facts": sum(item["all_references_exact"] for item in facts),
                      "references": sum(len(item["references"]) for item in facts),
                      "mismatches": [item for fact in facts for item in fact["references"]
                                     if not item["matches_original"]]}))


if __name__ == "__main__":
    main()
