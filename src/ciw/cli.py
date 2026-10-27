"""命令行：ciw run / ciw status / ciw render / ciw capture cde。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _ws_default(slug: str) -> Path:
    return Path(
        os.environ.get(f"CIW_WORKSPACE_{slug.upper().replace('-', '_')}", f"~/Developer/ciw-workspaces/{slug}")
    ).expanduser()


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ciw", description="竞品调研子系统：适应症 → release → A/B/C 门户")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="运行流水线并发布 release")
    r.add_argument("config", help="indications/<slug>.yaml")
    r.add_argument("--workspace", help="工作区目录（默认 ~/Developer/ciw-workspaces/<slug>）")
    r.add_argument("--offline", action="store_true", help="只读工作区 CAS，不访问网络")
    r.add_argument("--with-models", action="store_true", help="对非结构化来源启用异构模型交叉核对")
    r.add_argument("--llm-config", help="模型角色配置（默认包内 data/llm.yaml）")

    s = sub.add_parser("status", help="查看 current release 的统计、覆盖与待核")
    s.add_argument("--workspace", required=True)

    rd = sub.add_parser("render", help="只重渲染 current release")
    rd.add_argument("--workspace", required=True)

    au = sub.add_parser("audit", help="抽样核对 B 数值与 CAS 原件（PRD §5 科学验收）")
    au.add_argument("--workspace", required=True)
    au.add_argument("-n", type=int, default=30)

    c = sub.add_parser("capture", help="浏览器采集中国来源（需要 ego lite 专用空间）")
    c.add_argument("source", choices=["cde", "nmpa", "docs"])
    c.add_argument("config")
    c.add_argument("--workspace")
    c.add_argument("--space", type=int, required=True, help="ego-browser TaskSpace ID")
    c.add_argument("--max-details", type=int, default=None)
    c.add_argument("--resume-only", action="store_true", help="复用已发现的NMPA地址，只补缺失详情")
    c.add_argument("--url", help="明确的公开文章地址（docs）")
    c.add_argument("--kind", choices=["company", "wechat"], default="company")
    c.add_argument("--page", default="p1", help="docs采集时已打开的Agent Page标签")

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _parser()
    a = ap.parse_args(argv)
    from ciw.store import Workspace

    if a.cmd == "run":
        return _run_command(a)
    if a.cmd == "status":
        return _status_command(a)
    if a.cmd == "render":
        from ciw.render.site import render_release

        d = Workspace(a.workspace).current_release_dir()
        if d is None:
            print("没有 current release")
            return 1
        print(render_release(d))
        return 0
    if a.cmd == "audit":
        from ciw.audit import audit

        out = audit(Workspace(a.workspace), n=a.n)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if not out["errors"] else 1
    if a.cmd == "capture":
        return _capture_command(a, ap)
    return 2


def _run_command(a) -> int:
    from ciw.api import run_indication
    from ciw.config import load_indication

    cfg = load_indication(a.config)
    res = run_indication(
        a.config,
        a.workspace or _ws_default(cfg.slug),
        offline=a.offline,
        with_models=a.with_models,
        llm_config=a.llm_config,
    )
    print(
        json.dumps(
            {
                "release_id": res.release_id,
                "release": str(res.release_path),
                "site": str(res.site_dir),
                "stats": res.stats,
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


def _status_command(a) -> int:
    from ciw.api import current_release

    cur = current_release(a.workspace)
    if cur is None:
        print("没有 current release")
        return 1
    doc, d = cur
    print(
        json.dumps(
            {
                "release_id": doc["release_id"],
                "dir": str(d),
                "generated_at": doc["generated_at"],
                "coverage": doc["coverage"],
                "stats": doc["stats"],
                "review_queue": len(doc["review_queue"]),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


def _capture_command(a, ap) -> int:
    from ciw.config import load_indication
    from ciw.sources.cde_registry import capture
    from ciw.store import Workspace

    cfg = load_indication(a.config)
    ws = Workspace(a.workspace or _ws_default(cfg.slug))
    if a.source == "docs":
        from ciw.sources.document import capture_document

        if not a.url:
            ap.error("capture docs 需要 --url")
        result = capture_document(ws, cfg, a.space, a.url, a.kind, page_label=a.page)
    elif a.source == "nmpa":
        from ciw.sources.nmpa.capture import capture as capture_nmpa

        result = capture_nmpa(ws, cfg, a.space, max_details=a.max_details, resume_only=a.resume_only)
    else:
        result = capture(ws, cfg, a.space, max_details=a.max_details)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
