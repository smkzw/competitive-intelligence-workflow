from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts" / "kangzhe"
MANIFEST = CONTRACT_ROOT / "manifest.json"
DESIGN_ENTRY = CONTRACT_ROOT / "design.md"
DESIGN_PACKAGE = CONTRACT_ROOT / "design_specs"

SOURCE_COLLECTION_SHA256 = "be066868dd15d693c9b1d4c66cda45de7908f164bb8fe99f88d43d13b07cfc4f"
SOURCE_ENTRY_SHA256 = "049c0406823ce66bcfd5b5271ff8741730ed18abae0e5f2a7d19f92e8d3c9711"
SOURCE_COMPAT_STUB_SHA256 = "e513b4c5d56ae666148f1c22d535295483447f236da02d55efead0d8d185ed18"
PROJECT_ENTRY_SHA256 = "fa30cea68539a37aee2767b573e9a74acf3d9d38d86da9910661c5baef71735c"
SOURCE_DESIGN_SPECS_FILES = {
    "ARCHITECTURE.md": "c10c9b347fec85d0e147c2059a554cffdcc3c6e81e54d6a718a625a95f76622b",
    "README.md": "bf7e8d81881733c69d03782dbc52afaa1bc3b2553bfa2cdb691b8c409ce621fc",
    "ROUTER.md": "b007e9fd9b8005b8e1ccc592a520c6f35136c6bb411cf93a9afb4fc762fc65f5",
    "assets/htmlppt/gx_fx.css": "7e2ba09538f2e9c59c07f2ad2c8f708828c71f5f8e71771c5aa337da6bb5a572",
    "assets/htmlppt/gx_fx.js": "92cdb59102b888db0d046caeae34700cc29c97275dba626a652560603cb9c86b",
    "assets/logo_bot.svg": "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae",
    "core.md": "43a820323808dcbf6061226b9aaac82f64be31c0ceccc5514c929e2faf5edc5f",
    "htmlppt_fx.md": "0c3dbbe693f2cb39d463f360376b4c6237458734f1f9d677e04a271ee3a0496a",
    "local_map.md": "d9547afd2fcd476bd294b96c8ed032009803f3361fb9c5e2a061869d96610747",
    "tests/test_package_load.py": (
        "fc797f3540d1374b1c5137857d2d40f5a6e23131b123c38e6668a19a6f9e092c"
    ),
    "track_htmlppt.md": "deb873581246d8ce130805b27de2171adee53babe2ccb6ae902c9ee33f32e592",
    "track_interactive.md": "0e5c3cdfdd3e2cbfb68dd404e3afa9bb1c943b6bc849933cbd94a331ee1a3932",
    "track_pptx.md": "85e7a4910f80cef081cc0f7b29fbc8beaa7577806a730a3616916dd960543ad6",
    "track_site.md": "29961fc88c252bdbadf217e2a77717bce4cb94bf576ec40f7c58c8b165da1d1f",
    "track_stream.md": "219653f2c91f62137e4945d86fa5e8ab954e018f7c3c9bac340aaf17abb299ab",
}
REQUIRED_TRACKS = {
    "track_htmlppt.md",
    "track_interactive.md",
    "track_pdf.md",
    "track_pptx.md",
    "track_site.md",
    "track_stream.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collection_digest(files: list[Path], base: Path) -> str:
    lines = [f"{path.relative_to(base).as_posix()}\t{_sha256(path)}\n" for path in files]
    return hashlib.sha256("".join(sorted(lines)).encode()).hexdigest()


def _load_manifest() -> dict[str, object]:
    assert MANIFEST.is_file(), "项目内康哲设计合同清单尚未建立"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def test_latest_stable_source_and_user_internalization_decision_are_recorded() -> None:
    manifest = _load_manifest()
    source = manifest["source"]
    decision = manifest["decision"]
    assert isinstance(source, dict)
    assert isinstance(decision, dict)
    assert source["entry_sha256"] == SOURCE_ENTRY_SHA256
    assert source["stable_collection_sha256"] == SOURCE_COLLECTION_SHA256
    assert source["stable_double_read"] is True
    assert source["design_specs_files"] == SOURCE_DESIGN_SPECS_FILES
    assert decision["policy"] == "project_owned_frozen_copy"
    assert decision["upstream_sync_required"] is False
    assert decision["user_instruction"] == (
        "康哲design.md请选取最新版，并内化为项目自己的design spec，后续不用同步改通用版design.md。"
    )


def test_project_contract_is_self_contained_and_has_one_runtime_authority() -> None:
    manifest = _load_manifest()
    runtime = manifest["runtime"]
    assert isinstance(runtime, dict)
    assert runtime["entrypoint"] == "design.md"
    assert runtime["authority"] == "design_specs"
    assert DESIGN_ENTRY.is_file()
    assert _sha256(DESIGN_ENTRY) == PROJECT_ENTRY_SHA256
    entry = DESIGN_ENTRY.read_text(encoding="utf-8")
    assert "design_specs/ROUTER.md" in entry
    assert "非全文" in entry

    required = {
        "README.md",
        "ROUTER.md",
        "ARCHITECTURE.md",
        "core.md",
        "project_profile.md",
        "local_map.md",
        "assets/logo_bot.svg",
        "schemas/design-run-manifest.schema.json",
        "schemas/design-source-pack.schema.json",
        "schemas/design-verdict.schema.json",
    } | REQUIRED_TRACKS
    for relative in required:
        assert (DESIGN_PACKAGE / relative).is_file(), relative

    portable_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in DESIGN_PACKAGE.rglob("*.md")
        if path.name != "local_map.md"
    )
    assert "/Users/" not in portable_text
    assert "MUST同时更新两版" not in portable_text
    assert "根文件仅为兼容入口" in (DESIGN_PACKAGE / "ARCHITECTURE.md").read_text(encoding="utf-8")
    local_map = (DESIGN_PACKAGE / "local_map.md").read_text(encoding="utf-8")
    assert "/Users/" not in local_map
    assert "不读取通用版" in local_map


