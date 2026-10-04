"""ci-r24-181：真实宿主显式模型/强度选择器的失败关闭与命令行构造合同。

- 缺失、空值或不透明 auto/default：Codex/Hermes/OMP 一律在任何子进程
  启动之前拒绝（不静默采用宿主配置默认）；
- 显式选择器按宿主构造到真实命令行（Codex ``-m``/``-c``、Hermes
  ``--provider``/``--model``/``--reasoning``、OMP provider/model 与
  ``--thinking``），恢复参数原样保留、不被隐式替换；
- runner 层逐宿主透传显式选择器；
- fixture-only（非真实宿主）路径不要求选择器，命令也不注入任何选择器。

选择器是**请求身份**；宿主实际运行身份不在本进程可观测范围内，本套件
不对已观测身份做任何主张。
"""

from __future__ import annotations

import subprocess
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ci_workflow.application import host_smoke
from ci_workflow.application import host_smoke_runner as runner
from ci_workflow.application.host_smoke import HOSTS, HostSmokeError

_EXPLICIT_SELECTORS: dict[str, dict[str, str]] = {
    "codex": {"codex_model": "gpt-5.6-luna", "codex_reasoning": "high"},
    "hermes": {
        "hermes_provider": "anthropic",
        "hermes_model": "anthropic/claude-sonnet-4",
        "hermes_reasoning": "high",
    },
    "omp": {"omp_model": "openai/gpt-5.2", "omp_thinking": "high"},
}
_SELECTOR_KEYS: dict[str, tuple[str, ...]] = {
    host: tuple(selectors) for host, selectors in _EXPLICIT_SELECTORS.items()
}
_MISSING_CASES = [(host, key) for host in HOSTS for key in _SELECTOR_KEYS[host]]
_EMPTY_SELECTOR_VALUES = ("", "   ")
_OPAQUE_SELECTOR_VALUES = ("auto", "default", "AUTO", " Default ")


def _fake_entry(tmp_path: Path) -> Any:
    return SimpleNamespace(command=(str(tmp_path / "ci-workflow"),))


def _flag_value(argv: list[str], flag: str) -> str | None:
    for index, item in enumerate(argv[:-1]):
        if item == flag:
            return argv[index + 1]
    return None


def _capture_argv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, host: str
) -> dict[str, list[str]]:
    """拦截宿主子进程并捕获 argv；只替身解析与 Popen，不触达真实宿主。"""
    captured: dict[str, list[str]] = {}

    def capture(argv: list[str], **kwargs: Any) -> Any:
        captured["argv"] = [str(item) for item in argv]
        raise HostSmokeError("ARGV_CAPTURED_WITHOUT_DISPATCH")

    monkeypatch.setattr(
        host_smoke,
        "resolve_host_executable",
        lambda *args, **kwargs: ({"path": str(tmp_path / host)}, None),
    )
    monkeypatch.setattr(subprocess, "Popen", capture)
    return captured


def _spawn_sentinel(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    spawned: list[Any] = []

    def sentinel(*args: Any, **kwargs: Any) -> Any:
        spawned.append(args)
        raise AssertionError("缺失或非法选择器时不得启动任何子进程")

    monkeypatch.setattr(subprocess, "Popen", sentinel)
    return spawned


def _run_real_host_smoke(
    host: str,
    *,
    tmp_path: Path,
    selectors: dict[str, str] | None = None,
    resume: bool = False,
) -> None:
    """按动态选择器调用真实宿主路径；失败关闭或替身捕获会抛出。"""
    kwargs: dict[str, Any] = dict(selectors or {})
    host_smoke.run_host_smoke(
        host,
        project_root=tmp_path / "项目",
        entry=_fake_entry(tmp_path),
        resume=resume,
        require_external_host_process=True,
        **kwargs,
    )


def _layout(tmp_path: Path) -> tuple[Any, Path, Path]:
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text("fixture identity", encoding="utf-8")
    manifest = tmp_path / "package-manifest.json"
    manifest.write_text("package identity", encoding="utf-8")
    layout = SimpleNamespace(
        bundle_digest="a" * 64,
        package_manifest=manifest,
        bundle_root=tmp_path / "bundle",
        install_root=tmp_path,
        entrypoint=tmp_path / "bin" / "ci-workflow",
        verify_layout=lambda: None,
    )
    return layout, tmp_path / "project", catalog


# ─── 失败关闭：缺失 / 空值 / 不透明选择器 ──────────────────────────────────


@pytest.mark.parametrize(("host", "missing_key"), _MISSING_CASES)
def test_missing_selector_fails_closed_before_any_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    missing_key: str,
) -> None:
    spawned = _spawn_sentinel(monkeypatch)
    selectors = dict(_EXPLICIT_SELECTORS[host])
    selectors.pop(missing_key)
    with pytest.raises(HostSmokeError, match="必须显式指定"):
        _run_real_host_smoke(host, tmp_path=tmp_path, selectors=selectors)
    assert spawned == []


