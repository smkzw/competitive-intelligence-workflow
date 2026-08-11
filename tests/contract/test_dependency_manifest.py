from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
LOCKFILE = ROOT / "uv.lock"
REQUIRED_RUNTIME_DEPENDENCIES = {
    "pydantic",
    "jinja2",
    "reportlab",
    "pypdf",
    "pdfplumber",
    "playwright",
    "pyyaml",
    "jsonschema",
}
REQUIRED_DEVELOPMENT_DEPENDENCIES = {
    "pytest",
    "ruff",
    "mypy",
    "types-jsonschema",
    "types-pyyaml",
}
APPROVED_LICENSES = {"Apache-2.0", "BSD-3-Clause", "MIT"}


def _dependency_name(requirement: str) -> str:
    return re.split(r"[<>=!~\[]", requirement, maxsplit=1)[0].strip().casefold()


def _exact_version(requirement: str) -> str:
    match = re.fullmatch(r"[^=<>!~\[]+==([^; ]+)", requirement)
    assert match, f"依赖必须固定为精确版本：{requirement}"
    return match.group(1)


def test_dependency_manifest_has_locked_version_license_and_purpose() -> None:
    assert PYPROJECT.is_file(), "pyproject.toml 尚未建立"
    assert LOCKFILE.is_file(), "uv.lock 尚未建立"

    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime_requirements = project["project"]["dependencies"]
    development_requirements = project["dependency-groups"]["dev"]
    metadata = project["tool"]["ci-workflow"]["dependencies"]

    runtime_by_name = {_dependency_name(item): item for item in runtime_requirements}
    development_by_name = {
        _dependency_name(item): item for item in development_requirements
    }
    assert set(runtime_by_name) == REQUIRED_RUNTIME_DEPENDENCIES
    assert set(development_by_name) == REQUIRED_DEVELOPMENT_DEPENDENCIES

    all_requirements = runtime_by_name | development_by_name
    assert set(metadata) == set(all_requirements)

    lock = tomllib.loads(LOCKFILE.read_text(encoding="utf-8"))
    locked_versions = {
        package["name"].casefold(): package["version"] for package in lock["package"]
    }
    for name, requirement in all_requirements.items():
        version = _exact_version(requirement)
        record = metadata[name]
        assert record["version"] == version
        assert record["license"] in APPROVED_LICENSES
        assert record["purpose"].strip()
        assert record["source"].startswith("https://")
        assert locked_versions[name] == version

    python_range = project["project"]["requires-python"]
    assert python_range == ">=3.12,<3.14"

    echarts = project["tool"]["ci-workflow"]["assets"]["echarts"]
    assert echarts == {
        "version": "6.1.0",
        "license": "Apache-2.0",
        "purpose": "交互式临床数据图表",
        "source": "https://www.npmjs.com/package/echarts/v/6.1.0",
    }


def test_uv_lock_is_fresh_for_current_pyproject() -> None:
    result = subprocess.run(
        ["uv", "lock", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
