"""Compare a frozen A display payload with a new candidate without trusting row IDs.

This is a diagnostic, not a source-atom reconciliation or acceptance gate. The
older portal lacks exact source locators, so a shared title/value is only a
candidate match. Duplicate candidates deliberately remain unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DOMAINS = ("efficacy", "safety", "additional_observations")
ATOM_FIELDS = (
    "domain", "raw_value", "raw_value_type", "raw_unit", "outcome_title",
    "class_title", "category_title", "group_id", "group_title", "timepoint",
    "display_population", "denominator_candidates",
)
CandidateKey = tuple[str, str, str, str]
DisplayItem = tuple[str, dict[str, Any]]


def load_payload(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".js":
        prefix = "window.REPORT_A="
        if not source.startswith(prefix):
            raise ValueError("Expected a window.REPORT_A assignment")
        source = source[len(prefix):].rstrip().removesuffix(";")
    payload = json.loads(source)
    if not isinstance(payload, dict):
        raise ValueError("A report payload must be an object")
    return payload


def _text(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _value(row: dict[str, Any]) -> str:
    raw = row.get("raw_value", row.get("value"))
    if raw is None:
        return "<missing>"
    try:
        return format(Decimal(str(raw)).normalize(), "f")
    except InvalidOperation:
        return _text(raw)


def _key(domain: str, row: dict[str, Any]) -> CandidateKey:
    if domain == "safety":
        # A safety term_key is weaker than a source endpoint/instance locator.
        title = row.get("term_key") or row.get("term")
        family = "safety_term"
    else:
        title = row.get("endpoint_source") or row.get("endpoint")
        family = "outcome_title"
    return (family, _text(row.get("trial_id")), _text(title), _value(row))


def _items(payload: dict[str, Any]) -> list[DisplayItem]:
    result: list[DisplayItem] = []
    for domain in DOMAINS:
        rows = payload.get(domain, [])
        if not isinstance(rows, list):
            raise ValueError(f"{domain} must be an array")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{domain} has a non-object row")
            result.append((domain, row))
    return result


def _reference(domain: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "domain": domain,
        "row_id": row.get("row_id"),
        "product_id": row.get("product_id"),
        "group_assignment_state": row.get("group_assignment_state"),
    }


def _changes(
    old: DisplayItem, new: DisplayItem,
) -> dict[str, list[Any]]:
    old_domain, old_row = old
    new_domain, new_row = new
    changes: dict[str, list[Any]] = {}
    for label, left, right in (
        ("domain", old_domain, new_domain),
        ("product_id", old_row.get("product_id"), new_row.get("product_id")),
        ("denominator", old_row.get("denominator"), new_row.get("denominator")),
    ):
        if left != right:
            changes[label] = [left, right]
    # Only an old raw arm label can be compared to a new raw source label.
    old_raw_arm = old_row.get("arm_detail")
    if old_raw_arm and _text(old_raw_arm) != _text(new_row.get("arm")):
        changes["raw_arm_label"] = [old_raw_arm, new_row.get("arm")]
    return changes


def audit_payloads(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    old_items = _items(old)
    new_items = _items(new)
    old_by_key: dict[CandidateKey, list[DisplayItem]] = defaultdict(list)
    new_by_key: dict[CandidateKey, list[DisplayItem]] = defaultdict(list)
    for domain, row in old_items:
        old_by_key[_key(domain, row)].append((domain, row))
    for domain, row in new_items:
        new_by_key[_key(domain, row)].append((domain, row))

    matches: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    old_only: list[dict[str, Any]] = []
    new_only: list[dict[str, Any]] = []
    for key in sorted(old_by_key.keys() | new_by_key.keys()):
        before = old_by_key.get(key, [])
        after = new_by_key.get(key, [])
        identity = list(key)
        if len(before) == len(after) == 1:
            left, right = before[0], after[0]
            matches.append({
                "candidate_source_key": identity,
                "match_basis": key[0],
                "old_row_id": left[1].get("row_id"),
                "new_row_id": right[1].get("row_id"),
                "changes": _changes(left, right),
            })
        elif not after:
            old_only.append({"candidate_source_key": identity,
                             "old_rows": [_reference(*item) for item in before]})
        elif not before:
            new_only.append({"candidate_source_key": identity,
                             "new_rows": [_reference(*item) for item in after]})
        else:
            ambiguous.append({
                "candidate_source_key": identity,
                "old_row_ids": [item[1].get("row_id") for item in before],
                "new_row_ids": [item[1].get("row_id") for item in after],
                "old_count": len(before), "new_count": len(after),
            })

    old_by_row_id = {(domain, str(row.get("row_id"))): _key(domain, row)
                     for domain, row in old_items if row.get("row_id")}
    new_by_row_id = {(domain, str(row.get("row_id"))): _key(domain, row)
                     for domain, row in new_items if row.get("row_id")}
    reused = [
        {"domain": domain, "row_id": row_id,
         "old_candidate_source_key": list(old_by_row_id[(domain, row_id)]),
         "new_candidate_source_key": list(new_by_row_id[(domain, row_id)])}
        for domain, row_id in sorted(old_by_row_id.keys() & new_by_row_id.keys())
        if old_by_row_id[(domain, row_id)] != new_by_row_id[(domain, row_id)]
    ]
    unassigned = {
        domain: sum(row.get("group_assignment_state") == "unknown"
                    for row in new.get(domain, []))
        for domain in DOMAINS
    }
    return {
        "status": "diagnostic_not_source_atom_acceptance",
        "limits": [
            "Old A display rows lack exact source atom locators; candidate matches "
            "do not prove atom identity.",
            "Translated old labels and row ordering cannot establish a clinical "
            "context match.",
            "Duplicate title/value or safety term/value candidates remain "
            "ambiguous; no first-wins pairing.",
        ],
        "counts": {
            "old": {domain: len(old.get(domain, [])) for domain in DOMAINS},
            "new": {domain: len(new.get(domain, [])) for domain in DOMAINS},
            "matched_unique": len(matches),
            "reclassified": sum("domain" in item["changes"] for item in matches),
            "context_changed": sum(bool(item["changes"]) for item in matches),
            "old_only": len(old_only), "new_only": len(new_only),
            "old_only_rows": sum(len(item["old_rows"]) for item in old_only),
            "new_only_rows": sum(len(item["new_rows"]) for item in new_only),
            "ambiguous_or_count_drift": len(ambiguous),
            "ambiguous_old_rows": sum(item["old_count"] for item in ambiguous),
            "ambiguous_new_rows": sum(item["new_count"] for item in ambiguous),
            "row_id_reused_for_different_source_key": len(reused),
            "new_unassigned": unassigned,
        },
        "matched_unique": matches,
        "old_only": old_only,
        "new_only": new_only,
        "ambiguous_or_count_drift": ambiguous,
        "row_id_reused_for_different_source_key": reused,
    }


def audit_row_source_maps(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compare exact registered source paths, never a display title/value guess.

    This produces a candidate refresh bridge, not permission to migrate edits or
    accept changed source versions. A changed context must be adjudicated first.
    """
    def index(sidecar: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        rows = sidecar.get("row_source_map")
        if not isinstance(rows, list):
            raise ValueError("derivation missing row_source_map")
        indexed: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("source row must be an object")
            trial, path = row.get("trial_id"), row.get("value_path")
            if not isinstance(trial, str) or not isinstance(path, str) or not path:
                raise ValueError("source row missing exact trial/path")
            key = (trial.casefold(), path)
            if key in indexed:
                raise ValueError("duplicate exact source atom; do not first-win")
            indexed[key] = row
        return indexed

    before, after = index(old), index(new)
    pairs = []
    for key in sorted(before.keys() & after.keys()):
        left, right = before[key], after[key]
        changed = [field for field in ATOM_FIELDS if left.get(field) != right.get(field)]
        pairs.append({
            "trial_id": key[0], "value_path": key[1],
            "old_row_id": left.get("row_id"), "new_row_id": right.get("row_id"),
            "changed_fields": changed,
            "source_page_changed": left.get("source_page_sha256") != right.get(
                "source_page_sha256"
            ),
        })
    return {
        "status": "candidate_exact_path_delta_not_scientific_acceptance",
        "counts": {
            "old_atoms": len(before), "new_atoms": len(after),
            "unchanged": sum(not pair["changed_fields"] for pair in pairs),
            "modified": sum(bool(pair["changed_fields"]) for pair in pairs),
            "withdrawn": len(before.keys() - after.keys()),
            "added": len(after.keys() - before.keys()),
            "source_page_changed": sum(pair["source_page_changed"] for pair in pairs),
        },
        "pairs": pairs,
        "withdrawn": [{"trial_id": key[0], "value_path": key[1],
                       "old_row_id": before[key].get("row_id")}
                      for key in sorted(before.keys() - after.keys())],
        "added": [{"trial_id": key[0], "value_path": key[1],
                   "new_row_id": after[key].get("row_id")}
                  for key in sorted(after.keys() - before.keys())],
        "limitations": [
            "The same JSON array path can be repurposed; changed context needs review.",
            "A source page digest may change without a result atom changing.",
            "Unchanged atoms do not establish a closed competitor universe or edit migration.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--old-sidecar", type=Path)
    parser.add_argument("--new-sidecar", type=Path)
    args = parser.parse_args()
    if (args.old_sidecar is None) != (args.new_sidecar is None):
        parser.error("both source sidecars are required for exact-path comparison")
    report = audit_payloads(load_payload(args.old), load_payload(args.new))
    if args.old_sidecar is not None and args.new_sidecar is not None:
        report["exact_source_delta"] = audit_row_source_maps(
            json.loads(args.old_sidecar.read_text(encoding="utf-8")),
            json.loads(args.new_sidecar.read_text(encoding="utf-8")),
        )
    report["input_sha256"] = {
        "old": hashlib.sha256(args.old.read_bytes()).hexdigest(),
        "new": hashlib.sha256(args.new.read_bytes()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
