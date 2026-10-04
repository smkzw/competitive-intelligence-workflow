"""Current KZ6 site authority must travel with the HTML-only installed skill."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.bundle_contract import default_allowlist, expand_allowlist, is_v1_deferred_path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/kangzhe"


def test_current_site_contract_records_kz6_and_binds_installed_bytes() -> None:
    manifest = json.loads((CONTRACT / "manifest.json").read_text())
    assert manifest["current_source"]["version"] == "6.0.0"
    assert manifest["current_source"]["revision"] == "KZ6-0929-A04"
    assert manifest["runtime"]["authority"] == "v6-site"
    allowed = set(expand_allowlist(ROOT, default_allowlist(ROOT)))
    for relative, expected in manifest["runtime"]["files"].items():
        assert f"contracts/kangzhe/{relative}" in allowed
        assert hashlib.sha256((CONTRACT / relative).read_bytes()).hexdigest() == expected


def test_html_only_bundle_excludes_obsolete_design_runtime_and_tracks() -> None:
    allowed = set(expand_allowlist(ROOT, default_allowlist(ROOT)))
    old = {path for path in allowed if path.startswith("contracts/kangzhe/design_specs/")}
    assert old == {
        "contracts/kangzhe/design_specs/schemas/design-run-manifest.schema.json",
        "contracts/kangzhe/design_specs/schemas/design-source-pack.schema.json",
        "contracts/kangzhe/design_specs/schemas/design-verdict.schema.json",
    }
    assert not any("contracts/kangzhe/history/" in path for path in allowed)
    assert is_v1_deferred_path("contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.js")


def test_current_site_profile_keeps_user_scope_over_brand_defaults() -> None:
    profile = (CONTRACT / "v6-site/project-profile.md").read_text()
    for phrase in (
        "1440×900", "1600×900", "1920×1080", "2560×1440",
        "A/B/C", "登记", "监管", "16px", "HTML-only", "P0/P1",
    ):
        assert phrase in profile
    entry = (CONTRACT / "design.md").read_text()
    assert "v6-site/project-profile.md" in entry
    assert "design_specs/ROUTER.md" not in entry


def test_current_normative_snapshot_has_no_personal_paths_or_nonhtml_code() -> None:
    manifest = json.loads((CONTRACT / "manifest.json").read_text())
    copied = manifest["current_source"]["files"]
    assert "design_specs/06-motion-film.md" in copied
    assert "tokens/tokens.json" in copied
    for relative, expected in copied.items():
        path = CONTRACT / "v6-site" / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        assert path.suffix not in {".js", ".css", ".py"}
        if path.suffix in {".md", ".json"}:
            assert "/Users/" not in path.read_text()