@pytest.mark.parametrize(("host", "key"), _MISSING_CASES)
def test_empty_or_opaque_selector_fails_closed_before_any_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    key: str,
) -> None:
    spawned = _spawn_sentinel(monkeypatch)
    selectors = dict(_EXPLICIT_SELECTORS[host])
    for empty in _EMPTY_SELECTOR_VALUES:
        selectors[key] = empty
        with pytest.raises(HostSmokeError, match="必须显式指定"):
            _run_real_host_smoke(host, tmp_path=tmp_path, selectors=selectors)
    for opaque in _OPAQUE_SELECTOR_VALUES:
        selectors[key] = opaque
        with pytest.raises(HostSmokeError, match="不透明取值"):
            _run_real_host_smoke(host, tmp_path=tmp_path, selectors=selectors)
    assert spawned == []


@pytest.mark.parametrize("bad_model", ["gpt-5.2", "opus", "openai", "openai/", "/gpt-5.2"])
def test_omp_model_must_be_provider_qualified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_model: str,
) -> None:
    spawned = _spawn_sentinel(monkeypatch)
    selectors = dict(_EXPLICIT_SELECTORS["omp"])
    selectors["omp_model"] = bad_model
    with pytest.raises(HostSmokeError, match="提供方限定"):
        _run_real_host_smoke("omp", tmp_path=tmp_path, selectors=selectors)
    assert spawned == []


# ─── 显式命令行构造：三宿主 ────────────────────────────────────────────────


@pytest.mark.parametrize("host", HOSTS)
def test_explicit_selectors_construct_real_host_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host: str,
) -> None:
    captured = _capture_argv(monkeypatch, tmp_path, host)
    selectors = _EXPLICIT_SELECTORS[host]
    with pytest.raises(HostSmokeError, match="ARGV_CAPTURED_WITHOUT_DISPATCH"):
        _run_real_host_smoke(host, tmp_path=tmp_path, selectors=selectors, resume=True)
    argv = captured["argv"]
    assert argv[0] == str(tmp_path / host)
    if host == "codex":
        assert _flag_value(argv, "-m") == selectors["codex_model"]
        assert _flag_value(argv, "-c") == (
            f'model_reasoning_effort="{selectors["codex_reasoning"]}"'
        )
    elif host == "hermes":
        assert _flag_value(argv, "--provider") == selectors["hermes_provider"]
        assert _flag_value(argv, "--model") == selectors["hermes_model"]
        assert _flag_value(argv, "--reasoning") == selectors["hermes_reasoning"]
    else:
        assert _flag_value(argv, "--model") == selectors["omp_model"]
        assert _flag_value(argv, "--thinking") == selectors["omp_thinking"]
    # 恢复参数保留：显式恢复指令与显式选择器同时出现，无隐式替换
    prompt = argv[-1]
    assert "--resume" in prompt
    assert "不得重新初始化" in prompt


def test_hermes_resume_session_preserved_with_explicit_selectors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_argv(monkeypatch, tmp_path, "hermes")
    selectors = {**_EXPLICIT_SELECTORS["hermes"], "hermes_resume_session": "session-123"}
    with pytest.raises(HostSmokeError, match="ARGV_CAPTURED_WITHOUT_DISPATCH"):
        _run_real_host_smoke("hermes", tmp_path=tmp_path, selectors=selectors, resume=True)
    argv = captured["argv"]
    assert _flag_value(argv, "--resume") == "session-123"
    assert "--no-restore-cwd" in argv
    assert _flag_value(argv, "--model") == _EXPLICIT_SELECTORS["hermes"]["hermes_model"]


