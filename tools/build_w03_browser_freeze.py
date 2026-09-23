#!/usr/bin/env python3
"""Build the minimal W03 C browser-byte freeze from the fixed PNH CAS."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

from ci_workflow.application.fresh_c_research_package import load_fresh_c_research_package
from ci_workflow.renderers.portal.report_c import render_report_c_site

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "packets/2026-09-11-pnh-vertical"
EVIDENCE = ROOT / "packets/2026-09-22-sol-delivery/evidence/W03-browser-freeze"
PAGE_IDS = ("endpoint-timepoint-matrix", "treatment-arms")
JOURNEY_PATHS = tuple(EVIDENCE / "journeys" / f"{page_id}.json" for page_id in PAGE_IDS)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_builder(name: str):
    path = PACKET / name
    spec = importlib.util.spec_from_file_location("w03_freeze_" + path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法装载生产 builder：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build(temp: Path, site: Path) -> None:
    inputs = temp / "inputs"
    project = temp / "project"
    inputs.mkdir()
    project.mkdir()

    a_builder = _load_builder("build_pnh_a_payload.py")
    a_builder.OUT = inputs / "pnh-a-payload.json"
    a_builder.main()

    c_builder = _load_builder("build_pnh_c_audit.py")
    c_builder.HERE = inputs
    c_builder.PROJECT = project
    c_builder.main()

    package_path = project / "evidence/library/c-research-package.json"
    package = load_fresh_c_research_package(package_path)
    generated = render_report_c_site(package.report_data, site)

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    retained_data = EVIDENCE / "data"
    retained_data.mkdir(exist_ok=True)
    report_js = site / "data/report.js"
    sitemap = site / "data/sitemap.json"
    retained_report = retained_data / "report.js"
    retained_sitemap = retained_data / "sitemap.json"
    shutil.copyfile(report_js, retained_report)
    shutil.copyfile(sitemap, retained_sitemap)

    source_paths = (
        ROOT / "src/ci_workflow/application/fresh_c_research_package.py",
        ROOT / "src/ci_workflow/renderers/portal/report_c.py",
        ROOT / "src/ci_workflow/renderers/portal/templates/c/base.html.j2",
        ROOT / "src/ci_workflow/renderers/portal/templates/c/page.html.j2",
        ROOT / "src/ci_workflow/renderers/portal/assets/portal.js",
        ROOT / "src/ci_workflow/renderers/portal/assets/portal.css",
        ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js",
        ROOT / "src/ci_workflow/renderers/portal/assets/report-c.css",
        PACKET / "build_pnh_a_payload.py",
        PACKET / "build_pnh_c_audit.py",
        ROOT / "tools/build_w03_browser_freeze.py",
    )
    existing_journeys = tuple(path for path in JOURNEY_PATHS if path.is_file())
    if existing_journeys and len(existing_journeys) != len(JOURNEY_PATHS):
        raise RuntimeError("W03 browser freeze 旅程必须成对存在")
    journey_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in existing_journeys]
    screenshots = [ROOT / item["screenshot"]["path"] for item in journey_payloads]
    report_payload = package.report_data.model_dump(mode="json")
    manifest = {
        "schema_version": "w03-browser-freeze-v2",
        "report": "C",
        "builder_chain": "fixed-ctgov-cas -> PNH A main -> PNH C main -> render_report_c_site",
        "retention_policy": (
            "retain manifest, report.js, sitemap, two structured journey receipts, and two "
            "screenshots; full rebuild site remains outside the evidence bundle"
        ),
        "fixed_cas": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
            for path in a_builder.CAS
        ],
        "current_sources": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
            for path in source_paths
        ],
        "generated": {
            "c_research_package_sha256": _sha256(package_path),
            "site_file_count": len(generated),
            "sitemap_sha256": _sha256(sitemap),
            "retained_report_js": "data/report.js",
            "retained_report_js_sha256": _sha256(retained_report),
            "retained_sitemap": "data/sitemap.json",
            "retained_sitemap_sha256": _sha256(retained_sitemap),
            "trial_display_ids": sorted(trial["display_id"] for trial in report_payload["trials"]),
            "pages": [
                {
                    "page_id": page_id,
                    "route": f"/c/{page_id}",
                    "site_path": f"{page_id}.html",
                    "sha256": _sha256(site / f"{page_id}.html"),
                }
                for page_id in PAGE_IDS
            ],
        },
        "journeys": [
            {
                "page_id": payload["page_id"],
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
            }
            for path, payload in zip(existing_journeys, journey_payloads, strict=True)
        ],
        "screenshots": [
            {
                "page_id": payload["page_id"],
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
            }
            for path, payload in zip(screenshots, journey_payloads, strict=True)
        ],
    }
    (EVIDENCE / "site.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site-root",
        type=Path,
        help="Optional empty directory in which to retain the rebuilt site for a browser journey.",
    )
    args = parser.parse_args()
    if args.site_root is None:
        with tempfile.TemporaryDirectory(prefix="w03-browser-freeze-") as raw_tmp:
            temp = Path(raw_tmp)
            _build(temp, temp / "site")
        return

    site_root = args.site_root.resolve()
    if site_root.exists() and any(site_root.iterdir()):
        raise RuntimeError(f"--site-root 必须为空：{site_root}")
    site_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="w03-browser-freeze-build-") as raw_tmp:
        _build(Path(raw_tmp), site_root)


if __name__ == "__main__":
    main()
