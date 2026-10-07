"""Replay fixed baseline sources into existing CAS/SQLite/snapshot, never publish.

This is source-layer ingestion, not universe closure, arm association, semantic
equivalence or a fresh retrieval. The original source directory stays read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.ctgov_baseline_atoms import extract_ctgov_baseline_atoms
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import source_json_decoder


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def materialize(
    *, source_root: Path, raw_asset: ContentBlob, output: Path,
    trial_ids: tuple[str, ...], indication: str, cutoff: str, observed_at: datetime,
) -> dict[str, Any]:
    if (observed_at.tzinfo is None or observed_at.utcoffset() is None
        or observed_at > datetime.now(UTC)):
        raise ValueError("离线重放时间必须带时区且不在未来")
    if output.exists() or output.is_symlink():
        raise ValueError("基线候选必须使用全新输出目录")
    trials = tuple(nct.upper() for nct in trial_ids)
    if not trials or len(trials) != len(set(trials)):
        raise ValueError("请求研究集合为空或身份重复")
    raw = ContentAddressedStore(source_root).read_bytes(raw_asset)
    record = source_json_decoder().decode(raw.decode())
    studies = record.get("studies") if isinstance(record, dict) else None
    if not isinstance(studies, list):
        raise ValueError("原始分页缺少研究集合")
    counts: dict[str, int] = {}
    for study in studies:
        try:
            nct = study["protocolSection"]["identificationModule"]["nctId"]
        except (KeyError, TypeError):
            continue
        if isinstance(nct, str):
            counts[nct.upper()] = counts.get(nct.upper(), 0) + 1
    if any(counts.get(nct) != 1 for nct in trials):
        raise ValueError("请求研究不在固定来源集合内或存在重复身份")
    contract = create_project_contract(indication=indication, reports=["B"], outputs=["html"],
                                       cutoff=cutoff, created_at=observed_at)
    output.mkdir(parents=True, exist_ok=False)
    root = output / "project"
    create_project_workspace(root, contract)
    if ContentAddressedStore(root).put_bytes(raw, media_type=raw_asset.media_type) != raw_asset:
        raise ValueError("复制后的原始来源摘要不一致")
    # Derivation writes only the NEW project's CAS, never the original source root.
    sources = tuple(source_capture_from_ctgov_study(root, derive_saved_ctgov_record(
        root, raw_asset, nct, replayed_at=observed_at,
    )) for nct in trials)
    batches = tuple(extract_ctgov_baseline_atoms(source) for source in sources)
    facts = tuple(fact for batch in batches for fact in batch.facts)
    if not facts:
        raise ValueError("所有来源均无基线事实；失败候选保留，不发布零值结果")
    if len({fact.fact_id for fact in facts}) != len(facts):
        raise ValueError("基线原子身份重复，不采用first-wins")
    claims = tuple(ResearchClaim(
        claim_id="claim-" + fact.fact_id, claim_kind="direct_evidence",
        claim_text=fact.original_text, fact_ids=(fact.fact_id,),
    ) for fact in facts)
    fact_bytes = _json([fact.model_dump(mode="json") for fact in facts])
    issue_bytes = _json([asdict(issue) for batch in batches for issue in batch.issues])
    input_bytes = _json({
        "raw_asset": raw_asset.model_dump(mode="json"), "trial_ids": trials,
        "contract": contract.model_dump(mode="json"),
        "sources": [source.model_dump(mode="json") for source in sources],
        "acquisition_mode": "offline_cas_replay",
    })
    digest = _sha(fact_bytes + b"\n" + issue_bytes + b"\n" + input_bytes)
    lineage = ingest_research_evidence(
        project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="B",
        data_cutoff=contract.data_cutoff, scientific_content_digest=digest,
        created_at=observed_at, sources=sources, route_attempts=(), facts=facts, claims=claims,
    )
    for name, body in (("facts.json", fact_bytes), ("issues.json", issue_bytes),
                       ("inputs.json", input_bytes)):
        (output / name).write_bytes(body)
    receipt: dict[str, Any] = {
        "schema_version": "ctgov-baseline-source-candidate-1", "extractor_version": "1",
        "sources": len(sources), "facts": len(facts),
        "numeric_atoms": sum(fact.result_context is not None for fact in facts),
        "issues": sum(len(batch.issues) for batch in batches),
        "trial_ids": trials, "raw_asset": raw_asset.model_dump(mode="json"),
        "source_version_ids": lineage.source_version_ids,
        "fact_version_by_ref": dict(lineage.fact_version_by_ref),
        "snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "scientific_content_digest": digest, "observed_at": observed_at.isoformat(),
        "scientific_acceptance": "not_accepted", "current_generation_switched": False,
        "acquisition_mode": "offline_cas_replay", "product_binding": "not_inferred",
        "semantic_comparison": "not_accepted", "universe_closed": False,
        "file_sha256": {"facts.json": _sha(fact_bytes), "issues.json": _sha(issue_bytes),
                        "inputs.json": _sha(input_bytes)},
    }
    repo = Path(__file__).resolve().parents[1]
    receipt["code_sha256"] = {name: _sha((repo / name).read_bytes()) for name in (
        "tools/materialize_ctgov_baseline_candidate.py",
        "src/ci_workflow/application/ctgov_baseline_atoms.py",
        "src/ci_workflow/application/source_research_service.py",
        "src/ci_workflow/application/fresh_research_ingestion.py",
        "src/ci_workflow/sources/connectors/ctgov_fetch.py",
        "src/ci_workflow/storage/source_derivation.py",
    )}
    (output / "candidate-manifest.json").write_bytes(_json(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--raw-descriptor", type=Path, required=True)
    parser.add_argument("--trial", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--indication", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    result = materialize(
        source_root=args.source_root,
        raw_asset=ContentBlob.model_validate_json(args.raw_descriptor.read_text()),
        output=args.output, trial_ids=tuple(args.trial), indication=args.indication,
        cutoff=args.cutoff, observed_at=datetime.fromisoformat(args.observed_at),
    )
    print(json.dumps({key: result[key] for key in (
        "sources", "facts", "numeric_atoms", "issues", "scientific_acceptance",
        "current_generation_switched", "scientific_content_digest",
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
