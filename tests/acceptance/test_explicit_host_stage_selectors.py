"""ci-r24-183：pre-RC 宿主冒烟阶段与验收 CLI 的显式选择器接线合同。

- 真实批次（缺省 runner）在构建阶段必须携带三宿主完整选择器并失败关闭；
- 提供的选择器在构建时校验并冻结，执行时原样传给真实批次；
- 注入 ``smoke_runner`` 的合同测试替身保持兼容：未提供选择器时不新增参数；
- ``tools/run_acceptance.py`` 暴露七个真实路由 CLI 参数并透传选择器映射；
- 中文安装指南只使用调用者按当前真实路由提供的占位符，不固化旧测试模型。

选择器是**请求身份**；真实宿主实际运行身份不在本套件主张范围内。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ci_workflow.application.fresh_install as fresh_install
from ci_workflow.application.acceptance_runner import (
    AcceptanceRunnerError,
    build_host_smoke_stage,
)
from ci_workflow.application.host_smoke_runner import HostSmokeRunnerError

ROOT = Path(__file__).resolve().parents[2]

_SELECTION: dict[str, str] = {
    "codex_model": "gpt-5.6-luna",
    "codex_reasoning": "high",
    "hermes_provider": "anthropic",
    "hermes_model": "anthropic/claude-sonnet-4",
    "hermes_reasoning": "high",
    "omp_model": "openai/gpt-5.2",
    "omp_thinking": "high",
}

_SELECTOR_FLAGS = (
    "--codex-model",
    "--codex-reasoning",
    "--hermes-provider",
    "--hermes-model",
    "--hermes-reasoning",
    "--omp-model",
    "--omp-thinking",
)


def _fake_install_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """以最小候选布局替身隔离 fresh-install 核验（其真实核验不在本套件范围）。"""
    manifest = tmp_path / "package-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "package": {
                    "name": "competitive-intelligence-workflow",
                    "version": "0.1.0+candidate",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    entrypoint = tmp_path / "bin" / "ci-workflow"
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    entrypoint.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(exist_ok=True)
    layout = SimpleNamespace(
        package_manifest=manifest,
        entrypoint=entrypoint,
        bundle_digest="a" * 64,
        bundle_root=bundle_root,
        install_root=tmp_path,
    )
    monkeypatch.setattr(fresh_install, "load_fresh_install_layout", lambda _root: layout)
    return layout


def _load_run_acceptance_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "run_acceptance_under_test", ROOT / "tools" / "run_acceptance.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ─── 阶段构建：缺省真实批次要求显式选择器 ──────────────────────────────────


def test_stage_requires_explicit_selection_for_default_production_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_install_layout(tmp_path, monkeypatch)
    with pytest.raises(AcceptanceRunnerError, match="选择器"):
        build_host_smoke_stage(
            install_root=tmp_path / "install",
            acceptance_root=tmp_path / "acceptance",
            smoke_runner=None,
        )


@pytest.mark.parametrize(
    ("selection", "match"),
    [
        (
            {"codex_model": "gpt-5.6-luna", "codex_reasoning": "high"},
            "必须显式指定",
        ),
        ({**_SELECTION, "omp_model": "openai/auto"}, "不透明"),
        ({**_SELECTION, "hermes_model": ""}, "必须显式指定"),
        ({**_SELECTION, "codex_temperature": "0.5"}, "未声明字段"),
    ],
)
def test_stage_rejects_incomplete_or_opaque_selection_at_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selection: dict[str, str],
    match: str,
) -> None:
    _fake_install_layout(tmp_path, monkeypatch)
    with pytest.raises(AcceptanceRunnerError, match=match):
        build_host_smoke_stage(
            install_root=tmp_path / "install",
            acceptance_root=tmp_path / "acceptance",
            host_selection=selection,
            smoke_runner=lambda *args, **kwargs: None,
        )


# ─── 阶段执行：冻结透传与注入替身兼容 ─────────────────────────────────────


def test_stage_freezes_and_forwards_selection_to_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_install_layout(tmp_path, monkeypatch)
    captured: dict[str, Any] = {}

    def fake_runner(
        layout: Any, *, evidence_root: Path, project_root: Path, **kwargs: Any
    ) -> Any:
        captured.update(kwargs)
        raise HostSmokeRunnerError("SELECTION_FORWARDED_STOP")

    caller_selection = {**_SELECTION, "codex_model": " gpt-5.6-luna "}
    stage = build_host_smoke_stage(
        install_root=tmp_path / "install",
        acceptance_root=tmp_path / "acceptance",
        host_selection=caller_selection,
        smoke_runner=fake_runner,
    )
    # 构建后篡改调用方映射不得影响冻结值。
    caller_selection["codex_model"] = "auto"
    caller_selection["omp_model"] = "openai/auto"
    with pytest.raises(AcceptanceRunnerError, match="SELECTION_FORWARDED_STOP"):
        stage({"pre_rc_run_id": "pre-rc-test-183"})
    assert captured == _SELECTION


def test_injected_smoke_runner_without_selection_remains_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_install_layout(tmp_path, monkeypatch)
    captured: dict[str, Any] = {}

    def fake_runner(
        layout: Any, *, evidence_root: Path, project_root: Path, **kwargs: Any
    ) -> Any:
        captured.update(kwargs)
        raise HostSmokeRunnerError("INJECTED_RUNNER_STOP")

    stage = build_host_smoke_stage(
        install_root=tmp_path / "install",
        acceptance_root=tmp_path / "acceptance",
        smoke_runner=fake_runner,
    )
    with pytest.raises(AcceptanceRunnerError, match="INJECTED_RUNNER_STOP"):
        stage({"pre_rc_run_id": "pre-rc-test-183"})
    assert captured == {}


# ─── 验收 CLI：七个显式路由参数 ───────────────────────────────────────────


def test_run_acceptance_cli_exposes_seven_flags_and_forwards_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_run_acceptance_module()
    parser = module._build_parser()
    option_strings = {
        option for action in parser._actions for option in action.option_strings
    }
    for flag in _SELECTOR_FLAGS:
        assert flag in option_strings

    captured: dict[str, Any] = {}

    def fake_stage_builder(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "build_host_smoke_stage", fake_stage_builder)
    monkeypatch.setattr(module, "build_project_verify_stage", lambda **kwargs: object())
    monkeypatch.setattr(module, "build_pre_rc_receipts_stage", lambda **kwargs: object())
    monkeypatch.setattr(
        module, "run_pre_rc_rehearsal", lambda **kwargs: {"stages": [], "stage_order": []}
    )
    monkeypatch.setattr(module, "format_pre_rc_rehearsal_ok", lambda summary: "PRE_RC_TEST_OK")
    argv = [
        "--pipeline",
        "full",
        "--project-root",
        str(tmp_path / "project"),
        "--acceptance-root",
        str(tmp_path / "acceptance"),
        "--codex-model",
        _SELECTION["codex_model"],
        "--codex-reasoning",
        _SELECTION["codex_reasoning"],
        "--hermes-provider",
        _SELECTION["hermes_provider"],
        "--hermes-model",
        _SELECTION["hermes_model"],
        "--hermes-reasoning",
        _SELECTION["hermes_reasoning"],
        "--omp-model",
        _SELECTION["omp_model"],
        "--omp-thinking",
        _SELECTION["omp_thinking"],
    ]
    with pytest.raises(SystemExit) as exit_info:
        module.main(argv)
    assert exit_info.value.code == 0
    assert captured["host_selection"] == _SELECTION


# ─── 中文安装指南：调用者按真实路由提供占位符 ──────────────────────────────


def test_install_guide_documents_explicit_host_selectors_as_caller_placeholders() -> None:
    text = (ROOT / "docs" / "user-guide" / "install.md").read_text(encoding="utf-8")
    for flag in _SELECTOR_FLAGS:
        assert flag in text
    for variable in (
        "CODEX_MODEL",
        "CODEX_REASONING",
        "HERMES_PROVIDER",
        "HERMES_MODEL",
        "HERMES_REASONING",
        "OMP_MODEL",
        "OMP_THINKING",
    ):
        assert variable in text
    assert "provider/model" in text
    # 指南不得固化旧测试模型取值；真实路由由调用者提供。
    for stale in ("gpt-5.6-luna", "claude-sonnet-4", "openai/gpt-5.2"):
        assert stale not in text
