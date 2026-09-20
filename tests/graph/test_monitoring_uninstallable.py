"""Task 9.3 监测可卸载性测试：核心工作流不依赖监测模块或监测 Skill。

设计合同（Task 9.3 design.md §边界与依赖方向）：监测是可选叶子能力，
核心项目服务和刷新服务不得反向导入监测模块；删除监测模块或不导入
监测时，项目新建/校验、打开/恢复与 Task 9.2 手动刷新回归继续通过。

两层证据：

1. 静态导入图扫描：解析 ``src/ci_workflow`` 全部源码，除监测模块自身
   外，任何模块都不得导入 ``application.monitoring_service``、
   ``domain.monitoring`` 或 ``graph.definitions.monitoring``。
2. 动态移除仿真：通过 sitecustomize 元路径钩子在子进程中把监测模块
   标记为"已移除"（导入即失败并记录），然后走真实 CLI 建项目/校验，
   并在独立进程中驱动项目服务、刷新分支裁定、修订绑定与控制图执行器；
   全程不得有任何监测导入尝试。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "src" / "ci_workflow"

MONITORING_MODULE_NAMES = frozenset(
    {
        "ci_workflow.application.monitoring_service",
        "ci_workflow.domain.monitoring",
        "ci_workflow.graph.definitions.monitoring",
    }
)

# 静态扫描中允许导入监测模块的文件（监测模块自身；包初始化不重导出监测）。
MONITORING_FILE_SUFFIXES = (
    Path("application") / "monitoring_service.py",
    Path("domain") / "monitoring.py",
    Path("graph") / "definitions" / "monitoring.py",
)

_SITECUSTOMIZE = """
import os
import sys

_BLOCKED = {blocked!r}
_LOG_PATH = os.environ.get("CI_MONITORING_BLOCK_LOG", "")


class _MonitoringRemoved:
    def find_spec(self, name, path=None, target=None):
        if name in _BLOCKED or any(name.startswith(module + ".") for module in _BLOCKED):
            if _LOG_PATH:
                with open(_LOG_PATH, "a", encoding="utf-8") as handle:
                    handle.write(name + "\\n")
            raise ImportError("监测模块已在本测试中移除: " + name)
        return None


sys.meta_path.insert(0, _MonitoringRemoved())
"""

_CORE_DRIVERS_SCRIPT = """
import json
import tempfile
import sys
from datetime import UTC, datetime
from pathlib import Path

BLOCKED = {blocked!r}
attempted = []


class _MonitoringRemoved:
    def find_spec(self, name, path=None, target=None):
        if name in BLOCKED or any(name.startswith(module + ".") for module in BLOCKED):
            attempted.append(name)
            raise ImportError("监测模块已在本测试中移除: " + name)
        return None


sys.meta_path.insert(0, _MonitoringRemoved())

