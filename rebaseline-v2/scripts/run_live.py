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
from ciw2.domain.availability import require_supported_cutoff
from ciw2.pipeline.context import IncompleteWork
from ciw2.pipeline.runner import stages_for
from ciw2.pipeline.stages import STAGES, render
from ciw2.render.portal import report_data
from ciw2.service import Service


def source_hashes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ('src/ciw2', 'skills') for path in sorted((root / folder).rglob('*'))
            if path.is_file() and path.suffix in {'.py', '.md', '.html', '.js', '.css'}}


def run_stage(service: Service, project: str, run_id: str, name: str) -> None:
    p = service.db.project(project)
    run = service.db.one('SELECT project_id FROM runs WHERE id=?', (run_id,))
    if p is None or run is None or run['project_id'] != project:
        raise ValueError('项目与运行不匹配')
    current = name
    service.db.set_run(run_id, 'running')
    service.db.set_stage(run_id, current, 'running')
    try:
        require_supported_cutoff(p['cutoff_date'])
        stage = next((stage for stage in stages_for(p['reports']) if stage.name == name), None)
        if stage is None:
            raise ValueError('该报告不包含指定工作阶段')
        rc = service.context(project, run_id)
        rc.stage = current
        output = stage.fn(rc)
        service.db.set_stage(run_id, current, 'succeeded', output=output)
        if name.startswith('analysis_'):
            current = rc.stage = 'render'
            service.db.set_stage(run_id, current, 'running')
            service.db.set_stage(run_id, current, 'succeeded', output=render(rc))
        service.db.set_run(run_id, 'succeeded')
    except Exception as exc:  # noqa: BLE001 - bounded real-stage receipt, not full-pipeline acceptance
        service.db.set_stage(run_id, current, 'failed', error=f'{type(exc).__name__}: {exc}',
                             output=exc.output if isinstance(exc, IncompleteWork) else None)
        service.db.set_run(run_id, 'failed', error=f'{current}: {type(exc).__name__}: {exc}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--indication', required=True)
    parser.add_argument('--reports', default='C')
    parser.add_argument('--focus', default='')
    parser.add_argument('--project')
    parser.add_argument('--resume-run')
    parser.add_argument('--only-stage', choices=[stage.name for stage in STAGES])
    args = parser.parse_args()
    if args.resume_run and not args.project:
        parser.error('--resume-run requires --project')
    if args.only_stage and not args.project:
        parser.error('--only-stage requires --project pointing to an isolated prepared candidate')
    service = Service(get_settings())
    project = args.project or service.create_project(args.indication, args.reports.split(','), focus=args.focus)
    run_id = args.resume_run or service.db.create_run(project)
    first_step = service.db.one('SELECT COALESCE(MAX(id),0) id FROM agent_steps WHERE run_id=?', (run_id,))['id']
    root = service.settings.data_dir / 'receipts'
    root.mkdir(exist_ok=True)
    attempt = len(list(root.glob(f'{run_id}*.json'))) + 1
    marker = root / f'{run_id}-attempt-{attempt:04d}.json'
    initial = {'project_id': project, 'run_id': run_id, 'requested_model': service.settings.llm_model,
               'state': 'STARTED_REAL_STAGE_NOT_ACCEPTED' if args.only_stage else 'STARTED_REAL_PIPELINE_NOT_ACCEPTED',
               'scope': 'stage' if args.only_stage else 'pipeline', 'only_stage': args.only_stage,
               'pipeline_acceptance': 'NOT_RUN' if args.only_stage else 'NOT_ASSESSED',
               'runner_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'start_step_id': first_step,
               'runtime_settings': {'max_agent_steps': service.settings.max_agent_steps,
                                    'search_provider': service.settings.websearch_provider},
               'source_hashes': source_hashes(Path.cwd())}
    with marker.open('x') as stream:
        stream.write(json.dumps(initial, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in initial.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)
    if args.only_stage:
        run_stage(service, project, run_id, args.only_stage)
    else:
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
    errors = service.db.query("SELECT content FROM agent_steps WHERE run_id=? AND role='model_error' AND id>? ORDER BY id",
                             (run_id, first_step))
    result = {**initial, 'state': 'REAL_STAGE_RETURNED_NOT_PIPELINE_ACCEPTANCE' if args.only_stage else
              'REAL_PIPELINE_RETURNED_NOT_VISUAL_OR_SCIENTIFIC_ACCEPTANCE',
              'run_status': run['status'], 'stages': stages, 'rows': {r: len(v) for r, v in rows.items()},
              'facts': len(service.db.current_facts(project)), 'files': files,
              'source_hashes_end': source_hashes(Path.cwd()),
              'model_calls': [json.loads(x['content']) for x in identity],
              'model_errors': [json.loads(x['content']) for x in errors]}
    marker.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: result[k] for k in ('project_id', 'run_id', 'run_status', 'rows', 'facts')},
                     ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
