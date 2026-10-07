"""Replay pinned A-compatible source rows with reopened official identities.

Development candidate only. Updating its report cutoff does not refresh dynamic
pipeline/approval facts or sign science. It never promotes a current generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ci_workflow.qc.browser import site_directory_digest
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.common.identity_projection import load_identity_context


def replay(source: Path, expected: str, project: Path, output: Path,
           cutoff: datetime) -> dict[str, Any]:
    if (source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != expected
            or output.exists() or cutoff.tzinfo is None or cutoff.utcoffset() is None
            or not output.resolve().is_relative_to(project.resolve())):
        raise ValueError("Requires pinned input, aware cutoff and fresh in-project output")
    checkpoint = json.loads((project / "identity-checkpoint.json").read_bytes())
    context = load_identity_context(project, checkpoint["graph_asset"])
    payload = json.loads(source.read_bytes())
    old_cutoff = payload["data_cutoff"]
    payload.update(data_cutoff=cutoff.isoformat(), report_version="1007V1-identity-dev-v1")
    a, b = ReportAPortalData.model_validate(payload), ReportBPortalData.model_validate(payload)
    projected = context.project(a.product_ids, cutoff=cutoff)
    limitation = (
        "身份来源开发候选：监管持有人依据已取得说明书版本；集团关系仅代表原文观察时点。"
        "临床事实沿用固定旧源，未重新核查动态管线/监管状态；不表示完整宇宙、医学接受或正式交付。"
    )
    render_report_a_site(a, output / "A", identity_context=context,
                         publication_limitation_zh=limitation)
    render_report_b_site(b, output / "B", identity_context=context,
                         publication_limitation_zh=limitation)
    sites = {}
    for kind, model in (("A", a), ("B", b)):
        root = output / kind
        (root / "builder-input.json").write_text(model.model_dump_json())
        digest, size = site_directory_digest(root)
        for product_id, identity in projected.items():
            for page in (root / "overview.html", root / "products" / f"{product_id}.html"):
                if identity["display_name"] not in page.read_text() or identity[
                    "company_label"
                ] not in page.read_text():
                    raise ValueError("Ordinary portal failed to consume reopened source identity")
        sites[kind] = {"site_sha256": digest, "site_bytes": size,
                       "physical_pages": len(list(root.rglob("*.html")))}
    receipt = {"input_sha256": expected, "historical_input_cutoff": old_cutoff,
               "candidate_cutoff": cutoff.isoformat(), "graph_asset": checkpoint["graph_asset"],
               "source_raw_sha256": checkpoint["source_raw_sha256"],
               "identity_product_ids": sorted(projected), "reports": sites,
               "dynamic_status_rechecked": False, "clinical_source_closure_accepted": False,
               "independent_science_accepted": False, "browser_inspected": False,
               "current_promoted": False, "rc_accepted": False}
    (output / "checkpoint.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cutoff", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    print(json.dumps(replay(args.input, args.sha256, args.project, args.output, args.cutoff),
                     ensure_ascii=False))