def test_latest_site_track_was_refreshed_once_then_frozen_in_project() -> None:
    manifest = _load_manifest()
    runtime = manifest["runtime"]
    assert isinstance(runtime, dict)
    refresh = runtime["latest_site_refresh"]
    assert isinstance(refresh, dict)
    expected = "29961fc88c252bdbadf217e2a77717bce4cb94bf576ec40f7c58c8b165da1d1f"
    assert refresh["upstream_track_sha256"] == expected
    assert refresh["project_track_sha256"] == expected
    assert refresh["policy_after_refresh"] == "project_owned_frozen_copy_no_future_sync"
    assert _sha256(DESIGN_PACKAGE / "track_site.md") == expected


def test_runtime_manifest_binds_every_project_contract_file() -> None:
    manifest = _load_manifest()
    runtime = manifest["runtime"]
    assert isinstance(runtime, dict)
    recorded = runtime["files"]
    assert isinstance(recorded, dict)

    actual_files = sorted(
        [
            DESIGN_ENTRY,
            *[
                path
                for path in DESIGN_PACKAGE.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            ],
        ]
    )
    actual = {path.relative_to(CONTRACT_ROOT).as_posix(): _sha256(path) for path in actual_files}
    assert recorded == actual
    assert runtime["collection_sha256"] == _collection_digest(actual_files, CONTRACT_ROOT)


def test_project_profile_freezes_user_language_and_four_format_routes() -> None:
    profile = (DESIGN_PACKAGE / "project_profile.md").read_text(encoding="utf-8")
    router = (DESIGN_PACKAGE / "ROUTER.md").read_text(encoding="utf-8")
    for phrase in (
        "资深临床试验医学人员",
        "中文原生",
        "不得展示程序状态、日志标签、提示词或后端字段名",
        "门户首页与详情页",
        "图在前、完整表格在后",
        "原生 PDF",
        "HTML-PPT",
        "PPT Master",
    ):
        assert phrase in profile
    for route in ("portal", "pdf", "htmlppt", "pptx"):
        assert f"`{route}`" in router
    portal_row = next(line for line in router.splitlines() if "`portal`" in line)
    assert "track_site.md" in portal_row
    assert "track_interactive.md" not in portal_row
    assert "track_pdf.md" in router


