"""工具注册表。每个工具 = 名称 + 中文说明 + Pydantic 参数模型 + Python 函数。

Skill 只能调用 SKILL.md 中 `tools:` 白名单里的工具；submit_result 由 Harness 自动提供。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ciw2.harness.cancellation import RunCancelled


@dataclass
class ToolContext:
    """工具运行时可见的上下文（数据库、CAS、项目、运行），由 pipeline 注入。"""

    db: Any = None
    cas: Any = None
    settings: Any = None
    project_id: str | None = None
    run_id: str | None = None
    stage: str | None = None
    extra: dict[str, Any] | None = None


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[ToolContext, Any], Any]

    def schema(self) -> dict[str, Any]:
        params = self.args_model.model_json_schema()
        params.pop("title", None)
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                                                 "parameters": params}}

    def run(self, ctx: ToolContext, raw_args: dict[str, Any]) -> str:
        try:
            args = self.args_model.model_validate(raw_args)
        except ValidationError as exc:
            return json.dumps({"error": "参数不合法", "detail": exc.errors(include_url=False)},
                              ensure_ascii=False, default=str)
        try:
            result = self.fn(ctx, args)
        except RunCancelled:
            raise   # 停止意图不是工具失败，不能回给模型后继续重试
        except Exception as exc:  # noqa: BLE001 - 工具边界将未知异常显式交回模型
            return json.dumps({"error": f"{type(exc).__name__}: {exc}", "status": "tool_failed"},
                              ensure_ascii=False)
        text = result if isinstance(result, str) else (
            result.model_dump_json() if isinstance(result, BaseModel)
            else json.dumps(result, ensure_ascii=False, default=str))
        if len(text) <= 12000:
            return text
        if ctx.cas is None:
            return json.dumps({'status': 'tool_failed', 'error': '长结果缺少可恢复存储'}, ensure_ascii=False)
        digest = ctx.cas.put(text.encode('utf-8'))
        if ctx.extra is None:
            ctx.extra = {}
        ctx.extra.setdefault('tool_result_ids', set()).add(digest)
        return json.dumps(_page_result(ctx, PageArgs(result_id=digest)), ensure_ascii=False)


class PageArgs(BaseModel):
    result_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    offset: int = Field(default=0, ge=0)


def _page_result(ctx: ToolContext, args: PageArgs) -> dict[str, Any]:
    if ctx.cas is None or args.result_id not in (ctx.extra or {}).get('tool_result_ids', set()):
        return {'status': 'tool_failed', 'error': '当前工作单元未读取该结果'}
    text = ctx.cas.get_text(args.result_id)
    if args.offset > len(text):
        return {'status': 'tool_failed', 'error': '分页位置超出结果范围'}
    end = min(args.offset + 4000, len(text))
    return {'status': 'paged', 'result_id': args.result_id, 'offset': args.offset,
            'total_chars': len(text), 'next_offset': end if end < len(text) else None,
            'text': text[args.offset:end]}


RESULT_PAGE_TOOL = Tool('read_tool_result', '继续读取本工作单元已获取的长结果，不重新请求来源。',
                        PageArgs, _page_result)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, args_model: type[BaseModel]) -> Callable[
            [Callable[[ToolContext, Any], Any]], Callable[[ToolContext, Any], Any]]:
        def deco(fn: Callable[[ToolContext, Any], Any]) -> Callable[[ToolContext, Any], Any]:
            if name in self._tools:
                raise ValueError(f"工具重名：{name}")
            self._tools[name] = Tool(name, description, args_model, fn)
            return fn
        return deco

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def subset(self, names: list[str]) -> list[Tool]:
        missing = [n for n in names if n not in self._tools]
        if missing:
            raise KeyError(f"Skill 引用了未注册的工具：{missing}")
        return [self._tools[n] for n in names]

    def names(self) -> list[str]:
        return sorted(self._tools)


# 全局默认注册表；sources/*.py 在 import 时把工具注册到这里。
REGISTRY = ToolRegistry()


class ReadFactArgs(BaseModel):
    fact_id: str = Field(min_length=1)


@REGISTRY.register('read_project_fact', '读取当前事实完整值、科学上下文与来源；支持本次摘要短引用，长结果可继续分页。', ReadFactArgs)
def read_project_fact(ctx: ToolContext, args: ReadFactArgs) -> Any:
    if ctx.db is None or not ctx.project_id:
        return {'status': 'tool_failed', 'error': '缺少当前项目'}
    allowed = (ctx.extra or {}).get('summary_fact_refs')
    if allowed is not None and args.fact_id not in allowed and args.fact_id not in allowed.values():
        return {'status': 'tool_failed', 'error': '该事实不属于本次摘要工作单元'}
    fact_id = (allowed or {}).get(args.fact_id, args.fact_id)
    fact = next((fact for fact in ctx.db.current_facts(ctx.project_id) if fact['id'] == fact_id), None)
    if fact is None:
        return {'status': 'tool_failed', 'error': '该事实不属于本项目当前事实集合'}
    if ctx.extra is None:
        ctx.extra = {}
    if fact['source_id']:
        ctx.extra.setdefault('source_ids_read', set()).add(fact['source_id'])
    return {'status': 'ok', 'requested_ref': args.fact_id, 'fact': fact}
