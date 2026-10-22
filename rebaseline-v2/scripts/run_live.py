"""Real model pipeline; uses configured environment, never stores credentials.

Run from the v2 directory with: uv run python scripts/run_live.py --indication ...
The local receipt records identity/results, not logs or full source text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ciw2.config import get_settings
from ciw2.render.portal import report_data
from ciw2.service import Service


def source_hashes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ('src/ciw2', 'skills') for path in sorted((root / folder).rglob('*'))
            if path.is_file() and path.suffix in {'.py', '.md', '.html', '.js', '.css'}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--indication', required=True)
    parser.add_argument('--reports', default='C')
    parser.add_argument('--focus', default='')
    parser.add_argument('--project')
    parser.add_argument('--resume-run')
    args = parser.parse_args()
    if args.resume_run and not args.project:
        parser.error('--resume-run requires --project')
    service = Service(get_settings())
    project = args.project or service.create_project(args.indication, args.reports.split(','), focus=args.focus)
    run_id = args.resume_run or service.db.create_run(project)
    first_step = service.db.one('SELECT COALESCE(MAX(id),0) id FROM agent_steps WHERE run_id=?', (run_id,))['id']
    root = service.settings.data_dir / 'receipts'
    root.mkdir(exist_ok=True)
    attempt = len(list(root.glob(f'{run_id}*.json'))) + 1
    marker = root / f'{run_id}-attempt-{attempt:04d}.json'
    initial = {'project_id': project, 'run_id': run_id, 'requested_model': service.settings.llm_model,
               'state': 'STARTED_REAL_PIPELINE_NOT_ACCEPTED',
               'start_step_id': first_step,
               'runtime_settings': {'max_agent_steps': service.settings.max_agent_steps,
                                    'search_provider': service.settings.websearch_provider},
               'source_hashes': source_hashes(Path.cwd())}
    with marker.open('x') as stream:
        stream.write(json.dumps(initial, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in initial.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)
    service.start_run(project, resume_run=run_id, background=False)
    run = service.db.one('SELECT * FROM runs WHERE id=?', (run_id,))
    stages = service.db.query('SELECT name,status,error FROM stages WHERE run_id=?', (run_id,))
    rows = {r: report_data(service.db, project, r).get('rows', [])
            for r in service.db.project(project)['reports']}
    files = {}
    for path in (service.settings.portals_dir / project).glob('*.html'):
        files[str(path.relative_to(service.settings.data_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()
    identity = service.db.query("SELECT content FROM agent_steps WHERE run_id=? AND role='model' AND id>? ORDER BY id",
                               (run_id, first_step))
    result = {**initial, 'state': 'REAL_PIPELINE_RETURNED_NOT_VISUAL_OR_SCIENTIFIC_ACCEPTANCE',
              'run_status': run['status'], 'stages': stages, 'rows': {r: len(v) for r, v in rows.items()},
              'facts': len(service.db.current_facts(project)), 'files': files,
              'source_hashes_end': source_hashes(Path.cwd()),
              'model_calls': [json.loads(x['content']) for x in identity]}
    marker.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: result[k] for k in ('project_id', 'run_id', 'run_status', 'rows', 'facts')},
                     ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
