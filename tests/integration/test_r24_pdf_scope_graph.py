"""Exact source clauses and reciprocal scope links; never clinical acceptance."""

import json
import os
from pathlib import Path

import pytest
from pypdf import PdfReader

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote
from tools import complete_r24_pdf_scope_graph as builder

ROOT = Path(__file__).resolve().parents[2]
V5 = ROOT / ".artifacts/r24-147-native-pdf-scope-successor-20261003/proposal-v5.json"
V6 = ROOT / ".artifacts/r24-150-pdf-complete-scope-20261003/proposal-v6.json"


def _data() -> dict:
    path = Path(os.environ.get("CI_PDF_GRAPH_PROPOSAL", str(V6))).resolve()
    assert path.is_relative_to(ROOT)
    return json.loads(path.read_text())


def _atom(data: dict, suffix: str) -> dict:
    matches = [a for a in data["atoms"] if a["proposal_id"].endswith(suffix)]
    assert len(matches) == 1, suffix
    return matches[0]


def test_complete_primary_clauses_have_explicit_roles_without_a_fabricated_timepoint() -> None:
    data = _data()
    for suffix in ("p40-complete-primary-endpoints", "p8-primary-safety-endpoint"):
        a = _atom(data, suffix)
        assert a["endpoint_key"] == "primary_endpoint"
        assert a["design_field_family"] == "endpoint"
        assert a["c_field_mapping"]["gate_unit"] is None
        assert a["scientific_scope"]["timepoint"] is None
    assert "single and multiple SC doses" in " ".join(
        _atom(data, "p40-complete-primary-endpoints")["original_quote"].split()
    )


def test_printed_precedence_remains_scoped_governance_not_a_universal_winner() -> None:
    a = _atom(_data(), "p8-statistical-section-precedence")
    assert "supersedes" in a["original_quote"]
    assert a["design_field_family"] is None
    assert a["scientific_scope"]["scope"] == "statistical_section_discrepancies_only"
    assert a["scientific_scope"]["automatic_winner"] is False


def test_conflict_links_are_reciprocal_and_ldh_points_to_the_actual_threshold() -> None:
    data = _data()
    atoms = {a["proposal_id"]: a for a in data["atoms"]}
    conflicts = {c["conflict_id"]: c for c in data["conflicts"]}
    for cid, conflict in conflicts.items():
        for aid in conflict["linked_atoms"]:
            assert cid in atoms[aid]["conflict_links"], (cid, aid)
    for aid, a in atoms.items():
        for cid in a["conflict_links"]:
            assert aid in conflicts[cid]["linked_atoms"], (aid, cid)
    conflict = conflicts["conflict-ak581-ldh-threshold-boundary"]
    for aid in conflict["linked_atoms"]:
        assert "1.8" in atoms[aid]["original_quote"], aid


def test_membership_and_disposition_use_have_separate_original_quotes() -> None:
    data = _data()
    membership = _atom(data, "p21-screened-set")
    usage = _atom(data, "p22-screened-disposition-use")
    assert "disposition" not in membership["scientific_scope"]["rule"]
    assert usage["proposal_id"] in membership["related_proposal_ids"]
    assert "Patient disposition" in usage["original_quote"]


def test_qualified_n_wordings_do_not_fill_a_critical_numeric_slot() -> None:
    data = _data()
    for a in data["atoms"]:
        if a["design_field_family"] == "sample_size":
            assert a["c_field_mapping"]["gate_unit"] is None
            assert a["status"] == "unreviewed"
    assert not data["accepted"]


