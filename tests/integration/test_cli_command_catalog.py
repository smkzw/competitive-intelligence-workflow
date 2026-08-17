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
    for directory in ("schemas", "contracts", "assets", "skills", "migrations"):
        shutil.copytree(ROOT / directory, target / directory)


def test_frozen_command_catalog_has_real_package_and_project_handlers_and_fail_closed_stubs(
    tmp_path: Path,
) -> None:
    package = _run("package", "verify", "--root", str(ROOT))
    assert package.returncode == 0, package.stderr
    assert package.stdout.strip() == (
        "PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted"
    )

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
    assert stub["schema_version"] == "1.0"
    assert stub["active_contract_version"] == 1
    contract = stub["project_contract_versions"][0]
    assert contract["indication"] == "慢性鼻窦炎伴鼻息肉"
    assert contract["reports"] == ["A", "B", "C"]
    assert contract["outputs"] == ["html", "pdf", "html-ppt"]

    verified = _run("project", "verify", "--root", str(project_root))
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout.strip().startswith("PROJECT_OK")
    assert "项目可继续使用" in verified.stdout

    deferred_commands = [
        ("project", "run", "--root", str(project_root)),
        ("project", "run", "--root", str(project_root), "--resume"),
    ]
    for args in deferred_commands:
        result = _run(*args)
        assert result.returncode == 0
        assert "项目已启动" in result.stdout or "运行标识" in result.stdout

    # Task 5.4 起，登记完整且有真实 A 渲染器的案例必须真正完成。
    result = _run(
        "fixture", "run", "--case", "a-complete",
        "--reports", "A", "--outputs", "html",
        "--project", str(tmp_path / "fixture"),
    )
    assert result.returncode == 0, result.stderr
    assert "案例运行完成" in result.stdout
    assert (tmp_path / "fixture/reports/A/v-fixture-001/html/overview.html").is_file()

    for forbidden_alias in (
        ("verify-project",),
        ("host", "preflight"),
        ("project", "execute"),
    ):
        result = _run(*forbidden_alias)
        assert result.returncode != 0


def test_cli_project_run_resume_rebinds_canonical_input_and_preserves_blocked_decision(
    tmp_path: Path,
) -> None:
    """真实 CLI：fixture run（exit 4）后 project run --resume 自动绑定规范宇宙
    输入、保留既有阻断决策并记录当前运行复用/终态事件；证据缺失时失败关闭。"""
    from ci_workflow.application.run_service import validate_run_manifest
    from ci_workflow.storage.event_store import EventStore

    fixture_root = tmp_path / "fixture-项目"
    first = _run(
        "fixture", "run", "--case", "no-draft-a-empty",
        "--reports", "A", "--outputs", "html", "--project", str(fixture_root),
    )
    assert first.returncode == 4, first.stderr
    assert "证据不足" in first.stdout
    first_manifest = json.loads(
        (fixture_root / "manifests" / "current_run.json").read_text(encoding="utf-8")
    )

    # CLI --resume：发现并绑定 evidence/library/universe.json，保留阻断决策
    second = _run("project", "run", "--resume", "--root", str(fixture_root))
    assert second.returncode == 4, second.stderr
    assert "证据不足" in second.stdout
    assert "已启动" not in second.stdout
    second_manifest = json.loads(
        (fixture_root / "manifests" / "current_run.json").read_text(encoding="utf-8")
    )
    assert second_manifest["run_id"] != first_manifest["run_id"]
    assert second_manifest["outputs"] == []
    assert {a["relative_path"] for a in second_manifest["reused_artifacts"]} == {
        "blockers/A/v1/audit.json",
        "blockers/A/v1/audit.md",
    }
    assert validate_run_manifest(fixture_root)["run_id"] == second_manifest["run_id"]
    events = EventStore(fixture_root).read_all()
    assert any(
        e.event_type == "run.node.reused" and e.run_id == second_manifest["run_id"]
        for e in events
    )
    assert any(
        e.event_type == "run.terminal_decision.recorded"
        and e.run_id == second_manifest["run_id"]
        for e in events
    )
    assert not any(
        e.run_id == second_manifest["run_id"]
        and e.event_type == "graph.node.completed"
        for e in events
    )

    # 删除规范宇宙输入后 resume → 失败关闭，不宣称“已启动”
    (fixture_root / "evidence" / "library" / "universe.json").unlink()
    third = _run("project", "run", "--resume", "--root", str(fixture_root))
    assert third.returncode == 2
    assert "已启动" not in third.stdout
    assert "证据" in third.stderr


def test_cli_project_run_resume_rejects_pre_drifted_blocker_package(
    tmp_path: Path,
) -> None:
    """P2-1：resume 前阻断说明文件被修改 → 失败关闭并给出中文恢复/重开指引；
    不写新清单/新决策、不宣称证据结果；恢复内容与 mtime 后正常 resume。"""
    import os

    fixture_root = tmp_path / "fixture-漂移项目"
    first = _run(
        "fixture", "run", "--case", "no-draft-a-empty",
        "--reports", "A", "--outputs", "html", "--project", str(fixture_root),
    )
    assert first.returncode == 4, first.stderr
    manifest_before = (
        fixture_root / "manifests" / "current_run.json"
    ).read_bytes()
    events_before = (fixture_root / "events" / "events.jsonl").read_bytes()

    # 修改阻断说明（内容 + mtime 漂移）后 resume → 失败关闭
    audit_md = fixture_root / "blockers" / "A" / "v1" / "audit.md"
    original_stat = audit_md.stat()
    original_md = audit_md.read_bytes()
    audit_md.write_bytes(original_md + "<!-- 漂移 -->\n".encode())
    drifted = _run("project", "run", "--resume", "--root", str(fixture_root))
    assert drifted.returncode == 2
    assert "已启动" not in drifted.stdout
    assert "证据不足" not in drifted.stdout
    assert "恢复" in drifted.stderr
    assert "重新打开" in drifted.stderr
    assert "Traceback" not in drifted.stderr
    # 没有新的接受清单/决策：清单与事件流保持原样
    assert (fixture_root / "manifests" / "current_run.json").read_bytes() == (
        manifest_before
    )
    assert (fixture_root / "events" / "events.jsonl").read_bytes() == events_before

    # 恢复原始内容与精确 mtime → 正常 resume 通过
    audit_md.write_bytes(original_md)
    os.utime(audit_md, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    restored = _run("project", "run", "--resume", "--root", str(fixture_root))
    assert restored.returncode == 4, restored.stderr
    assert "证据不足" in restored.stdout
    restored_manifest = json.loads(
        (fixture_root / "manifests" / "current_run.json").read_text(encoding="utf-8")
    )
    assert restored_manifest["run_id"] != json.loads(
        manifest_before.decode("utf-8")
    )["run_id"]


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
