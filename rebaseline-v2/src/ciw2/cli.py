"""命令行：serve | run | skills | backup | restore。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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
    r.add_argument("--max-drugs", type=int, default=None, help="可选执行预算；留空处理全部药物，未处理项保留供恢复")
    sub.add_parser("skills", help="校验并列出 Skill")
    requalify_parser=sub.add_parser('requalify',help='离线复核当前已核实LLM事实的原文裁决；只追加回执，不调用模型或网络')
    requalify_parser.add_argument('--project',required=True)
    requalify_parser.add_argument('--dry-run',action='store_true',help='只统计，不写入任何回执')
    backup_parser=sub.add_parser('backup',help='备份当前数据库与引用资料；输出必须为新目录')
    backup_parser.add_argument('--output',type=Path,required=True)
    restore_parser=sub.add_parser('restore',help='验证资料备份并恢复到明确的新数据目录，不覆盖当前资料')
    restore_parser.add_argument('--input',type=Path,required=True)
    restore_parser.add_argument('--output',type=Path,required=True)
    a = ap.parse_args(argv)

    from ciw2.config import get_settings
    if a.cmd == 'requalify':
        from ciw2.config import Settings
        from ciw2.pipeline.requalify import requalify_project
        from ciw2.store.cas import CAS
        from ciw2.store.db import DB
        settings=Settings()  # 不为一次离线复核隐式创建新的数据根
        if not settings.db_path.exists():
            print('项目不存在；未写入任何核验回执。',file=sys.stderr)
            return 2
        try:
            summary=requalify_project(DB(settings.db_path),CAS(settings.cas_dir),a.project,dry_run=a.dry_run)
        except KeyError:
            print('项目不存在；未写入任何核验回执。',file=sys.stderr)
            return 2
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        return 0
    if a.cmd in {'backup','restore'}:
        from sqlite3 import Error as SQLiteError

        from ciw2.config import Settings
        from ciw2.store.backup import BackupError, create_backup, restore_backup
        try:
            manifest=(create_backup(Settings().data_dir,a.output) if a.cmd=='backup'
                      else restore_backup(a.input,a.output))
        except (BackupError,OSError,SQLiteError) as exc:
            print(f'资料备份/恢复未完成（{type(exc).__name__}），原资料未被替换。',file=sys.stderr)
            return 1
        print(json.dumps(manifest,ensure_ascii=False,indent=2))
        return 0
    if a.cmd == "serve":
        import uvicorn

        from ciw2.web.app import create_app
        uvicorn.run(create_app(), host=a.host, port=a.port)
        return 0
    if a.cmd == "skills":
        import ciw2.sources  # noqa: F401
        from ciw2.config import Settings
        from ciw2.harness.skills import load_skills
        from ciw2.harness.tools import REGISTRY
        skills = load_skills(Settings().skills_dir)
        if not skills:
            print('未找到可用 Skill；请检查安装包或 CIW_SKILLS_DIR。',file=sys.stderr)
            return 2
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
    run = svc.db.one('SELECT status,error FROM runs WHERE id=?', (rid,))
    return 0 if run['status'] == 'succeeded' and not run['error'] else 1


if __name__ == "__main__":
    sys.exit(main())
