"""独立测试者侧的构建器参数化补丁（不改动参考 packet）。

参考构建器 build_pnh_{audit,b_audit,c_audit,b_payload}.py 存在不可移植的外部依赖：
  1. PROJECT 来自进程外文件 /tmp/pnh-proj-path.txt；
  2. CAS 根硬编码 .artifacts/source-cas/ctgov-live-20260906（该目录本次为空）；
  3. 采集日期与截止日硬编码 2026-09-06。

本脚本把副本改为从环境变量取项目根、从项目 CAS 取原始页、使用本轮采集日，
并重建 derivation sidecar 的页序（产品自带 fetch-ctgov 会把逐记录派生正文与
回执一并写入 evidence/raw/sha256，tools/build_a_payload.py 的页面发现会
把它们全部当成 CT.gov 检索页）。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

BUILDERS = Path(__file__).resolve().parent
PROJECT = Path(os.environ["CI_TEST_PROJECT"]).resolve()
OLD_DATES = ("2026-09-12", "2026-09-06")
NEW_DATE = "2026-09-20"

PROJECT_OLD = 'PROJECT = Path(open("/tmp/pnh-proj-path.txt").read().strip().split("=", 1)[1])'
PROJECT_NEW = (
    'PROJECT = Path(os.environ.get("CI_TEST_PROJECT", "")).resolve()\n'
    'if not (PROJECT / "project.yaml").is_file():\n'
    '    raise SystemExit("CI_TEST_PROJECT 未指向测试项目目录")'
)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    original = text
    if "\nimport os\n" not in text:
        text = re.sub(r"(from __future__ import annotations\n)", r"\1\nimport os\n", text, count=1)
        assert "\nimport os\n" in text, path
    if PROJECT_OLD in text:
        text = text.replace(PROJECT_OLD, PROJECT_NEW)
    else:
        print("no PROJECT constant (ok):", path.name)
    lines = []
    for line in text.splitlines(keepends=True):
        if "ctgov-live-20260906" in line:
            line = line.replace(".artifacts/source-cas/ctgov-live-20260906/", "")
            line = line.replace("ROOT /", "PROJECT /")
        lines.append(line)
    text = "".join(lines)
    for old in OLD_DATES:
        text = text.replace(old, NEW_DATE)
    assert "ctgov-live-20260906" not in text, path
    assert "pnh-proj-path.txt" not in text, path
    if text != original:
        path.write_text(text, encoding="utf-8")
        print("patched:", path.name)


def rebuild_derivation() -> None:
    """按 fetch-ctgov 回执的真实页序重建 derivation.pages。"""
    raw_root = PROJECT / "evidence" / "raw" / "sha256"
    receipt = None
    receipt_sha = ""
    for blob in sorted(raw_root.rglob("*.bin")):
        data = json.loads(blob.read_bytes())
        if "acquisition" in data and "records" in data:
            (receipt, receipt_sha) = (data, blob.stem)
            break
    assert receipt is not None, "未找到 fetch-ctgov 回执"
    pages = receipt["acquisition"]["pages"]
    derivation_path = BUILDERS / "pnh-a-payload.derivation.json"
    derivation = json.loads(derivation_path.read_text(encoding="utf-8"))
    derivation["pages"] = [
        {"page": page["page_number"], "sha256": page["raw_asset"]["sha256"]} for page in pages
    ]
    derivation["cas_root"] = "evidence/raw/sha256"
    derivation["fetch_receipt"] = {
        "sha256": receipt_sha,
        "condition": receipt["acquisition"]["condition"],
        "total_count": receipt["acquisition"]["total_count"],
        "pagination_complete": receipt["acquisition"]["pagination_complete"],
        "projection_status": receipt["projection_status"],
        "acquired_at": receipt["records"][0]["acquired_at"],
        "record_count": len(receipt["records"]),
    }
    derivation_path.write_text(
        json.dumps(derivation, ensure_ascii=False, indent=1), encoding="utf-8",
    )
    print("derivation pages:", len(derivation["pages"]), "| first:", derivation["pages"][0])


def normalize_a_payload() -> None:
    """tools/build_a_payload.py 忽略 --cutoff，把 data_cutoff 硬编码为 2026-09-06。

    该硬编码值会被 FreshAResearchContent 的数据截止一致性校验拒绝，
    因此在本轮截止日上对齐（最小改动，不改动其它派生事实）。
    """
    path = BUILDERS / "pnh-a-payload.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    target = f"{NEW_DATE}T23:59:59.999999+08:00"
    if payload.get("data_cutoff") != target:
        print("data_cutoff:", payload.get("data_cutoff"), "->", target)
        payload["data_cutoff"] = target
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    for name in (
        "build_pnh_audit.py", "build_pnh_b_audit.py",
        "build_pnh_c_audit.py", "build_pnh_b_payload.py",
    ):
        patch(BUILDERS / name)
    normalize_a_payload()
    rebuild_derivation()
