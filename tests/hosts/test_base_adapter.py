"""Task 9.4 HA01 公共边界验证（只验证既有实现，不修改 HA01）。

验收标准 1 的结构化表述：``HostAdapter`` 只能调用工具（公共 CLI 调用
计划）、映射中断/恢复、解析最小输入、提供路径（运行身份）、发送必要
状态和返回产物。当前 HA01 实现把该边界固化为：

- 共享语义面 ``HOST_SHARED_SEMANTIC_SURFACE``（六类薄操作）全部由基类
  承担，子类覆写在类定义时失败关闭；
- 子类公共成员只能是运行身份钩子与两个身份 ClassVar；
- 禁区操作名与非法宿主名在类定义/实例化时失败关闭。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.hosts.base import (
    HOST_ADAPTER_PUBLIC_API,
    HOST_RUN_IDENTITY_HOOKS,
    HOST_SHARED_SEMANTIC_SURFACE,
    HostAdapter,
    HostBoundaryError,
)
from ci_workflow.hosts.codex import CodexHostAdapter


def _public_members(cls: type[object]) -> set[str]:
    return {
        name
        for name in vars(cls)
        if not name.startswith("_") and name not in ("host", "host_label_zh")
    }


def test_host_adapter_can_only_call_tools_map_interrupts_paths_status_and_artifacts(
    tmp_path: Path,
) -> None:
    # 结构面：基类公共成员 = 共享语义面 + 抽象运行身份钩子；
    # 适配器唯一可声明的公共成员就是这三个运行身份钩子。
    assert _public_members(HostAdapter) == (
        HOST_SHARED_SEMANTIC_SURFACE | HOST_RUN_IDENTITY_HOOKS
    )
    assert _public_members(CodexHostAdapter) == HOST_RUN_IDENTITY_HOOKS
    assert (
        HOST_SHARED_SEMANTIC_SURFACE
        | HOST_RUN_IDENTITY_HOOKS
        | {"host", "host_label_zh"}
    ) == HOST_ADAPTER_PUBLIC_API
    # 六类薄操作逐项在场：解析最小输入、能力选择（调用工具）、
    # 规范状态（发送状态）、中断/恢复映射、产物定位、路径与调用计划。
    assert frozenset(
        {
            "resolve_minimal_input",
            "capability_matrix",
            "build_semantic_receipt",
            "resolve_executable",
            "resolve_install_entry",
            "run_identity",
            "invocation_plan",
        }
    ) == HOST_SHARED_SEMANTIC_SURFACE
    # 共享语义在合法适配器上未被覆写（语义一律来自基类）。
    for name in HOST_SHARED_SEMANTIC_SURFACE:
        assert getattr(CodexHostAdapter, name) is getattr(HostAdapter, name)

    # 行为面：越权子类在类定义时失败关闭。
    with pytest.raises(HostBoundaryError, match="共享语义面"):
        class OverridesSemantic(CodexHostAdapter):
            def build_semantic_receipt(  # type: ignore[override]
                self, **kwargs: object
            ) -> object:
                raise AssertionError("不应被调用")

    with pytest.raises(HostBoundaryError, match="构造函数"):
        class OverridesInit(CodexHostAdapter):
            def __init__(self) -> None:
                raise AssertionError("不应被调用")

    with pytest.raises(HostBoundaryError, match="特殊方法.*__setattr__"):
        class InterceptsProbeAssignment(CodexHostAdapter):
            def __setattr__(self, name: str, value: object) -> None:
                object.__setattr__(self, name, value)

    with pytest.raises(HostBoundaryError, match="特殊方法.*__getattribute__"):
        class InterceptsSharedState(CodexHostAdapter):
            def __getattribute__(self, name: str) -> object:
                return object.__getattribute__(self, name)

    with pytest.raises(HostBoundaryError, match="新增公共成员"):
        class AddsMember(CodexHostAdapter):
            def fetch_extra_sources(self) -> None:
                raise AssertionError("不应被调用")

    with pytest.raises(HostBoundaryError, match="越权"):
        class SetSourceWeight(CodexHostAdapter):
            def set_source_weight(self) -> None:
                raise AssertionError("不应被调用")

    with pytest.raises(HostBoundaryError, match="宿主名只能是"):
        class WrongHost(CodexHostAdapter):
            host = "local"  # type: ignore[assignment]

    # 行为面：合法最小子类可实例化，语义面直接可用（真实 API 建模）。
    adapter = CodexHostAdapter(probe=StaticCapabilityProbe())
    assert adapter.host == "codex"
    identity = adapter.run_identity()
    assert identity.host == "codex"
    assert identity.session_channel == "codex-cli-session"
