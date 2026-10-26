"""Narrow per-tool runtime bindings and the shared harness execution surface.

A Skill receipt must change when one of its whitelisted tool implementations
changes, but not when a tool the Skill cannot call changes in the same module.
The tool body is digested from loaded code; the rest of its module (helpers,
parsers, constants) stays bound while other registered tool entry points are
excluded. Explicit source adapter helper modules and on-disk scripts remain
per-tool dependencies from ``stage_dependencies``. Shared execution (agent
dispatch, submit validation, Tool.run/schema, registry lookup and pagination)
is bound once for every Skill stage instead of hashing whole harness modules.
"""
from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from types import CodeType
from typing import Any

from ciw2.pipeline.stage_dependencies import _TOOL_FILES, _TOOL_MODULES

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _digests() -> Any:
    """Resolve shared digest primitives lazily: stage_versions imports us."""
    from ciw2.pipeline import stage_versions
    return stage_versions


def _implementation(fn: Any) -> str:
    digest = _digests()
    return digest._digest({'code': digest.function_digest(fn),
                           'config': digest._callable_config(fn)})


def _entry_names(rc: Any, module_name: str) -> frozenset[str]:
    """Module attributes that are registered tool entry points.

    Names are matched as well as identities: a simulation may swap one
    registry entry without re-importing the module, and the original sibling
    entry point must still stay out of another tool's helper digest.
    """
    module = importlib.import_module(module_name)
    entries = [rc.registry.get(name) for name in rc.registry.names()]
    identities = {id(tool.fn) for tool in entries}
    names = {getattr(tool.fn, '__name__', '') for tool in entries
             if getattr(tool.fn, '__module__', None) == module_name}
    return frozenset(
        name for name, value in vars(module).items()
        if inspect.isfunction(value)
        and (id(value) in identities
             or (name in names and getattr(value, '__module__', None) == module_name)))



def source_helper_digest(fn: Any) -> str:
    """Summary tools bind their actually named helpers; source acquisition stays explicit.

    Limited to plain CT.gov search/summary code, not a Python dependency engine.
    Dynamic global lookup or local helper classes keep the conservative module binding.
    Imported function aliases bind the actual loaded callable as well as declared modules.
    """
    digest=_digests();module=importlib.import_module(fn.__module__)
    pending=[getattr(fn,'__code__',None)];seen=set();entries={}
    while pending:
        code=pending.pop()
        if not isinstance(code,CodeType):return digest.module_digest(module.__name__)
        if code in seen:continue
        seen.add(code)
        pending.extend(value for value in code.co_consts if isinstance(value,CodeType))
        if {'globals','eval','exec','getattr'} & set(code.co_names):return digest.module_digest(module.__name__)
        for name in code.co_names:
            if name in entries:continue
            value=vars(module).get(name)
            if inspect.isfunction(value):
                entries[name]={'function':_implementation(value),'module':value.__module__}
                if value.__module__==module.__name__:pending.append(value.__code__)
            elif inspect.isclass(value) and value.__module__==module.__name__:
                return digest.module_digest(module.__name__)
            elif name.isupper():
                payload=digest._constant_payload(value)
                if payload is not None:entries[name]={'constant':payload}
    return digest._digest(entries)

def tool_binding(rc: Any, name: str) -> dict[str, Any]:
    """Bind one whitelisted tool; sibling tool entry points stay out."""
    try:
        tool = rc.registry.get(name)
    except KeyError:
        return {'name': name, 'missing': True}
    digest = _digests()
    module_name = getattr(tool.fn, '__module__', None)
    dependencies = _TOOL_MODULES.get(name, ())
    files = _TOOL_FILES.get(name, ())
    return {
        'name': name,
        'schema': digest._digest(tool.schema()),
        'implementation': _implementation(tool.fn),
        'module': module_name,
        'helpers': (source_helper_digest(tool.fn) if name in {'ctgov_search','ctgov_get'}
                    and module_name=='ciw2.sources.ctgov' else digest.module_digest_excluding(
                        module_name,_entry_names(rc,module_name))) if module_name else None,
        'dependencies': [[module, digest.module_digest(module)] for module in dependencies],
        'files': {'components': list(files),
                  'digest': digest.package_files_digest(_PACKAGE_ROOT, files)}
        if files else None,
    }


def _agent_digest(digest: Any) -> str:
    agent = importlib.import_module('ciw2.harness.agent')
    return digest._digest([
        ['fn:run_skill', digest.function_digest(agent.run_skill)],
        ['fn:_dispatch', digest.function_digest(agent._dispatch)],
        ['fn:_submit_tool', digest.function_digest(agent._submit_tool)],
    ])


def _tooling_digest(digest: Any) -> str:
    tools = importlib.import_module('ciw2.harness.tools')
    return digest._digest([
        ['class:Tool', digest._class_digest(tools.Tool, tools.__name__)],
        ['class:ToolRegistry', digest._class_digest(tools.ToolRegistry, tools.__name__)],
        ['schema:PageArgs', digest._digest(tools.PageArgs.model_json_schema())],
        ['fn:_page_result', digest.function_digest(tools._page_result)],
        ['tool:read_tool_result', digest._digest({
            'name': tools.RESULT_PAGE_TOOL.name,
            'description': tools.RESULT_PAGE_TOOL.description,
            'schema': tools.RESULT_PAGE_TOOL.schema(),
        })],
    ])


def shared_execution_digest() -> str:
    """Harness loop plus tool runtime executed by every Skill stage."""
    digest = _digests()
    return digest._digest({'agent': _agent_digest(digest), 'tooling': _tooling_digest(digest)})
