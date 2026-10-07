"""Replay a pinned real source slice through the ordinary B portal, not current.

This tool subsets only explicit study membership. It never fills semantic fields,
renames products or signs acceptance. Keep historical inputs/sites unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ci_workflow.qc.browser import site_directory_digest
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _embedded(text: str, name: str) -> Any:
    return json.JSONDecoder().raw_decode(text.split(f"window.{name} = ", 1)[1].lstrip())[0]


def replay(source: Path, expected_sha: str, output: Path, studies: set[str]) -> dict[str, Any]:
    if output.exists() or source.is_symlink() or _sha(source) != expected_sha:
        raise ValueError("requires a pinned regular input and a fresh explicit output")
    raw = json.loads(source.read_bytes())
    raw["related_studies"] = [row for row in raw["related_studies"] if row["id"] in studies]
    if {row["id"] for row in raw["related_studies"]} != studies:
        raise ValueError("selected studies must all exist in the pinned source input")
    expected: dict[str, dict[str, Any]] = {}
    for key in ("efficacy_views", "safety_views", "supporting_evidence_views"):
        raw[key]["facts"] = [row for row in raw[key]["facts"] if row["trial_id"] in studies]
        expected.update({row["row_id"]: row for row in raw[key]["facts"]})
    raw["report_version"] = "1007V1-workspace-real-source-slice-v1"
    data = ReportBPortalData.model_validate(raw)
    output.mkdir(parents=True)
    candidate_input = output / "input.json"
    candidate_input.write_text(data.model_dump_json(), encoding="utf-8")
    pages = render_report_b_site(data, output / "site", publication_limitation_zh=(
        "1007V1固定登记资料交互开发切片，未本次重新核查动态状态。"
        "组别/产品未知关系保留，不表示医学接受、创新宇宙完整或正式交付。"
    ))
    html = (output / "site/overview.html").read_text(encoding="utf-8")
    workspace = _embedded(html, "__B_COMPARISON_WORKSPACE__")
    rows = {row["row_id"]: row for group in _embedded(html, "__CHART_GROUPS__")
            for row in group["rows"]}
    evidence = {item["row"]["row_id"]: item for item in _embedded(html, "__EVIDENCE_VIEWS__")}
    if not expected.keys() <= set(workspace["membership"]["row_ids"]):
        raise ValueError("ordinary overview lost a supplied source observation")
    for row_id, original in expected.items():
        row, view = rows[row_id], evidence[row_id]
        if row["value"] != original["value"] or row["unit"] != original["unit"]:
            raise ValueError("matrix projection changed a source value/unit")
        if view["original_text"] != original["source_text"]:
            raise ValueError("matrix projection changed the source quote")
    if _sha(source) != expected_sha:
        raise ValueError("historical source input changed during replay")
    digest, size = site_directory_digest(output / "site")
    receipt = {
        "source_sha256": expected_sha, "input_sha256": _sha(candidate_input),
        "study_ids": sorted(studies), "source_observations": len(expected),
        "matrix_members": len(workspace["membership"]["row_ids"]),
        "matrix_columns": len(workspace["columns"]), "physical_pages": len(pages),
        "site_sha256": digest, "site_bytes": size,
        "values_units_quotes_retained": True, "browser_inspected": False,
        "independent_science_accepted": False, "current_promoted": False,
        "multi_drug_equivalence_accepted": False, "rc_accepted": False,
    }
    (output / "checkpoint.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study", action="append", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.input, args.sha256, args.output, set(args.study)),
                     ensure_ascii=False))
