"""C must share an existing ABC project rather than secretly fork its evidence."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from tests.integration.test_r24_c_candidate_materialization import _raw
from tests.integration.test_r24_ctgov_c_design_projection import _CAS_ROOT, _full_bindings
from tools.materialize_ctgov_c_candidate import materialize, render_review_preview


def _project(tmp_path, *, reports=None):
    root = tmp_path / "shared-project"
    contract = create_project_contract(indication="阵发性睡眠性血红蛋白尿症",
        reports=reports or ["A", "B", "C"], outputs=["html"],
        cutoff="2026-09-26", created_at=datetime(2026, 10, 3, tzinfo=UTC))
    create_project_workspace(root, contract)
    return root, contract


def _materialize(root, output, **changes):
    args = dict(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
        cutoff="2026-09-26", observed_at=datetime(2026, 10, 3, tzinfo=UTC), project_root=root)
    args.update(changes)
    return materialize(**args)


def test_existing_abc_project_c_uses_same_contract_and_source_repository(tmp_path):
    root, contract = _project(tmp_path)
    before = (root / "project.yaml").read_bytes()
    output = root / "evidence/library/c-candidate"
    result = _materialize(root, output)
    assert result["observations"] == 85
    saved = json.loads((output / "inputs.json").read_bytes())
    assert saved["contract"]["project_id"] == contract.project_id
    assert (root / result["snapshot"]["relative_path"]).is_file()
    assert not (output / "project").exists()
    assert (root / "project.yaml").read_bytes() == before
    assert not (root / "reports/current.json").exists()


@pytest.mark.parametrize("conflict", ["indication", "cutoff", "report", "outside"])
def test_contract_or_output_conflict_fails_before_ingestion(tmp_path, conflict):
    root, _contract = _project(tmp_path, reports=["A", "B"] if conflict == "report" else None)
    output = (tmp_path / "outside" if conflict == "outside"
              else root / "evidence/library/c-candidate")
    changes = ({"indication": "不同适应症"} if conflict == "indication" else
               {"cutoff": "2026-09-25"} if conflict == "cutoff" else {})
    before = (root / "state/project.sqlite").read_bytes()
    with pytest.raises(ValueError, match="合同|项目内"):
        _materialize(root, output, **changes)
    assert not output.exists()
    assert (root / "state/project.sqlite").read_bytes() == before


def test_existing_project_preview_registers_c_only_and_is_not_current(tmp_path):
    root, _contract = _project(tmp_path)
    output = root / "evidence/library/c-candidate"
    _materialize(root, output)
    result = render_review_preview(output, rendered_at=datetime(2026, 10, 3, tzinfo=UTC),
                                   project_root=root)
    assert result["registered_consumers"] == 85
    assert result["site_path_base"] == "project"
    assert (root / result["site_relative_path"] / "overview.html").is_file()
    assert result["scientific_acceptance"] is False
    assert not (root / "reports/current.json").exists()


def test_relative_cli_style_paths_share_existing_project(tmp_path, monkeypatch):
    root, _contract = _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    output = Path("shared-project/evidence/library/c-relative")
    result = _materialize(Path("shared-project"), output)
    assert result["source_versions"] == 2
    assert (root / result["snapshot"]["relative_path"]).is_file()


def test_official_uppercase_registry_ids_do_not_break_internal_design_identity(tmp_path):
    root, _contract = _project(tmp_path)
    output = root / "evidence/library/c-uppercase"
    bindings = tuple(binding.model_copy(update={"trial_id": binding.trial_id.upper()})
                     for binding in _full_bindings())
    result = _materialize(root, output, bindings=bindings)
    assert result["observations"] == 85
    observations = json.loads((output / "projection.json").read_bytes())["observations"]
    assert {row["trial_id"] for row in observations} == {"nct02264639", "nct03829449"}
