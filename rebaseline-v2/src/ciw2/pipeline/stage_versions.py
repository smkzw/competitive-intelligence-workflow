"""Per-stage runtime compatibility receipts, stored in the existing stages table.

A completion receipt binds one successful stage output to the runtime that
actually produced it: the loaded stage callable (symbol plus code object and
primitive closure configuration), an explicit code dependency group, the
relevant Skill bodies/tools/output schemas, the requested model contract, the
report applicability/blocking flag and the ordered plan predecessors.

Receipts are internal stage rows named ``stage_version:<stage>:...``. They never
enter the planned stage table and never rewrite unit cache rows. Python behavior
is digested from loaded code objects, not filenames, line numbers, or current disk
bytes. Explicit source adapter scripts executed from disk are bound by relative
path and checked before and after each stage; a mid-stage replacement cannot
receive a success receipt. Render templates/assets are read on-render and affect
rendering only.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import CodeType
from typing import Any

from ciw2.pipeline import tool_versions
from ciw2.pipeline.stage_dependencies import (
    _ASSETS,
    _CONST,
    _FILES,
    _FN,
    _MODULE,
    _MODULES,
    _STAGE_CODE,
    _STAGE_SKILLS,
)

SCHEMA_VERSION = 'ciw2-stage-runtime-v1'
RECEIPT_PREFIX = 'stage_version:'

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_RENDER_ROOT = _PACKAGE_ROOT / 'render'

def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    ).hexdigest()


def _symbol(value: Any) -> str:
    module = getattr(value, '__module__', None) or getattr(type(value), '__module__', '?')
    name = getattr(value, '__qualname__', None) or getattr(value, '__name__', type(value).__qualname__)
    return f'{module}.{name}'


def _literal_digest(value: Any) -> Any:
    if isinstance(value, CodeType):
        return {'code': _code_digest(value)}
    if isinstance(value, slice):
        return {'slice': [_literal_digest(part) for part in (value.start, value.stop, value.step)]}
    if isinstance(value, tuple):
        return {'tuple': [_literal_digest(item) for item in value]}
    if isinstance(value, frozenset):
        return {'frozenset': sorted((_literal_digest(item) for item in value), key=json.dumps)}
    if isinstance(value, bytes):
        return {'bytes': value.hex()}
    if isinstance(value, float) and math.isnan(value):
        return {'float': 'nan'}
    return {'value': value}


def _code_digest(code: CodeType) -> str:
    """Digest loaded bytecode and constants without file names or line numbers."""
    return _digest({
        'name': code.co_name,
        'argcount': code.co_argcount,
        'posonly': code.co_posonlyargcount,
        'kwonly': code.co_kwonlyargcount,
        'flags': code.co_flags,
        'stacksize': code.co_stacksize,
        'bytecode': code.co_code.hex(),
        'names': list(code.co_names),
        'varnames': list(code.co_varnames),
        'cellvars': list(code.co_cellvars),
        'freevars': list(code.co_freevars),
        'consts': [_literal_digest(item) for item in code.co_consts],
    })


def _default_payload(value: Any, seen: set[int] | None = None) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {'bytes': value.hex()}
    if isinstance(value, CodeType):
        return {'code': _code_digest(value)}
    if inspect.isfunction(value) or inspect.ismethod(value):
        target = getattr(value, '__func__', value)
        code = getattr(target, '__code__', None)
        return {'callable': _symbol(value),
                'code': _code_digest(code) if isinstance(code, CodeType) else None}
    if isinstance(value, type):
        return {'type': _symbol(value)}

    seen = seen if seen is not None else set()
    identity = id(value)
    if identity in seen:
        return {'kind': type(value).__qualname__, 'recursive': True}
    seen.add(identity)
    try:
        if isinstance(value, (tuple, list)):
            return {'kind': type(value).__name__,
                    'items': [_default_payload(item, seen) for item in value]}
        if isinstance(value, (set, frozenset)):
            items = [_default_payload(item, seen) for item in value]
            return {'kind': type(value).__name__,
                    'items': sorted(items, key=lambda item: json.dumps(item, sort_keys=True))}
        if isinstance(value, dict):
            items = [[_default_payload(key, seen), _default_payload(item, seen)]
                     for key, item in value.items()]
            return {'kind': 'dict', 'items': sorted(
                items, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))}
    finally:
        seen.remove(identity)
    return {'kind': f'{type(value).__module__}.{type(value).__qualname__}'}


def function_digest(fn: Any) -> str:
    """Digest loaded code and call defaults, excluding filenames and line numbers."""
    target = getattr(fn, '__func__', fn)
    code = getattr(target, '__code__', None)
    if not isinstance(code, CodeType):
        return _digest({'callable': _symbol(fn)})
    code_hash = _code_digest(code)
    defaults = getattr(target, '__defaults__', None)
    kwdefaults = getattr(target, '__kwdefaults__', None)
    if defaults is None and kwdefaults is None:
        return code_hash
    payload = {'code': code_hash}
    if defaults is not None:
        payload['defaults_sha256'] = _digest(_default_payload(defaults))
    if kwdefaults is not None:
        payload['kwdefaults_sha256'] = _digest(_default_payload(kwdefaults))
    return _digest(payload)

def _class_digest(cls: type, module_name: str) -> str:
    entries = []
    for name, value in sorted(vars(cls).items()):
        if isinstance(value, (staticmethod, classmethod)):
            value = value.__func__
        elif isinstance(value, property):
            value = value.fget
        if inspect.isfunction(value) and getattr(value, '__module__', None) == module_name:
            entries.append([name, function_digest(value)])
        elif inspect.isclass(value) and getattr(value, '__module__', None) == module_name:
            entries.append([name, _class_digest(value, module_name)])
    return _digest(entries)


def _constant_payload(value: Any) -> Any:
    if isinstance(value, re.Pattern):
        return {'pattern': value.pattern, 'flags': value.flags}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (tuple, set, frozenset)):
        items = list(value)
        if all(item is None or isinstance(item, (bool, int, float, str)) for item in items):
            return {'kind': type(value).__name__, 'items': sorted(items, key=str)}
        return None
    if isinstance(value, (list, dict)):
        try:
            json.dumps(value, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            # CT.gov phase maps have ordered tuple-of-string keys, not JSON object keys.
            if isinstance(value, dict) and all(isinstance(key, tuple)
                    and all(isinstance(part, str) for part in key) and isinstance(item, str)
                    for key, item in value.items()):
                return _default_payload(value)
            return None
        return value
    return None


def _module_entries(module_name: str, skipped: set[str]) -> str:
    module = importlib.import_module(module_name)
    entries = []
    for name, value in sorted(vars(module).items()):
        if name in skipped:
            continue
        if inspect.isfunction(value) and getattr(value, '__module__', None) == module.__name__:
            entries.append([name, function_digest(value)])
        elif inspect.isclass(value) and getattr(value, '__module__', None) == module.__name__:
            entries.append([name, _class_digest(value, module.__name__)])
        elif name.isupper() and not name.startswith('__'):
            payload = _constant_payload(value)
            if payload is not None:
                entries.append([name, payload])
    return _digest(entries)


def module_digest(module_name: str) -> str:
    """Digest functions/classes and data constants defined by one loaded module."""
    return _module_entries(module_name, set())


def module_digest_excluding(module_name: str, exclude: Iterable[str]) -> str:
    """Digest one module without its registered tool entry points."""
    return _module_entries(module_name, set(exclude))


def assets_digest(root: Path, names: Iterable[str]) -> str:
    """Digest read-on-render files under package-relative directories."""
    root = Path(root)
    entries = []
    for name in names:
        base = root / name
        if not base.is_dir():
            continue
        for path in sorted((item for item in base.rglob('*') if item.is_file()),
                           key=lambda item: item.relative_to(root).as_posix()):
            entries.append([path.relative_to(root).as_posix(),
                            hashlib.sha256(path.read_bytes()).hexdigest()])
    return _digest(entries)


def package_files_digest(root: Path, names: Iterable[str]) -> str:
    """Digest explicit package files executed from disk, using relative names only."""
    root = Path(root)
    entries = []
    for name in names:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'代码组件路径必须位于包目录内：{name}')
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f'运行版本绑定的代码组件缺失：{relative.as_posix()}')
        entries.append([relative.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()])
    return _digest(entries)


def _loaded(module_name: str, name: str) -> Any:
    module = importlib.import_module(module_name)
    try:
        return getattr(module, name)
    except AttributeError as exc:
        raise RuntimeError(f'运行版本绑定的代码组件缺失：{module_name}.{name}') from exc


def code_binding(stage_name: str) -> dict[str, Any] | None:
    components = _STAGE_CODE.get(stage_name)
    if not components:
        return None
    parts = []
    for component in components:
        kind = component[0]
        if kind == _FN:
            _, module_name, name = component
            parts.append([f'fn:{module_name}.{name}', function_digest(_loaded(module_name, name))])
        elif kind == _CONST:
            _, module_name, name = component
            value = _loaded(module_name, name)
            if not isinstance(value, str):
                raise RuntimeError(f'代码组件常量必须是字符串：{module_name}.{name}')
            parts.append([f'const:{module_name}.{name}', value])
        elif kind == _MODULE:
            _, module_name = component
            parts.append([f'module:{module_name}', module_digest(module_name)])
        elif kind == _MODULES:
            for module_name in component[1]:
                parts.append([f'module:{module_name}', module_digest(module_name)])
        elif kind == _ASSETS:
            names = tuple(component[1])
            parts.append([f'assets:{",".join(names)}', assets_digest(_RENDER_ROOT, names)])
        elif kind == _FILES:
            names = tuple(component[1])
            parts.append([f'files:{",".join(names)}', package_files_digest(_PACKAGE_ROOT, names)])
        else:  # pragma: no cover - development guard for the explicit table
            raise RuntimeError(f'未知代码组件类型：{kind}')
    if _STAGE_SKILLS.get(stage_name):
        # Bind the shared execution surface once, not every tool implementation:
        # a tool the Skill cannot call does not change the stage behavior.
        parts.append(['harness:execution', tool_versions.shared_execution_digest()])
    return {'components': [part[0] for part in parts], 'digest': _digest(parts)}


def _stable_value(value: Any, seen: set[int] | None = None) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {'kind': 'bytes', 'sha256': hashlib.sha256(value).hexdigest()}
    if isinstance(value, tuple) and all(
            item is None or isinstance(item, (bool, int, float, str)) for item in value):
        return {'kind': 'tuple', 'items': list(value)}
    if isinstance(value, type):
        return {'kind': 'type', 'symbol': _symbol(value)}
    if inspect.isfunction(value) or inspect.ismethod(value):
        target = getattr(value, '__func__', value)
        identity = id(target)
        binding = {
            'kind': 'function',
            'symbol': _symbol(value),
            'code': function_digest(value),
        }
        seen = seen if seen is not None else set()
        if identity in seen:
            return binding
        seen.add(identity)
        config = _callable_config(target, seen)
        seen.remove(identity)
        if config:
            binding['config'] = config
        return binding
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        # Mutable containers are runtime state (e.g. test counters), not configuration.
        return {'kind': type(value).__name__}
    return {'kind': f'{type(value).__module__}.{type(value).__qualname__}'}


def _callable_config(fn: Any, seen: set[int] | None = None) -> dict[str, Any]:
    target = getattr(fn, '__func__', fn)
    code = getattr(target, '__code__', None)
    closure = getattr(target, '__closure__', None) or ()
    names = getattr(code, 'co_freevars', ()) if isinstance(code, CodeType) else ()
    seen = seen if seen is not None else {id(target)}
    config: dict[str, Any] = {}
    for name, cell in zip(names, closure, strict=False):
        try:
            config[name] = _stable_value(cell.cell_contents, seen)
        except ValueError:
            config[name] = {'kind': 'empty-cell'}
    return config


def _skill_bindings(rc: Any, names: Sequence[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items, tools = [], []
    for name in names:
        skill = rc.skills.get(name)
        if skill is None:
            items.append({'name': name, 'missing': True})
            continue
        tool_bindings = [tool_versions.tool_binding(rc, tool) for tool in skill.tools]
        tools.extend(tool_bindings)
        items.append({
            'name': skill.name,
            'body': _digest(skill.body),
            'tools': [item['name'] for item in tool_bindings],
            'max_steps': skill.max_steps,
            'output': _symbol(skill.output) if skill.output is not None else None,
            'output_schema': _digest(skill.output.model_json_schema()) if skill.output is not None else None,
        })
    deduped = {item.get('name'): item for item in tools}
    return items, [deduped[name] for name in sorted(deduped)]


def stage_binding(rc: Any, stage: Any, predecessors: Sequence[str] = ()) -> dict[str, Any]:
    from ciw2.harness.agent import HARNESS_RULES

    skills, tools = _skill_bindings(rc, _STAGE_SKILLS.get(stage.name, ()))
    return {
        'schema': SCHEMA_VERSION,
        'stage': stage.name,
        'reports': sorted(stage.reports),
        'blocking': bool(stage.blocking),
        'predecessors': list(predecessors),
        'callable': {
            'symbol': _symbol(stage.fn),
            'code': function_digest(stage.fn),
            'config': _callable_config(stage.fn),
        },
        'code': code_binding(stage.name),
        'skills': skills,
        'tools': tools,
        'rules': _digest(HARNESS_RULES) if skills else None,
        'max_agent_steps': rc.settings.max_agent_steps if skills else None,
        'model': {'requested': rc.settings.llm_model, 'check_requested': rc.settings.llm_check_model},
    }


def output_digest(output: Any) -> str:
    return _digest(output)


def _render_artifacts(rc: Any, output: Any) -> list[dict[str, Any]] | None:
    if not isinstance(output, dict) or 'files' not in output:
        return None
    names = output['files']
    allowed = {f'{report}.html' for report in rc.project['reports']}
    if not isinstance(names, list) or set(names) != allowed or len(names) != len(allowed):
        raise ValueError('渲染文件集合与本项目报告不一致')
    root = rc.settings.portals_dir / rc.project_id
    artifacts = []
    for name in sorted(names):
        path = root / name
        valid = path.is_file() and not path.is_symlink()
        artifacts.append({'name': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()
                          if valid else None})
    return artifacts


def _receipt_name(receipt: dict[str, Any]) -> str:
    name = (f"{RECEIPT_PREFIX}{receipt['stage']}:"
            f"{receipt['binding_sha256'][:16]}:{receipt['output_sha256'][:16]}")
    if receipt.get('artifacts_sha256'):
        name += ':' + receipt['artifacts_sha256'][:16]
    return name


def completion_receipt(rc: Any, stage: Any, output: Any,
                       predecessors: Sequence[str] = (), *,
                       expected_binding: dict[str, Any] | None = None) -> dict[str, Any]:
    binding = stage_binding(rc, stage, predecessors)
    if expected_binding is not None and binding != expected_binding:
        raise RuntimeError('阶段运行期间源码、Skill 或计划绑定发生变化；拒绝记录成功回执')
    receipt = {
        'schema': SCHEMA_VERSION,
        'stage': stage.name,
        'binding': binding,
        'binding_sha256': _digest(binding),
        'output_sha256': output_digest(output),
    }
    artifacts = _render_artifacts(rc, output) if stage.name == 'render' else None
    if artifacts is not None:
        if any(item['sha256'] is None for item in artifacts):
            raise RuntimeError('渲染文件不存在或不是普通文件，拒绝成功回执')
        receipt.update(artifacts=artifacts, artifacts_sha256=_digest(artifacts))
    return receipt


def write_receipt(rc: Any, receipt: dict[str, Any]) -> None:
    """Append-only receipt row; the caller owns the surrounding success transaction."""
    name = _receipt_name(receipt)
    serialized = json.dumps(receipt, ensure_ascii=False)
    existing = rc.db.one("SELECT status, output_json FROM stages WHERE run_id=? AND name=?",
                         (rc.run_id, name))
    if existing is not None:
        if existing['status'] == 'succeeded' and existing['output_json'] == serialized:
            return
        raise RuntimeError('运行版本回执标识冲突；拒绝覆盖历史回执')
    rc.db.set_stage(rc.run_id, name, 'succeeded', output=receipt)

def _stored_output(row: dict[str, Any]) -> Any:
    raw = row.get('output_json')
    if raw in (None, ''):
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _receipt_index(rc: Any) -> dict[str, list[dict[str, Any]]]:
    rows = rc.db.query("SELECT name, status, output_json FROM stages WHERE run_id=? AND name LIKE ?",
                       (rc.run_id, RECEIPT_PREFIX + '%'))
    index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if (not row['name'].startswith(RECEIPT_PREFIX) or row['status'] != 'succeeded'
                or not row.get('output_json')):
            continue
        try:
            receipt = json.loads(row['output_json'])
        except (TypeError, ValueError):
            continue
        if not isinstance(receipt, dict) or receipt.get('schema') != SCHEMA_VERSION:
            continue
        stage = receipt.get('stage')
        binding = receipt.get('binding')
        binding_sha256 = receipt.get('binding_sha256')
        output_sha256 = receipt.get('output_sha256')
        if (not isinstance(stage, str) or not isinstance(binding, dict)
                or binding.get('schema') != SCHEMA_VERSION or binding.get('stage') != stage
                or binding_sha256 != _digest(binding)
                or not isinstance(output_sha256, str) or len(output_sha256) != 64
                or any(char not in '0123456789abcdef' for char in output_sha256)):
            continue
        if 'artifacts' in receipt and receipt.get('artifacts_sha256') != _digest(receipt['artifacts']):
            continue
        expected_name = _receipt_name(receipt)
        if row['name'] != expected_name:
            continue
        index.setdefault(stage, []).append(receipt)
    return index


def _verdict(rc: Any, stage: Any, predecessors: Sequence[str], row: dict[str, Any],
             stored: Sequence[dict[str, Any]]) -> str:
    if not stored:
        return 'legacy'
    digest = output_digest(_stored_output(row))
    matching = [receipt for receipt in stored
                if receipt.get('schema') == SCHEMA_VERSION
                and receipt.get('output_sha256') == digest]
    if not matching:
        return 'incompatible'
    if stage.name == 'render':
        try:
            artifacts = _render_artifacts(rc, _stored_output(row))
        except (ValueError, OSError, TypeError):
            return 'incompatible'
        if artifacts is not None:
            if any(item['sha256'] is None for item in artifacts):
                return 'incompatible'
            matching = [receipt for receipt in matching if receipt.get('artifacts') == artifacts]
    binding = stage_binding(rc, stage, predecessors)
    if any(receipt.get('binding') == binding for receipt in matching):
        return 'compatible'
    return 'incompatible'


WORKFLOW_SCOPE_NAME = 'pipeline_scope:ordinary'


def ensure_pipeline_scope(rc: Any) -> bool:
    """Recognize ordinary runs; never relabel preexisting component/legacy rows."""
    expected = {'schema': 'ciw2-pipeline-scope-v1', 'scope': 'ordinary_pipeline',
                'project_id': rc.project_id, 'run_id': rc.run_id}
    with rc.db.tx():
        rows = rc.db.query('SELECT name,status,output_json FROM stages WHERE run_id=?', (rc.run_id,))
        if not rows:
            rc.db.set_stage(rc.run_id, WORKFLOW_SCOPE_NAME, 'succeeded', output=expected)
            return True
        marker = next((row for row in rows if row['name'] == WORKFLOW_SCOPE_NAME), None)
        return bool(marker and marker['status'] == 'succeeded' and _stored_output(marker) == expected)


def resume_boundary(rc: Any, plan: Sequence[Any]) -> tuple[int, list[str]]:
    """Return (first stage that must run, unbound legacy stages in the reused prefix).

    A succeeded stage without any receipt is legacy: it would otherwise be
    skipped, so the caller must fail closed instead of stamping or replaying it.
    A versioned but mismatching stage simply invalidates itself and descendants.
    """
    indexed = _receipt_index(rc)
    for index, stage in enumerate(plan):
        row = rc.db.one("SELECT * FROM stages WHERE run_id=? AND name=?", (rc.run_id, stage.name))
        if row is None or row['status'] != 'succeeded':
            return index, []
        verdict = _verdict(rc, stage, [item.name for item in plan[:index]], row,
                           indexed.get(stage.name, ()))
        if verdict == 'compatible':
            continue
        return index, [stage.name] if verdict == 'legacy' else []
    return len(plan), []
