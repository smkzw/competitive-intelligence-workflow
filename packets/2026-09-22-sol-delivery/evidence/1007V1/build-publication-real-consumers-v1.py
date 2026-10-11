"""Real accepted source cells through ordinary A/B consumers and renderers.

Representative two-study slice, not a closed universe or multi-drug release.
Only append-only consumer declarations change in the existing project. Original
source facts, accepted reviews, current34 and historical report bytes stay fixed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.portal_consumer_registry import (
    SourceRowContext,
    register_a_source_consumers,
    register_b_shared_source_consumers,
)
from ci_workflow.application.source_research_service import ResearchFact
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.b.source_publication import build_source_publication_views
from ci_workflow.reports.common.identity_projection import load_identity_binding
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
RUN = PROJECT / "runs/publication-object-formal-v1"
OUT = ROOT / ".artifacts/1007-publication-real-consumers-v3"
TABLES = (
    "fact_versions",
    "evidence_fragments",
    "source_versions",
    "claim_versions",
    "claim_facts",
    "fact_evidence",
    "evidence_derivations",
    "source_text_derivations",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scientific_state() -> dict[str, str]:
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        return {
            table: hashlib.sha256(
                json.dumps(
                    db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            for table in TABLES
        }


def main() -> None:
    assert not OUT.exists(), "Resume the durable phase receipt; do not rebuild blindly"
    validate_portal_asset_mirror(ROOT)
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 34
    package = RUN / "source-package.json"
    assert sha(package) == "e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0"
    proof_path = ROOT / ".artifacts/1007-publication-identity-proof-v1/proposal.json"
    assert sha(proof_path) == "01a5d0b3aee1c441dce82d84e311c845cd40ec0f68a2fda5ba231133556f796b"
    review = (
        ROOT / "runs/conference/ci-1007-publication-identity-review-v1/evidence_single_object.md"
    )
    assert sha(review) == "9d076f50d9d29c2b80d1a1b939a7c38118a03588d503ba65fa29a9b06954a6f1"
    proof = json.loads(proof_path.read_bytes())
    cells = {cell["fact_id"]: cell for cell in proof["primary_cells"]}
    originals = json.loads(package.read_bytes())["facts"]
    facts = tuple(ResearchFact.model_validate(raw) for raw in originals if raw["fact_id"] in cells)
    assert len(facts) == 4
    ingestion = json.loads((RUN / "ingestion-return.json").read_bytes())
    snapshot = LockedSnapshot.model_validate(ingestion["evidence_snapshot"])
    snapshot_payload = SnapshotStore(PROJECT).read(snapshot)
    original_snapshot_id = snapshot.snapshot_id
    versions = ingestion["fact_version_by_ref"]
    source_versions = {}
    with sqlite3.connect(f"file:{PROJECT / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for fact in facts:
            version = versions[fact.fact_id]
            row = db.execute(
                "SELECT v.review_state,v.raw_value,v.normalized_value,"
                "f.content_text,f.source_version_id FROM fact_versions v JOIN evidence_fragments f "
                "ON f.fragment_id=v.primary_fragment_id WHERE v.fact_version_id=?",
                (version,),
            ).fetchone()
            assert row and row[:4] == ("accepted", fact.raw_value, None, fact.original_text)
            assert version == cells[fact.fact_id]["fact_version_id"]
            source_versions[fact.source_id] = row[4]
    a_delivery = next(item for item in current.reports if item.report == "A")
    base_path = PROJECT / a_delivery.builder_input_relative_path
    assert sha(base_path) == a_delivery.builder_input_sha256
    base = json.loads(base_path.read_bytes())
    product_id = "dupilumab-sar231893"
    product = next(item for item in base["products"] if item["id"] == product_id)
    # This representative slice contains only the primary efficacy table, not a
    # new claim that a full safety/landscape report has been generated.
    product = {**product, "result_status": "已有部分公开结果"}
    identity_binding = json.loads(
        (PROJECT / a_delivery.site_relative_path / "data/identity-context.json").read_bytes()
    )
    identity = load_identity_binding(PROJECT, identity_binding).for_products((product_id,))
    assert identity.project((product_id,), cutoff=current.created_at)[product_id]
    native_views = build_source_publication_views(
        facts, source_versions=source_versions, fact_versions=versions
    )
    rows, contexts, row_versions, questions = [], {}, {}, []
    view_rows = []
    arm_labels: dict[str, list[str]] = {"PRIME": [], "PRIME2": []}
    for view in native_views["efficacy"]["facts"]:
        fact = next(item for item in facts if item.fact_id == view["row_id"])
        context = fact.result_context
        assert context and context.trial_id in arm_labels
        cell = cells[fact.fact_id]
        assert cell["study"] == context.trial_id and cell["printed"] == fact.raw_value
        arm = "对照组" if cell["treatment_or_control"] == "control" else "治疗组"
        short_id = f"p1-{context.trial_id.lower()}-{'control' if arm == '对照组' else 'treatment'}"
        endpoint = "瘙痒评分（WI-NRS）改善≥4分"
        week = 24 if context.trial_id == "PRIME" else 12
        assert context.timepoint == f"week {week}"
        population = "全分析集（FAS）"
        row = {
            "row_id": short_id,
            "source_view_row_id": fact.fact_id,
            "product_id": product_id,
            "trial_id": context.trial_id.lower(),
            "group_id": context.group_id,
            "group_assignment_state": "declared",
            "endpoint": endpoint,
            "timepoint": f"第{week}周",
            "arm": arm,
            "arm_detail": context.group_title,
            "value": view["value"],
            "unit": "%",
            "population": population,
            "cohort_id": population,
            "value_basis": "reported_percent",
            "numerator": None,
            "denominator": None,
            "source_field_path": context.source_measure_path,
            "source_version_id": view["source_version_id"],
            "source_text": fact.original_text,
        }
        rows.append(row)
        ref = "efficacy:" + short_id
        row_versions[ref] = versions[fact.fact_id]
        contexts[ref] = SourceRowContext(
            endpoint=context.endpoint,
            timepoint=context.timepoint,
            group_title=context.group_title,
            value_path=context.source_measure_path,
        )
        arm_labels[context.trial_id].append(context.group_title)
        # Change only presentation/consumer association; source_fact, original
        # scientific context, paths, printed n and percent remain exact.
        display = {
            **view,
            "trial_id": context.trial_id.lower(),
            "product_id": product_id,
            "arm_id": context.group_id,
            "arm_label": arm,
            "arm_role": cell["treatment_or_control"],
            "group_label_zh": arm,
            "group_assignment_state": "declared",
            "value_basis": "reported_percent",
            "endpoint": endpoint,
            "original_definition": endpoint,
            "timepoint": row["timepoint"],
            "analysis_population": population,
            "analysis_population_zh": population,
        }
        assert display["source_fact"] == fact.model_dump(mode="json")
        view_rows.append(display)
        clause = display["source_clause_context"]
        label = clause["scientific_scope"]["row_label_path"]
        reference = next(
            item for item in clause["continuations"] if item["locator"]["field_path"] == label
        )
        questions.append(
            {
                "source_version_id": view["source_version_id"],
                "source_measure_path": context.source_measure_path,
                "question_id": "q-pruritus-nrs-ge4-improvement",
                "question_label_zh": "瘙痒评分改善≥4分",
                "basis_reference_ids": [reference["reference_id"]],
                "comparison_purpose": "clinical_question_descriptive",
            }
        )
    trials = [
        {
            "id": label.lower(),
            "display_id": label,
            "name": label,
            "product_id": product_id,
            "phase": "III期",
            "region": "全球",
            "status": "已完成",
            "role": "主要结果论文",
            "sample_size": None,
            "product_links": [
                {"product_id": product_id, "arm_role": "experimental", "arm_labels": labels}
            ],
        }
        for label, labels in arm_labels.items()
    ]
    # A new immutable consumer candidate, identical science/closure and new
    # creation time. Earlier uppercase-route declarations remain untouched.
    # The reversible presentation slug is not a new trial or a guessed NCT.
    snapshot = SnapshotStore(PROJECT).lock_evidence_snapshot(
        {**snapshot_payload, "created_at": datetime.now(UTC).isoformat()}
    )
    payload = {
        **base,
        "report_version": "1007-p1-source-slice-v3",
        "source_evidence_snapshot_id": snapshot.snapshot_id,
        "products": [product],
        "trials": trials,
        "efficacy": rows,
        "safety": [],
        "additional_observations": [],
        "user_edits": {},
        "efficacy_views": {
            "coverage_mode": "complete",
            "facts": view_rows,
            "clinical_questions": questions,
        },
        "safety_views": None,
        "sources": [
            {
                "source": "PMID 37142763｜Nature Medicine",
                "scope": "PRIME、PRIME2主要终点",
                "maturity": "主要结果论文",
                "limitation": "",
            }
        ],
    }
    for collection in ("regulatory", "companies", "patents", "history"):
        payload[collection] = [
            item for item in base[collection] if item["product_id"] == product_id
        ]
    data_a = ReportAPortalData.model_validate(payload)
    data_b = ReportBPortalData.model_validate(payload)
    before = scientific_state()
    OUT.mkdir()
    prewrite = {
        "phase": "PREPARED",
        "current_revision": 34,
        "science": before,
        "source_package_sha256": sha(package),
        "review_sha256": sha(review),
        "row_versions": row_versions,
    }
    (OUT / "phase.json").write_text(json.dumps(prewrite, sort_keys=True), encoding="utf-8")
    a = register_a_source_consumers(
        PROJECT,
        snapshot,
        data_a,
        row_versions,
        registered_at=datetime.now(UTC),
        source_row_contexts=contexts,
    )
    b = register_b_shared_source_consumers(
        PROJECT, snapshot, data_b, row_versions, registered_at=datetime.now(UTC)
    )
    assert len(a) == len(b) == 4
    for code, data, renderer in (
        ("A", data_a, render_report_a_site),
        ("B", data_b, render_report_b_site),
    ):
        (OUT / f"report-{code.lower()}-data.json").write_text(
            data.model_dump_json(), encoding="utf-8"
        )
        renderer(data, OUT / code, identity_context=identity)
    assert scientific_state() == before and read_current_delivery(PROJECT) == current
    result = {
        **prewrite,
        "phase": "REAL_SOURCE_CONSUMERS_AND_ORDINARY_RENDER_PASSED",
        "consumer_counts": {"A": len(a), "B": len(b)},
        "facts": 4,
        "studies": ["PRIME", "PRIME2"],
        "source_current_writes": 0,
        "browser_and_current_save": "NOT_RUN",
        "multi_drug": False,
        "files": {
            path.relative_to(OUT).as_posix(): sha(path) for path in OUT.rglob("*") if path.is_file()
        },
        "recipe_sha256": sha(Path(__file__)),
        "source_snapshot_id": original_snapshot_id,
        "consumer_snapshot": snapshot.model_dump(mode="json"),
        "reversible_trial_alias": {label.lower(): label for label in arm_labels},
        "prior_instrument_failure": "v1 ordinary render rejected instrument coverage_mode=full; "
        "eight source consumers already registered and reused idempotently; "
        "old partial output retained; "
        "v2 A rendered, B rejected uppercase route IDs. New v3 lowercase presentation aliases "
        "have a distinct consumer candidate snapshot, original facts and v1/v2 bindings unchanged",
    }
    (OUT / "actual.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8"
    )
    print(
        json.dumps(
            {key: result[key] for key in ("phase", "consumer_counts", "facts", "multi_drug")}
        )
    )


if __name__ == "__main__":
    main()
