"""OMP（Oh My Pi）宿主薄适配器（HA04）。

只提供 OMP 运行身份（可执行文件候选、安装入口、会话通道）；最小输入
解析、能力选择、中断/恢复映射和产物定位全部继承共享基类，不复制业务
逻辑，也不改变科学真源。
"""

from __future__ import annotations

from pathlib import Path

from ci_workflow.hosts.base import HostAdapter


class OmpHostAdapter(HostAdapter):
    """OMP 宿主：同一工作流经 Oh My Pi 会话入口运行。"""

    host = "omp"
    host_label_zh = "Oh My Pi"

    def executable_candidates(self) -> tuple[Path, ...]:
        return (
            Path.home() / ".local" / "bin" / "omp",
            Path("/opt/homebrew/bin/omp"),
            Path("/usr/local/bin/omp"),
        )

    def install_entry_candidates(self) -> tuple[Path, ...]:
        return (Path.home() / ".omp",)

    def session_channel(self) -> str:
        return "omp-cli-session"
