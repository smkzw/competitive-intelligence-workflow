"""Prepare exact ordinary A data and direct-consumer candidates, without DB writes.

No registration/adoption/render/current/semantic permission is granted here.
All report rows remain present, including unknown links and non-direct values.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.portal_consumer_registry import _safety_source_context_matches
from ci_workflow.renderers.portal.report_a import ReportAPortalData, SafetyRow

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
POOL = ROOT / ".artifacts/1007-scoped-source-pool-reconcile-v2"
OUT = ROOT / ".artifacts/1007-scoped-consumer-preparation-v2"
SNAPSHOT = PROJECT / "snapshots/evidence/evidence-snapshot_70170bf126764571d59faba8.json"
SEPARATE = {"nct04183335", "nct04202679", "nct04501666", "nct04501679"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Existing candidate preparation; reopen original, do not overwrite")
    assert (
        sha(POOL / "candidate.json")
        == "9aae15b65841b35910c51469ac0db875729d17fa47454e71e6cc281aa8f22587"
    )
    assert sha(SNAPSHOT) == "e8197d2ce20b10b3fb06fae8e2ed70637711ec61194c67454e400b435e932237"
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 11
    delivery = next(r for r in current.reports if r.report == "A")
    assert delivery.builder_input_relative_path is not None
    prior_path = PROJECT / delivery.builder_input_relative_path
    assert sha(prior_path) == delivery.builder_input_sha256
    before = {
        p: sha(p) for p in (PROJECT / "state/project.sqlite", PROJECT / "reports/current.json")
    }
    old = ReportAPortalData.model_validate_json(prior_path.read_bytes())
    raw = json.loads((POOL / "a-scoped.json").read_bytes())
    pool = json.loads((POOL / "candidate.json").read_bytes())
    snapshot = json.loads(SNAPSHOT.read_bytes())
    captured = {
        item["capture"]["source_id"]: item["source_version_id"]
        for item in snapshot["closure"]["sources"]
    }
    primaries = {}
    for item in snapshot["closure"]["facts"]:
        context = item["fact"].get("result_context")
        if context and context["value_role"] != "denominator":
            ref = item["consumer_binding"]["row_ref"]
            assert ref not in primaries
            primaries[ref] = item
    bound = {r["row_id"]: r for r in pool["bound_rows"]}
    payload = old.model_dump(mode="json")
    assert {p["id"] for p in raw["products"]} == set(old.product_ids)
    # Retain source-proven product labels/metadata; new trials come from the
    # ordinary fixed-source builder, never from a name/array-order guess.
    payload["trials"] = raw["trials"]
    payload["additional_observations"] = raw["additional_observations"]
    payload["source_evidence_snapshot_id"] = SNAPSHOT.stem
    payload["report_version"] = "v1-1007-scoped-source-v2-prepared"
    for collection in ("efficacy", "safety"):
        prior_rows = {r.row_id: r.model_dump(mode="json") for r in getattr(old, collection)}
        payload[collection] = [
            prior_rows[r["row_id"]] if r["trial_id"] in SEPARATE else bound.get(r["row_id"], r)
            for r in raw[collection]
        ]
    preliminary = ReportAPortalData.model_validate(payload)
    trials = {t.id: t for t in preliminary.trials}
    admitted, contexts, not_direct = {}, {}, []
    for collection in ("efficacy", "safety"):
        for row in getattr(preliminary, collection):
            ref = f"{collection}:{row.row_id}"
            item = primaries.get(ref)
            reason = None
            if row.group_assignment_state != "declared" or not row.group_id:
                reason = "arm_product_relation_unknown"
            elif item is None:
                reason = "no_locked_snapshot_primary_for_this_row"
            else:
                fact = item["fact"]
                context = fact["result_context"]
                numeric = float(fact["raw_value"])
                trial = trials[row.trial_id]
                source_group = context["group_title"].strip().casefold()
                relations = any(
                    link.product_id == row.product_id
                    and source_group in {label.strip().casefold() for label in link.arm_labels}
                    for link in trial.product_links
                )
                exact = (
                    row.value == numeric
                    and row.source_field_path == fact["locator"]["field_path"]
                    and row.source_version_id == captured[fact["source_id"]]
                    and row.source_text == fact["original_text"]
                )
                denominators = {
                    n["parsed_value"]
                    for n in context["denominator_candidates"]
                    if n["group_id"] == row.group_id
                }
                if not relations:
                    reason = "explicit_source_arm_product_relation_not_proven"
                elif not exact:
                    reason = "direct_value_or_locator_mismatch_derivation_not_assumed"
                elif collection == "efficacy":
                    count = context["value_role"] == "participant_count"
                    if (
                        context["domain"] != "efficacy"
                        or len(denominators) > 1
                        or (denominators and row.denominator not in denominators)
                        or (not denominators and row.denominator is not None)
                        or (count and (len(denominators) != 1 or row.numerator != numeric))
                        or (not count and row.numerator is not None)
                    ):
                        reason = "direct_role_or_scoped_denominator_unproven"
                    else:
                        contexts[ref] = {
                            "endpoint": context["endpoint"],
                            "timepoint": row.timepoint,
                            "group_title": context["group_title"],
                            "value_path": fact["locator"]["field_path"],
                        }
                elif not isinstance(row, SafetyRow) or not _safety_source_context_matches(
                    context,
                    row,
                    numeric,
                ):
                    reason = "safety_statistical_context_not_directly_compatible"
                if reason is None:
                    admitted[ref] = item["fact_version_id"]
            if reason is not None:
                not_direct.append({"row_ref": ref, "reason": reason})
    assert len(set(admitted.values())) == len(admitted)
    assert len(admitted) + len(not_direct) == len(preliminary.efficacy) + len(preliminary.safety)
    assert all(sha(p) == h for p, h in before.items())
    OUT.mkdir()
    write("a-preliminary.json", preliminary.model_dump(mode="json"))
    write(
        "direct-consumer-candidates.json",
        {
            "row_versions": admitted,
            "source_row_contexts": contexts,
            "not_direct": not_direct,
            "source_evidence_snapshot_id": SNAPSHOT.stem,
        },
    )
    write(
        "proof.json",
        {
            "status": "PREPARED_ONLY_NOT_REGISTERED_NOT_ACCEPTED_NOT_CURRENT",
            "input_hashes": {str(p.relative_to(ROOT)): h for p, h in before.items()},
            "a_sha256": sha(OUT / "a-preliminary.json"),
            "direct_candidates_sha256": sha(OUT / "direct-consumer-candidates.json"),
            "all_rows": len(admitted) + len(not_direct),
            "direct_candidates": len(admitted),
            "excluded_from_editing_not_from_report": dict(Counter(r["reason"] for r in not_direct)),
            "trials": len(preliminary.trials),
            "limits": (
                "Actual registration/independent source adoption/views/B/current NOT_RUN; "
                "no coaxis or universe permission"
            ),
        },
    )
    print(
        json.dumps(
            {
                "state": "PREPARED_ONLY",
                "direct_candidates": len(admitted),
                "all_rows": len(admitted) + len(not_direct),
            }
        )
    )


if __name__ == "__main__":
    main()
