"""R2 信任根 bundle 闭合合同：科学复核 Python 模块必须随 HTML-only 包分发。

astra 阶段审阅 P1-5：默认 allowlist 对 ``qc`` 逐文件列举，漏收
``qc/review_receipt.py``；被收录的 ``application/scientific_review_transition.py``
与 ``application/run_service.py`` 直接 import 它，干净安装包中的科学复核路径
会缺第一方依赖。注册 receipt schema 不能弥补 Python 模块缺失。

本合同失败关闭地保证：

- 默认 allowlist 覆盖包内全部第一方 ``ci_workflow.*`` import 闭包（AST 审计）；
- 最终必需内容包含科学复核信任根链（运行时接线、回执、判定模型、
  能力层校验与两个 schema）；
- 隔离安装环境（过滤源码路径后）可完成科学复核入口导入、最小调用，
  且 v1 延后的非 HTML 格式运行时不可导入（HTML-only 闭合）。
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ci_workflow.application.fresh_install import install_bundle
from tools.build_bundle import build_bundle
from tools.bundle_contract import (
    DEFAULT_ALLOWLIST,
    FINAL_REQUIRED_CONTENT,
    expand_allowlist,
    validate_portal_asset_mirror,
)

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"

# 科学复核信任根链：独立回执签发 → 状态迁移的唯一授权路径所需模块与 schema。
SCIENTIFIC_REVIEW_REQUIRED_CONTENT: tuple[str, ...] = (
    "src/ci_workflow/application/review_issuer.py",
    "src/ci_workflow/application/scientific_review_transition.py",
    "src/ci_workflow/qc/review_receipt.py",
    "src/ci_workflow/qc/scientific.py",
    "src/ci_workflow/capabilities/scientific_qc.py",
    "schemas/scientific-qc-verdict.schema.json",
    "schemas/scientific-review-receipt.schema.json",
)

RESEARCH_HANDOFF_REQUIRED_CONTENT: tuple[str, ...] = (
    "src/ci_workflow/application/autonomous_research.py",
    "src/ci_workflow/application/research_package_submission.py",
    "src/ci_workflow/application/yaozh_access.py",
    "schemas/research-package.schema.json",
)

# 隔离安装环境必须能导入的科学复核入口（B/C 状态迁移依赖闭包的代表入口）。
ISOLATED_IMPORT_MODULES: tuple[str, ...] = (
    "ci_workflow",
    "ci_workflow.qc.review_receipt",
    "ci_workflow.qc.scientific",
    "ci_workflow.capabilities.scientific_qc",
    "ci_workflow.application.review_issuer",
    "ci_workflow.application.scientific_review_transition",
    "ci_workflow.application.autonomous_research",
    "ci_workflow.application.research_package_submission",
    "ci_workflow.application.yaozh_access",
)

# v1 延后的非 HTML 格式运行时：安装包必须保持不可导入。
DEFERRED_RUNTIME_MODULES: tuple[str, ...] = (
    "ci_workflow.renderers.pdf_native",
    "ci_workflow.renderers.html_ppt",
    "ci_workflow.renderers.pptx_master",
    "ci_workflow.application.ppt_master_job",
)

# 最小调用：纯函数，不依赖项目状态或宿主执行。
ISOLATED_MINIMAL_CALL = (
    "from ci_workflow.application.scientific_review_transition import "
    "scientific_review_receipt_path; "
    "path = scientific_review_receipt_path('B'); "
    "assert path.as_posix() == 'receipts/scientific_review/B/receipt.json', path"
)


def _allowed_files() -> set[str]:
    return set(expand_allowlist(ROOT, DEFAULT_ALLOWLIST))


def _first_party_import_gaps(allowed: set[str]) -> dict[str, list[str]]:
    """AST 审计：返回 allowlist 文件引用了但 allowlist 未覆盖的第一方模块。"""

    gaps: dict[str, list[str]] = {}
    for relative in sorted(allowed):
        if not relative.endswith(".py"):
            continue
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                if module != "ci_workflow" and not module.startswith("ci_workflow."):
                    continue
                base = "src/" + module.replace(".", "/")
                for candidate in (f"{base}.py", f"{base}/__init__.py"):
                    if (ROOT / candidate).is_file():
                        if candidate not in allowed:
                            gaps.setdefault(candidate, []).append(relative)
                        break
    return gaps


def test_default_allowlist_covers_first_party_import_closure() -> None:
    gaps = _first_party_import_gaps(_allowed_files())
    assert not gaps, (
        "默认 allowlist 漏收包内模块的第一方依赖，干净安装会导入失败："
        f"{ {target: sorted(importers) for target, importers in gaps.items()} }"
    )


def test_portal_asset_author_source_mirror_and_manifest_are_consistent() -> None:
    validate_portal_asset_mirror(ROOT)


def test_final_required_content_closes_scientific_review_trust_root() -> None:
    allowed = _allowed_files()
    missing_from_contract = [
        path for path in SCIENTIFIC_REVIEW_REQUIRED_CONTENT if path not in FINAL_REQUIRED_CONTENT
    ]
    assert not missing_from_contract, (
        f"最终必需内容缺少科学复核信任根模块：{missing_from_contract}"
    )
    absent = [path for path in SCIENTIFIC_REVIEW_REQUIRED_CONTENT if not (ROOT / path).is_file()]
    assert not absent, f"科学复核信任根文件不存在：{absent}"
    unallowed = [path for path in SCIENTIFIC_REVIEW_REQUIRED_CONTENT if path not in allowed]
    assert not unallowed, f"科学复核信任根文件不在默认 allowlist 内：{unallowed}"


def test_final_required_content_closes_research_handoff_boundary() -> None:
    allowed = _allowed_files()
    assert not [
        path for path in RESEARCH_HANDOFF_REQUIRED_CONTENT if path not in FINAL_REQUIRED_CONTENT
    ]
    assert not [path for path in RESEARCH_HANDOFF_REQUIRED_CONTENT if path not in allowed]


@pytest.fixture(scope="module")
def isolated_install(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """构建默认候选包并安装到隔离根，返回安装包内 src 根。"""

    if sys.platform == "win32":  # pragma: no cover - 平台守卫
        pytest.skip("隔离安装导入测试使用 POSIX 进程隔离")
    base = tmp_path_factory.mktemp("scientific-closure")
    result = build_bundle(ROOT, base)
    layout = install_bundle(result.archive_path, base / "install")
    return layout.bundle_root / "src"


def test_isolated_install_imports_scientific_review_entry_without_source_path(
    isolated_install: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """不借助源码路径：过滤 dev 环境注入的仓库 sys.path 后再导入并最小调用。"""

    driver = f"""