# ─── runner 层透传与 fixture-only 兼容 ─────────────────────────────────────


def test_runner_single_host_forwards_explicit_selectors_and_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout, project, catalog = _layout(tmp_path)
    runner._prepare_smoke_project(
        project, layout=layout, host="codex", catalog=catalog, resume=False
    )
    (project / "sentinel").write_bytes(b"preserve")
    captured: dict[str, Any] = {}

    def reached(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        raise host_smoke.HostSmokeError("LOWER_LAYER_REACHED")

    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())
    monkeypatch.setattr(host_smoke, "run_host_smoke", reached)
    with pytest.raises(runner.HostSmokeRunnerError, match="LOWER_LAYER_REACHED"):
        runner.run_installed_single_host_smoke(
            layout,
            host="codex",
            receipt_path=tmp_path / "receipt.json",
            project_root=project,
            catalog_path=catalog,
            resume=True,
            codex_model="gpt-5.6-luna",
            codex_reasoning="high",
        )
    assert captured["codex_model"] == "gpt-5.6-luna"
    assert captured["codex_reasoning"] == "high"
    assert captured["resume"] is True
    assert (project / "sentinel").read_bytes() == b"preserve"


def test_runner_batch_forwards_explicit_selectors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout, projects, catalog = _layout(tmp_path)
    captured: dict[str, Any] = {}

    def dispatch(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        raise host_smoke.HostSmokeError("BATCH_SELECTORS_CAPTURED")

    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())
    monkeypatch.setattr(host_smoke, "run_host_smoke", dispatch)
    with pytest.raises(runner.HostSmokeRunnerError, match="BATCH_SELECTORS_CAPTURED"):
        runner.run_installed_host_smoke(
            layout,
            project_root=projects,
            catalog_path=catalog,
            codex_model="gpt-5.6-luna",
            codex_reasoning="high",
            omp_model="openai/gpt-5.2",
            omp_thinking="high",
            hermes_provider="anthropic",
            hermes_model="anthropic/claude-sonnet-4",
            hermes_reasoning="high",
        )
    assert captured["codex_model"] == "gpt-5.6-luna"
    assert captured["codex_reasoning"] == "high"
    assert captured["omp_model"] == "openai/gpt-5.2"
    assert captured["omp_thinking"] == "high"
    assert captured["hermes_provider"] == "anthropic"
    assert captured["hermes_model"] == "anthropic/claude-sonnet-4"
    assert captured["hermes_reasoning"] == "high"


def test_fixture_only_path_needs_no_selectors_and_keeps_workflow_argv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, list[str]] = {}

    def capture(argv: list[str], **kwargs: Any) -> Any:
        captured["argv"] = [str(item) for item in argv]
        raise HostSmokeError("FIXTURE_ARGV_CAPTURED")

    # 只替身宿主解析与宿主进程启动；fixture 路径不要求任何模型选择器。
    monkeypatch.setattr(
        host_smoke,
        "resolve_host_executable",
        lambda *args, **kwargs: ({"path": str(tmp_path / "codex")}, None),
    )
    monkeypatch.setattr(subprocess, "Popen", capture)
    with pytest.raises(HostSmokeError, match="FIXTURE_ARGV_CAPTURED"):
        host_smoke.run_host_smoke(
            "codex",
            project_root=tmp_path / "项目",
            entry=_fake_entry(tmp_path),
        )
    argv = captured["argv"]
    assert argv[1:3] == ["fixture", "run"]
    assert "--host-smoke-recovery" not in argv
    for flag in ("-m", "--model", "--provider", "--reasoning", "--thinking", "-c"):
        assert flag not in argv


# ─── ci-r24-183：分量别名、完整批次选择器与冻结透传 ────────────────────────


@pytest.mark.parametrize(
    "opaque_alias",
    [
        "openai/auto",
        "openai/default",
        "default/gpt-5.2",
        "AUTO/gpt-5.2",
        "openai/Auto",
        " auto /gpt-5.2",
        "openai/ Default ",
    ],
)
def test_omp_model_component_aliases_remain_opaque(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    opaque_alias: str,
) -> None:
    """提供方限定不豁免分量别名：provider/model 任一分为 auto/default 即拒绝。"""
    captured = _capture_argv(monkeypatch, tmp_path, "omp")
    selectors = dict(_EXPLICIT_SELECTORS["omp"])
    selectors["omp_model"] = opaque_alias
    with pytest.raises(HostSmokeError, match="不透明"):
        _run_real_host_smoke("omp", tmp_path=tmp_path, selectors=selectors)
    assert "argv" not in captured


