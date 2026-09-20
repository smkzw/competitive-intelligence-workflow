from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
LOGO = ASSETS / "brand" / "cms-logo.svg"
ECHARTS = ASSETS / "third-party" / "echarts"
HTML_PPT = ASSETS / "html-ppt"

LOGO_SHA256 = "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae"
ECHARTS_SHA256 = "b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0"
ECHARTS_LICENSE_SHA256 = "634293835b43a6dd2094fa39182a3d9a6b9ca43b7fdb9ac354e8037af2a3093a"
HTML_PPT_UPSTREAM_RUNTIME_SHA256 = (
    "d7b066a96b99fcf5c9e15b593283a57a3d43ac2bcf795d172adc7f3ba0844f79"
)
HTML_PPT_LICENSE_SHA256 = "a5ed4059e25a3ec35e439abd2623753d1f42d4aa4989ffb5c6b7a97b61f6a949"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def test_cms_logo_is_the_verified_official_offline_asset() -> None:
    manifest = _load_json(ASSETS / "brand" / "manifest.json")
    source = ROOT / str(manifest["source"])
    assert LOGO.is_file()
    assert source.is_file()
    assert _sha256(LOGO) == LOGO_SHA256
    assert _sha256(source) == LOGO_SHA256
    assert source.read_bytes() == LOGO.read_bytes()
    assert manifest["name"] == "康哲品牌标识"
    assert manifest["file"] == "cms-logo.svg"
    assert manifest["sha256"] == LOGO_SHA256
    assert manifest["bytes"] == 9542
    assert manifest["view_box"] == "0 0 121 25"
    assert manifest["official_url"] == (
        "https://web.cms.net.cn/wp-content/themes/qnz/assets/img/logo_bot.svg"
    )
    assert manifest["official_retrieval_date"] == "2026-08-11"
    svg = LOGO.read_text(encoding="utf-8")
    assert "<svg" in svg
    assert 'viewBox="0 0 121 25"' in svg
    assert "<script" not in svg.casefold()


def test_echarts_6_1_0_classic_bundle_and_license_are_exact_and_offline() -> None:
    bundle = ECHARTS / "echarts.min.js"
    license_file = ECHARTS / "LICENSE"
    manifest = _load_json(ECHARTS / "manifest.json")
    assert _sha256(bundle) == ECHARTS_SHA256
    assert _sha256(license_file) == ECHARTS_LICENSE_SHA256
    assert manifest["name"] == "echarts"
    assert manifest["version"] == "6.1.0"
    assert manifest["license"] == "Apache-2.0"
    assert manifest["bundle_sha256"] == ECHARTS_SHA256
    assert manifest["license_sha256"] == ECHARTS_LICENSE_SHA256
    assert manifest["npm_integrity"] == (
        "sha512-q0yaFPggC9FUdsWH4blavRWFmxdrIodbkoKNAjJudAI6CA9gNPxHtV2RcZNEepZV"
        "lk4yvBYkOkbk6HIVpIyHZA=="
    )
    text = bundle.read_text(encoding="utf-8")
    assert "sourceMappingURL" not in text
    assert "require(" not in text
    assert "import(" not in text


def test_html_ppt_runtime_manifest_binds_upstream_and_every_derived_file() -> None:
    manifest = _load_json(HTML_PPT / "manifest.json")
    assert manifest["source_repository"] == "https://github.com/lewislulu/html-ppt-skill"
    assert manifest["source_commit"] == "f3a8435d3901697d5ac5e64d356c933637e43107"
    assert manifest["source_runtime_sha256"] == HTML_PPT_UPSTREAM_RUNTIME_SHA256
    assert manifest["license"] == "MIT"
    assert manifest["license_sha256"] == HTML_PPT_LICENSE_SHA256
    assert _sha256(HTML_PPT / "LICENSE") == HTML_PPT_LICENSE_SHA256
    files = manifest["derived_files"]
    assert isinstance(files, dict)
    assert files == {
        "runtime.css": _sha256(HTML_PPT / "runtime.css"),
        "runtime.js": _sha256(HTML_PPT / "runtime.js"),
    }


def test_html_ppt_runtime_is_chinese_native_and_has_no_generic_theme_controls() -> None:
    runtime = (HTML_PPT / "runtime.js").read_text(encoding="utf-8")
    for label in (
        "演讲者视图",
        "当前页",
        "下一页",
        "逐字稿",
        "计时",
        "上一页",
        "重新计时",
        "演示结束",
    ):
        assert label in runtime
    for forbidden in (
        "cycleTheme",
        "data-themes",
        "themeIdx",
        "cycleAnimation",
        "animationIndicator",
        "overview",
        "Presenter View",
        "CURRENT",
        "SPEAKER SCRIPT",
        "END OF DECK",
    ):
        assert forbidden not in runtime
    assert not re.search(r"case\s+['\"](?:t|T|a|A|o|O)['\"]", runtime)


def test_html_ppt_runtime_has_required_navigation_presenter_and_offline_boundaries() -> None:
    runtime = (HTML_PPT / "runtime.js").read_text(encoding="utf-8")
    css = (HTML_PPT / "runtime.css").read_text(encoding="utf-8")
    for key in ("ArrowLeft", "ArrowRight", "PageUp", "PageDown", "Home", "End"):
        assert key in runtime
    for key in ("case \"f\"", "case \"s\"", "case \"n\"", "case \"r\""):
        assert key in runtime.casefold()
    assert "BroadcastChannel" in runtime
    assert "aside.notes" in runtime
    assert "?preview=" in runtime
    assert "#/" in runtime
    assert "data-current" in runtime and "data-total" in runtime
    assert "1280" in css and "720" in css
    assert "Math.min(viewportWidth / DESIGN_WIDTH, viewportHeight / DESIGN_HEIGHT)" in runtime
    for forbidden_network_api in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource"):
        assert forbidden_network_api not in runtime
    assert "@import" not in css
    assert "url(http" not in css.casefold()


def test_runtime_css_is_structure_only_and_does_not_replace_kangzhe_brand_tokens() -> None:
    css = (HTML_PPT / "runtime.css").read_text(encoding="utf-8")
    for generic_selector in (".card", ".pill", ".kpi-grid", ".theme-"):
        assert generic_selector not in css
    assert "#ff9900" not in css.casefold()
    assert ".deck > .slide:not(.is-active)" in css
    assert "visibility: hidden" in css
    assert "pointer-events: none" in css
