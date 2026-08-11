from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALL_READY = {
    capability_id: True
    for capability_id in (
        "project_file_io",
        "script_runtime",
        "http_network",
        "search_browser",
        "login_browser",
        "document_ingestion",
        "ocr",
        "browser_validation",
        "native_pdf",
        "html_ppt_runtime",
        "ppt_master",
        "office_renderer",
    )
}


def _run(*args: str, overrides: dict[str, bool] | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["CI_WORKFLOW_TEST_MODE"] = "1"
    environment["CI_WORKFLOW_CAPABILITY_OVERRIDES"] = json.dumps(
        {**ALL_READY, **(overrides or {})}, ensure_ascii=False
    )
    return subprocess.run(
        [sys.executable, "-m", "ci_workflow", *args],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_project_and_inline_selection_produce_the_same_capability_summary(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "项目"
    created = _run(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "慢性鼻窦炎伴鼻息肉",
        "--reports",
        "A,C",
        "--outputs",
        "html,pdf",
    )
    assert created.returncode == 0, created.stderr

    inline_path = tmp_path / "inline.json"
    project_path = tmp_path / "project.json"
    inline = _run(
        "capability",
        "preflight",
        "--host",
        "local",
        "--reports",
        "A,C",
        "--outputs",
        "html,pdf",
        "--json",
        str(inline_path),
    )
    project = _run(
        "capability",
        "preflight",
        "--host",
        "local",
        "--project",
        str(project_root),
        "--json",
        str(project_path),
    )
    assert inline.returncode == project.returncode == 0
    assert "能力预检完成" in inline.stdout
    assert "PREFLIGHT_COMPLETE" in inline.stdout
    inline_payload = json.loads(inline_path.read_text(encoding="utf-8"))
    project_payload = json.loads(project_path.read_text(encoding="utf-8"))
    for field in ("selection", "capabilities", "research", "deliveries", "overall_state"):
        assert inline_payload[field] == project_payload[field]


def test_missing_pptx_capability_blocks_only_pptx_and_gives_plain_chinese_guidance(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "preflight.json"
    result = _run(
        "capability",
        "preflight",
        "--host",
        "omp",
        "--reports",
        "A,B,C",
        "--outputs",
        "html,pdf,pptx",
        "--json",
        str(result_path),
        overrides={"ppt_master": False, "office_renderer": True},
    )
    assert result.returncode == 0, result.stderr
    assert "可编辑 PPTX 暂时无法生成" in result.stdout
    assert "HTML、PDF 不受影响" in result.stdout
    assert "gate" not in result.stdout.lower()
    assert "signal" not in result.stdout.lower()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    states = {(item["report"], item["output"]): item["state"] for item in payload["deliveries"]}
    assert all(states[(report, "pptx")] == "blocked" for report in ("A", "B", "C"))
    assert all(states[(report, "html")] == "ready" for report in ("A", "B", "C"))
    assert all(states[(report, "pdf")] == "ready" for report in ("A", "B", "C"))

    both_missing = _run(
        "capability",
        "preflight",
        "--host",
        "omp",
        "--reports",
        "A",
        "--outputs",
        "html,pptx",
        "--json",
        str(tmp_path / "both-missing.json"),
        overrides={"ppt_master": False, "office_renderer": False},
    )
    assert both_missing.returncode == 0
    assert both_missing.stdout.count("可编辑 PPTX 暂时无法生成") == 1