def test_validate_explicit_host_selection_requires_complete_mapping() -> None:
    """七项选择器映射必须完整、未知字段拒绝、返回值规范化。"""
    complete = {
        "codex_model": " gpt-5.6-luna ",
        "codex_reasoning": "high",
        "hermes_provider": "anthropic",
        "hermes_model": "anthropic/claude-sonnet-4",
        "hermes_reasoning": "high",
        "omp_model": "openai/gpt-5.2",
        "omp_thinking": "high",
    }
    frozen = host_smoke.validate_explicit_host_selection(complete)
    assert set(frozen) == set(complete)
    assert frozen["codex_model"] == "gpt-5.6-luna"

    codex_only = {key: complete[key] for key in ("codex_model", "codex_reasoning")}
    with pytest.raises(HostSmokeError, match="必须显式指定"):
        host_smoke.validate_explicit_host_selection(codex_only)

    with pytest.raises(HostSmokeError, match="未声明字段"):
        host_smoke.validate_explicit_host_selection({**complete, "codex_temperature": "0.5"})


def test_batch_partial_selection_starts_no_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """缺失 Hermes/OMP 时，即使 Codex 选择器完整也不得启动任何宿主。"""
    layout, projects, catalog = _layout(tmp_path)
    dispatched: list[dict[str, Any]] = []

    def must_not_dispatch(*args: Any, **kwargs: Any) -> Any:
        dispatched.append(kwargs)
        raise host_smoke.HostSmokeError("PARTIAL_SELECTION_DISPATCHED")

    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())
    monkeypatch.setattr(host_smoke, "run_host_smoke", must_not_dispatch)
    with pytest.raises(runner.HostSmokeRunnerError, match="必须显式指定"):
        runner.run_installed_host_smoke(
            layout,
            project_root=projects,
            catalog_path=catalog,
            codex_model="gpt-5.6-luna",
            codex_reasoning="high",
        )
    assert dispatched == []


def test_batch_freezes_normalized_selection_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """批次校验通过后向宿主派发规范化冻结值，而不是调用方原始取值。"""
    layout, projects, catalog = _layout(tmp_path)
    dispatched: list[dict[str, Any]] = []

    def capture_dispatch(*args: Any, **kwargs: Any) -> Any:
        dispatched.append(kwargs)
        raise host_smoke.HostSmokeError("FROZEN_SELECTION_CAPTURED")

    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())
    monkeypatch.setattr(host_smoke, "run_host_smoke", capture_dispatch)
    with pytest.raises(runner.HostSmokeRunnerError, match="FROZEN_SELECTION_CAPTURED"):
        runner.run_installed_host_smoke(
            layout,
            project_root=projects,
            catalog_path=catalog,
            codex_model=" gpt-5.6-luna ",
            codex_reasoning="high",
            omp_model=" openai/gpt-5.2 ",
            omp_thinking="high",
            hermes_provider="anthropic",
            hermes_model="anthropic/claude-sonnet-4",
            hermes_reasoning="high",
        )
    assert dispatched[0]["codex_model"] == "gpt-5.6-luna"
    assert dispatched[0]["omp_model"] == "openai/gpt-5.2"


def test_batch_without_any_selector_rejects_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R184：全空不再走旧的晚检路径；原 R183 通过记录保留为历史。"""
    layout, projects, catalog = _layout(tmp_path)
    dispatched: list[dict[str, Any]] = []

    def legacy_dispatch(*args: Any, **kwargs: Any) -> Any:
        dispatched.append(kwargs)
        raise host_smoke.HostSmokeError("LEGACY_DISPATCH_REACHED")

    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())
    monkeypatch.setattr(host_smoke, "run_host_smoke", legacy_dispatch)
    with pytest.raises(runner.HostSmokeRunnerError, match="必须显式指定"):
        runner.run_installed_host_smoke(layout, project_root=projects, catalog_path=catalog)
    assert dispatched == []
    assert not projects.exists()
