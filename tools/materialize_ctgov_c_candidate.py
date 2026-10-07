"""Persist a fixed CT.gov C candidate, optionally a clearly review-only library.

Replay is not a live acquisition or a complete historical/universe search. Caller
product bindings are explicit proposals, not independent product identity proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ci_workflow.application.c_portal_consumer_registry import register_c_source_consumers
from ci_workflow.application.ctgov_c_design_projection import (
    CtgovCTrialBinding,
    project_ctgov_c_design_observations,
)
from ci_workflow.application.ctgov_design_atoms import extract_ctgov_protocol_design_atoms
from ci_workflow.application.fresh_c_research_package import research_facts_from_c_observations
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    SourceCapture,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.renderers.portal.report_a import ProductRow, StudyRow
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    render_report_c_review_candidate,
)
from ci_workflow.reports.c.endpoint_instances import validate_endpoint_timepoint_pairs
from ci_workflow.reports.common.identity_projection import load_project_identity_context
from ci_workflow.sources.connectors.ctgov_fetch import derive_saved_ctgov_record
from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
from ci_workflow.storage.snapshot_store import LockedSnapshot

# Keep this importable helper independent of command-line modules, which parse
# argv on import. These are registry display labels, not product-state claims.
_PHASE_LABELS = {
    "EARLY_PHASE1": "早期I期", "PHASE1": "I期", "PHASE2": "II期",
    "PHASE3": "III期", "PHASE4": "IV期", "NA": "不适用",
}
_STATUS_LABELS = {
    "RECRUITING": "招募中", "ACTIVE_NOT_RECRUITING": "进行中（不招募）",
    "COMPLETED": "已完成", "TERMINATED": "已终止", "WITHDRAWN": "已撤回",
    "NOT_YET_RECRUITING": "尚未招募", "SUSPENDED": "已暂停",
    "ENROLLING_BY_INVITATION": "邀请入组中", "UNKNOWN": "状态未更新",
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_recorded_time(moment: datetime) -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("实际记录时间必须包含明确时区")
    if moment > datetime.now(UTC):
        raise ValueError("实际记录时间不能位于未来")


def materialize(
    *, source_root: Path, raw_asset: ContentBlob, output: Path,
    bindings: tuple[CtgovCTrialBinding, ...], indication_id: str, indication: str,
    cutoff: str, observed_at: datetime,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Validate before creating a fresh output; retain exact originals and gaps."""
    _validate_recorded_time(observed_at)
    if output.exists() or output.is_symlink():
        raise ValueError("C candidate output requires a fresh/new directory")
    if not bindings:
        raise ValueError("C candidate requires explicit trial bindings")
    if project_root is None:
        contract = create_project_contract(
            indication=indication, reports=["C"], outputs=["html"],
            cutoff=cutoff, created_at=observed_at,
        )
    else:
        root = project_root.resolve()
        if project_root.is_symlink() or not output.resolve().is_relative_to(root):
            raise ValueError("既有C候选输出必须留在项目内")
        ContentAddressedStore(root).resolve_relative(output.resolve().relative_to(root).as_posix())
        contract = verify_project_workspace(root).contract
        if (contract.indication != indication or cutoff != contract.data_cutoff.date().isoformat()
                or "C" not in {kind.value for kind in contract.reports}):
            raise ValueError("C来源摄取与既有项目合同不一致")
    try:
        original = ContentAddressedStore(source_root).read_bytes(raw_asset)
    except (OSError, ContentIntegrityError, ValueError) as error:
        raise ValueError("C source CAS bytes cannot be verified") from error
    captures = tuple(
        source_capture_from_ctgov_study(source_root, derive_saved_ctgov_record(
            source_root, raw_asset, binding.trial_id.upper(), replayed_at=observed_at,
        )) for binding in bindings
    )
    projection = project_ctgov_c_design_observations(
        tuple(extract_ctgov_protocol_design_atoms(source) for source in captures),
        captures={source.source_id: source for source in captures},
        bindings=bindings, indication_id=indication_id,
    )
    instances = validate_endpoint_timepoint_pairs(
        projection.observations,
        universe_trial_ids={binding.trial_id.casefold() for binding in bindings},
        protocol_sources={source.source_id: source.content_text for source in captures},
    )
    facts = research_facts_from_c_observations(
        projection.observations, sources=captures,
        trial_names={binding.trial_id.casefold(): source.title
                     for binding, source in zip(bindings, captures, strict=True)},
    )
    claims = tuple(ResearchClaim(
        claim_id="claim-" + fact.fact_id, claim_kind="direct_evidence",
        claim_text=fact.normalized_value or fact.original_text,
        fact_ids=(fact.fact_id,),
    ) for fact in facts)
    projection_bytes = _json_bytes(projection.model_dump(mode="json"))
    input_bytes = _json_bytes({
        "raw_asset": raw_asset.model_dump(mode="json"),
        "bindings": [item.model_dump(mode="json") for item in bindings],
        "sources": [source.model_dump(mode="json") for source in captures],
        "contract": contract.model_dump(mode="json"),
        "indication_id": indication_id,
    })
    candidate_digest = _digest(projection_bytes + b"\n" + input_bytes)

    # No gate or current-generation writer is called here. A failed materialization
    # remains a recoverable failed directory, never a published candidate.
    output.mkdir(parents=True, exist_ok=False)
    root = project_root.resolve() if project_root is not None else output / "project"
    if project_root is None:
        create_project_workspace(root, contract)
    copied = ContentAddressedStore(root).put_bytes(original, media_type=raw_asset.media_type)
    if copied != raw_asset:
        raise ValueError("C candidate original CAS descriptor changed while copying")
    lineage = ingest_research_evidence(
        project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="C",
        data_cutoff=contract.data_cutoff, scientific_content_digest=candidate_digest,
        created_at=observed_at, sources=captures, route_attempts=(),
        facts=facts, claims=claims,
    )
    (output / "projection.json").write_bytes(projection_bytes)
    (output / "inputs.json").write_bytes(input_bytes)
    versions = dict(lineage.fact_version_by_ref)
    manifest: dict[str, Any] = {
        "schema_version": "ctgov-c-source-candidate-1",
        "observations": len(projection.observations),
        "source_versions": len(lineage.source_version_ids),
        "source_version_ids": list(lineage.source_version_ids),
        "endpoint_instances": len(instances),
        "unsupported_atoms": len(projection.unsupported_atoms),
        "unresolved_atoms": len(projection.unresolved_atoms),
        "protocol_gaps": len(projection.gaps),
        "scientific_content_digest": candidate_digest,
        "snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "fact_version_by_ref": versions,
        "current_generation_switched": False,
        "scientific_acceptance": "not_accepted",
        "acquisition_mode": "offline_cas_replay",
        "raw_asset": raw_asset.model_dump(mode="json"),
        "observed_at": observed_at.isoformat(),
        "file_sha256": {"projection.json": _digest(projection_bytes),
                        "inputs.json": _digest(input_bytes)},
        "limitations": [
            "固定登记分页离线重放，不是动态状态重新核查或历史时点还原。",
            "产品绑定是调用方提案；未证明产品别名、完整竞品宇宙或关键论文闭包。",
            "所有观察仍为候选；未运行独立医学、报告或发布验收。",
            "未支持、缺口和未决原子完整保存在 projection.json，不以占位补齐。",
            "终点标题、完整description和时间窗独立保留；队列限定仍按原文，未推断分析集或共轴资格。",
            "登记页面列有Protocol/SAP，但本候选未摄取PDF正文；统计设计未闭合。",
            "公开日期仅表示当前登记版本的posted day，不是研究首次公开日。",
            "period与development_role仍未设定，不从标题或研究顺序补造。",
        ],
    }
    package_root = Path(__file__).resolve().parents[1]
    manifest["code_sha256"] = {
        relative: _digest((package_root / relative).read_bytes()) for relative in (
            "tools/materialize_ctgov_c_candidate.py",
            "src/ci_workflow/application/ctgov_design_atoms.py",
            "src/ci_workflow/application/ctgov_c_design_projection.py",
            "src/ci_workflow/application/source_research_service.py",
            "src/ci_workflow/application/fresh_c_research_package.py",
            "src/ci_workflow/application/fresh_research_ingestion.py",
            "src/ci_workflow/reports/c/endpoint_instances.py",
            "src/ci_workflow/sources/connectors/ctgov_fetch.py",
            "src/ci_workflow/storage/source_derivation.py",
        )
    }
    (output / "candidate-manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def render_review_preview(output: Path, *, rendered_at: datetime,
                          project_root: Path | None = None) -> dict[str, Any]:
    """Reach ordinary C pages from a verified candidate; never publish current.

    Product identity stays an explicit caller proposal. Registry trial metadata is
    not a product pipeline, developer or regulatory-approval determination.
    """
    _validate_recorded_time(rendered_at)
    if output.is_symlink():
        raise ValueError("C review candidate root must not be a symlink")
    manifest = json.loads((output / "candidate-manifest.json").read_bytes())
    if manifest.get("schema_version") != "ctgov-c-source-candidate-1":
        raise ValueError("C review candidate manifest is not recognized")
    observed = datetime.fromisoformat(manifest["observed_at"])
    _validate_recorded_time(observed)
    if rendered_at < observed:
        raise ValueError("呈现时间不能早于资料观察时间")
    for name in ("inputs.json", "projection.json"):
        path = output / name
        if path.is_symlink() or _digest(path.read_bytes()) != manifest["file_sha256"][name]:
            raise ValueError("C review candidate inputs changed after materialization")
    inputs = json.loads((output / "inputs.json").read_bytes())
    projection = json.loads((output / "projection.json").read_bytes())
    sources = tuple(SourceCapture.model_validate(item) for item in inputs["sources"])
    by_trial = {source.query_or_identifier.casefold(): source for source in sources}
    if len(by_trial) != len(sources):
        raise ValueError("C review candidate has duplicate registry identities")
    bindings = tuple(CtgovCTrialBinding.model_validate(item) for item in inputs["bindings"])
    source_records = {
        trial_id: json.loads(source.content_text) for trial_id, source in by_trial.items()
    }
    products = tuple(ProductRow(
        id=product_id, name=product_id, target="未核实", modality="未核实",
        phase="产品阶段未核实", status="监管状态未核实", regions=("未核实",),
        route="未核实", developer="未核实", developer_basis="unverified",
        mechanism="未核实", result_status=(
            "已有部分公开结果" if any(
                source_records.get(binding.trial_id.casefold(), {}).get("resultsSection")
                for binding in bindings if binding.product_id == product_id
            ) else "暂无公开关键结果"
        ),
    ) for product_id in sorted({binding.product_id for binding in bindings
                               if binding.product_id is not None}))
    trials: list[StudyRow] = []
    for binding in bindings:
        source = by_trial.get(binding.trial_id.casefold())
        if source is None:
            raise ValueError("C review candidate binding has no actual registry record")
        protocol = json.loads(source.content_text)["protocolSection"]
        if protocol["identificationModule"]["nctId"].casefold() != binding.trial_id.casefold():
            raise ValueError("C review candidate trial ID differs from its actual source")
        design = protocol.get("designModule", {})
        enrollment = design.get("enrollmentInfo", {})
        count = enrollment.get("count")
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            raise ValueError("登记入组人数无法解析，不得补成零或删除研究")
        enrollment_type: Literal["ACTUAL", "ESTIMATED", "UNKNOWN"] = "UNKNOWN"
        if enrollment.get("type") == "ACTUAL":
            enrollment_type = "ACTUAL"
        elif enrollment.get("type") == "ESTIMATED":
            enrollment_type = "ESTIMATED"
        countries = tuple(sorted({str(location["country"])
            for location in protocol.get("contactsLocationsModule", {}).get("locations", [])
            if location.get("country")}))
        trials.append(StudyRow(
            id=binding.trial_id.casefold(), display_id=binding.trial_id.upper(),
            product_id=binding.product_id, name=source.title,
            phase="/".join(_PHASE_LABELS.get(str(phase), str(phase))
                           for phase in design.get("phases") or []) or "分期未列示",
            region="、".join(countries) or "研究地点未列示",
            status=_STATUS_LABELS.get(
                str(protocol.get("statusModule", {}).get("overallStatus") or ""),
                str(protocol.get("statusModule", {}).get("overallStatus") or "登记状态未列示"),
            ),
            sample_size=count if enrollment_type == "ACTUAL" else None,
            planned_sample_size=count if enrollment_type == "ESTIMATED" else None,
            reported_sample_size=count if enrollment_type != "ESTIMATED" else None,
            enrollment_type=enrollment_type, role="设计先例（待复核）",
        ))
    root = project_root.resolve() if project_root is not None else output / "project"
    contract = verify_project_workspace(root).contract
    if inputs["contract"] != contract.model_dump(mode="json"):
        raise ValueError("C候选来源与呈现项目合同不一致")
    report = ReportCPortalData(
        schema_version="1.0", report_version="r24-source-review-candidate",
        indication_id=inputs["indication_id"], indication=contract.indication,
        data_cutoff=contract.data_cutoff, products=products, trials=tuple(trials),
        observations=tuple(projection["observations"]),
    )
    site = root / "reports/C/review-candidate/html"
    if site.is_symlink() or (site.exists() and (not site.is_dir() or any(site.iterdir()))):
        raise ValueError(
            "C review preview requires a new empty site; earlier evidence stays intact"
        )
    registered = register_c_source_consumers(
        root, LockedSnapshot.model_validate(manifest["snapshot"]), report,
        manifest["fact_version_by_ref"], {source.source_id: source for source in sources},
        registered_at=rendered_at,
    )
    pages = render_report_c_review_candidate(report, site,
        identity_context=load_project_identity_context(root), publication_limitation_zh=(
        "仅展示本候选已捕获的登记研究，不代表竞品宇宙完整；产品对应关系待复核，"
        "研究阶段与地点不是产品管线或监管批准状态。方案/SAP全文尚未并入，统计细节仍有缺口。"
    ))
    (output / "review-portal-data.json").write_text(report.model_dump_json(), encoding="utf-8")
    result: dict[str, Any] = {
        "schema_version": "c-review-preview-1", "observations": len(report.observations),
        "registered_consumers": len(registered), "physical_pages": len(pages),
        "site_relative_path": site.relative_to(
            root if project_root is not None else output).as_posix(),
        "site_path_base": "project" if project_root is not None else "candidate",
        "scientific_acceptance": False, "current_generation_switched": False,
        "source_manifest_sha256": _digest((output / "candidate-manifest.json").read_bytes()),
        "report_data_sha256": _digest((output / "review-portal-data.json").read_bytes()),
        "html_sha256": {page.relative_to(site).as_posix(): _digest(page.read_bytes())
                        for page in pages},
    }
    (output / "review-preview-manifest.json").write_bytes(_json_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--raw-descriptor", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--indication-id", required=True)
    parser.add_argument("--indication", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--render-review-preview", action="store_true")
    parser.add_argument("--project", type=Path,
                        help="Ingest C into this existing project; preserve its contract")
    args = parser.parse_args()
    result = materialize(
        source_root=args.source_root,
        raw_asset=ContentBlob.model_validate_json(args.raw_descriptor.read_bytes()),
        output=args.output,
        bindings=tuple(CtgovCTrialBinding.model_validate(item)
                       for item in json.loads(args.bindings.read_bytes())),
        indication_id=args.indication_id, indication=args.indication, cutoff=args.cutoff,
        observed_at=datetime.fromisoformat(args.observed_at),
        project_root=args.project,
    )
    if args.render_review_preview:
        render_review_preview(args.output, rendered_at=datetime.fromisoformat(args.observed_at),
                              project_root=args.project)
    print(json.dumps({key: result[key] for key in (
        "observations", "source_versions", "endpoint_instances",
        "scientific_acceptance", "current_generation_switched", "scientific_content_digest",
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()
