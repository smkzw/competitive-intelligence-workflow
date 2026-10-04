"""Union verified source sets without first-wins, Top-N, or scientific adoption."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from tests.integration.test_r24_ctgov_source_inventory import _study, _write_cas
from tools.build_ctgov_source_inventory import InventoryError, build_inventory


def _inventory(
    tmp_path: Path, name: str, studies: list[dict], *, condition: str | None = None,
) -> Path:
    cas = tmp_path / name
    receipt = _write_cas(cas, studies)
    if condition:
        data = json.loads(receipt.read_text())
        data["acquisition"]["condition"] = condition
        receipt.write_text(json.dumps(data, sort_keys=True))
    path = tmp_path / f"{name}.json"
    build_inventory(cas_dir=cas, capture_receipt=receipt, output=path)
    return path


def _union(paths: list[Path]) -> dict:
    tool = importlib.import_module("tools.build_ctgov_inventory_union")
    return tool.build_union(paths)


def test_identical_study_joins_routes_without_double_count_or_adoption(tmp_path: Path) -> None:
    study = _study("NCT00000011", interventions=[{"type": "DRUG", "name": "Example"}])
    first = _inventory(tmp_path, "first", [study])
    second = _inventory(tmp_path, "second", [study], condition="Nasal Polyps")
    result = _union([first, second])
    assert result["unique_studies"] == 1
    assert result["query_memberships"] == 2
    assert len(result["studies"][0]["versions"]) == 1
    assert len(result["studies"][0]["versions"][0]["memberships"]) == 2
    assert result["accepted"] is False
    assert result["universe_closed"] is False
    assert result["studies"][0]["decision"] == "review_pending"


def test_record_difference_keeps_both_versions_and_no_winner(tmp_path: Path) -> None:
    first = _inventory(tmp_path, "first", [_study("NCT00000011", interventions=[])])
    second = _inventory(tmp_path, "second", [_study(
        "NCT00000011", interventions=[], conditions=["COPD"], enrollment_count=0,
    )])
    result = _union([first, second])
    entry = result["studies"][0]
    assert entry["version_conflict"] is True
    assert len(entry["versions"]) == 2
    assert {tuple(v["conditions"]) for v in entry["versions"]} == {
        ("Chronic Rhinosinusitis with Nasal Polyps",), ("COPD",),
    }
    assert result["source_version_conflicts"] == 1
    assert "active_version" not in entry


def test_source_input_order_does_not_change_manifest(tmp_path: Path) -> None:
    first = _inventory(tmp_path, "first", [_study("NCT00000011", interventions=[])])
    second = _inventory(tmp_path, "second", [_study("NCT00000012", interventions=[])])
    assert _union([first, second]) == _union([second, first])


def test_duplicate_inventory_argument_does_not_duplicate_routes(tmp_path: Path) -> None:
    first = _inventory(tmp_path, "first", [_study("NCT00000011", interventions=[])])
    assert _union([first]) == _union([first, first])


def test_tampered_projection_is_rejected_before_union(tmp_path: Path) -> None:
    first = _inventory(tmp_path, "first", [_study("NCT00000011", interventions=[])])
    data = json.loads(first.read_text())
    data["studies"][0]["conditions"] = ["invented condition"]
    first.write_text(json.dumps(data))
    with pytest.raises(InventoryError, match="projection"):
        _union([first])


def test_cas_mutation_is_rejected_not_reinterpreted_as_no_studies(tmp_path: Path) -> None:
    first = _inventory(tmp_path, "first", [_study("NCT00000011", interventions=[])])
    data = json.loads(first.read_text())
    page = Path(data["source"]["cas_dir"]) / data["source"]["pages"][0]["relative_path"]
    page.write_bytes(b"{}")
    with pytest.raises(InventoryError):
        _union([first])
