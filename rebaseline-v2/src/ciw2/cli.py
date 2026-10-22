"""命令行：ciw2 serve | ciw2 run | ciw2 skills"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ciw2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="启动 Web 平台")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    r = sub.add_parser("run", help="命令行跑一次调研（前台）")
    r.add_argument("--indication", required=True)
    r.add_argument("--reports", default="A", help="如 A,B,C")
    r.add_argument("--request", default="")
    r.add_argument("--focus", default="")
    r.add_argument("--max-drugs", type=int, default=30)
    sub.add_parser("skills", help="校验并列出 Skill")
    a = ap.parse_args(argv)

    from ciw2.config import get_settings
    if a.cmd == "serve":
        import uvicorn

        from ciw2.web.app import create_app
        uvicorn.run(create_app(), host=a.host, port=a.port)
        return 0
    if a.cmd == "skills":
        import ciw2.sources  # noqa: F401
        from ciw2.harness.skills import load_skills
        from ciw2.harness.tools import REGISTRY
        skills = load_skills(get_settings().skills_dir)
        for sk in skills.values():
            REGISTRY.subset(sk.tools)
            print(f"{sk.name:22s} tools={','.join(sk.tools) or '-':60s} output={sk.output.__name__ if sk.output else '-'}")
        return 0
    from ciw2.service import Service
    svc = Service(get_settings())
    pid = svc.create_project(a.indication, a.reports.split(","), a.request, a.focus)
    rid = svc.start_run(pid, background=False, max_drugs=a.max_drugs)
    print(json.dumps({"project_id": pid, "run_id": rid, "run": svc.db.one("SELECT * FROM runs WHERE id=?", (rid,))},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
