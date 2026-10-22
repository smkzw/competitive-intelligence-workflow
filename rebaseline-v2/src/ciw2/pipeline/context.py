"""一次运行的上下文。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ciw2.config import Settings
from ciw2.harness.agent import run_skill
from ciw2.harness.llm import LLM
from ciw2.harness.skills import Skill
from ciw2.harness.tools import REGISTRY, ToolContext, ToolRegistry
from ciw2.store.cas import CAS
from ciw2.store.db import DB


class IncompleteWork(RuntimeError):
    def __init__(self, message: str, output: dict[str, Any]) -> None:
        super().__init__(message)
        self.output = output


def work_limit(value: Any) -> int | None:
    if value is not None and (type(value) is not int or value < 1):
        raise ValueError('执行预算必须为正整数或留空；预算不是研究范围')
    return value


@dataclass
class RunContext:
    db: DB
    cas: CAS
    settings: Settings
    llm: LLM
    skills: dict[str, Skill]
    project_id: str
    run_id: str
    registry: ToolRegistry = REGISTRY
    check_llm: LLM | None = None
    stage: str = ""
    cache: dict[str, Any] = field(default_factory=dict)

    @property
    def project(self) -> dict[str, Any]:
        p = self.db.project(self.project_id)
        assert p is not None
        return p

    def tool_ctx(self) -> ToolContext:
        return ToolContext(db=self.db, cas=self.cas, settings=self.settings, project_id=self.project_id,
                           run_id=self.run_id, stage=self.stage,
                           extra={'fetch_cache': self.cache.setdefault('fetch_cache', {})})

    def skill(self, name: str, task: dict[str, Any]) -> Any:
        ctx = self.tool_ctx()
        try:
            return run_skill(self.skills[name], task, self.llm, self.registry, ctx,
                             max_steps=self.settings.max_agent_steps)
        finally:
            self.cache['last_skill_source_ids'] = sorted((ctx.extra or {}).get('source_ids_read', set()))
