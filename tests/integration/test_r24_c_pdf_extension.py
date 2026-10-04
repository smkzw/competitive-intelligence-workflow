"""Real Protocol/SAP statistical clauses reach legal, unreviewed C consumers."""

import hashlib
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".artifacts/r24-115-real-c-review-candidate-v3-20261003"
PDF = ROOT / ".artifacts/r24-164-current-native-pdf-candidate-20261004"


def _arguments(tmp_path: Path) -> dict:
    return {
        "registry_root": REGISTRY,
        "pdf_root": PDF,
        "registry_sha256": hashlib.sha256(
            (REGISTRY / "candidate-manifest.json").read_bytes()
        ).hexdigest(),
        "pdf_sha256": "176e5ab3e7fd339fc483203cfa183b6644a1a1c11b693e5653572ade97e3c83d",
        "output": tmp_path / "combined-c",
        "observed_at": datetime.now(UTC),
    }


def _builder():
    assert importlib.util.find_spec("tools.materialize_c_pdf_extension") is not None, (
        "Native PDF statistical clauses are not connected to ordinary C consumers"
    )
    from tools.materialize_c_pdf_extension import extend_candidate

    return extend_candidate


def test_real_source_statistical_extension_registers_without_acceptance(tmp_path: Path):
    result = _builder()(**_arguments(tmp_path))
    output = tmp_path / "combined-c"
    report = json.loads((output / "review-portal-data.json").read_bytes())
    baseline = json.loads((REGISTRY / "review-portal-data.json").read_bytes())
    assert report["observations"][:85] == baseline["observations"]
    extra = report["observations"][85:]
    assert len(extra) == 42
    assert sum(item["field_family"] == "statistical" for item in extra) == 37
    assert sum(item["field_family"] == "sample_size" for item in extra) == 5
    assert {item["source_role"] for item in extra} == {"protocol_sap"}
    assert {item["review_state"] for item in extra} == {"candidate"}
    assert all(item["threshold_value"] is None and item["endpoint_key"] is None for item in extra)
    assert all(
        item["source_locator"]["page"] and item["source_locator"]["paragraph"] for item in extra
    )
    from ci_workflow.renderers.portal.report_c import _cohort_label_zh, _group_label_zh

    assert _cohort_label_zh(extra[0]["cohort_id"]) == "条款适用范围见原文"
    assert _group_label_zh(extra[0]["group_id"]) == "组别适用范围见原文"
    assert any(item["conflict_disposition"] == "open_conflict_preserved" for item in extra)
    assert len(result["deferred_clauses"]) == 22
    assert result["registered_consumers"] == 127
    assert result["scientific_acceptance"] is False
    assert result["current_generation_switched"] is False
    assert not (output / "project/reports/current.json").exists()
    with open_database(output / "project/state/project.sqlite") as database:
        assert (
            database.execute("SELECT COUNT(*) FROM source_portal_consumer_bindings").fetchone()[0]
            == 127
        )
        assert (
            database.execute(
                "SELECT COUNT(*) FROM fact_versions WHERE review_state='accepted'"
            ).fetchone()[0]
            == 0
        )
    snapshot = SnapshotStore(output / "project").read(
        LockedSnapshot.model_validate(result["snapshot"])
    )
    assert len(snapshot["closure"]["sources"]) == 33
    assert all(
        source["capture"]["first_disclosed_at"] is None
        for source in snapshot["closure"]["sources"]
        if source["capture"]["source_type"] == "protocol_sap"
    )
    page = (output / result["site_relative_path"] / "sample-analysis-statistics.html").read_text()
    assert "statistical_model" in page and "missing_data_sensitivity" in page
    assert all(item["row_id"] in page for item in extra)
    assert "首次公开日期" in page and "待复核" in page
    site = output / result["site_relative_path"]
    assert result["site_file_sha256"] == {
        path.relative_to(site).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(site.rglob("*")) if path.is_file()
    }
    assert "assets/portal.js" in result["site_file_sha256"]
    assert "data/report.js" in result["site_file_sha256"]


@pytest.mark.parametrize("damage", ["registry_pin", "pdf_pin", "future", "before_receipt"])
def test_bad_input_fails_before_creating_combined_candidate(tmp_path: Path, damage: str):
    arguments = _arguments(tmp_path)
    if damage.endswith("pin"):
        arguments[damage.replace("_pin", "_sha256")] = "0" * 64
    elif damage == "future":
        arguments["observed_at"] = datetime.now(UTC) + timedelta(days=1)
    else:
        arguments["observed_at"] = datetime(2026, 10, 3, 16, tzinfo=UTC)
    with pytest.raises(ValueError):
        _builder()(**arguments)
    assert not arguments["output"].exists()


def test_existing_output_keeps_unrelated_bytes(tmp_path: Path):
    arguments = _arguments(tmp_path)
    arguments["output"].mkdir()
    sentinel = arguments["output"] / "keep.txt"
    sentinel.write_text("existing output belongs to its owner")
    with pytest.raises(ValueError, match="fresh|新"):
        _builder()(**arguments)
    assert sentinel.read_text() == "existing output belongs to its owner"


def test_original_pdf_candidate_and_clause_versions_remain_immutable(tmp_path: Path):
    arguments = _arguments(tmp_path)
    originals = {
        str(path): path.read_bytes()
        for path in (
            PDF / "candidate-manifest.json",
            REGISTRY / "candidate-manifest.json",
            REGISTRY / "review-portal-data.json",
        )
    }
    result = _builder()(**arguments)
    for path, raw in originals.items():
        assert Path(path).read_bytes() == raw
    manifest = json.loads((PDF / "candidate-manifest.json").read_bytes())
    proposal = json.loads(
        ContentAddressedStore(PDF).read_bytes(
            ContentBlob.model_validate(manifest["proposal_asset"]),
        )
    )
    report = json.loads((arguments["output"] / "review-portal-data.json").read_bytes())
    quotes = {atom["proposal_id"]: atom["original_quote"] for atom in proposal["atoms"]}
    assert {item["source_row_id"] for item in report["observations"][85:]} <= set(quotes)
    assert all(
        item["source_text"] == quotes[item["source_row_id"]].strip()
        for item in report["observations"][85:]
    )
    assert result["original_clause_count"] == 64
