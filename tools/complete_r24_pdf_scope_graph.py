"""Replay a fixed public-PDF successor with complete clauses and scoped links.

This is a bounded evidence repair, not scientific acceptance or an extractor.
Historical proposals, original documents and committed current are read-only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".artifacts/r24-147-native-pdf-scope-successor-20261003/proposal-v5.json"
SOURCE_SHA = "e8d2ef1a05fa035e49205ac9b7a5d3dead5a3beee68701431e6a84812ca72678"
PDFS = ROOT / ".artifacts/r24-96-c-public-documents-20261003/downloads"
OUTPUT = ROOT / ".artifacts/r24-150-pdf-complete-scope-20261003/proposal-v6.json"
V6_SHA = "e152c0c3e3a10dd5842b0aa71c8d0fb2b7b68821bf0c8822e635597ed93b349e"
V7_OUTPUT = ROOT / ".artifacts/r24-155-pdf-scoped-relations-20261003/proposal-v7.json"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_successor() -> dict[str, Any]:
    raw = SOURCE.read_bytes()
    if _sha(raw) != SOURCE_SHA:
        raise ValueError("Frozen predecessor changed")
    result: dict[str, Any] = copy.deepcopy(json.loads(raw))
    readers: dict[str, PdfReader] = {}
    for document in result["documents"]:
        path = PDFS / document["filename"]
        if _sha(path.read_bytes()) != document["raw_sha256"]:
            raise ValueError("Original PDF changed")
        readers[document["filename"]] = PdfReader(path)
    atoms = {a["proposal_id"]: a for a in result["atoms"]}

    def atom(suffix: str) -> dict[str, Any]:
        found = [a for a in atoms.values() if a["proposal_id"].endswith(suffix)]
        if len(found) != 1:
            raise ValueError(f"Expected one exact atom: {suffix}")
        return found[0]  # type: ignore[no-any-return]

    def add(
        template: str, suffix: str, page: int, start: str, stop: str,
        family: str | None, scope: dict[str, Any], label: str, *, include_stop: bool = False,
    ) -> dict[str, Any]:
        before = atom(template)
        text = readers[before["document_filename"]].pages[page - 1].extract_text()
        begin = text.index(start)
        end = text.index(stop, begin) + (len(stop) if include_stop else 0)
        new = {k: before[k] for k in (
            "trial_id", "document_filename", "document_raw_sha256", "source_role",
        )}
        stem = before["proposal_id"].split("-p", 1)[0]
        printed = re.search(r"(?:Section \d+ )?Page\s+\d+\s+of\s+\d+", text)
        new.update(
            proposal_id=f"{stem}-{suffix}", physical_page=page,
            printed_page_label=printed.group(0) if printed else None,
            original_quote=text[begin:end].strip(), anchor=start,
            native_page_sha256=_sha(text.encode()),
            canonical_page_text_sha256=_sha(text.strip().encode()),
            design_field_family=family, existing_c_field=family,
            scientific_scope=scope, status="unreviewed", conflict_links=[],
            provisional_chinese_label=label,
            surrounding_context={"preceding_text_snippet": text[max(0, begin - 150):begin],
                                 "following_text_snippet": text[end:end + 150]},
            c_field_mapping={"surface": "design_field_family" if family else "unmapped",
                             "field_id": family, "gate_unit": None,
                             "reason": "Exact scoped clause; not numeric/critical-slot acceptance"},
            review_note="Owner-added exact source clause; independent acceptance pending",
        )
        if family == "endpoint":
            new["endpoint_key"] = "primary_endpoint"
        if new["proposal_id"] in atoms:
            raise ValueError("Duplicate new atom identity")
        atoms[new["proposal_id"]] = new
        result["atoms"].append(new)
        return new

    add("p61-safety-endpoints-primary", "p40-complete-primary-endpoints", 40,
        "The primary endpoints of the study", "As exploratory PD endpoints", "endpoint",
        {"domain": "primary_endpoints", "role": "primary",
         "exposure": "single and multiple SC doses", "timepoint": None},
        "主要终点：TEAE数量与严重程度、单次及多次给药后的PK参数")
    add("p21-full-analysis-set", "p8-primary-safety-endpoint", 8,
        "2.4.1 Primary Endpoint", "2.4.2 Secondary Endpoints", "endpoint",
        {"domain": "primary_safety_endpoint", "role": "primary",
         "duration_wording": "long term", "timepoint": None},
        "主要终点：长期安全性（AE、SAE、生命体征、实验室及ECG）")
    pk = add("p61-pk-population-definition", "p63-measurable-pk-population", 63,
             "All subjects dosed and having", "The individual plasma", "statistical",
             {"domain": "pharmacokinetics_population",
              "criteria": "dosed with any measurable serum study-drug concentration"},
             "PK分析集：已给药且有可测量血清药物浓度")
    pd = add("p61-pk-population-definition", "p64-measurable-pd-population", 64,
             "All subjects dosed and having", "PD parameters include", "statistical",
             {"domain": "pharmacodynamics_population",
              "criteria": "dosed with any measurable PD data"},
             "PD分析集：已给药且有可测量PD数据")
    governance = add("p8-medical-benefit-repeat", "p8-statistical-section-precedence", 8,
                     "In the event that a discrepancy", "Any amendments to the SAP", None,
                     {"domain": "document_precedence",
                      "scope": "statistical_section_discrepancies_only",
                      "automatic_winner": False},
                     "SAP明确的优先范围仅限方案统计章节中的描述差异")
    ldh = add("p69-statistical-methods", "p69-ldh-threshold-categories", 69,
              "The proportion of subjects with serum Lactate", "(ULN).", "endpoint",
              {"domain": "ldh_categories", "role": "unknown",
               "boundary_limitation": "Source omits equality at 1.8 ULN"},
              "方案LDH分档原文：未覆盖等于1.8倍ULN的边界", include_stop=True)
    ldh["endpoint_key"] = "unknown_endpoint"
    usage = add("p21-screened-set", "p22-screened-disposition-use", 22,
                "Patient disposition will be provided", "The total number of patients",
                "statistical",
                {"domain": "analysis_population_usage", "population": "all screened patients",
                 "purpose": "patient disposition"}, "筛选人群的受试者处置汇总用途")
    add("p27-ae-date-teae-rule", "p27-ae-coding-version", 27,
        "Version 17.0 of Medical Dictionary", "AEs will be considered", None,
        {"domain": "ae_coding", "dictionary": "MedDRA", "version": "17.0"},
        "AE编码采用MedDRA 17.0；不推广至其他域或文件")

    membership = atom("p21-screened-set")
    membership["scientific_scope"]["rule"] = (
        "Screened Set = all patients screened for participation"
    )
    membership["related_proposal_ids"] = [usage["proposal_id"]]
    usage["related_proposal_ids"] = [membership["proposal_id"]]
    exploratory = atom("p20-exploratory-tests")["scientific_scope"]
    exploratory["coexisting_statement"] = exploratory.pop("qualifies")
    repeat = atom("p8-medical-benefit-repeat")
    repeat["scientific_scope"].pop("divergence", None)
    repeat["scientific_scope"]["relationship"] = (
        "Protocol synopsis permits repeat participation; SAP adds experienced medical benefit. "
        "No unique-subject count or double-counting risk is established by this clause."
    )
    for a in result["atoms"]:
        if a["design_field_family"] == "sample_size":
            a["status"] = "unreviewed"
            a["c_field_mapping"]["gate_unit"] = None
            a["c_field_mapping"]["reason"] = (
                "Qualified source wording and distinct cohort/completer counts retained; "
                "not an accepted numeric total or critical-slot fulfillment."
            )

    conflicts = {c["conflict_id"]: c for c in result["conflicts"]}
    population = conflicts["conflict-apl-cp0514-population-def-protocol-vs-sap"]
    population["linked_atoms"] += [pk["proposal_id"], pd["proposal_id"]]
    population["description"] = (
        "Retain ITT/mITT differences and protocol-internal PK population tension: "
        "physical61 sample-drawn definition versus physical63 measurable-concentration rule. "
        "Physical64 measurable-PD population, SAP23 definitions and SAP20 unique-subject "
        "counting are separate context. SAP8 states statistical-section precedence, not "
        "universal authority and not resolution of protocol-internal differences."
    )
    population["related_context_atoms"] = [governance["proposal_id"]]
    conflicts["conflict-ak581-ldh-threshold-boundary"]["linked_atoms"] = [
        ldh["proposal_id"], atom("p21-protocol-changes-ldh-ada")["proposal_id"],
    ]
    formal = conflicts["conflict-apl-cp0514-no-formal-testing-vs-cohort4-ttests"]
    context_ids = [atom(s)["proposal_id"] for s in (
        "p20-baseline-counting-rules", "p62-efficacy-analysis-part2",
        "p3-amendment-output-provenance",
    )]
    formal["linked_atoms"] = [a for a in formal["linked_atoms"] if a not in context_ids]
    formal["related_context_atoms"] = context_ids + [governance["proposal_id"]]
    formal["description"] += (
        " Baseline rules, exploratory-output and amendment provenance are context, "
        "not opposing test declarations."
    )
    conflicts["conflict-apl-cp0514-missing-data-scope"]["linked_atoms"].append(
        atom("p27-ae-partial-stop-date-bullets")["proposal_id"]
    )
    result["conflicts"].append({
        "conflict_id": "conflict-apl-repeat-participation-condition", "trial_id": "NCT02264639",
        "title": "Repeat-participation wording: permission versus experienced-benefit condition",
        "description": (
            "Distinct printed conditions retained; no automatic winner or inferred count."
        ),
        "status": "unresolved_scope_difference",
        "resolution_policy": "retained_as_source_disclosed_without_winner_selection",
        "linked_atoms": [atom("p2-synopsis-sample-size")["proposal_id"], repeat["proposal_id"]],
    })
    # Rebuild both directions from the curated scoped graph, not the erroneous
    # inherited atom backlinks. No historical graph is changed in place.
    for a in result["atoms"]:
        a["conflict_links"] = []
    for c in result["conflicts"]:
        for identity in c["linked_atoms"]:
            atoms[identity]["conflict_links"].append(c["conflict_id"])
    for a in result["atoms"]:
        text = readers[a["document_filename"]].pages[a["physical_page"] - 1].extract_text()
        if _sha(text.encode()) != a["native_page_sha256"]:
            raise ValueError("Native page digest changed")
        extract_locator_quote(text, media_type="text/plain", locator=EvidenceLocator(
            document_role="design_document", page=a["physical_page"], paragraph=a["original_quote"],
        ))
    result.update(
        schema_version="ci-r24-c-native-pdf-design-proposal-v6", accepted=False,
        status="proposal_only", proposed_at=datetime.now(UTC).isoformat(),
        supersedes={"relative_path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA},
        owner_scope_repair={"id": "r24-150", "acceptance": "not_accepted"},
        verification={"native_quotes_replayed": len(result["atoms"]), "raw_pdfs_replayed": 4,
                      "accepted": False, "checked_at": datetime.now(UTC).isoformat()},
    )
    return result


def build_reviewed_scope_successor() -> dict[str, Any]:
    """Repair three source-checked metadata relations, without accepting facts."""
    raw = OUTPUT.read_bytes()
    if _sha(raw) != V6_SHA:
        raise ValueError("Frozen v6 predecessor changed")
    result: dict[str, Any] = copy.deepcopy(json.loads(raw))
    atoms = {a["proposal_id"]: a for a in result["atoms"]}

    def atom(suffix: str) -> dict[str, Any]:
        matches = [a for a in atoms.values() if a["proposal_id"].endswith(suffix)]
        if len(matches) != 1:
            raise ValueError(f"Expected one exact atom: {suffix}")
        return matches[0]  # type: ignore[no-any-return]

    for suffix in ("p71-number-of-patients", "p26-sample-size-determination"):
        atom(suffix)["c_field_mapping"]["reason"] = (
            "Protocol approximately 50 versus SAP up to approximately 50; "
            "retain qualified wording, not an accepted numeric total or critical-slot fulfillment."
        )
    population = next(c for c in result["conflicts"] if c["conflict_id"] == (
        "conflict-apl-cp0514-population-def-protocol-vs-sap"
    ))
    context = [atom(s)["proposal_id"] for s in (
        "p64-measurable-pd-population", "p20-general-analysis-baseline",
    )]
    population["linked_atoms"] = [a for a in population["linked_atoms"] if a not in context]
    population["related_context_atoms"] = list(dict.fromkeys(
        population.get("related_context_atoms", []) + context
    ))
    population["description"] = (
        "Protocol61 states ITT for disposition and safety/mITT for dosed subjects, "
        "while SAP23 combines ITT and Safety as dosed subjects. PK definitions retain "
        "Protocol61 sample-drawn, Protocol63 measurable-concentration, and SAP23 "
        "Safety-Set plus drawn sample with measurable concentration qualifications. "
        "Protocol64 PD and SAP20 unique-subject counting are separate related context. "
        "SAP8 precedence is limited to statistical-section discrepancies, not an automatic winner."
    )
    result["conflicts"].append({
        "conflict_id": "conflict-apl-ae-coding-dictionary-version-wording",
        "trial_id": "NCT02264639",
        "title": "AE coding dictionary: current version versus named version 17.0",
        "description": (
            "Protocol62 names the current MedDRA version for all AEs; SAP27 names 17.0 "
            "for all AEs. Retain the version-wording difference without inferring an error, "
            "a unique protocol version, or a rule for medical-history coding."
        ),
        "status": "unresolved_version_wording_difference",
        "resolution_policy": "retained_as_source_disclosed_without_winner_selection",
        "scientific_scope": {"domain": "ae_coding", "automatic_winner": False},
        "linked_atoms": [atom(s)["proposal_id"] for s in (
            "p62-teae-definition", "p27-ae-coding-version",
        )],
    })
    for a in result["atoms"]:
        a["conflict_links"] = []
    for c in result["conflicts"]:
        for aid in c["linked_atoms"]:
            atoms[aid]["conflict_links"].append(c["conflict_id"])
    readers: dict[str, PdfReader] = {}
    for document in result["documents"]:
        path = PDFS / document["filename"]
        if _sha(path.read_bytes()) != document["raw_sha256"]:
            raise ValueError("Original PDF changed")
        readers[document["filename"]] = PdfReader(path)
    for a in result["atoms"]:
        text = readers[a["document_filename"]].pages[a["physical_page"] - 1].extract_text()
        if _sha(text.encode()) != a["native_page_sha256"]:
            raise ValueError("Native page digest changed")
        extract_locator_quote(text, media_type="text/plain", locator=EvidenceLocator(
            document_role="design_document", page=a["physical_page"], paragraph=a["original_quote"],
        ))
    result.update(
        schema_version="ci-r24-c-native-pdf-design-proposal-v7", accepted=False,
        status="proposal_only", proposed_at=datetime.now(UTC).isoformat(),
        supersedes={"relative_path": str(OUTPUT.relative_to(ROOT)), "sha256": V6_SHA},
        owner_scope_repair={"id": "r24-155", "acceptance": "not_accepted"},
        verification={"native_quotes_replayed": len(result["atoms"]), "raw_pdfs_replayed": 4,
                      "accepted": False, "checked_at": datetime.now(UTC).isoformat()},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--successor", choices=("v6", "v7"), default="v6")
    args = parser.parse_args()
    result = build_reviewed_scope_successor() if args.successor == "v7" else build_successor()
    output = V7_OUTPUT if args.successor == "v7" else OUTPUT
    output.parent.mkdir(exist_ok=False)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode()
    with output.open("xb") as handle:
        handle.write(raw)
    print(json.dumps({"path": str(output.relative_to(ROOT)), "sha256": _sha(raw),
                      "atoms": len(result["atoms"]), "accepted": False, "current_changed": False}))


if __name__ == "__main__":
    main()
