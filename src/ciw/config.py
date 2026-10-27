"""适应症配置。一个适应症的全部差异只写在 indications/<slug>.yaml，不写进 Python。"""

from __future__ import annotations

import re
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductCfg(_Cfg):
    id: str
    name_en: str
    name_zh: str = ""  # 只填已核实的正式中文名；未核实留空，门户显示 INN/代号
    aliases: list[str] = Field(default_factory=list)
    brand: str = ""
    target: str = ""
    mechanism: str = ""
    modality: str = ""
    route: str = ""
    company: str = ""
    china_partner: str = ""
    innovative: bool | None = True
    own: bool = False
    note: str = ""

    def all_names(self) -> list[str]:
        return [self.name_en, *self.aliases, *([self.name_zh] if self.name_zh else [])]


class ConceptCfg(_Cfg):
    id: str
    label: str
    patterns: list[str]
    exclude: list[str] = Field(default_factory=list)
    direction: Literal["lower_better", "higher_better", "none"] = "none"
    domain: Literal["efficacy", "pd", "other"] = "efficacy"

    @cached_property
    def _rx(self) -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
        return ([re.compile(p, re.I) for p in self.patterns], [re.compile(p, re.I) for p in self.exclude])

    def matches(self, text: str) -> bool:
        inc, exc = self._rx
        return any(r.search(text) for r in inc) and not any(r.search(text) for r in exc)


class CtgovCfg(_Cfg):
    conditions: list[str]
    relevance_patterns: list[str]
    relevance_exclude_patterns: list[str] = Field(default_factory=list)
    extra_intervention_queries: list[str] = Field(default_factory=list)


class ChinaCfg(_Cfg):
    cde_queries: list[str] = Field(default_factory=list)
    nmpa_queries: list[str] = Field(default_factory=list)
    wechat_accounts: list[str] = Field(default_factory=list)
    wechat_queries: list[str] = Field(default_factory=list)


class DesignTopicCfg(_Cfg):
    label: str
    patterns: list[str]

    @field_validator("patterns")
    @classmethod
    def _patterns(cls, values):
        for pattern in values:
            try:
                re.compile(pattern, re.I)
            except re.error as exc:
                raise ValueError("design_topics包含无效匹配表达式") from exc
        return values


class IndicationConfig(_Cfg):
    slug: str
    name_zh: str
    name_en: str
    abbr: str = ""
    cutoff: date | None = None
    ctgov: CtgovCfg
    china: ChinaCfg = Field(default_factory=ChinaCfg)
    products: list[ProductCfg]
    background_patterns: list[str] = Field(default_factory=list)
    concepts: list[ConceptCfg] = Field(default_factory=list)
    design_topics: list[DesignTopicCfg] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", v):
            raise ValueError("slug 只能包含小写字母、数字和连字符")
        return v

    @model_validator(mode="after")
    def _check(self) -> IndicationConfig:
        ids = [p.id for p in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("products.id 重复")
        if sum(p.own for p in self.products) > 1:
            raise ValueError("最多一个本品（own: true）")
        seen: dict[str, str] = {}
        for p in self.products:
            for name in p.all_names():
                key = normalize_name(name)
                if key in seen and seen[key] != p.id:
                    raise ValueError(f"别名 {name!r} 同时属于 {seen[key]} 和 {p.id}")
                seen[key] = p.id
        cids = [c.id for c in self.concepts]
        if len(cids) != len(set(cids)):
            raise ValueError("concepts.id 重复")
        return self

    @property
    def own_product_id(self) -> str | None:
        return next((p.id for p in self.products if p.own), None)

    @cached_property
    def _relevance_rx(self) -> list[re.Pattern[str]]:
        return [re.compile(p, re.I) for p in self.ctgov.relevance_patterns]

    def is_relevant_text(self, text: str) -> bool:
        # Remove explicit nonmatching phrases, not whole mixed-population records.
        for pattern in self.ctgov.relevance_exclude_patterns:
            text = re.sub(pattern, "", text, flags=re.I)
        return any(r.search(text) for r in self._relevance_rx)

    @cached_property
    def _background_rx(self) -> list[re.Pattern[str]]:
        return [re.compile(p, re.I) for p in self.background_patterns]

    def is_background(self, name: str) -> bool:
        return any(r.search(name) for r in self._background_rx)


def normalize_name(name: str) -> str:
    s = name.casefold()
    s = re.sub(r"[®™()\[\]（）]", " ", s)
    s = re.sub(r"[^0-9a-z一-鿿]+", "", s)
    return s


def load_indication(path: str | Path) -> IndicationConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return IndicationConfig.model_validate(data)
