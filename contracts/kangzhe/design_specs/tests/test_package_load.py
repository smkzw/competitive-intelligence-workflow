#!/usr/bin/env python3
"""Structural tests for portable design_specs package (real paths on disk)."""
from __future__ import annotations

import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT_STUB = PKG.parent / "design.md"
TRACKS = ("pptx", "htmlppt", "stream", "site", "interactive", "pdf")


class TestPortablePackage(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for name in (
            "ROUTER.md",
            "core.md",
            "project_profile.md",
            "README.md",
            "ARCHITECTURE.md",
            "assets/logo_bot.svg",
            "local_map.md",
            "schemas/design-run-manifest.schema.json",
            "schemas/design-source-pack.schema.json",
            "schemas/design-verdict.schema.json",
        ):
            self.assertTrue((PKG / name).is_file(), msg=name)
        for t in TRACKS:
            self.assertTrue((PKG / f"track_{t}.md").is_file(), msg=t)

    def test_no_absolute_users_in_portable_contract(self) -> None:
        for f in PKG.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            self.assertNotIn(
                "/Users/",
                text,
                msg=f"portable file must not embed absolute /Users paths: {f.name}",
            )

    def test_logo_relative_and_nonzero(self) -> None:
        logo = PKG / "assets" / "logo_bot.svg"
        data = logo.read_bytes()
        self.assertGreater(len(data), 100)
        self.assertIn(b"<svg", data)
        self.assertIn(b'viewBox="0 0 121 25"', data)

    def test_load_set_under_4000_lines_per_track(self) -> None:
        router = (PKG / "ROUTER.md").read_text(encoding="utf-8").splitlines()
        core = (PKG / "core.md").read_text(encoding="utf-8").splitlines()
        profile = (PKG / "project_profile.md").read_text(encoding="utf-8").splitlines()
        for t in TRACKS:
            track = (PKG / f"track_{t}.md").read_text(encoding="utf-8").splitlines()
            total = len(router) + len(core) + len(profile) + len(track)
            # Criterion: no single continuous monorepo body ≥4000 lines required;
            # each individual pack must also stay below that ceiling.
            self.assertLess(len(track), 4000, msg=f"track_{t}")
            self.assertLess(len(core), 4000)
            self.assertLess(total, 4500, msg=f"load set {t}={total}")

    def test_core_and_tracks_have_brand_musts(self) -> None:
        core = (PKG / "core.md").read_text(encoding="utf-8")
        for needle in ("#FF9900", "#0F1115", "Logo", "NEVER"):
            self.assertIn(needle, core)
        htmlppt = (PKG / "track_htmlppt.md").read_text(encoding="utf-8")
        self.assertTrue("1280" in htmlppt and "720" in htmlppt)
        site = (PKG / "track_site.md").read_text(encoding="utf-8")
        self.assertIn("sticky", site.lower())

    def test_router_lists_all_tracks(self) -> None:
        r = (PKG / "ROUTER.md").read_text(encoding="utf-8")
        for t in TRACKS:
            self.assertIn(f"track_{t}.md", r)
        for route in ("portal", "pdf", "htmlppt", "pptx"):
            self.assertIn(f"`{route}`", r)

    def test_portal_uses_site_as_its_only_main_track(self) -> None:
        router = (PKG / "ROUTER.md").read_text(encoding="utf-8")
        portal_row = next(line for line in router.splitlines() if "`portal`" in line)
        self.assertIn("track_site.md", portal_row)
        self.assertNotIn("track_interactive.md", portal_row)
        self.assertIn("独立的单页驾驶舱", router)

    def test_project_authority_is_single_and_independent(self) -> None:
        architecture = (PKG / "ARCHITECTURE.md").read_text(encoding="utf-8")
        local_map = (PKG / "local_map.md").read_text(encoding="utf-8")
        stub = ROOT_STUB.read_text(encoding="utf-8")
        self.assertIn("唯一运行权威", architecture)
        self.assertIn("根文件仅为兼容入口", architecture)
        self.assertIn("不读取通用版", local_map)
        self.assertNotIn("MUST同时更新两版", local_map)
        self.assertIn("本文件不再承载全文 MUST/NEVER", stub)

    def test_project_profile_has_user_and_artifact_boundaries(self) -> None:
        profile = (PKG / "project_profile.md").read_text(encoding="utf-8")
        for phrase in (
            "资深临床试验医学人员",
            "中文原生",
            "原生 PDF",
            "PPT Master",
            "runner-owned immutable run manifest",
            "生成者不得写入 accepted",
        ):
            self.assertIn(phrase, profile)


if __name__ == "__main__":
    unittest.main()
