"""SKILL.md 加载器。

格式：
---
name: universe-china
description: 一句话说明
tools: [ctgov_search, web_search]
output: UniverseResult          # ciw2.domain.models 中的模型名
max_steps: 20
---
正文 = 该 Skill 的工作说明（作为 system prompt 的一部分）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel

from ciw2.domain import models as domain_models


@dataclass
class Skill:
    name: str
    description: str
    body: str
    tools: list[str] = field(default_factory=list)
    output: type[BaseModel] | None = None
    max_steps: int = 20
    path: Path | None = None


class SkillError(ValueError):
    pass


def parse_skill(text: str, path: Path | None = None) -> Skill:
    if not text.startswith("---"):
        raise SkillError(f"{path}: 缺少 frontmatter")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    for key in ("name", "description"):
        if not meta.get(key):
            raise SkillError(f"{path}: frontmatter 缺少 {key}")
    output_name = meta.get("output")
    output = None
    if output_name:
        output = getattr(domain_models, output_name, None)
        if not (isinstance(output, type) and issubclass(output, BaseModel)):
            raise SkillError(f"{path}: 未知输出模型 {output_name}")
    return Skill(
        name=meta["name"], description=meta["description"], body=body.strip(),
        tools=list(meta.get("tools") or []), output=output,
        max_steps=int(meta.get("max_steps") or 20), path=path,
    )


def load_skills(root: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for p in sorted(root.glob("*/SKILL.md")):
        s = parse_skill(p.read_text(encoding="utf-8"), p)
        if s.name in skills:
            raise SkillError(f"Skill 重名：{s.name}")
        skills[s.name] = s
    return skills
