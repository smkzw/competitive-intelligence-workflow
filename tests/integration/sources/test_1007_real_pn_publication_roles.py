"""Optional pinned real-source replay; SKIP is not a real-source PASS."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.pubmed import classify_pubmed_records, parse_pubmed_efetch_xml
from ci_workflow.storage.content_store import ContentAddressedStore

ROOT = Path(__file__).resolve().parents[3] / ".artifacts/1007-pn-publications-current-v1"


@pytest.mark.parametrize("pmid", ("37142763", "37888917", "39602139"))
def test_actual_primary_report_with_response_proportions_is_not_demoted(pmid: str) -> None:
    receipt = ROOT / "abstracts.json"
    if not receipt.is_file():
        pytest.skip("Pinned local real source unavailable; not an actual-source acceptance")
    evidence = json.loads(receipt.read_bytes())
    blob = ContentBlob.model_validate(evidence["receipt"]["raw_asset"])
    store = ContentAddressedStore(ROOT)
    raw = store.read_bytes(blob)
    records = parse_pubmed_efetch_xml(raw.decode())
    record = next(row for row in records if row.pmid == pmid)
    verdict, = classify_pubmed_records((record,), target_nct_ids=(
        "NCT04183335", "NCT04202679", "NCT04501666", "NCT04501679",
    ))
    assert verdict.role == "primary_report"
    assert verdict.can_replace_primary_report  # heuristic, not scientific adoption
    assert verdict.record == record
    assert hashlib.sha256(store.read_bytes(blob)).hexdigest() == blob.sha256


def test_actual_lte_lead_in_id_does_not_receive_lte_results() -> None:
    receipt = ROOT / "abstracts.json"
    if not receipt.is_file():
        pytest.skip("Pinned local real source unavailable; not actual-source acceptance")
    evidence = json.loads(receipt.read_bytes())
    blob = ContentBlob.model_validate(evidence["receipt"]["raw_asset"])
    store = ContentAddressedStore(ROOT)
    raw = store.read_bytes(blob)
    record = next(row for row in parse_pubmed_efetch_xml(raw.decode()) if row.pmid == "41405008")
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT03181503", "NCT04204616"))
    assert result.matched_nct_ids == ("NCT04204616",)
    assert result.model_dump().get("contextual_nct_ids") == ("NCT03181503",)
    assert result.record == record
    lead_in, = classify_pubmed_records((record,), target_nct_ids=("NCT03181503",))
    assert not lead_in.can_replace_primary_report
    assert lead_in.matched_nct_ids == ()
    assert hashlib.sha256(store.read_bytes(blob)).hexdigest() == blob.sha256