def test_density_exception_and_current_artifact_acceptance_cannot_be_self_declared() -> None:
    profile = (DESIGN_PACKAGE / "project_profile.md").read_text(encoding="utf-8")
    assert "data-density=ultra" in profile
    assert "仅限表体或坐标轴标签" in profile
    assert "KPI、流程标签、图例不得使用" in profile
    assert "生成者不得写入 accepted" in profile
    assert "runner-owned immutable run manifest" in profile
    assert "旧产物改写 mtime" in profile
    assert "当前 run" in profile
    for exact_condition in (
        "主体行不超过 18 行",
        "行高不低于 18 px",
        "对比度至少 4.5:1",
        "逐页原分辨率人工可读",
        "data-detail-ref",
    ):
        assert exact_condition in profile

    pptx_track = (DESIGN_PACKAGE / "track_pptx.md").read_text(encoding="utf-8")
    assert "只允许用于表体和坐标轴标签" in pptx_track
    assert "轴标签和辅助说明" not in pptx_track


def test_four_format_negative_boundaries_are_explicit() -> None:
    router = (DESIGN_PACKAGE / "ROUTER.md").read_text(encoding="utf-8")
    pdf_track = (DESIGN_PACKAGE / "track_pdf.md").read_text(encoding="utf-8")
    pptx_track = (DESIGN_PACKAGE / "track_pptx.md").read_text(encoding="utf-8")
    assert "不能继承 1280×720 幻灯片画布" in router
    assert "不得由网页截图拼接" in router
    assert "PPTX 必须经 PPT Master" in router
    assert "python-pptx" in pptx_track
    assert "截图" in pdf_track and "原生" in pdf_track


def test_project_profile_cannot_override_the_approved_v12_scope() -> None:
    profile = (DESIGN_PACKAGE / "project_profile.md").read_text(encoding="utf-8")
    assert "用户当前指令 > 已批准 v1.2 及其已批准范围修订 > 本文件 > 通用 `core/track`" in profile
    assert "不得缩减 A/B/C 报告范围" in profile


def test_project_profile_requires_pre_delivery_visual_finalization_loop() -> None:
    profile = (DESIGN_PACKAGE / "project_profile.md").read_text(encoding="utf-8")
    for phrase in (
        "定稿前视觉策划与美化闭环",
        "视觉策划 → 候选生成 → 真实渲染与逐项诊断 → 定向美化并复测",
        "最多进行三轮",
        "审阅者与生成者不同",
        "“无横向溢出”只是一项检查",
    ):
        assert phrase in profile


def test_compatibility_stubs_cannot_reintroduce_a_second_contract_body() -> None:
    manifest = _load_manifest()
    source = manifest["source"]
    assert isinstance(source, dict)
    source_stubs = source["compatibility_stubs"]
    assert isinstance(source_stubs, dict)
    assert set(source_stubs) == {
        "design.md",
        "design_share_v2.md",
        "design_shareable.md",
        "design_v2.md",
    }
    assert set(source_stubs.values()) == {SOURCE_COMPAT_STUB_SHA256}
    assert DESIGN_ENTRY.read_text(encoding="utf-8").count("MUST") <= 1
    assert "本文件不再承载全文 MUST/NEVER" in DESIGN_ENTRY.read_text(encoding="utf-8")
    mutated_entry = (
        DESIGN_ENTRY.read_text(encoding="utf-8") + "\n## 第二套规则正文\nMUST 另行执行\n"
    )
    assert hashlib.sha256(mutated_entry.encode()).hexdigest() != PROJECT_ENTRY_SHA256
