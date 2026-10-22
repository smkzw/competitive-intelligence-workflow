from conftest import fake_llm_responder
from fastapi.testclient import TestClient

from ciw2.harness.llm import ScriptedLLM
from ciw2.web.app import create_app


def test_web_flow(settings, offline_ctgov):
    app = create_app(settings, llm_factory=lambda s: (ScriptedLLM(fake_llm_responder), None), background=False)
    c = TestClient(app)
    assert c.get("/").status_code == 200
    r = c.post("/api/projects", json={"indication": "特应性皮炎", "reports": ["A", "C"]})
    pid, rid = r.json()["project_id"], r.json()["run_id"]
    st = c.get(f"/api/runs/{rid}").json()
    assert st["status"] == "succeeded", st
    page = c.get(f"/projects/{pid}")
    assert page.status_code == 200 and "特应性皮炎" in page.text
    a = c.get(f"/projects/{pid}/portal/A")
    assert a.status_code == 200 and "nemolizumab" in a.text and "/static/echarts.min.js" in a.text
    assert c.get(f"/projects/{pid}/portal/B").status_code == 404
    assert c.get(f"/projects/{pid}/portal/C").status_code == 200
    facts = c.get(f"/api/projects/{pid}/facts", params={"field_prefix": "design."}).json()
    assert any(f["field"] == "design.sample_size" and f["value"] == 941 for f in facts)
    assert c.get("/static/kangzhe.css").status_code == 200
    r2 = c.post("/projects", data={"indication": "银屑病", "reports": ["A"]}, follow_redirects=False)
    assert r2.status_code == 303


def test_access_token(settings, offline_ctgov, monkeypatch):
    monkeypatch.setenv("CIW_ACCESS_TOKEN", "s3cret")
    app = create_app(settings, llm_factory=lambda s: (ScriptedLLM(fake_llm_responder), None), background=False)
    c = TestClient(app)
    assert c.get("/").status_code == 401
    assert c.get("/", params={"token": "s3cret"}).status_code == 200
    assert c.get("/").status_code == 200   # cookie 生效


def test_missing_llm_key_fails_run_cleanly(settings):
    from dataclasses import replace
    app = create_app(replace(settings, llm_api_key=""), background=False)
    c = TestClient(app)
    r = c.post("/api/projects", json={"indication": "x", "reports": ["A"]})
    assert r.status_code == 200
    st = c.get(f"/api/runs/{r.json()['run_id']}").json()
    assert st["status"] == "failed" and "CIW_LLM_API_KEY" in st["error"]
