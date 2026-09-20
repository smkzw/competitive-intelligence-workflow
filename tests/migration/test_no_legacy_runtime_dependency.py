from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCANNER = REPOSITORY_ROOT / "tools" / "check_no_legacy_refs.py"
LEGACY_REPOSITORY_ROOT = Path(
    "/Users/smkzw/Documents/AI Products/" + "竞品调研" + "工作流"
)


def _run_scanner(root: Path, legacy_root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["CI_WORKFLOW_LEGACY_ROOT"] = str(legacy_root)
    return subprocess.run(
        [sys.executable, str(SCANNER), "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_no_legacy_runtime_dependency_contract(tmp_path: Path) -> None:
    assert SCANNER.is_file(), "旧运行依赖扫描器尚未实现"

    legacy_root = tmp_path / "旧工程"
    legacy_root.mkdir()
    candidate = tmp_path / "新工程"
    (candidate / "src").mkdir(parents=True)
    (candidate / "docs").mkdir()
    (candidate / "fixtures").mkdir()
    (candidate / "logs").mkdir()
    (candidate / "src" / "clean.py").write_text("VALUE = 'self-contained'\n")

    clean = _run_scanner(candidate, legacy_root)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "LEGACY_REF_OK" in clean.stdout

    (candidate / "src" / "bad.py").write_text(
        f"LEGACY_DATA = {str(legacy_root)!r}\n",
        encoding="utf-8",
    )
    runtime_reference = _run_scanner(candidate, legacy_root)
    assert runtime_reference.returncode == 1
    assert "LEGACY_RUNTIME_REFERENCE" in runtime_reference.stdout
    (candidate / "src" / "bad.py").unlink()

    (candidate / "src" / "bad_relative.py").write_text(
        f"LEGACY_DATA = '../{legacy_root.name}/data'\n",
        encoding="utf-8",
    )
    relative_reference = _run_scanner(candidate, legacy_root)
    assert relative_reference.returncode == 1
    assert "LEGACY_RUNTIME_REFERENCE" in relative_reference.stdout
    (candidate / "src" / "bad_relative.py").unlink()

    (candidate / "docs" / "history.md").write_text(
        f"historical: 原系统曾位于 {legacy_root}\n",
        encoding="utf-8",
    )
    marked_history = _run_scanner(candidate, legacy_root)
    assert marked_history.returncode == 0, marked_history.stdout

    (candidate / "docs" / "history.md").write_text(
        f"原系统曾位于 {legacy_root}\n",
        encoding="utf-8",
    )
    unmarked_history = _run_scanner(candidate, legacy_root)
    assert unmarked_history.returncode == 1
    assert "UNMARKED_HISTORICAL_REFERENCE" in unmarked_history.stdout
    (candidate / "docs" / "history.md").unlink()

    (candidate / "logs" / "review.txt").write_text(
        f"只读复核曾检查 {legacy_root}\n",
        encoding="utf-8",
    )
    process_record = _run_scanner(candidate, legacy_root)
    assert process_record.returncode == 0, process_record.stdout

    outside_target = tmp_path / "outside-runtime.txt"
    outside_target.write_text("external", encoding="utf-8")
    (candidate / "src" / "external-link").symlink_to(outside_target)
    external_symlink = _run_scanner(candidate, legacy_root)
    assert external_symlink.returncode == 1
    assert "EXTERNAL_RUNTIME_SYMLINK" in external_symlink.stdout


def test_current_repository_has_no_legacy_runtime_dependency() -> None:
    current_repository = _run_scanner(REPOSITORY_ROOT, LEGACY_REPOSITORY_ROOT)
    assert current_repository.returncode == 0, current_repository.stdout
    assert "LEGACY_REF_OK" in current_repository.stdout


def test_legacy_marker_is_lexical_and_does_not_resolve_symlink(tmp_path: Path) -> None:
    """The scanner must never probe or resolve the forbidden legacy root."""

    actual_legacy = tmp_path / "actual-legacy"
    actual_legacy.mkdir()
    lexical_alias = tmp_path / "forbidden-legacy-alias"
    lexical_alias.symlink_to(actual_legacy, target_is_directory=True)
    candidate = tmp_path / "candidate"
    (candidate / "src").mkdir(parents=True)
    (candidate / "src" / "marker.py").write_text(
        f"HISTORICAL_OTHER_PATH = {str(actual_legacy)!r}\n",
        encoding="utf-8",
    )

    result = _run_scanner(candidate, lexical_alias)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "LEGACY_REF_OK" in result.stdout


def test_external_runtime_symlink_is_classified_without_resolving_target(tmp_path: Path) -> None:
    """Read the link payload, but never follow its external target or aliases."""

    actual_target = tmp_path / "actual-target"
    actual_target.mkdir()
    external_alias = tmp_path / "external-alias"
    external_alias.symlink_to(actual_target, target_is_directory=True)
    candidate = tmp_path / "candidate"
    (candidate / "src").mkdir(parents=True)
    (candidate / "src" / "runtime-link").symlink_to(external_alias)

    result = _run_scanner(candidate, tmp_path / "synthetic-legacy-marker")

    assert result.returncode == 1
    assert "EXTERNAL_RUNTIME_SYMLINK" in result.stdout
    assert f"target={external_alias}" in result.stdout
    assert f"target={actual_target}" not in result.stdout
