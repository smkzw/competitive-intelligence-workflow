#!/usr/bin/env python3
"""Launch the PK04 runner from an isolated candidate installation.

The launcher deliberately re-execs the interpreter with the candidate ``src``
first on ``PYTHONPATH``. The runner module then invokes each host-smoke command
as a separate external process and persists Task 9.4 ``HostReceipt`` JSON.

Usage::

    uv run python tools/run_host_smoke.py --install-root /tmp/ci-candidate
    uv run python tools/run_host_smoke.py --host codex --case host-smoke-v1 \
      --require-external-host-process --receipt /tmp/codex.json
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _candidate_src(install_root: Path) -> Path:
    root = install_root.expanduser().resolve()
    versions = root / "versions"
    if not versions.is_dir():
        raise SystemExit(f"候选安装缺少 versions 根：{versions}")
    candidates = [
        entry for entry in versions.iterdir() if entry.is_dir() and not entry.is_symlink()
    ]
    if len(candidates) != 1:
        raise SystemExit("候选安装必须恰好包含一个内容地址版本")
    source = candidates[0] / "src"
    if not source.is_dir():
        raise SystemExit(f"候选安装缺少 Python 包源码根：{source}")
    return source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--install-root",
        default=os.environ.get(
            "CI_WORKFLOW_INSTALL_ROOT",
            str(
                Path.home()
                / ".cc-switch"
                / "skills"
                / "clinical-research"
                / "competitive-intelligence-workflow"
            ),
        ),
    )
    args, remaining = parser.parse_known_args(argv)
    root = Path(args.install_root).expanduser().resolve()
    source = _candidate_src(root)
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        [str(root / "bin"), environment.get("PATH", "")]
    ).strip(os.pathsep)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(source), environment.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    environment["CI_WORKFLOW_PYTHON"] = sys.executable
    command = [
        sys.executable,
        "-m",
        "ci_workflow.application.host_smoke_runner",
        "--install-root",
        str(root),
        *remaining,
    ]
    os.execvpe(sys.executable, command, environment)


if __name__ == "__main__":
    raise SystemExit(main())
