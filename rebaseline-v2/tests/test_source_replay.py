"""Focused regression family for the captured CT.gov source replay helper.

These tests use synthetic capture directories only; they never open the live
ciw-data database or CAS.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from ciw2.render.portal import data_c
from ciw2.store.db import DB, SCHEMA

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "replay_design_sources.py"
PROJECT_ID = "prj_replay_test"


def _load_helper():
    spec = importlib.util.spec_from_file_location("_ciw2_replay_design_sources_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


@pytest.fixture(scope="module")
def replay():
    return _load_helper()


MISSING = object()


def _study(
    nct: str,
    *,
    study_type: str = "INTERVENTIONAL",
    phases: tuple[str, ...] = ("PHASE2",),
    interventions: list[dict] | None = None,
    enrollment: object = 100,
    enrollment_type: str | None = "ACTUAL",
    primary_outcomes: list[dict] | None = None,
) -> dict:
    design = {
        "studyType": study_type,
        "phases": list(phases),
        "designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "DOUBLE"}},
    }
    if enrollment is MISSING:
        design["enrollmentInfo"] = {}
    else:
        design["enrollmentInfo"] = {"count": enrollment, "type": enrollment_type}
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": f"Study {nct}", "officialTitle": None},
            "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2020-01-01"}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Sponsor"}},
            "designModule": design,
            "conditionsModule": {"conditions": ["Atopic Dermatitis"]},
            "armsInterventionsModule": {
                "interventions": interventions if interventions is not None else [{"type": "DRUG", "name": "DrugA"}],
                "armGroups": [],
            },
            "eligibilityModule": {
                "minimumAge": "18 Years",
                "maximumAge": "65 Years",
                "sex": "ALL",
                "eligibilityCriteria": "Inclusion Criteria:\n- EASI >= 16",
            },
            "outcomesModule": {
                "primaryOutcomes": primary_outcomes if primary_outcomes is not None else [
                    {"measure": "EASI-75", "timeFrame": "Week 16", "description": "Proportion achieving EASI-75"}
                ],
                "secondaryOutcomes": [],
            },
        },
        "hasResults": False,
    }


def _put(root: Path, data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    path = root / digest[:2] / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest


def _capture(
    root: Path,
    *,
    source_id: str,
    document: dict,
    fetched_at: str,
    url: str,
    title: str = "captured search",
    text: bytes | None = None,
    published_date: str | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "ciw2.sqlite3"
    connection = sqlite3.connect(database)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute(
        "INSERT OR IGNORE INTO projects VALUES (?,?,?,?,?,?,?,?)",
        (PROJECT_ID, "特应性皮炎", "[]", '["C"]', "", "design precedent", None, "2026-01-01T00:00:00+00:00"),
    )
    raw = json.dumps(document, ensure_ascii=False).encode("utf-8")
    digest = _put(root / "cas", raw)
    text_digest = _put(root / "cas", text) if text is not None else digest
    connection.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)",
        (source_id, PROJECT_ID, "ctgov", url, title, digest, text_digest, published_date, fetched_at,
         json.dumps({"content_type": "application/json"})),
    )
    connection.commit()
    connection.close()


def _run(replay, tmp_path: Path) -> tuple[dict, Path]:
    source = tmp_path / "source"
    output = tmp_path / "output"
    receipt = replay.run_replay(source, PROJECT_ID, output)
    return receipt, output


def _output_source_rows(output: Path) -> list[dict]:
    connection = sqlite3.connect(output / "data" / "ciw2.sqlite3")
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute("SELECT * FROM sources ORDER BY id")]
    finally:
        connection.close()


def _output_facts(output: Path) -> list[dict]:
    connection = sqlite3.connect(output / "data" / "ciw2.sqlite3")
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        for row in connection.execute(
            "SELECT f.*, e.name AS trial FROM facts f JOIN entities e ON e.id=f.entity_id ORDER BY f.rowid"
        ):
            item = dict(row)
            item["value"] = json.loads(item["value"])
            item["context"] = json.loads(item["context"])
            rows.append(item)
        return rows
    finally:
        connection.close()


# ---------------------------------------------------------------- selection / container identity
def test_latest_capture_wins_and_facts_use_its_exact_container_locator(replay, tmp_path):
    old = _study("NCT00000001", enrollment=10)
    filler = _study("NCT00000002", enrollment=50)
    new = _study("NCT00000001", enrollment=99, phases=("PHASE3",))
    _capture(tmp_path / "source", source_id="src_old", document={"studies": [old]},
             fetched_at="2026-01-01T00:00:00+00:00", url="https://example.org/search?version=old")
    _capture(tmp_path / "source", source_id="src_new", document={"studies": [filler, new]},
             fetched_at="2026-02-01T00:00:00+00:00", url="https://example.org/search?version=new")

    receipt, output = _run(replay, tmp_path)

    trial = next(item for item in receipt["selection"]["trials"] if item["nct"] == "NCT00000001")
    assert trial["captured_source_id"] == "src_new"
    assert trial["container_locator"] == "$.studies[1]"
    assert trial["enrollment"] == 99
    assert trial["phase"] == "phase3"
    assert receipt["source_snapshot"]["unique_ncts"] == 2
    assert receipt["source_snapshot"]["superseded_bindings"] == 1

    facts = _output_facts(output)
    sample = next(f for f in facts if f["trial"] == "NCT00000001" and f["field"] == "design.sample_size")
    assert sample["value"] == 99
    assert sample["context"]["json_path"] == (
        "$.studies[1].protocolSection.designModule.enrollmentInfo.count"
    )
    assert sample["context"]["container_locator"] == "$.studies[1]"
    assert sample["context"]["captured_source_id"] == "src_new"
    assert sample["source_id"] == trial["isolated_source_id"]

    urls = {row["url"] for row in _output_source_rows(output)}
    assert urls == {"https://example.org/search?version=new"}


def test_equal_fetch_times_use_source_id_as_deterministic_tie_break(replay, tmp_path):
    _capture(tmp_path / "source", source_id="src_aaa", document={"studies": [_study("NCT00000003", enrollment=1)]},
             fetched_at="2026-03-01T00:00:00+00:00", url="https://example.org/search?version=aaa")
    _capture(tmp_path / "source", source_id="src_zzz", document={"studies": [_study("NCT00000003", enrollment=2)]},
             fetched_at="2026-03-01T00:00:00+00:00", url="https://example.org/search?version=zzz")

    receipt, _ = _run(replay, tmp_path)
    trial = receipt["selection"]["trials"][0]
    assert trial["captured_source_id"] == "src_zzz"
    assert trial["enrollment"] == 2


def test_single_study_capture_uses_root_locator(replay, tmp_path):
    _capture(tmp_path / "source", source_id="src_single", document=_study("NCT00000020", enrollment=77),
             fetched_at="2026-04-01T00:00:00+00:00",
             url="https://clinicaltrials.gov/api/v2/studies/NCT00000020")

    receipt, output = _run(replay, tmp_path)
    trial = receipt["selection"]["trials"][0]
    assert trial["container_locator"] == "$"
    fact = next(f for f in _output_facts(output) if f["field"] == "design.sample_size")
    assert fact["context"]["json_path"] == "$.protocolSection.designModule.enrollmentInfo.count"
    source = _output_source_rows(output)[0]
    metadata = json.loads(source["meta"])
    assert metadata["capture_kind"] == "ctgov_single_study"
    assert metadata["per_nct_fetch"] is True
    assert receipt["critical_verification"]["mismatch"] == 0


# ---------------------------------------------------------------- missing vs zero
def test_missing_enrollment_is_unknown_while_zero_stays_zero(replay, tmp_path):
    _capture(
        tmp_path / "source",
        source_id="src_edge",
        document={"studies": [
            _study("NCT00000010", enrollment=MISSING, primary_outcomes=[]),
            _study("NCT00000011", enrollment=0, primary_outcomes=[]),
        ]},
        fetched_at="2026-05-01T00:00:00+00:00",
        url="https://example.org/search?edge=enrollment",
    )

    receipt, output = _run(replay, tmp_path)
    facts = _output_facts(output)
    missing = next(f for f in facts if f["trial"] == "NCT00000010" and f["field"] == "design.sample_size")
    zero = next(f for f in facts if f["trial"] == "NCT00000011" and f["field"] == "design.sample_size")
    assert missing["value"] is None and missing["status"] == "unknown"
    assert zero["value"] == 0 and zero["status"] == "verified"

    data = data_c(DB(output / "data" / "ciw2.sqlite3"), receipt["render"]["project_id"])
    rows = {row["trial"]: row for row in data["rows"]}
    assert rows["NCT00000010"]["sample_size"] is None
    assert rows["NCT00000011"]["sample_size"] == 0
    assert data["charts"]["size"]["values"] == [0]
    assert receipt["critical_verification"]["unknown"] == 1
    assert receipt["critical_verification"]["match"] == 1
    assert receipt["critical_verification"]["mismatch"] == 0
    limitations = {item["kind"]: item["count"] for item in receipt["parser_limitations"]}
    assert limitations["missing_enrollment"] == 1
    assert missing["quote"] is None


# ---------------------------------------------------------------- lineage / byte copy / refusal
def test_source_lineage_preserves_url_time_meta_and_copies_both_cas_objects(replay, tmp_path):
    text = b"plain text rendition of the captured search container"
    _capture(
        tmp_path / "source",
        source_id="src_lineage",
        document={"studies": [_study("NCT00000030", enrollment=123)]},
        fetched_at="2026-06-01T12:34:56+00:00",
        url="https://clinicaltrials.gov/api/v2/studies?pageSize=100&query.cond=Atopic+Dermatitis",
        title="search {'query.cond': 'Atopic Dermatitis'}",
        text=text,
        published_date="2025-05-01",
    )

    receipt, output = _run(replay, tmp_path)
    source = _output_source_rows(output)[0]
    metadata = json.loads(source["meta"])
    assert source["url"] == "https://clinicaltrials.gov/api/v2/studies?pageSize=100&query.cond=Atopic+Dermatitis"
    assert source["fetched_at"] == "2026-06-01T12:34:56+00:00"
    assert source["published_date"] == "2025-05-01"
    assert metadata["capture_kind"] == "ctgov_studies_array"
    assert metadata["per_nct_fetch"] is False
    assert metadata["replay_of_source_id"] == "src_lineage"
    assert metadata["replay_of_project_id"] == PROJECT_ID
    assert metadata["captured_at"] == "2026-06-01T12:34:56+00:00"
    assert metadata["container_locators"] == ["$.studies[0]"]

    raw_digest = source["digest"]
    text_digest = source["text_digest"]
    raw_path = output / "data" / "cas" / raw_digest[:2] / raw_digest
    text_path = output / "data" / "cas" / text_digest[:2] / text_digest
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == raw_digest
    assert hashlib.sha256(text_path.read_bytes()).hexdigest() == text_digest
    assert text_path.read_bytes() == text
    assert raw_path.read_bytes() != text_path.read_bytes()

    fact = _output_facts(output)[0]
    assert fact["source_id"] == source["id"]
    assert receipt["copied_sources"][0]["raw_sha256"] == raw_digest
    assert receipt["copied_sources"][0]["text_sha256"] == text_digest

    for key in ("parser", "render_portal", "render_design"):
        assert len(receipt["files"][key]["sha256"]) == 64
    assert len(receipt["render"]["html_sha256"]) == 64
    assert receipt["render"]["rows"] == 1
    assert (output / "portal-C.html").is_file()
    assert (output / "receipt.json").is_file()


def test_existing_output_directory_is_refused_without_overwrite(replay, tmp_path):
    _capture(tmp_path / "source", source_id="src_refuse", document={"studies": [_study("NCT00000040")]},
             fetched_at="2026-07-01T00:00:00+00:00", url="https://example.org/search?refuse=1")
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("owner data", encoding="utf-8")

    with pytest.raises(replay.ReplayError, match="already exists"):
        replay.run_replay(tmp_path / "source", PROJECT_ID, output)
    assert sentinel.read_text(encoding="utf-8") == "owner data"
    assert not (output / "data").exists()
    assert list(output.iterdir()) == [sentinel]


# ---------------------------------------------------------------- scope / no Top-N
def test_scope_is_explicit_and_all_qualifying_trials_are_kept(replay, tmp_path):
    _capture(
        tmp_path / "source",
        source_id="src_scope",
        document={"studies": [
            _study("NCT00000050", phases=("PHASE2",)),
            _study("NCT00000051", phases=("PHASE1", "PHASE2")),
            _study("NCT00000052", phases=("PHASE2",), interventions=[{"type": "BIOLOGICAL", "name": "BioX"}]),
            _study("NCT00000053", study_type="OBSERVATIONAL", phases=("PHASE2",)),
            _study("NCT00000054", phases=("PHASE1",)),
            _study("NCT00000055", phases=("PHASE4",)),
            _study("NCT00000056", phases=("PHASE2",), interventions=[{"type": "DRUG", "name": "Placebo"}]),
        ]},
        fetched_at="2026-08-01T00:00:00+00:00",
        url="https://example.org/search?scope=1",
    )

    receipt, output = _run(replay, tmp_path)
    included = {item["nct"] for item in receipt["selection"]["trials"]}
    assert included == {"NCT00000050", "NCT00000051", "NCT00000052"}
    assert receipt["selection"]["counts"]["top_n_applied"] is False
    assert receipt["selection"]["counts"]["included"] == 3
    assert receipt["selection"]["counts"]["excluded"] == 4
    reasons = receipt["selection"]["excluded_by_reason"]
    assert reasons["study_type_not_interventional"] == 1
    assert reasons["phase_not_2_or_3"] == 2
    assert reasons["no_qualifying_drug_or_biological_intervention"] == 1

    connection = sqlite3.connect(output / "data" / "ciw2.sqlite3")
    try:
        drugs = {row[0] for row in connection.execute("SELECT name FROM entities WHERE type='drug'")}
    finally:
        connection.close()
    assert drugs == {"DrugA", "BioX"}


# ---------------------------------------------------------------- exact verification, not quote substring
def test_critical_verification_compares_exact_source_type_and_value(replay):
    study = _study("NCT00000060", enrollment=100, primary_outcomes=[])
    document = {"studies": [study]}
    locator = "$.studies[0]"
    path = locator + ".protocolSection.designModule.enrollmentInfo.count"

    def fact(value, quote):
        return {"id": "f_test", "field": "design.sample_size", "tier": "critical", "status": "verified",
                "value": value, "quote": quote, "context": {"json_path": path}}

    wrong_value = replay.verify_facts(document, locator, "NCT00000060", [fact(1001, "1001")])
    assert wrong_value["checked"] == 1 and wrong_value["mismatch"] == 1
    wrong_type = replay.verify_facts(document, locator, "NCT00000060", [fact("100", "100")])
    assert wrong_type["mismatch"] == 1
    exact = replay.verify_facts(document, locator, "NCT00000060", [fact(100, "100")])
    assert exact["match"] == 1 and exact["mismatch"] == 0

    wrong_identity = replay.verify_facts(document, locator, "NCT99999999", [fact(100, "100")])
    assert wrong_identity["identity"]["mismatch"] == 1
    assert wrong_identity["mismatch"] == 1


def test_failed_materialization_keeps_partial_output_and_failure_receipt(replay, tmp_path, monkeypatch):
    _capture(tmp_path / 'source', source_id='src_fail', document={'studies': [_study('NCT00000070')]},
             fetched_at='2026-01-01T00:00:00+00:00', url='https://example.org/capture')

    def fail(source, project, output, *args):
        (output / 'partial.json').write_text('{"retained": true}')
        raise replay.ReplayError('controlled output failure')

    monkeypatch.setattr(replay, '_materialize', fail)
    with pytest.raises(replay.ReplayError, match='controlled output failure'):
        _run(replay, tmp_path)
    assert json.loads((tmp_path / 'output/partial.json').read_text()) == {'retained': True}
    assert json.loads((tmp_path / 'output/FAILED.json').read_text())['status'] == 'FAILED'


def test_unavailable_readonly_connection_reports_original_failure(replay, tmp_path, monkeypatch):
    _capture(tmp_path / 'source', source_id='src_fail', document={'studies': [_study('NCT00000070')]},
             fetched_at='2026-01-01T00:00:00+00:00', url='https://example.org/capture')

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('controlled readonly open failure')

    monkeypatch.setattr(replay.sqlite3, 'connect', unavailable)
    with pytest.raises(replay.ReplayError, match='controlled readonly open failure'):
        _run(replay, tmp_path)
