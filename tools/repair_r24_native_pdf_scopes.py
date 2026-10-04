"""Create a preserved, unaccepted scope successor from fixed public PDF evidence.

This bounded evidence repair is not a clinical extraction engine or acceptance
route. Source/history/current are never overwritten; no synthetic acquisition.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "runs/execution/ci-r24-137-native-pdf-complete-scope-repair-20261003/"
    "native-pdf-design-proposal-v4.json"
)
SOURCE_SHA = "b3e9035857dd9f6bfc981039542de93b777db6057800e216f9b3a371ce2b796d"
PDFS = ROOT / ".artifacts/r24-96-c-public-documents-20261003/downloads"
OUTPUT = ROOT / ".artifacts/r24-147-native-pdf-scope-successor-20261003"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_successor() -> dict[str, Any]:
    raw = SOURCE.read_bytes()
    if _sha(raw) != SOURCE_SHA:
        raise ValueError("Frozen predecessor bytes changed; do not silently repair another source")
    old = json.loads(raw)
    result: dict[str, Any] = copy.deepcopy(old)
    result.update(
        schema_version="ci-r24-c-native-pdf-design-proposal-v5",
        status="proposal_only", accepted=False,
        proposed_at=datetime.now(UTC).isoformat(),
        status_note="Owner source-scope repair only; not medical acceptance or fresh acquisition",
        supersedes={"relative_path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA,
                    "predecessor_proposed_at": old["proposed_at"],
                    "time_limitation": "Predecessor time is future-dated; not time evidence"},
    )
    result["owner_scope_repair"] = {"id": "r24-147", "acceptance": "not_accepted"}
    atoms = {a["proposal_id"]: a for a in result["atoms"]}

    def atom(suffix: str) -> dict[str, Any]:
        found = [a for a in atoms.values() if a["proposal_id"].endswith(suffix)]
        if len(found) != 1:
            raise ValueError("Scope repair needs one exact predecessor identity")
        return found[0]  # type: ignore[no-any-return]

    # Do not disguise scientific family to work around critical-endpoint gates.
    # Only two source clauses explicitly name the exploratory/primary role.
    for suffix, role in (
        ("p61-efficacy-endpoint-exploratory", "exploratory_endpoint"),
        ("p61-safety-endpoints-primary", "primary_endpoint"),
        ("p61-pk-endpoints", "unknown_endpoint"),
        ("p61-efficacy-analysis-part1", "unknown_endpoint"),
        ("p62-teae-definition", "unknown_endpoint"),
        ("p71-pk-complement-activity", "unknown_endpoint"),
    ):
        a = atom(suffix)
        a.update(design_field_family="endpoint", existing_c_field="endpoint", endpoint_key=role)
        a["c_field_mapping"] = {
            "surface": "design_field_family", "field_id": "endpoint", "gate_unit": None,
            "reason": "Correct scientific type; explicit role separate. No endpoint/timepoint "
                      "pairing or full critical coverage is proved by this mapping alone.",
        }
    for suffix in ("p63-subgroup-descriptive-only", "p71-significance-level"):
        a = atom(suffix)
        a["existing_c_field"] = "statistical_model"
        a["c_field_mapping"] = {
            "surface": "closed_statistical_field", "field_id": "statistical_model",
            "gate_unit": "c_statistical_model",
            "reason": "Scoped descriptive-method statement, not a multiplicity procedure/alpha.",
        }
    a = atom("p1-metadata-and-version")
    a.update(design_field_family=None, existing_c_field=None)
    a["c_field_mapping"] = {
        "surface": "unmapped", "field_id": None, "gate_unit": None,
        "reason": "Version/date/CSR provenance is not regional, visit or operational design.",
    }
    atom("p22-general-data-handling-lloq-uloq")["provisional_chinese_label"] = (
        "实验室数据处理（低于LLOQ按下限一半推定；高于ULOQ仅称使用定量限，具体替代值未明确）"
    )

    readers = {}
    for doc in result["documents"]:
        raw_pdf = (PDFS / doc["filename"]).read_bytes()
        if _sha(raw_pdf) != doc["raw_sha256"]:
            raise ValueError("Original PDF bytes changed")
        readers[doc["filename"]] = PdfReader(PDFS / doc["filename"])

    start = atom("p27-ae-partial-date-bullets")
    page = readers[start["document_filename"]].pages[26].extract_text().strip()
    begin = page.index("x If a stop date is missing")
    end = page.index("Adverse Events Summary", begin)
    stop = {k: copy.deepcopy(start[k]) for k in (
        "trial_id", "document_filename", "document_raw_sha256", "physical_page",
        "printed_page_label", "source_role", "design_field_family", "existing_c_field",
        "native_page_sha256", "conflict_links", "c_field_mapping",
    )}
    stop_id = start["proposal_id"].replace("date-bullets", "stop-date-bullets")
    stop.update(
        proposal_id=stop_id, original_quote=page[begin:end].strip(),
        anchor="If a stop date is missing", status="unreviewed",
        provisional_chinese_label="AE部分结束日期推定（缺日/缺月与末次研究日期的对应规则）",
        scientific_scope={"domain": "ae_partial_stop_date_imputation",
                          "rules": start["scientific_scope"]["rules"][2:]},
        related_proposal_ids=[start["proposal_id"]],
        surrounding_context={"preceding_text_snippet": page[max(0, begin - 150):begin],
                             "following_text_snippet": page[end:end + 150]},
        review_note="New exact stop-date source sibling, unreviewed; no old quote changed",
    )
    start["scientific_scope"]["rules"] = start["scientific_scope"]["rules"][:2]
    start["provisional_chinese_label"] = "AE部分起始日期推定（缺日/缺月与首剂日期的对应规则）"
    start["related_proposal_ids"] = [stop_id]
    result["atoms"].append(stop)
    baseline = atom("p20-baseline-counting-rules")
    baseline["scientific_scope"]["rules"] = baseline["scientific_scope"]["rules"][:2]
    baseline["provisional_chinese_label"] = "基线定义（Day1及缺失替代；多次给药按队列与参数区分）"
    baseline["related_proposal_ids"] = [atom("p20-general-analysis-baseline")["proposal_id"]]

    # Replay every quote against the actual page and production exact locator.
    # No fuzzy translations, cross-page concatenation, OCR or source rewrite.
    for a in result["atoms"]:
        text = readers[a["document_filename"]].pages[a["physical_page"] - 1].extract_text()
        if _sha(text.encode()) != a["native_page_sha256"]:
            raise ValueError("Native page text digest mismatch")
        # Historical native-page hashes cover raw pypdf output; the existing
        # production derivation canonicalizes only boundary whitespace. Keep
        # both identities instead of changing a frozen predecessor digest.
        a["canonical_page_text_sha256"] = _sha(text.strip().encode())
        extract_locator_quote(
            text, media_type="text/plain", locator=EvidenceLocator(
                document_role="design_document", page=a["physical_page"],
                paragraph=a["original_quote"],
            ),
        )
    result["verification"] = {
        "checked_at": datetime.now(UTC).isoformat(), "native_quotes_replayed": len(result["atoms"]),
        "raw_pdfs_replayed": len(result["documents"]), "accepted": False,
        "page_hash_policy": "native_page_sha256=raw pypdf;canonical_page_text_sha256=strip",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = build_successor()
    OUTPUT.mkdir(exist_ok=False)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode()
    with (OUTPUT / "proposal-v5.json").open("xb") as handle:
        handle.write(raw)
    print(json.dumps({"path": str((OUTPUT / "proposal-v5.json").relative_to(ROOT)),
                      "sha256": _sha(raw), "atoms": len(result["atoms"]),
                      "accepted": False, "current_changed": False}))


if __name__ == "__main__":
    main()
