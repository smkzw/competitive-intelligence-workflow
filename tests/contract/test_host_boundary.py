from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.hosts import (
    FORBIDDEN_HOST_OPERATIONS,
    HOST_ADAPTER_NAMES,
    HOST_ADAPTER_PUBLIC_API,
    HOST_RUN_IDENTITY_HOOKS,
    HOST_SHARED_SEMANTIC_SURFACE,
    CodexHostAdapter,
    HermesHostAdapter,
    HostAdapter,
    HostBoundaryError,
    OmpHostAdapter,
)

ROOT = Path(__file__).resolve().parents[2]
HOSTS_PACKAGE_DIR = ROOT / "src" / "ci_workflow" / "hosts"

# 宿主层唯一可复用的公共设施（Task 9.4 authoritative-boundaries）：公共
# capability preflight、公共项目合同校验、只读交付投影与规范事件流。门槛评估器、来源
# 策略写入、事实/声明存储、快照锁定与渲染内部实现不得进入宿主层。
ALLOWED_CI_WORKFLOW_IMPORTS = frozenset(
    {
        "ci_workflow.hosts",
        "ci_workflow.application.capability_preflight",
        "ci_workflow.application.project_service",
        "ci_workflow.application.delivered_artifacts",
        "ci_workflow.storage.event_store",
    }
)


def _thin_adapter_namespace(host: str = "codex") -> dict[str, Any]:
    """最小合法薄适配器：只声明宿主身份与三个运行身份钩子。"""
    return {
        "host": host,
        "host_label_zh": "测试宿主",
        "executable_candidates": lambda self: (),
        "install_entry_candidates": lambda self: (),
        "session_channel": lambda self: "test-session-channel",
    }


