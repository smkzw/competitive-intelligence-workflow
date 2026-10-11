"""Reproducible real six-atom holding/snapshot, not adoption or a product render."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime
from pathlib import Path

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    fact_version_material_digest,
    validate_research_historical_availability,
)
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import SnapshotStore

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".artifacts/1007-pmc-fact-holding-v1"
RECIPE = ROOT / "tests/integration/test_1007_pmc_fact_availability.py"


def main() -> None:
    assert hashlib.sha256(RECIPE.read_bytes()).hexdigest() == (
        "1bf59309de3f8aabe89493995f40ca8c2d70fcc4c36204bf1ddc0fa1ef2fc757"
    )
    OUT.mkdir()  # Never overwrite a previous candidate/failure.
    spec = importlib.util.spec_from_file_location("actual_six_replay", RECIPE)
    assert spec is not None and spec.loader is not None
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    project = OUT / "holding-project"
    sources, facts, proofs, cutoff = fixture.actual_case.__wrapped__(project)
    # Correct only copied contextual descriptions, not already-correct locators,
    # quotes, values, source bytes or frozen original packet.
    corrected = []
    for index, fact in enumerate(facts):
        context = fact.source_clause_context
        assert context is not None
        if fact.field_id == "efficacy.primary.prime.week24.contrast":
            context = context.model_copy(update={"label_zh": "PRIME第24周相对安慰剂差值"})
        elif fact.field_id == "safety.any_teae.column_3":
            context = context.model_copy(update={
                "label_zh": "总体治疗期TEAE暴露调整发生率",
                "scope_note_zh": "原表报告每100人年的暴露调整发生率；保留原公式脚注。",
            })
        else:
            continue
        updated = fact.model_copy(update={"source_clause_context": context})
        assert updated.original_text == fact.original_text and updated.locator == fact.locator
        corrected.append({"fact_id": fact.fact_id,
            "before_material_sha256": fact_version_material_digest(fact),
            "after_material_sha256": fact_version_material_digest(updated)})
        facts[index] = updated
        proofs[index] = proofs[index].model_copy(update={
            "fact_material_sha256": fact_version_material_digest(updated)})
    validate_research_historical_availability(sources, facts, proofs, cutoff)
    content = {"sources": [s.model_dump(mode="json") for s in sources],
        "facts": [f.model_dump(mode="json") for f in facts],
        "fact_public_version_proofs": [p.model_dump(mode="json") for p in proofs],
        "cutoff": cutoff.isoformat(), "state": "HOLDING_NOT_SCIENTIFICALLY_ADOPTED"}
    packet = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    (OUT / "holding-packet.json").write_bytes(packet)
    apply_migrations(project / "state/project.sqlite")
    digest = hashlib.sha256(packet).hexdigest()
    lineage = ingest_research_evidence(
        project_root=project, project_id="actual-six-object-holding", contract_version=1,
        report_kind="B", data_cutoff=cutoff, scientific_content_digest=digest,
        created_at=max(s.acquired_at for s in sources), sources=sources, facts=facts,
        route_attempts=(), claims=[ResearchClaim(claim_id="actual-six-source-holding",
            claim_text="真实六条来源候选，未授予临床采用", claim_kind="direct_evidence",
            fact_ids=tuple(f.fact_id for f in facts))],
    )
    manifest = project / lineage.evidence_snapshot.relative_path
    recovered = SnapshotStore(OUT / "recovered-project").restore_evidence_manifest(manifest)
    receipt = {"state": "ACTUAL_SIX_HOLDING_RESTORABLE_NOT_ADOPTED",
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                          text=True).strip(),
        "observed_at": datetime.now().astimezone().isoformat(),
        "packet_sha256": digest, "facts": len(facts), "sources": len(sources),
        "corrected_contexts": corrected,
        "source_hashes": {s.source_id: s.text_derivation.raw_asset.sha256 for s in sources},
        "snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "recovered_snapshot": recovered.model_dump(mode="json"),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "product_current_writes": 0, "publication_adoptions": 0}
    (OUT / "actual.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=1))
    print(json.dumps({"state": receipt["state"], "facts": len(facts), "sources": len(sources),
                      "corrected_contexts": len(corrected), "publication_adoptions": 0}))


if __name__ == "__main__":
    main()
