#!/usr/bin/env python3
"""把候选包安装到调用方指定的隔离根，不覆盖既有入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ci_workflow.application.fresh_install import FreshInstallError, install_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="安装竞品调研工作流候选包")
    parser.add_argument("--bundle", required=True, help="候选 .tar.zst 包")
    parser.add_argument("--root", required=True, help="全新、独立的安装目录")
    args = parser.parse_args()
    try:
        layout = install_bundle(Path(args.bundle), Path(args.root))
    except FreshInstallError as exc:
        print(f"安装未完成：{exc}", file=sys.stderr)
        return 2
    print(f"安装完成：{layout.install_root}")
    print(f"公共 Skill：{layout.public_skill}")
    print(f"运行入口：{layout.entrypoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
