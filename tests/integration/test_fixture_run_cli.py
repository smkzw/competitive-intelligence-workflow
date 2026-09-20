"""Task 3.6 FX01–FX02：`fixture run` 创建隔离项目并调用同一真实 RunService。

- FX01：`no-draft-a-empty` 案例创建隔离项目、经真实图执行 A 空宇宙路径，以
  evidence_blocked/exit 4 结束，只产生 blockers/A/v1/audit.json 与中文 audit.md；
  实际运行结果必须与 catalog 预期 outcome 一致，否则 FixtureCaseError。
- FX02：未来输出格式在 fixture-case schema 边界失败关闭，且不创建伪项目、
  产物或收据。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

from ci_workflow.application.fixture_runner import FixtureCaseError, run_fixture_case

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_fixture_run_creates_project_and_dispatches_registered_graph(
    tmp_path: Path,
) -> None:
    """FX01：fixture run 创建隔离项目并经真实 RunService 运行已注册节点。"""
    project_root = tmp_path / "项目"
    result = run_fixture_case(
        "no-draft-a-empty",
        project_root=project_root,
        reports=["A"],
        outputs=["html"],
    )

    assert result.case_id == "no-draft-a-empty"
    assert result.case_digest
    assert result.project_root == project_root

    run_result = result.run_result
    assert run_result.run_id
    assert run_result.outcome == "evidence_blocked"
    assert run_result.exit_code == 4

    # 隔离项目已创建，真实事件流非空
    assert (project_root / "project.yaml").is_file()
    events_text = (project_root / "events" / "events.jsonl").read_text(encoding="utf-8")
    assert events_text.strip()

    # 唯一阻断产物：blockers/A/v1/audit.json 与中文 audit.md
    audit_json = project_root / "blockers" / "A" / "v1" / "audit.json"
    audit_md = project_root / "blockers" / "A" / "v1" / "audit.md"
    assert audit_json.is_file()
    assert audit_md.is_file()
    markdown = audit_md.read_text(encoding="utf-8")
    assert _CJK_RE.search(markdown)
    assert "证据不足" in markdown


def test_fixture_run_rejects_deferred_output_before_project_creation(
    tmp_path: Path,
) -> None:
    """FX02：未来输出格式在 catalog/schema 边界失败关闭，不创建项目。"""
    case_id = "rendered-deferred-format"
    cases_dir = tmp_path / "cases"
    case_root = cases_dir / case_id
    inputs_dir = case_root / "inputs"
    inputs_dir.mkdir(parents=True)
    universe = inputs_dir / "universe.json"
    universe.write_text('{"products": []}\n', encoding="utf-8")
    catalog_path = cases_dir / "catalog.yaml"
    case_sha = _sha256_bytes(universe.read_bytes())
    case_fields = {
        "id": case_id,
        "description_zh": "首版拒绝未来输出格式",
        "indication": "非小细胞肺癌",
        "timezone": "Asia/Shanghai",
        "data_cutoff": "2026-07-31",
        "created_at": "2026-08-12T10:00:00+08:00",
        "reports": ["B"],
        "outputs": ["pptx"],
        "inputs": [
            {
                "path": "inputs/universe.json",
                "role": "universe_closure",
                "sha256": case_sha,
            }
        ],
        "expected": {"report": "B", "report_version": "v1", "outcome": "rendered"},
    }
    case_digest = _sha256_bytes(
        json.dumps(
            case_fields,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    catalog_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "cases": [{**case_fields, "case_digest": case_digest}],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    project_root = tmp_path / "项目"
    with pytest.raises(FixtureCaseError, match="fixture-case schema"):
        run_fixture_case(
            case_id,
            project_root=project_root,
            reports=["B"],
            outputs=["pptx"],
            catalog_path=catalog_path,
        )

    # schema 边界拒绝发生在建项目之前：没有项目、清单、阻断包或事件流。
    assert not project_root.exists()


def test_fixture_run_rejects_outcome_mismatch_against_catalog_expectation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fixture 运行结果必须与 catalog 预期一致；不一致以 FixtureCaseError 失败。"""
    from ci_workflow.application import run_service as run_service_module
    from ci_workflow.application.fixture_runner import FixtureCaseError
    from ci_workflow.application.run_service import RunContext, RunResult

    def fake_run_project(
        project_root: Path,
        *,
        resume: bool = False,
        run_context: RunContext | None = None,
    ) -> RunResult:
        result = run_service_module.run_project(
            project_root, resume=resume, run_context=run_context
        )
        return RunResult(
            run_id=result.run_id,
            project_id=result.project_id,
            contract_version=result.contract_version,
            outcome="running",
            exit_code=0,
            node_summary={},
            reused=(),
            outputs=(),
        )

    monkeypatch.setattr(
        "ci_workflow.application.fixture_runner.run_project", fake_run_project
    )
    with pytest.raises(FixtureCaseError, match="运行结果与预期不符"):
        run_fixture_case(
            "no-draft-a-empty",
            project_root=tmp_path / "项目",
            reports=["A"],
            outputs=["html"],
        )
