"""Replay a locked baseline candidate through the ordinary B portal renderer.

Creates a new, explicitly unaccepted preview only. No source DB initialization,
source rewrite, current pointer, freshness check or universe acceptance occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ci_workflow.application.source_research_service import ResearchFact, SourceCapture
from ci_workflow.qc.browser import site_directory_digest
from ci_workflow.renderers.portal.report_a import SourceRow, StudyRow
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.b.source_baseline import build_source_baseline_view
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore


def build_preview(candidate: Path, output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise ValueError("预览必须使用全新目录，不覆盖历史候选")
    manifest_bytes = (candidate / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema_version") != "ctgov-baseline-source-candidate-1":
        raise ValueError("不是已声明的基线来源候选")
    for name in ("facts.json", "issues.json", "inputs.json"):
        if hashlib.sha256((candidate / name).read_bytes()).hexdigest() != (
            manifest["file_sha256"][name]
        ):
            raise ValueError("候选文件摘要不一致")
    snapshot = SnapshotStore(candidate / "project").read(
        LockedSnapshot.model_validate(manifest["snapshot"])
    )
    # Source versions are sorted in the manifest, not paired to input order.
    # Use explicit source/version relations from the immutable closure instead.
    sources = tuple(SourceCapture.model_validate(entry["capture"])
                    for entry in snapshot["closure"]["sources"])
    versions = {entry["capture"]["source_id"]: entry["source_version_id"]
                for entry in snapshot["closure"]["sources"]}
    if len(versions) != len(sources):
        raise ValueError("重复来源身份，不按数组顺序分配版本")
    facts = tuple(ResearchFact.model_validate(f) for f in
                  json.loads((candidate / "facts.json").read_bytes()))
    view = build_source_baseline_view(facts, source_versions=versions,
                                     fact_versions=manifest["fact_version_by_ref"])
    studies: list[StudyRow] = []
    for source in sources:
        protocol = json.loads(source.content_text)["protocolSection"]
        identity = protocol["identificationModule"]
        design = protocol.get("designModule", {})
        enrollment = design.get("enrollmentInfo", {})
        size = enrollment.get("count")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            size = None
        kind = enrollment.get("type", "UNKNOWN")
        if kind not in {"ACTUAL", "ESTIMATED"}:
            kind = "UNKNOWN"
        studies.append(StudyRow(
            id=identity["nctId"].casefold(), display_id=identity["nctId"], product_id=None,
            name=identity.get("briefTitle") or identity["nctId"],
            phase=" / ".join(design.get("phases", ())) or "未列示",
            region="登记研究", status=protocol.get("statusModule", {}).get(
                "overallStatus", "未列示"), role="来源研究，未绑定结果组产品",
            sample_size=size if kind == "ACTUAL" else None,
            reported_sample_size=size if kind == "ACTUAL" else None,
            planned_sample_size=size if kind == "ESTIMATED" else None,
            enrollment_type=kind,
        ))
    data = ReportBPortalData(
        schema_version="1.0", report_version="baseline-source-preview-v1",
        indication=json.loads((candidate / "inputs.json").read_bytes())["contract"]["indication"],
        data_cutoff=snapshot["data_cutoff"], report_snapshot_id=manifest["snapshot"]["snapshot_id"],
        related_studies=tuple(studies), baseline_views=view,
        sources=tuple(SourceRow(
            source=source.url, scope="登记基线：" + source.query_or_identifier,
            maturity="已定位来源，科学接受未完成",
            limitation="固定来源重放，不证明本次新鲜度或竞品宇宙闭包",
        ) for source in sources),
    )
    output.mkdir(parents=True, exist_ok=False)
    payload = data.model_dump_json(indent=2).encode()
    (output / "report-data.json").write_bytes(payload)
    site = output / "html"
    pages = render_report_b_site(data, site, publication_limitation_zh=(
        "基线来源候选：仅四项研究的描述性对照，不代表竞品全量或临床等价。"
    ))
    receipt: dict[str, Any] = {
        "source_candidate_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_snapshot_sha256": manifest["snapshot"]["sha256"],
        "report_data_sha256": hashlib.sha256(payload).hexdigest(),
        "site_digest": site_directory_digest(site), "pages": len(pages),
        "studies": len(studies), "source_numeric_atoms": len(view["facts"]),
        "scientific_acceptance": "not_accepted", "browser_acceptance": "not_run",
        "current_generation_switched": False, "product_association_inferred": False,
        "source_version_by_source": versions,
    }
    repo = Path(__file__).resolve().parents[1]
    receipt["code_sha256"] = {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in (
        "tools/render_baseline_source_candidate.py",
        "src/ci_workflow/reports/b/source_baseline.py",
        "src/ci_workflow/renderers/portal/report_b.py",
        "src/ci_workflow/reports/common/numeric_projection.py",
    )}
    (output / "preview-manifest.json").write_text(json.dumps(receipt, ensure_ascii=False,
                                                            sort_keys=True, indent=2))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_preview(args.candidate, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
