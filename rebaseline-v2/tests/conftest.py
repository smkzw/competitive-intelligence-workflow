from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ciw2.config import Settings
from ciw2.harness.llm import LLMReply, ToolCall

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ctgov_NCT03985943_trimmed.json"
PAPER_URL = "https://example.org/paper-arcadia"
PAPER_TEXT = ("In ARCADIA 1, at week 16, IGA success was achieved by 35.6% of patients in the nemolizumab group "
              "versus 24.6% in the placebo group. Serious adverse events occurred in 1.3% of patients.")


@pytest.fixture
def study() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", skills_dir=ROOT / "skills", llm_api_key="test")


@pytest.fixture
def offline_ctgov(monkeypatch: pytest.MonkeyPatch, study: dict[str, Any]) -> None:
    """CT.gov 与网页抓取全部离线。"""
    from ciw2.sources import ctgov, http

    def fake_search(ctx: Any, **kw: Any) -> list[dict[str, Any]]:
        return [ctgov.parse_study(study)]

    def fake_get(ctx: Any, nct: str) -> tuple[dict[str, Any], str | None]:
        sid = http.register_text(ctx, kind="ctgov", url=f"{ctgov.API}/{nct}", text=json.dumps(study)) if ctx else None
        return study, sid

    monkeypatch.setattr(ctgov, "search", fake_search)
    monkeypatch.setattr(ctgov, "get_study", fake_get)
    # All discovery/expansion integration tests stay offline, including China fallbacks.
    from ciw2.sources import china

    def blocked_china(*args, **kwargs):
        raise china.RegistryBlocked('Offline fixture: direct China source unavailable')

    monkeypatch.setattr(china, 'direct_search', blocked_china)


def _skill_of(messages: list[dict[str, Any]]) -> str:
    return messages[0]["content"].split("# Skill：", 1)[1].split("\n", 1)[0].strip()


def _submit(args: dict[str, Any]) -> LLMReply:
    return LLMReply(tool_calls=[ToolCall(id="s1", name="submit_result", arguments=args)])


def fake_llm_responder(messages: list[dict[str, Any]]) -> LLMReply:
    """按 Skill 返回预置结果，用于端到端测试。"""
    skill = _skill_of(messages)
    turns = sum(1 for m in messages if m["role"] == "assistant")
    if skill == "intake":
        return _submit({"indication": "特应性皮炎", "indication_en": "Atopic Dermatitis", "aliases": ["AD"],
                        "reports": ["A", "B", "C"], "focus": "IL-31 通路"})
    if skill in ("universe-china", "universe-global"):
        region = skill.split("-")[1]
        if turns == 0:
            return LLMReply(tool_calls=[ToolCall(id="t1", name="ctgov_search", arguments={
                "condition": "Atopic Dermatitis", "route_id": f"{region}:ctgov:condition", "region": region})])
        return _submit({"region": region, "routes_run": [f"{region}:ctgov:condition"], "candidates": [
            {"name": "nemolizumab", "name_zh": None, "aliases": ["CD14152"], "targets": ["IL-31RA"],
             "companies": ["Galderma"], "highest_phase_global": "approved", "highest_phase_china": "unknown",
             "evidence_urls": ["https://clinicaltrials.gov/study/NCT03985943"],
             "route_id": f"{region}:ctgov:condition"},
            {"name": "placebo-like-noise", "route_id": f"{region}:ctgov:condition"}]})
    if skill == "coverage-review":
        return _submit({"decisions": [{"drug": "nemolizumab", "in_scope": True, "reason": "IL-31RA 单抗"},
                                      {"drug": "placebo-like-noise", "in_scope": False, "reason": "非药物"}]})
    if skill == "extract-results":
        base = {"entity": "NCT03985943", "endpoint": "IGA success", "timepoint": "Week 16", "unit": "%",
                "stat_type": "proportion", "source_url": PAPER_URL}
        return _submit({"facts": [
            {**base, "field": "result.primary.value", "value": 35.6, "arm": "nemolizumab",
             "quote": "IGA success was achieved by 35.6% of patients in the nemolizumab group"},
            {**base, "field": "result.primary.value", "value": 41.2, "arm": "nemolizumab",
             "quote": "IGA success was achieved by 41.2% of patients"},          # 编造片段
            {**base, "field": "result.key_secondary.value", "value": 12.0, "arm": "nemolizumab",
             "source_url": "https://example.org/never-fetched", "quote": "12.0%"},  # 未读取来源
        ], "gaps": ["52 周维持期数据未在论文中找到"]})
    if skill == "extract-design":
        return _submit({"facts": [], "gaps": []})
    if skill.startswith("analysis-"):
        rep = skill[-1].upper()
        return _submit({"report": rep, "findings": [{"title": f"{rep} 要点", "bullets": ["示例"]}]})
    raise AssertionError(f"unexpected skill {skill}")
