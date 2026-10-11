"""Exact real six-atom cutoff proof and portable closure, never clinical adoption."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_research_service import (
    FactPublicVersionProof,
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    fact_version_material_digest,
    source_capture_from_linked_jats_xml,
    validate_research_historical_availability,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.sources.connectors.pmc_object_availability import (
    PmcObjectAvailabilityError,
    build_pmc_object_witness,
    verify_pmc_object_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import extract_locator_quote
from ci_workflow.storage.sqlite import open_database

ROOT = Path(__file__).resolve().parents[2]
OBJECTS = ROOT / ".artifacts/1007-pmc-object-witness-v2"
PACKET = ROOT / ".artifacts/1007-public-version-witness-slice-v1/packet.json"


@pytest.fixture
def actual_case(tmp_path):
    if not (OBJECTS / "actual.json").is_file() or not PACKET.is_file():
        pytest.skip("Actual frozen objects/six-atom packet absent; not synthetic acceptance")
    original = PACKET.read_bytes()
    assert hashlib.sha256(original).hexdigest() == (
        "a5cb55ffb40a1fbdcaa2298c1b18259d5ff93f3fbecbb657043f4d7d9c0822a5"
    )
    packet = json.loads(original)
    captures, proofs, facts = [], [], []
    store = ContentAddressedStore(tmp_path)
    for record in json.loads((OBJECTS / "actual.json").read_text())["records"]:
        metadata_name = record["metadata"]["relative_path"]
        xml_name = record["xml"]["relative_path"]
        xml = (OBJECTS / xml_name).read_bytes()
        metadata = json.loads((OBJECTS / metadata_name).read_text())
        witness = build_pmc_object_witness(
            store, metadata_bytes=(OBJECTS / metadata_name).read_bytes(), xml_bytes=xml,
            metadata_receipt_bytes=(OBJECTS / (metadata_name + ".receipt.json")).read_bytes(),
            xml_receipt_bytes=(OBJECTS / (xml_name + ".receipt.json")).read_bytes(),
        )
        url = record["xml"]["url"]
        _, native = source_capture_from_linked_jats_xml(
            tmp_path, xml, expected_pmid=str(metadata["pmid"]), expected_pmcid=metadata["pmcid"],
            expected_doi=metadata["doi"], url=url,
            acquired_at=datetime.fromisoformat(record["xml"]["response_completed_at"]),
        )
        assert native is not None
        source_id = {"PMC10202800": "pubmed-record-37142763",
                     "PMC13308661": "pubmed-record-41405008"}[metadata["pmcid"]]
        source = SourceCapture.model_validate({**native.model_dump(mode="json"),
            "source_id": source_id, "pmc_object_availability": witness.model_dump(mode="json")})
        captures.append(source)
        locator = EvidenceLocator(document_role="original_linked_publication",
            field_path="/article/front[1]/article-meta[1]/article-version[1]", url=url)
        version_reference = {"reference_id": "pmc-version", "source_id": source_id,
            "label_zh": "官方对象版本", "locator": locator,
            "original_text": extract_locator_quote(source.content_text,
                media_type=source.media_type, locator=locator)}
        for raw in packet["facts"]:
            if raw["source_id"] != source_id:
                continue
            item = copy.deepcopy(raw)
            item["locator"]["url"] = url
            for reference in item.get("source_clause_context", {}).get("continuations", []):
                reference["locator"]["url"] = url
            fact = ResearchFact.model_validate(item)
            facts.append(fact)
            proofs.append(FactPublicVersionProof.model_validate({
                "fact_id": fact.fact_id,
                "fact_material_sha256": fact_version_material_digest(fact),
                "source_content_sha256": {source_id: hashlib.sha256(
                    source.content_text.encode()).hexdigest()},
                "official_object_xml_sha256": witness.xml_asset.sha256,
                "version_references": [version_reference], "correction_state": "unresolved",
            }))
    assert len(facts) == 6
    return captures, facts, proofs, datetime.fromisoformat(packet["cutoff"])


def test_six_real_atoms_prove_exact_bytes_without_rewriting_dates(actual_case):
    sources, facts, proofs, cutoff = actual_case
    validate_research_historical_availability(sources, facts, proofs, cutoff)
    assert all(s.first_disclosed_at is None and not s.is_available_by(cutoff) for s in sources)
    assert all(p.public_by is None and p.correction_state == "unresolved" for p in proofs)


@pytest.mark.parametrize("case", ["sibling", "fact_change", "wrong_object", "late_clock"])
def test_object_proof_cannot_grant_other_fact_or_bytes(actual_case, case):
    sources, facts, proofs, cutoff = actual_case
    if case == "sibling":
        facts = [*facts, facts[0].model_copy(update={"fact_id": "unproved-sibling"})]
    elif case == "fact_change":
        facts[0] = facts[0].model_copy(update={"normalized_value": "changed"})
    elif case == "wrong_object":
        proofs[0] = proofs[0].model_copy(update={"official_object_xml_sha256": "0" * 64})
    else:
        witness = sources[0].pmc_object_availability
        assert witness is not None
        cutoff = witness.xml_last_modified.replace(year=2025)
    with pytest.raises(ValueError):
        validate_research_historical_availability(sources, facts, proofs, cutoff)


def _ingest(root, actual_case):
    sources, facts, _, cutoff = actual_case
    return ingest_research_evidence(
        project_root=root, project_id="actual-six-holding", contract_version=1, report_kind="B",
        data_cutoff=cutoff, scientific_content_digest="a" * 64,
        created_at=max(s.acquired_at for s in sources), sources=sources, route_attempts=(),
        facts=facts, claims=[ResearchClaim(claim_id="actual-six",
            claim_text="真实六事实候选，未授予临床采用", claim_kind="direct_evidence",
            fact_ids=tuple(f.fact_id for f in facts))],
    )


def test_raw_receipt_reopens_before_lineage_write(tmp_path, actual_case):
    apply_migrations(tmp_path / "state/project.sqlite")
    sources, _, _, _ = actual_case
    witness = sources[0].pmc_object_availability
    assert witness is not None
    (tmp_path / witness.xml_receipt_asset.relative_path).write_bytes(b"{}")
    with pytest.raises(PmcObjectAvailabilityError):
        _ingest(tmp_path, actual_case)
    with open_database(tmp_path / "state/project.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0] == 0


def test_four_object_assets_survive_snapshot_restore(tmp_path, actual_case):
    apply_migrations(tmp_path / "state/project.sqlite")
    lineage = _ingest(tmp_path, actual_case)
    restored = tmp_path / "separate-restore"
    SnapshotStore(restored).restore_evidence_manifest(
        tmp_path / lineage.evidence_snapshot.relative_path,
    )
    sources, _, _, cutoff = actual_case
    for source in sources:
        witness = source.pmc_object_availability
        assert witness is not None
        assert verify_pmc_object_availability(ContentAddressedStore(restored), witness, cutoff)
        assert source.first_disclosed_at is None