def _ci_workflow_import_roots() -> set[str]:
    roots: set[str] = set()
    for path in sorted(HOSTS_PACKAGE_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(
                    alias.name
                    for alias in node.names
                    if alias.name.startswith("ci_workflow")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("ci_workflow")
            ):
                roots.add(node.module)
    return roots


def test_host_base_public_surface_is_frozen_to_thin_adapter_api() -> None:
    public_methods = {name for name in dir(HostAdapter) if not name.startswith("_")}
    assert public_methods == HOST_SHARED_SEMANTIC_SURFACE | HOST_RUN_IDENTITY_HOOKS
    assert public_methods | {"host", "host_label_zh"} == HOST_ADAPTER_PUBLIC_API
    # prd 验收 1 的六类薄操作全部由共享语义面承担，无需任何其他公共入口。
    for operation_family in (
        "resolve_minimal_input",
        "invocation_plan",
        "build_semantic_receipt",
        "run_identity",
        "capability_matrix",
    ):
        assert operation_family in public_methods


def test_host_layer_cannot_import_scientific_truth_layers() -> None:
    roots = _ci_workflow_import_roots()
    assert roots, "宿主层应至少导入自身包"
    for module in roots:
        allowed = any(
            module == item or module.startswith(f"{item}.")
            for item in ALLOWED_CI_WORKFLOW_IMPORTS
        )
        assert allowed, f"宿主层不得导入科学真源或渲染内部实现：{module}"


@pytest.mark.parametrize(("operation", "rule"), sorted(FORBIDDEN_HOST_OPERATIONS.items()))
def test_scientific_overreach_members_fail_at_class_definition(
    operation: str, rule: str
) -> None:
    namespace = _thin_adapter_namespace()
    namespace[operation] = lambda self: None
    with pytest.raises(HostBoundaryError) as excinfo:
        type(f"OverreachAdapter_{operation}", (HostAdapter,), namespace)
    assert operation in str(excinfo.value)
    assert rule in str(excinfo.value)


@pytest.mark.parametrize("method_name", sorted(HOST_SHARED_SEMANTIC_SURFACE))
def test_overriding_shared_semantic_surface_fails_closed(method_name: str) -> None:
    namespace = _thin_adapter_namespace()
    namespace[method_name] = lambda self, *args: "tampered"
    with pytest.raises(HostBoundaryError, match="共享语义面"):
        type("OverrideAdapter", (HostAdapter,), namespace)


def test_extra_public_member_fails_closed_with_thin_adapter_rule() -> None:
    namespace = _thin_adapter_namespace()
    namespace["publish_report"] = lambda self: None
    with pytest.raises(HostBoundaryError, match="不得新增公共成员"):
        type("FatAdapter", (HostAdapter,), namespace)


def test_public_attribute_declaration_fails_closed() -> None:
    namespace = _thin_adapter_namespace()
    namespace["__annotations__"] = {"custom_status_prefix": "str"}
    with pytest.raises(HostBoundaryError, match="不得新增公共属性声明"):
        type("AnnotatedAdapter", (HostAdapter,), namespace)


def test_constructor_override_fails_closed() -> None:
    namespace = _thin_adapter_namespace()
    namespace["__init__"] = lambda self: None
    with pytest.raises(HostBoundaryError, match="构造函数"):
        type("ReinitializedAdapter", (HostAdapter,), namespace)


@pytest.mark.parametrize("host_name", ["local", "claude", ""])
def test_illegal_host_names_fail_at_class_definition(host_name: str) -> None:
    namespace = _thin_adapter_namespace(host=host_name)
    with pytest.raises(HostBoundaryError, match="宿主名只能是"):
        type("IllegalHostAdapter", (HostAdapter,), namespace)


def test_adapter_without_declared_host_fails_at_instantiation() -> None:
    namespace = _thin_adapter_namespace()
    del namespace["host"]
    adapter_cls = type("HostlessAdapter", (HostAdapter,), namespace)
    with pytest.raises(HostBoundaryError, match="必须声明"):
        adapter_cls(probe=StaticCapabilityProbe())


def test_adapter_with_blank_display_label_fails_at_instantiation() -> None:
    namespace = _thin_adapter_namespace()
    namespace["host_label_zh"] = "   "
    adapter_cls = type("BlankLabelAdapter", (HostAdapter,), namespace)
    with pytest.raises(HostBoundaryError, match="非空中文宿主显示名"):
        adapter_cls(probe=StaticCapabilityProbe())


def test_private_host_helpers_are_still_allowed() -> None:
    namespace = _thin_adapter_namespace()
    namespace["_status_prefix"] = "codex"
    adapter_cls = type("PrivateHelperAdapter", (HostAdapter,), namespace)
    adapter = adapter_cls(probe=StaticCapabilityProbe())
    assert adapter._status_prefix == "codex"
    assert adapter.host == "codex"


@pytest.mark.parametrize(
    "adapter_cls",
    [CodexHostAdapter, HermesHostAdapter, OmpHostAdapter],
)
def test_real_adapters_stay_thin_and_share_invocation_semantics(
    adapter_cls: type[HostAdapter],
) -> None:
    instance = adapter_cls(probe=StaticCapabilityProbe())
    assert instance.host in HOST_ADAPTER_NAMES
    defined_public = {
        name for name in vars(adapter_cls) if not name.startswith("_")
    }
    assert defined_public <= HOST_RUN_IDENTITY_HOOKS | {"host", "host_label_zh"}
    plan = instance.invocation_plan(Path("/tmp/ci-host-project"))
    assert plan.host == instance.host
    assert plan.preflight_command[:5] == (
        "ci-workflow",
        "capability",
        "preflight",
        "--host",
        instance.host,
    )
    assert plan.run_command == (
        "ci-workflow",
        "project",
        "run",
        "--root",
        "/tmp/ci-host-project",
    )
    assert plan.resume_command == plan.run_command + ("--resume",)


def test_real_adapters_declare_each_host_exactly_once() -> None:
    declared = {
        cls(probe=StaticCapabilityProbe()).host
        for cls in (CodexHostAdapter, HermesHostAdapter, OmpHostAdapter)
    }
    assert declared == set(HOST_ADAPTER_NAMES)
