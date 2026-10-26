"""Workbench presentation contract on real rendered GET pages.

Runs against an isolated temporary database and a scripted offline LLM, so the
file is portable and never reads ciw-data. It asserts user-facing Chinese
labels, preserved form/action inputs, and complete diagnostics that stay
reachable in expandable areas. It is not a visual, keyboard or clinical
acceptance; Codex owns the four-width rendered review.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.runner import stages_for
from ciw2.pipeline.stages import STAGES
from ciw2.web.app import create_app

REPORT_NAMES = {"A": "竞争格局", "B": "疗效与安全性", "C": "试验设计先例"}
STAGE_LABELS = {
    "intake": "需求理解",
    "universe_china": "中国竞品检索",
    "universe_global": "全球竞品检索",
    "candidate_triage": "候选初筛",
    "universe_expand": "竞品范围扩展",
    "coverage_review": "检索覆盖复核",
    "trial_evidence": "试验证据采集",
    "trial_scope_review": "试验范围复核",
    "enrich_drugs": "药物资料补充",
    "extract_results": "疗效与安全性提取",
    "extract_design": "试验设计提取",
    "verify": "事实核验",
    "analysis_A": "竞争格局分析",
    "analysis_B": "疗效与安全性分析",
    "analysis_C": "试验设计先例分析",
    "render": "报告生成",
}


@pytest.fixture
def app(settings):
    return create_app(settings, llm_factory=lambda s: (ScriptedLLM([]), None), background=False)


@pytest.fixture
def client(app):
    return TestClient(app)


def _project(client, indication: str = "特应性皮炎", reports: tuple[str, ...] = ("A", "B", "C")) -> str:
    response = client.post("/api/projects", json={
        "indication": indication, "reports": list(reports), "start": False})
    assert response.status_code == 200, response.text
    return response.json()["project_id"]


def _complete_run(app, pid: str) -> str:
    db = app.state.svc.db
    rid = db.create_run(pid)
    for stage in STAGES:
        db.set_stage(rid, stage.name, "succeeded")
    db.set_run(rid, "succeeded")
    return rid


def _seed_entities(app, pid: str) -> None:
    db = app.state.svc.db
    db.upsert_entity(pid, "drug", "Drug One")
    db.upsert_entity(pid, "drug", "Drug Two")
    db.upsert_entity(pid, "trial", "NCT00000001")
    for name in ("Company One", "Company Two", "Company Three"):
        db.upsert_entity(pid, "company", name)


def test_index_renders_brand_runtime_and_explicit_chinese_form(client, app):
    pid = _project(client, "特应性皮炎", ("A", "C"))
    _complete_run(app, pid)
    html = client.get("/").text

    assert 'src="/static/logo_bot.svg"' in html and 'alt="康哲药业"' in html
    for asset in ("kz-tokens.css", "kangzhe.css", "workbench.css"):
        assert f'href="/static/{asset}"' in html
    for script in ("kz-motion.js", "kz-site.js"):
        assert f'src="/static/{script}"' in html
    assert client.get("/static/workbench.css").status_code == 200

    for name in ("indication", "reports", "request_text", "focus", "cutoff_date"):
        assert f'name="{name}"' in html, name
    for name in ("indication", "request_text", "focus", "cutoff_date"):
        assert f'for="wb-{name}"' in html and f'id="wb-{name}"' in html, name
    assert 'id="wb-cutoff_date"' in html and 'disabled' in re.search(r'<input[^>]*id="wb-cutoff_date"[^>]*>', html).group(0)
    for code in "ABC":
        tag = re.search(rf'<input[^>]*id="wb-report-{code.lower()}"[^>]*>', html).group(0)
        assert 'type="checkbox"' in tag and 'name="reports"' in tag and f'value="{code}"' in tag
        assert f'for="wb-report-{code.lower()}"' in html
    assert 'id="wb-report-a" type="checkbox" name="reports" value="A" checked' in html

    assert "特应性皮炎" in html and "已完成" in html
    for name in REPORT_NAMES.values():
        assert name in html
    assert "A 竞争格局 · C 试验设计先例" in html
    assert "&#34;" not in html
    assert "['A'" not in html and "succeeded" not in html


def test_index_empty_state_is_intentional(client):
    html = client.get("/").text
    assert "还没有项目" in html and "新建调研" in html
    assert "<tbody></tbody>" not in html


def test_project_page_leads_with_reports_counts_and_readable_stages(client, app):
    pid = _project(client)
    db = app.state.svc.db
    _seed_entities(app, pid)
    rid = db.create_run(pid)
    for stage in STAGES:
        db.set_stage(rid, stage.name, "succeeded")
    db.set_run(rid, "succeeded")
    db.log_coverage(rid, "global:ctgov:condition", "global", "atopic dermatitis", "ok", hits=4)
    html = client.get(f"/projects/{pid}").text

    counts = html.split('class="wb-counts"', 1)[1].split("</section>", 1)[0]
    assert re.search(r"<b>2</b><span>药物</span>", counts)
    assert re.search(r"<b>1</b><span>试验</span>", counts)
    assert re.search(r"<b>3</b><span>企业</span>", counts)

    for code in "ABC":
        assert f'href="/projects/{pid}/portal/{code}"' in html
    assert f'href="/api/projects/{pid}/facts/export?format=json"' in html
    assert f'href="/api/projects/{pid}/facts/export?format=csv"' in html

    total = len(stages_for(["A", "B", "C"]))
    assert f"已完成 {total} / {total} 个阶段" in html
    for stage in STAGES:
        assert STAGE_LABELS[stage.name] in html, stage.name
        assert f">{stage.name}<" not in html, stage.name
    assert html.index(f'href="/projects/{pid}/portal/A"') < html.index("运行诊断与来源覆盖")


def test_failed_run_is_uncompleted_and_keeps_full_diagnostics(client, app):
    pid = _project(client, "银屑病")
    db = app.state.svc.db
    rid = db.create_run(pid)
    db.set_stage(rid, "intake", "succeeded")
    stage_error = "阶段错误：" + "原始响应片段" * 40 + "阶段末尾标记KZ9"
    db.set_stage(rid, "universe_china", "failed", error=stage_error)
    run_error = "运行失败：<script>alert(1)</script>" + "诊断细节" * 60 + "运行末尾标记KZ9"
    db.set_run(rid, "failed", error=run_error)
    db.log_coverage(rid, "china:chinadrugtrials:condition", "china", "银屑病", "blocked")
    html = client.get(f"/projects/{pid}").text

    assert "失败" in html and 'role="alert"' in html
    assert "阶段末尾标记KZ9" in html and "运行末尾标记KZ9" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html

    assert f'action="/projects/{pid}/runs"' in html
    assert 'name="resume_run"' in html and f'value="{rid}"' in html
    assert "从失败处继续" in html

    diagnostics = re.search(r'<details[^>]*class="[^"]*wb-diagnostics[^"]*"[^>]*>', html).group(0)
    assert " open" not in diagnostics
    assert "运行诊断与来源覆盖" in html
    assert html.index("china:chinadrugtrials:condition") > html.index("运行诊断与来源覆盖")
    assert f'href="/api/runs/{rid}/steps"' in html


def test_running_run_names_the_current_stage_without_a_fake_percentage(client, app):
    pid = _project(client, "慢性荨麻疹", ("A",))
    db = app.state.svc.db
    rid = db.create_run(pid)
    db.set_stage(rid, "intake", "succeeded")
    db.set_stage(rid, "universe_china", "running")
    db.set_run(rid, "running")
    html = client.get(f"/projects/{pid}").text
    run_card = html.split('class="card wb-run"', 1)[1].split("</section>", 1)[0]
    assert "已完成 1 / " in run_card and "当前 中国竞品检索" in run_card
    assert "%" not in run_card
    assert f'action="/projects/{pid}/runs/{rid}/cancel"' in run_card


def test_queued_run_keeps_stop_action_and_plain_language(client, app):
    pid = _project(client, "慢性荨麻疹", ("A",))
    rid = app.state.svc.db.create_run(pid)
    html = client.get(f"/projects/{pid}").text
    assert "排队中" in html
    assert f'action="/projects/{pid}/runs/{rid}/cancel"' in html
    assert ">停止</button>" in html
