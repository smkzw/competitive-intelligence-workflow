"""Scope-repair evidence checks; no source or medical acceptance is implied."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pypdf import PdfReader

from ci_workflow.application.fresh_c_research_package import _unit_id_for
from ci_workflow.reports.c import DesignFieldFamily
from tests.integration.test_fresh_c_research_package import _observation

ROOT = Path(__file__).resolve().parents[2]
PDFS = ROOT / ".artifacts/r24-96-c-public-documents-20261003/downloads"
V4 = ROOT / (
    "runs/execution/ci-r24-137-native-pdf-complete-scope-repair-20261003/"
    "native-pdf-design-proposal-v4.json"
)
V5 = ROOT / ".artifacts/r24-147-native-pdf-scope-successor-20261003/proposal-v5.json"


@pytest.fixture(scope="module")
def proposal() -> dict:
    path = Path(os.environ.get("CI_SCOPE_PROPOSAL_PATH", str(V5))).resolve()
    assert path.is_relative_to(ROOT), "scope fixture must stay in the English root"
    return json.loads(path.read_text())


def _atom(proposal: dict, suffix: str) -> dict:
    matches = [a for a in proposal["atoms"] if a["proposal_id"].endswith(suffix)]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    ("suffix", "role"),
    [
        ("p61-efficacy-endpoint-exploratory", "exploratory_endpoint"),
        ("p61-safety-endpoints-primary", "primary_endpoint"),
        ("p61-pk-endpoints", "unknown_endpoint"),
        ("p61-efficacy-analysis-part1", "unknown_endpoint"),
        ("p62-teae-definition", "unknown_endpoint"),
        ("p71-pk-complement-activity", "unknown_endpoint"),
    ],
)
def test_endpoint_scientific_domain_is_not_disguised_to_avoid_critical_gate(
    proposal: dict, suffix: str, role: str,
) -> None:
    a = _atom(proposal, suffix)
    assert a["design_field_family"] == "endpoint"
    assert a["endpoint_key"] == role
    observation = _observation(
        a["trial_id"], "source-candidate-product", DesignFieldFamily.ENDPOINT,
        a["existing_c_field"], a["original_quote"], endpoint_key=role,
    )
    assert _unit_id_for(observation) == (
        "c_endpoint_definitions_timepoints" if role == "primary_endpoint" else None
    )


@pytest.mark.parametrize("suffix", ["p63-subgroup-descriptive-only", "p71-significance-level"])
def test_descriptive_method_is_not_a_multiplicity_procedure(proposal: dict, suffix: str) -> None:
    a = _atom(proposal, suffix)
    assert a["existing_c_field"] == "statistical_model"
    assert a["c_field_mapping"]["field_id"] == "statistical_model"
    assert a["scientific_scope"]["multiplicity_status"].startswith("unspecified")


def test_document_metadata_cannot_fill_regional_operational_coverage(proposal: dict) -> None:
    a = _atom(proposal, "p1-metadata-and-version")
    assert a["design_field_family"] is None
    assert a["existing_c_field"] is None
    assert a["c_field_mapping"]["gate_unit"] is None


def test_uloq_label_does_not_invent_the_imputed_numeric_value(proposal: dict) -> None:
    a = _atom(proposal, "p22-general-data-handling-lloq-uloq")
    assert "以ULOQ填补" not in a["provisional_chinese_label"]
    assert a["scientific_scope"]["above_uloq"] == "imputed using quantification limit"


def test_partial_start_and_stop_dates_have_separate_contiguous_quote_proof(proposal: dict) -> None:
    start = _atom(proposal, "p27-ae-partial-date-bullets")
    stop = _atom(proposal, "p27-ae-partial-stop-date-bullets")
    assert all("start" in rule and "stop" not in rule
               for rule in start["scientific_scope"]["rules"])
    assert all("stop" in rule and "start" not in rule for rule in stop["scientific_scope"]["rules"])
    assert stop["proposal_id"] in start["related_proposal_ids"]
    assert "If a stop date is missing" in stop["original_quote"]
    assert start["physical_page"] == stop["physical_page"] == 27


def test_baseline_quote_does_not_claim_unquoted_counting_rule(proposal: dict) -> None:
    a = _atom(proposal, "p20-baseline-counting-rules")
    assert len(a["scientific_scope"]["rules"]) == 2
    linked = _atom(proposal, "p20-general-analysis-baseline")
    assert linked["proposal_id"] in a["related_proposal_ids"]
    assert "unique subjects" in linked["original_quote"]


def test_proposal_time_is_real_and_not_an_acquisition_or_acceptance_receipt(proposal: dict) -> None:
    assert datetime.fromisoformat(proposal["proposed_at"]) <= datetime.now(UTC)
    assert proposal["status"] == "proposal_only"
    assert not proposal.get("accepted", False)


def test_all_predecessor_quotes_and_original_pdf_bytes_are_preserved(proposal: dict) -> None:
    old = json.loads(V4.read_text())
    atoms = {a["proposal_id"]: a for a in proposal["atoms"]}
    for before in old["atoms"]:
        after = atoms[before["proposal_id"]]
        for key in ("original_quote", "document_raw_sha256", "physical_page", "anchor"):
            assert after[key] == before[key]
    for doc in proposal["documents"]:
        raw = (PDFS / doc["filename"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == doc["raw_sha256"]
    readers = {doc["filename"]: PdfReader(PDFS / doc["filename"]) for doc in proposal["documents"]}
    for a in proposal["atoms"]:
        page = readers[a["document_filename"]].pages[a["physical_page"] - 1].extract_text()
        assert hashlib.sha256(page.encode()).hexdigest() == a["native_page_sha256"]
        assert hashlib.sha256(page.strip().encode()).hexdigest() == a["canonical_page_text_sha256"]
        assert " ".join(page.split()).count(" ".join(a["original_quote"].split())) == 1
