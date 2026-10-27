"""离线端到端：夹具 → CAS → 流水线 → release → 门户。"""

import json
import re

from ciw.pipeline import run
from ciw.release import load_release


def _run(cfg, ws):
    return run(cfg, ws, offline=True, log=lambda *_: None)


def test_offline_run_produces_valid_release_and_sites(cfg, seeded_ws):
    res = _run(cfg, seeded_ws)
    doc = load_release(res.release_path)  # schema 校验在 load 内
    assert doc["stats"]["trials_core"] == 5
    assert {c["source"]: c["status"] for c in doc["coverage"]}["cde"] == "not_captured"
    for rep in "ABC":
        html = (res.site_dir / rep / "index.html").read_text(encoding="utf-8")
        assert "data.js" in html and (res.site_dir / rep / "echarts.min.js").exists()
    assert seeded_ws.current_release_dir().name == res.release_id


def test_release_id_is_content_addressed(cfg, seeded_ws):
    a = _run(cfg, seeded_ws).release_id
    b = _run(cfg, seeded_ws).release_id
    assert a == b


def _question(doc, concept, tkey, kind, sub=""):
    return next(
        q
        for q in doc["b"]["questions"]
        if q["concept_id"] == concept and q["time_key"] == tkey and q["measure_kind"] == kind and q["subgroup"] == sub
    )


def test_nps_week24_comparisons_use_reported_analyses(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    q = _question(doc, "nps", "W24", "ls_mean")
    by = {(c["acronym"], c["kind"]): c for c in q["comparisons"]}
    sinus = by[("SINUS-52", "reported")]
    assert (sinus["value"], sinus["ci_lower"], sinus["ci_upper"]) == (-1.8, -2.1, -1.51)
    assert sinus["note"] == ""  # 方向已由组均值确定：试验−对照
    polyp = by[("POLYP 1", "reported")]
    assert polyp["value"] == -1.14
    # 亚组不进入总体问题，也不在总体问题里生成计算差值
    assert {r["acronym"] for r in q["rows"]}.isdisjoint({""}) and len(
        [r for r in q["rows"] if r["acronym"] == "SINUS-52"]
    ) == 2
    assert ("SINUS-52", "computed") not in by


def test_reported_analysis_wins_and_computed_is_same_trial_only(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    q = _question(doc, "nps", "W52", "ls_mean")
    way = next(c for c in q["comparisons"] if c["acronym"] == "WAYPOINT")
    assert (way["kind"], way["value"], way["ci_lower"]) == ("reported", -2.078, -2.399)
    for q in doc["b"]["questions"]:
        reported = {(c["result_id"], c["exp_group"]) for c in q["comparisons"] if c["kind"] == "reported"}
        for c in (c for c in q["comparisons"] if c["kind"] == "computed"):
            assert (c["result_id"], c["exp_group"]) not in reported and c["ci_lower"] is None
            rows = [r for r in q["rows"] if r["result_id"] == c["result_id"]]
            exp = next(r for r in rows if r["group_title"] == c["exp_group"])
            pbo = next(r for r in rows if r["role"] == "placebo")
            assert abs(c["value"] - (exp["value"] - pbo["value"])) < 1e-6


def test_head_to_head_orientation(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    q = _question(doc, "nps", "W24", "ls_mean")
    ev = next(c for c in q["comparisons"] if c["acronym"] == "EVEREST")
    assert ev["h2h"] and ev["product_id"] == "dupilumab" and ev["value"] < 0


def test_safety_table_uses_counts_and_threshold(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    row = next(r for r in doc["b"]["safety"] if r["acronym"] == "SINUS-52" and r["role"] == "placebo")
    assert (row["sae_n"], row["N"], row["sae_pct"], row["other_threshold"]) == (16, 150, 10.7, 5.0)
    assert (row["disc_n"], row["disc_N"]) == (4, 153)
    assert not any(r["group_title"] == "Run-in Period" for r in doc["b"]["safety"])


def test_landscape_and_own_product(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    rows = {p["product_id"]: p for p in doc["a"]["products"]}
    assert doc["a"]["products"][0]["product_id"] == "mg-k10"  # 本品置顶，即使暂无登记
    assert rows["dupilumab"]["global_phase"] == "IV（上市后）"  # EVEREST 为 IV 期
    assert rows["tezepelumab"]["global_phase"] == "III"


def test_portal_payload_has_no_internal_keys_or_local_paths(cfg, seeded_ws):
    res = _run(cfg, seeded_ws)
    for rep in "ABC":
        text = (res.site_dir / rep / "data.js").read_text(encoding="utf-8")
        assert "/Users/" not in text
    html = (res.site_dir / "B" / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"\b(registry_observation|fact_id|candidate|accepted)\b", html)


def test_design_matrix_keeps_full_eligibility(cfg, seeded_ws):
    doc = load_release(_run(cfg, seeded_ws).release_path)
    row = next(r for r in doc["c"]["rows"] if r["acronym"] == "SINUS-52")
    assert row["masking"] == "四盲" and row["enrollment"] == 448 and "Inclusion" in row["eligibility"]
    assert json.dumps(row["primary"], ensure_ascii=False).count("title") >= 2


def test_audit_sample_matches_source(cfg, seeded_ws):
    from ciw.audit import audit

    _run(cfg, seeded_ws)
    out = audit(seeded_ws, n=40)
    assert out["sampled"] == 40 and out["errors"] == []