# 核心导入：CLI、项目服务、刷新服务、修订绑定与控制图运行时
import ci_workflow.cli  # noqa: E402,F401
from ci_workflow.application.correction_service import CorrectionService  # noqa: E402,F401
from ci_workflow.application.project_service import (  # noqa: E402
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.application.refresh_service import RefreshService  # noqa: E402,F401
from ci_workflow.domain.contracts import create_project_contract  # noqa: E402
from ci_workflow.graph.definitions.correction import bindings_for_operation  # noqa: E402
from ci_workflow.graph.definitions.refresh import (  # noqa: E402
    BRANCH_LOCAL_REFRESH,
    RefreshBaselineIdentity,
    classify_refresh_branch,
)
from ci_workflow.graph.executor import GraphExecutor  # noqa: E402

# 项目新建与校验（打开/恢复）在无监测模块下工作
with tempfile.TemporaryDirectory() as tmp:
    contract = create_project_contract(
        indication="慢性鼻窦炎伴鼻息肉",
        reports=["A"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-08-20",
        created_at=datetime(2026, 8, 21, 9, 0, tzinfo=UTC),
    )
    workspace = create_project_workspace(Path(tmp) / "项目", contract)
    verification = verify_project_workspace(workspace)
    assert (workspace / "monitoring" / "inbox").is_dir(), "项目工作区必须保留监测收件目录"
    assert verification.contract.contract_version == 1

# 刷新分支裁定与修订迁移绑定不受监测移除影响
identity = RefreshBaselineIdentity(
    contract_schema_version="1.0",
    ontology_version="1.0",
    evidence_contract_version="1.0",
)
assert classify_refresh_branch(identity, identity).branch == BRANCH_LOCAL_REFRESH
assert bindings_for_operation("validate")

# 控制图执行器可完成共享证据节点（图运行时不触碰监测）
with tempfile.TemporaryDirectory() as tmp:
    executor = GraphExecutor(Path(tmp) / "项目", run_id="run_uninstall")
    executor.complete_node(
        "resolve",
        outputs={{"evidence_references": [{{"fragment_id": "frag_1", "sha256": "0" * 64}}]}},
        input_digest="resolve:1",
        project_id="p_uninstall",
        actor_id="test",
        occurred_at=datetime(2026, 8, 21, 9, 0, tzinfo=UTC),
    )

print(json.dumps({{"attempted": attempted, "ok": True}}, ensure_ascii=False))
"""


def _module_name_for(path: Path) -> tuple[str, str]:
    """返回 (模块全名, 所属包名)；__init__.py 视为包自身。"""
    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    parts = ("ci_workflow", *relative.parts)
    if parts[-1] == "__init__":
        module = ".".join(parts[:-1])
        return module, module
    module = ".".join(parts)
    return module, module.rsplit(".", 1)[0]


def _import_targets(tree: ast.Module, module: str, package: str) -> set[str]:
    """收集一个模块全部 import 目标全名（含 from X import Y 的 X.Y 形式）。"""
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                parts = package.split(".")
                # level=1 表示当前包；每多一级向上退一层
                anchor = parts[: len(parts) - (node.level - 1)]
                base = ".".join((*anchor, *(node.module.split(".") if node.module else ())))
            if base:
                targets.add(base)
                targets.update(f"{base}.{alias.name}" for alias in node.names)
    targets.discard(module)
    return targets


def test_no_core_module_imports_monitoring_statically() -> None:
    """静态导入图：除监测模块自身外，任何模块都不得导入监测。"""
    monitoring_files = {PACKAGE_ROOT / suffix for suffix in MONITORING_FILE_SUFFIXES}
    violations: list[str] = []
    scanned = 0
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if path in monitoring_files:
            continue
        scanned += 1
        module, package = _module_name_for(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hit = _import_targets(tree, module, package) & MONITORING_MODULE_NAMES
        if hit:
            violations.append(f"{path.relative_to(ROOT)} -> {sorted(hit)}")
    assert scanned > 50, "源码扫描范围异常，可能路径解析错误"
    assert not violations, f"核心模块反向导入监测: {violations}"


def test_project_create_and_verify_cli_runs_with_monitoring_modules_removed(
    tmp_path: Path,
) -> None:
    """真实 CLI 建项目 + 校验：监测模块被移除时仍通过，且无导入尝试。"""
    blocker_dir = tmp_path / "blocker"
    blocker_dir.mkdir()
    (blocker_dir / "sitecustomize.py").write_text(
        _SITECUSTOMIZE.format(blocked=tuple(MONITORING_MODULE_NAMES)),
        encoding="utf-8",
    )
    block_log = tmp_path / "block_log.txt"
    project_root = tmp_path / "呼吸疾病竞品项目"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(blocker_dir)
    env["CI_MONITORING_BLOCK_LOG"] = str(block_log)

    def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "ci_workflow", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    created = run_cli(
        "project",
        "create",
        "--root",
        str(project_root),
        "--indication",
        "慢性鼻窦炎伴鼻息肉",
        "--reports",
        "A,B,C",
        "--outputs",
        "html",
    )
    assert created.returncode == 0, created.stderr
    assert "PROJECT_CREATED" in created.stdout

    verified = run_cli("project", "verify", "--root", str(project_root))
    assert verified.returncode == 0, verified.stderr
    assert verified.stdout.strip().startswith("PROJECT_OK")
    assert "项目可继续使用" in verified.stdout

    # 全程零监测导入尝试：核心 CLI 路径不触碰监测模块
    # （阻断钩子只在有导入尝试时才落日志；文件不存在即零尝试）
    attempted = (
        [line for line in block_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        if block_log.exists()
        else []
    )
    assert attempted == [], f"核心 CLI 路径尝试导入已移除的监测模块: {attempted}"


def test_refresh_correction_and_graph_runtime_work_with_monitoring_removed(
    tmp_path: Path,
) -> None:
    """独立进程驱动项目服务、刷新裁定、修订绑定与图执行器；监测模块缺席。"""
    script = _CORE_DRIVERS_SCRIPT.format(blocked=tuple(MONITORING_MODULE_NAMES))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["attempted"] == [], (
        f"核心服务路径尝试导入已移除的监测模块: {payload['attempted']}"
    )