import importlib
import importlib.util
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
bundle_src = Path(sys.argv[2]).resolve()
source_entries = (repo, repo / "src")


def foreign(entry: str) -> bool:
    # 只剔除仓库源码路径（仓库根与 src 目录及其内部），保留宿主第三方
    # site-packages（含 .venv）：bundle 合同依赖宿主提供 pydantic/jsonschema
    # 等第三方运行时。
    if not entry:
        return False
    try:
        resolved = Path(entry).resolve()
    except OSError:
        return False
    if resolved in source_entries:
        return True
    return (repo / "src") in resolved.parents


sys.path[:] = [entry for entry in sys.path if not foreign(entry)]
sys.path.insert(0, str(bundle_src))

modules = {ISOLATED_IMPORT_MODULES!r}
origins = {{}}
for name in modules:
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", "") or ""
    assert origin, name
    resolved = Path(origin).resolve()
    assert bundle_src in resolved.parents, f"{{name}} 解析到安装包之外：{{origin}}"
    origins[name] = origin

{ISOLATED_MINIMAL_CALL}

deferred = {DEFERRED_RUNTIME_MODULES!r}
for name in deferred:
    assert importlib.util.find_spec(name) is None, f"延后格式运行时进入安装包：{{name}}"

print("ISOLATED_IMPORT_OK")
"""
    workdir = tmp_path_factory.mktemp("isolated-cwd")
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    env.setdefault("PATH", os.defpath)
    completed = subprocess.run(
        [sys.executable, "-E", "-s", "-c", driver, str(ROOT), str(isolated_install)],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, (
        "隔离安装环境导入科学复核入口失败：\n"
        f"stdout={completed.stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
    )
    assert "ISOLATED_IMPORT_OK" in completed.stdout
