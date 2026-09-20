#!/usr/bin/env python3
"""校验 Skill bundle 的逐文件清单、外部 SHA-256 与路径安全边界。

输入可以是构建器生成的 ``.tar.zst``，也可以是已解包的独立目录。校验器
不执行安装、不运行宿主、不修改被校验路径；缺文件、额外文件、摘要漂移、
重复成员、绝对路径、``..``、软链接和特殊 tar 节点均失败关闭。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:  # pragma: no cover - only used by direct CLI calls
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.bundle_contract import (  # noqa: E402
    REQUIRED_CATALOG_ID,
    BundleEnvironmentError,
    BundleError,
    BundleVerificationResult,
    verify_bundle,
)

__all__ = [
    "BundleEnvironmentError",
    "BundleError",
    "BundleVerificationResult",
    "verify_bundle",
    "main",
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle", "--archive", "--root", dest="bundle", required=True, help="归档或解包根目录"
    )
    parser.add_argument(
        "--sha256",
        dest="checksum_path",
        help="外部 SHA-256 文件；缺省自动读取 <bundle>.sha256",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest_path",
        help="外部逐文件 manifest；缺省自动读取 <bundle>.manifest.json（存在时）",
    )
    parser.add_argument(
        "--allow-missing-sha256",
        action="store_true",
        help="仅用于检查未压缩测试归档；候选 .tar.zst 默认必须有外部摘要",
    )
    parser.add_argument(
        "--expect-source-commit",
        dest="expect_source_commit",
        metavar="RC_COMMIT",
        help="要求 bundle 清单 source_commit 与该 RC commit 完全一致，否则失败关闭",
    )
    parser.add_argument(
        "--require-final-content",
        action="store_true",
        help="要求最终必需内容（required-v12 catalog、runner、设计合同、运行时）全部在包内",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_bundle(
            Path(args.bundle),
            checksum_path=Path(args.checksum_path) if args.checksum_path else None,
            manifest_path=Path(args.manifest_path) if args.manifest_path else None,
            require_external_digest=not args.allow_missing_sha256,
            expected_source_commit=args.expect_source_commit,
            require_final_content=args.require_final_content,
        )
    except BundleEnvironmentError as exc:
        print(f"BUNDLE_ENV_ERROR {exc}", file=sys.stderr)
        return 3
    except (BundleError, OSError, ValueError) as exc:
        print(f"BUNDLE_ERROR {exc}", file=sys.stderr)
        return 2
    digest = result.archive_sha256 or "directory"
    details = [
        f"path={result.bundle_path}",
        f"sha256={digest}",
        f"files={len(result.files)}",
    ]
    source_commit = result.manifest.get("source_commit")
    if isinstance(source_commit, str) and source_commit:
        details.append(f"source_commit={source_commit}")
    if args.require_final_content:
        details.append(f"catalog={REQUIRED_CATALOG_ID}")
    print("BUNDLE_OK " + " ".join(details))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
