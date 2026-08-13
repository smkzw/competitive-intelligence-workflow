"""Task 3.6 FX03–FX04：运行清单只记录规范产物路径并逐文件锁定真实摘要。

- FX03：`no-draft-a-empty` 运行后，清单产出的相对路径只能是规范 blockers 路径
  （blockers/<A|B|C>/<version>/{audit.json,audit.md}），拒绝任意/绝对路径；
  生产路径校验器同时接受 ArtifactPathService 的规范报告路径；清单可经
  validate_run_manifest 重新打开校验。
- FX04：清单为每个真实产出记录相对路径、SHA-256、字节数与精确 st_mtime_ns；
  预置的骨架文件不得计入产出；篡改、mtime-only 漂移、删除均重校验失败关闭；
  运行前已存在且本次运行未变化的阻断/报告文件不得被采纳。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.run_service import (
    ContractConfigError,
    RunContext,
    RunError,
    run_project,
    validate_run_manifest,
    validate_run_output_path,
)
from ci_workflow.domain.contracts import create_project_contract

ROOT = Path(__file__).resolve().parents[2]

# 本案例唯一合法产出：阻断包两文件（无任何报告产物）
_BLOCKER_OUTPUTS = frozenset(
    {"blockers/A/v1/audit.json", "blockers/A/v1/audit.md"}
)


def _run_no_draft_a_empty(tmp_path: Path) -> Path:
    project_root = tmp_path / "项目"
    result = run_fixture_case(
        "no-draft-a-empty",
        project_root=project_root,
        reports=["A"],
        outputs=["html"],
    )
    assert result.run_result.exit_code == 4
    return project_root


def _load_manifest(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "manifests" / "current_run.json"
    return cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fixture_outputs_only_use_artifact_path_service(tmp_path: Path) -> None:
    """FX03：清单产出路径只允许规范 blockers 路径，拒绝任意或绝对路径。"""
    project_root = _run_no_draft_a_empty(tmp_path)
    manifest = _load_manifest(project_root)

    outputs = manifest["outputs"]
    assert outputs
    for output in outputs:
        relative = PurePosixPath(output["relative_path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert relative.as_posix().startswith("blockers/")
        assert not relative.as_posix().startswith("reports/")

    # 清单可重新打开校验并返回数据
    validated = validate_run_manifest(project_root)
    assert isinstance(validated, dict)
    assert validated.get("run_id") == manifest["run_id"]

    # 直接练习生产路径校验器：规范阻断与报告路径通过
    valid_paths = [
        "blockers/A/v1/audit.json",
        "blockers/B/v1/audit.md",
        "blockers/C/v1.2-beta/audit.json",
        "reports/A/v1/html",
        "reports/B/v1/report.pdf",
        "reports/C/v1/html-ppt",
        "reports/A/v1/report.pptx",
        "reports/A/v1/html.manifest.json",
        "reports/A/v1/html.coverage-projection.json",
    ]
    for rel in valid_paths:
        validated_path = validate_run_output_path(rel)
        assert validated_path.as_posix() == rel

    # 非法变体一律失败关闭：绝对路径、穿越、任意命名空间、
    # 非规范阻断文件名/版本、非规范报告产物名、反斜杠
    invalid_paths = [
        "/etc/passwd",
        "../outside.txt",
        "blockers/A/audit.json",
        "blockers/A/v1/audit.txt",
        "blockers/A/v1/notes.md",
        "blockers/D/v1/audit.json",
        "blockers/A/1/audit.json",
        "blockers/A/v1",
        "reports/D/v1/html",
        "reports/A/1/html",
        "reports/A/v1/extra.html",
        "reports/A/v1/html.html",
        "arbitrary/namespace/file.json",
        "blockers/A/v1/audit.json/extra",
        "blockers\\A\\v1\\audit.json",
    ]
    for rel in invalid_paths:
        with pytest.raises(RunError):
            validate_run_output_path(rel)


def test_fixture_manifest_hashes_every_real_output(tmp_path: Path) -> None:
    """FX04：清单逐文件锁定路径、SHA-256、字节与精确 mtime_ns；篡改/漂移/缺失拒绝。"""
    project_root = _run_no_draft_a_empty(tmp_path)
    manifest = _load_manifest(project_root)

    # 产出恰好是阻断包两文件：预置骨架文件（project.yaml、coverage/*.json 等）不计入
    outputs = manifest["outputs"]
    assert {output["relative_path"] for output in outputs} == _BLOCKER_OUTPUTS

    # 每个产出与真实文件逐项一致
    for output in outputs:
        path = project_root / output["relative_path"]
        assert path.is_file()
        assert _sha256_file(path) == output["sha256"]
        assert path.stat().st_size == output["byte_size"]
        # mtime 以精确整数 st_mtime_ns 记录（不经过浮点往返），并保留带时区 ISO 显示
        assert output["mtime_ns"] == path.stat().st_mtime_ns
        assert datetime.fromisoformat(output["modified_at"]).tzinfo is not None

    # 篡改 audit.md → 重校验失败关闭（摘要不匹配）
    audit_md = project_root / "blockers" / "A" / "v1" / "audit.md"
    original_md_bytes = audit_md.read_bytes()
    audit_md.write_bytes(original_md_bytes + "\n<!-- 篡改 -->\n".encode())
    with pytest.raises(RunError, match="输出文件摘要不匹配"):
        validate_run_manifest(project_root)

    # 恢复原内容但只改 mtime → 重校验失败关闭（mtime-only 漂移）
    audit_md.write_bytes(original_md_bytes)
    audit_md.touch()
    with pytest.raises(RunError, match="输出文件修改时间不匹配"):
        validate_run_manifest(project_root)

    # 删除 audit.json → 重校验失败关闭（缺失）
    audit_json = project_root / "blockers" / "A" / "v1" / "audit.json"
    audit_json.unlink()
    with pytest.raises(RunError):
        validate_run_manifest(project_root)


def test_fixture_manifest_does_not_adopt_pre_existing_unchanged_outputs(
    tmp_path: Path,
) -> None:
    """FX04 补充：运行前已存在且本次运行未变化的阻断包/报告文件不得被采纳。"""
    first_root = tmp_path / "首个项目"
    first = run_fixture_case(
        "no-draft-a-empty",
        project_root=first_root,
        reports=["A"],
        outputs=["html"],
    )
    assert first.run_result.exit_code == 4
    contract = verify_project_workspace(first_root).contract

    # 第二个项目预置内容与首次运行完全一致的阻断包（内容确定性）与伪造报告
    second_root = create_project_workspace(tmp_path / "第二个项目", contract)
    shutil.copytree(
        first_root / "blockers" / "A" / "v1",
        second_root / "blockers" / "A" / "v1",
        dirs_exist_ok=True,
    )
    fake_report = second_root / "reports" / "A" / "v9" / "html"
    fake_report.parent.mkdir(parents=True)
    fake_report.write_text("<html>预先存在的伪造报告</html>\n", encoding="utf-8")

    fixture_universe = (
        ROOT / "fixtures" / "synthetic" / "no-draft-a-empty" / "inputs" / "universe.json"
    )
    run_context = RunContext(
        project_root=second_root,
        contract=contract,
        universe_input_path=fixture_universe,
        run_inputs={
            "case_id": "no-draft-a-empty",
            "case_digest": first.case_digest,
            "inputs/universe.json": _sha256_file(fixture_universe),
        },
    )
    result = run_project(second_root, run_context=run_context)
    assert result.outcome == "evidence_blocked"
    assert result.exit_code == 4

    # 预存阻断包内容一致校验通过、未被改写：不是本次运行产出，而是复用产物引用
    manifest = _load_manifest(second_root)
    assert manifest["outputs"] == []
    assert {a["relative_path"] for a in manifest["reused_artifacts"]} == {
        "blockers/A/v1/audit.json",
        "blockers/A/v1/audit.md",
    }
    for artifact in manifest["reused_artifacts"]:
        path = second_root / artifact["relative_path"]
        assert _sha256_file(path) == artifact["sha256"]
        assert path.stat().st_size == artifact["byte_size"]
        assert path.stat().st_mtime_ns == artifact["mtime_ns"]
    # 伪造报告文件既不是产出也不是复用引用（本次运行决策未引用它）
    assert (second_root / "reports" / "A" / "v9" / "html").is_file()
    # 本次运行清单重新打开校验仍通过（复用产物引用与终态决策事件绑定完整）
    validated = validate_run_manifest(second_root)
    assert validated.get("run_id") == result.run_id

    # 篡改复用阻断文件 → 重开校验失败关闭
    audit_md = second_root / "blockers" / "A" / "v1" / "audit.md"
    original_md = audit_md.read_bytes()
    audit_md.write_bytes(original_md + "\n<!-- 篡改 -->\n".encode())
    with pytest.raises(RunError, match="复用产物"):
        validate_run_manifest(second_root)
    audit_md.write_bytes(original_md)


def test_fixture_blocker_drift_write_fails_closed_with_chinese_guidance(
    tmp_path: Path,
) -> None:
    """P2-4：阻断包写入器检测到既有说明漂移时，包装为 ContractConfigError
    中文指引，绝不让原始异常穿透为 traceback。"""
    contract = create_project_contract(
        indication="非小细胞肺癌",
        reports=["A"],
        outputs=["html"],
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    package_dir = project_root / "blockers" / "A" / "v1"
    package_dir.mkdir(parents=True)
    (package_dir / "audit.json").write_text('{"伪造": true}\n', encoding="utf-8")
    (package_dir / "audit.md").write_text(
        "预先存在的伪造阻断说明（内容与本次结果不一致）\n", encoding="utf-8"
    )

    fixture_universe = (
        ROOT / "fixtures" / "synthetic" / "no-draft-a-empty" / "inputs" / "universe.json"
    )
    run_context = RunContext(
        project_root=project_root,
        contract=contract,
        universe_input_path=fixture_universe,
        run_inputs={
            "case_id": "no-draft-a-empty",
            "case_digest": "1" * 64,
            "inputs/universe.json": _sha256_file(fixture_universe),
        },
    )
    with pytest.raises(ContractConfigError, match="拒绝覆盖|阻断说明写入失败"):
        run_project(project_root, run_context=run_context)
