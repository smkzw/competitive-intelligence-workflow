"""CDE 登记平台采集解析（夹具为 2026-10-27 真实采集，含两页列表与两份详情）。"""

import shutil
from pathlib import Path

from ciw.pipeline import run
from ciw.release import load_release
from ciw.sources.cde_registry import _phase, _status, ingest

FIX = Path(__file__).resolve().parent / "fixtures" / "cde"


def _seed(ws):
    d = ws.root / "captures" / "cde"
    d.mkdir(parents=True, exist_ok=True)
    for f in FIX.glob("*.json"):
        name = f.name if f.name.startswith("detail-") else "list-crswnp-2026-10-27.json"
        shutil.copy(f, d / name)


def test_detail_parses_to_trial_with_explicit_roles(cfg, resolver, ws):
    _seed(ws)
    trials, cov = ingest(ws, cfg, resolver)
    t = {x.trial_id: x for x in trials}["CTR20221480"]
    assert (t.registry, t.phase, t.phase_rank, t.china) == ("cde", "III", 4, True)
    assert t.product_ids == ["stapokibart"] and t.relevance == "core"
    roles = {a.role for a in t.arms}
    assert {"experimental", "placebo"} <= roles
    assert t.design.enrollment == 180
    assert any(o.concept_id == "nps" for o in t.outcomes_planned if o.kind == "primary")
    assert cov["source"] == "cde" and cov["lists"][0]["complete"] is True


def test_biosimilar_and_active_comparator(cfg, resolver, ws):
    _seed(ws)
    t = {x.trial_id: x for x in ingest(ws, cfg, resolver)[0]}["CTR20221879"]
    comp = [a for a in t.arms if a.role == "active_comparator"]
    assert comp and all("mepolizumab" in a.product_ids for a in comp)
    assert "bat2606" in t.product_ids


def test_list_only_rows_keep_registry_identity(cfg, resolver, ws):
    _seed(ws)
    trials, cov = ingest(ws, cfg, resolver)
    assert cov["list_only"] > 0
    lo = [t for t in trials if t.locator.path.startswith("row:")]
    assert all(t.trial_id.startswith("CTR") and t.china for t in lo)


def test_status_and_phase_mapping():
    assert _status("进行中 招募中") == "RECRUITING" and _status("已完成") == "COMPLETED"
    assert _status("进行中 尚未招募") == "NOT_YET_RECRUITING"
    assert _phase("Ⅲ期") == ("III", 4) and _phase("其它其他说明:生物等效性研究") == ("其他", 0)


def test_pipeline_includes_cde_and_moves_biosimilar_out_of_universe(cfg, seeded_ws):
    _seed(seeded_ws)
    doc = load_release(run(cfg, seeded_ws, offline=True, log=lambda *_: None).release_path)
    cov = {c["source"]: c["status"] for c in doc["coverage"]}
    assert cov["cde"] in ("ok", "partial")
    ids = {p["product_id"] for p in doc["a"]["products"]}
    assert "stapokibart" in ids and "bat2606" not in ids
    assert "bat2606" in {p["product_id"] for p in doc["a"]["non_innovative"]}
    sta = next(p for p in doc["a"]["products"] if p["product_id"] == "stapokibart")
    assert sta["china_rank"] >= 4