def test_old_source_identity_is_preserved_and_every_new_clause_replays_production_locator() -> None:
    data = _data()
    atoms = {a["proposal_id"]: a for a in data["atoms"]}
    for before in json.loads(V5.read_text())["atoms"]:
        after = atoms[before["proposal_id"]]
        for key in ("original_quote", "document_raw_sha256", "physical_page", "anchor"):
            assert after[key] == before[key]
    pdfs = ROOT / ".artifacts/r24-96-c-public-documents-20261003/downloads"
    readers = {d["filename"]: PdfReader(pdfs / d["filename"]) for d in data["documents"]}
    for a in data["atoms"]:
        text = readers[a["document_filename"]].pages[a["physical_page"] - 1].extract_text()
        extract_locator_quote(text, media_type="text/plain", locator=EvidenceLocator(
            document_role="design_document", page=a["physical_page"],
            paragraph=a["original_quote"],
        ))


def test_builder_reproduces_the_scientific_graph_without_writing_a_current_pointer() -> None:
    rebuilt = builder.build_successor()
    saved = _data()
    for key in ("atoms", "conflicts", "documents", "gaps"):
        assert rebuilt[key] == saved[key]
    assert not rebuilt["accepted"]


def test_changed_predecessor_fails_closed_before_pdf_reads(tmp_path: Path, monkeypatch) -> None:
    changed = tmp_path / "changed-predecessor.json"
    changed.write_text("{}")
    monkeypatch.setattr(builder, "SOURCE", changed)
    with pytest.raises(ValueError, match="Frozen predecessor changed"):
        builder.build_successor()


def _reviewed_successor() -> dict:
    # Before the repair, exercise the actual existing v6 production builder.
    # Afterwards exercise its explicit successor, without rewriting v6.
    return getattr(builder, "build_reviewed_scope_successor", builder.build_successor)()


def test_qualified_ak_n_reason_does_not_invent_cohort_completer_counts() -> None:
    data = _reviewed_successor()
    for suffix in ("p71-number-of-patients", "p26-sample-size-determination"):
        a = _atom(data, suffix)
        reason = a["c_field_mapping"]["reason"]
        assert "cohort/completer" not in reason
        assert "approximately" in reason
        assert a["c_field_mapping"]["gate_unit"] is None


def test_population_relation_keeps_sap_definitions_opposing_not_context_only() -> None:
    data = _reviewed_successor()
    c = next(c for c in data["conflicts"] if c["conflict_id"] == (
        "conflict-apl-cp0514-population-def-protocol-vs-sap"
    ))
    assert "SAP23 definitions" not in c["description"]
    assert _atom(data, "p23-analysis-datasets")["proposal_id"] in c["linked_atoms"]
    for suffix in ("p64-measurable-pd-population", "p20-general-analysis-baseline"):
        identity = _atom(data, suffix)["proposal_id"]
        assert identity not in c["linked_atoms"]
        assert identity in c["related_context_atoms"]


def test_ae_coding_wordings_have_a_scoped_reciprocal_nonwinning_relation() -> None:
    data = _reviewed_successor()
    left = _atom(data, "p62-teae-definition")
    right = _atom(data, "p27-ae-coding-version")
    expected = {left["proposal_id"], right["proposal_id"]}
    matches = [c for c in data["conflicts"] if set(c["linked_atoms"]) == expected]
    assert len(matches) == 1
    relation = matches[0]
    assert relation["scientific_scope"]["domain"] == "ae_coding"
    assert not relation["scientific_scope"]["automatic_winner"]
    assert relation["conflict_id"] in left["conflict_links"]
    assert relation["conflict_id"] in right["conflict_links"]
    assert "current version" in left["original_quote"]
    assert "17.0" in right["original_quote"]


def test_reviewed_successor_retains_every_v6_quote_and_unaccepted_boundary() -> None:
    before = json.loads(V6.read_bytes())
    after = _reviewed_successor()
    assert after["documents"] == before["documents"]
    assert after["gaps"] == before["gaps"]
    assert len(after["atoms"]) == len(before["atoms"]) == 64
    by_id = {a["proposal_id"]: a for a in after["atoms"]}
    for a in before["atoms"]:
        for key in ("original_quote", "physical_page", "document_raw_sha256", "anchor"):
            assert by_id[a["proposal_id"]][key] == a[key]
    assert after["accepted"] is False
    assert after["status"] == "proposal_only"
