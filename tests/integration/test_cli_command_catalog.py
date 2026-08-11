from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _copy_verifiable_package(target: Path) -> None:
    target.mkdir()
    for file_name in ("package-manifest.json", "pyproject.toml"):
        shutil.copy2(ROOT / file_name, target / file_name)
    for directory in ("schemas", "contracts", "assets", "skills"):
        shutil.copytree(ROOT / directory, target / directory)


def test_frozen_command_catalog_has_real_package_and_project_handlers_and_fail_closed_stubs(
    tmp_path: Path,
) -> None:
    package = _run("package", "verify", "--root", str(ROOT))
    assert package.returncode == 0, package.stderr
    assert package.stdout.strip() == "PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4"

    project_root = tmp_path / "呼吸疾病竞品项目"
    created = _run(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "慢性鼻窦炎伴鼻息肉",
        "--reports",
        "A,B,C",
        "--outputs",
        "html,pdf,html-ppt",
    )
    assert created.returncode == 0, created.stderr
    assert "PROJECT_CREATED" in created.stdout
    stub = json.loads((project_root / "project.yaml").read_text(encoding="utf-8"))
    assert stub["indication"] == "慢性鼻窦炎伴鼻息肉"
    assert stub["reports"] == ["A", "B", "C"]
    assert stub["outputs"] == ["html", "pdf", "html-ppt"]
    assert stub["contract_status"] == "skeleton_pending_phase_1"

    verified = _run("project", "verify", "--root", str(project_root))
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout.strip().startswith("PROJECT_OK")

    deferred_commands = [
        ("capability", "preflight", "--host", "omp", "--reports", "A", "--outputs", "html"),
        ("project", "run", "--root", str(project_root)),
        ("project", "run", "--root", str(project_root), "--resume"),
        ("fixture", "run", "--case", "a-complete", "--root", str(tmp_path / "fixture")),
    ]
    for args in deferred_commands:
        result = _run(*args)
        assert result.returncode == 3
        assert "CAPABILITY_NOT_IMPLEMENTED" in result.stderr
        assert "功能尚未实现" in result.stderr

    for forbidden_alias in (
        ("verify-project",),
        ("host", "preflight"),
        ("project", "execute"),
    ):
        result = _run(*forbidden_alias)
        assert result.returncode != 0


def test_package_verify_rejects_cli_catalog_and_skill_prompt_drift(tmp_path: Path) -> None:
    extra_cli_root = tmp_path / "extra-cli"
    _copy_verifiable_package(extra_cli_root)
    manifest_path = extra_cli_root / "package-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cli"]["catalog"].append("project execute")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    extra_cli = _run("package", "verify", "--root", str(extra_cli_root))
    assert extra_cli.returncode == 2
    assert "安装包清单不符合合同" in extra_cli.stderr

    prompt_root = tmp_path / "prompt-drift"
    _copy_verifiable_package(prompt_root)
    agent_path = prompt_root / "skills/_internal/monitoring/agents/openai.yaml"
    agent_path.write_text(
        agent_path.read_text(encoding="utf-8").replace("$monitoring", "monitoring"),
        encoding="utf-8",
    )
    prompt_drift = _run("package", "verify", "--root", str(prompt_root))
    assert prompt_drift.returncode == 2
    assert "默认提示未绑定自身 Skill" in prompt_drift.stderr
