"""One real, primary-only protocol probe on a saved task; no research DB writes.

Credentials come only from existing CIW environment variables. A probe is not a
pipeline run or medical acceptance. Output contains safe metadata, not reasoning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.agent import HARNESS_RULES, _submit_tool
from ciw2.harness.llm import LLMError, OpenAICompatLLM
from ciw2.harness.skills import load_skills
from ciw2.pipeline.stages import _analysis_tasks, _compact
from ciw2.render.portal import report_data
from ciw2.store.db import DB


def saved_task(db_path: Path, run_id: str) -> dict:
    with sqlite3.connect(f'file:{db_path.resolve()}?mode=ro', uri=True) as conn:
        row = conn.execute("SELECT content FROM agent_steps WHERE run_id=? AND skill='analysis-c' "
                           "AND role='task' ORDER BY id LIMIT 1", (run_id,)).fetchone()
    if row is None:
        raise ValueError('No saved analysis-c task for the requested run')
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        # Historical log_step capped JSON at 20k. Reconstruct from the frozen
        # source candidate, requiring the entire retained prefix to match.
        task = current_task(db_path, run_id)
        if not json.dumps(task, ensure_ascii=False).startswith(row[0]):
            raise ValueError('Frozen task reconstruction differs from the recorded input') from None
        return task


def current_task(db_path: Path, run_id: str) -> dict:
    db = object.__new__(DB)
    db._conn = sqlite3.connect(f'file:{db_path.resolve()}?mode=ro', uri=True)
    db._conn.row_factory = sqlite3.Row
    db._lock = threading.RLock()
    try:
        run = db.one('SELECT project_id FROM runs WHERE id=?', (run_id,))
        if run is None:
            raise ValueError('Unknown run; no model call')
        project = db.project(run['project_id'])
        core = _compact(report_data(db, project['id'], 'C'))
        intake = db.stage_output(run_id, 'intake') or project
        base = {'indication': intake['indication'], 'focus': project['focus'],
                'cutoff_date': project['cutoff_date'],
                'overview': {key: len(value) for key, value in core.items() if isinstance(value, list)}}
        verified = {f['id'] for f in db.current_facts(project['id']) if f['status'] == 'verified'}
        return _analysis_tasks(core, base, verified)[0]
    finally:
        db._conn.close()


def probe(settings: Settings, task: dict, output_dir: Path, timeout: float = 120,
          input_origin: str = 'saved_task') -> dict:
    skill = load_skills(settings.skills_dir)['analysis-c']
    messages = [{'role': 'system', 'content': f'{HARNESS_RULES}\n本次最多 4 次模型交互，预留最后一次提交已核实结果。\n\n# Skill：{skill.name}\n{skill.body}'},
                {'role': 'user', 'content': json.dumps(task, ensure_ascii=False)}]
    if skill.tools:
        raise ValueError('This bounded diagnostic supports the no-research-tools analysis-c contract only')
    tools = [_submit_tool(skill.output)]
    encoded = json.dumps({'messages': messages, 'tools': tools}, ensure_ascii=False).encode()
    output_dir.mkdir(parents=True, exist_ok=False)
    result = {'status': 'STARTED_PROTOCOL_PROBE_NOT_ACCEPTED', 'requested_model': settings.llm_model,
              'input_sha256': hashlib.sha256(encoded).hexdigest(), 'input_bytes': len(encoded),
              'task_chars': len(messages[1]['content']), 'pipeline_acceptance': 'NOT_RUN',
              'input_origin': input_origin,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output_dir / 'started.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    client = OpenAICompatLLM(settings.llm_base_url, settings.llm_api_key, settings.llm_model,
                             timeout_s=timeout, max_retries=1)
    start = time.monotonic()
    try:
        reply = client.chat(messages, tools)
        result.update(status='RETURNED_PROTOCOL_PROBE_NOT_ACCEPTED', actual_model=reply.raw.get('model'),
                      usage=reply.raw.get('usage'), finish_reason=reply.raw['choices'][0].get('finish_reason'),
                      tool_names=[call.name for call in reply.tool_calls], body_chars=len(reply.content))
        if len(reply.tool_calls) == 1 and reply.tool_calls[0].name == 'submit_result':
            submitted = skill.output.model_validate(reply.tool_calls[0].arguments)
            result['schema_valid'] = True
            result['finding_count'] = len(submitted.findings)
            result['references_valid'] = all(f.fact_refs and set(f.fact_refs) <= set(task['verified_fact_ids'])
                                             for f in submitted.findings)
    except LLMError as exc:
        result.update(status='FAILED_PROTOCOL_PROBE', error_type=type(exc).__name__, metadata=exc.metadata)
    except ValueError:
        result.update(status='FAILED_PROTOCOL_PROBE', error_type='SchemaValidationError', schema_valid=False)
    finally:
        client._client.close()
        result['duration_seconds'] = round(time.monotonic() - start, 3)
        (output_dir / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--current-task', action='store_true', help='Plan first task with current code, not old log')
    args = parser.parse_args()
    settings = Settings(data_dir=args.data_dir)
    task = (current_task if args.current_task else saved_task)(settings.db_path, args.run)
    result = probe(settings, task, args.output_dir, args.timeout,
                   'current_code_task' if args.current_task else 'saved_task')
    print(json.dumps(result, ensure_ascii=False))
