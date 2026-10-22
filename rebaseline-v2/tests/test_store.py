from ciw2.store.cas import CAS
from ciw2.store.db import DB


def test_cas_roundtrip(tmp_path):
    cas = CAS(tmp_path)
    d = cas.put("原文".encode())
    assert cas.get_text(d) == "原文" and cas.put("原文".encode()) == d


def test_entity_merge_and_fact_supersede(tmp_path):
    db = DB(tmp_path / "x.sqlite3")
    pid = db.create_project("特应性皮炎", ["A"])
    e1, new1 = db.upsert_entity(pid, "drug", "nemolizumab", aliases=["CD14152"], route_id="r1")
    e2, new2 = db.upsert_entity(pid, "drug", "nemolizumab", name_zh="奈莫利珠单抗", aliases=["Nemluvio"], route_id="r2")
    assert e1 == e2 and new1 and not new2
    ent = db.entities(pid, "drug")[0]
    assert ent["aliases"] == ["CD14152", "Nemluvio"] and ent["found_by"] == ["r1", "r2"]
    f1 = db.add_fact({"project_id": pid, "entity_id": e1, "field": "design.sample_size", "value": 940,
                      "tier": "critical", "status": "unverified", "extracted_by": "llm:x"})
    db.add_fact({"project_id": pid, "entity_id": e1, "field": "design.sample_size", "value": 941,
                 "tier": "critical", "status": "verified", "extracted_by": "code:ctgov", "supersedes": f1})
    cur = db.current_facts(pid)
    assert [f["value"] for f in cur] == [941]
