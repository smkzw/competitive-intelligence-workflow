"""Portable identity ingestion must also attach to a real existing project.

The synthetic GET establishes only the existing proof contract, not a clinical
or regulatory acceptance. No existing project/identity may be overwritten.
"""

import json
from datetime import UTC, datetime

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.reports.common.identity_projection import load_identity_context
from tests.integration.test_1007_identity_source_replay import _inputs
from tools.materialize_identity_sources import materialize


def _project(tmp_path):
    source, spec, digest, root = _inputs(tmp_path)
    contract = create_project_contract(indication="测试身份摄取", reports=["A", "B", "C"],
        outputs=["html"], created_at=datetime.now(UTC))
    create_project_workspace(root, contract)
    return source, spec, digest, root


def test_identity_installs_into_existing_project_without_changing_contract(tmp_path):
    source, spec, digest, root = _project(tmp_path)
    before = (root / "project.yaml").read_bytes()
    receipt = materialize(source, spec, digest, root, project_workspace=True)
    canonical = json.loads((root / "evidence/library/portal-identity-context.json").read_bytes())
    assert canonical == {"schema_version": "portal-identity-context-1",
                         "graph_asset": receipt["graph_asset"]}
    context = load_identity_context(root, canonical["graph_asset"])
    assert context.project(("synthetic-product",), cutoff=datetime.now(UTC))[
        "synthetic-product"]["company_label"] == "公司：Group Ltd｜中国MAH所属集团"
    assert (root / "project.yaml").read_bytes() == before
    assert not (root / "reports/current.json").exists()
    assert receipt["science_accepted"] is False
    assert receipt["current_promoted"] is False


@pytest.mark.parametrize("occupied", ["evidence/library/portal-identity-context.json",
                                     "identity-checkpoint.json"])
def test_initial_install_refuses_existing_binding_before_any_db_change(tmp_path, occupied):
    source, spec, digest, root = _project(tmp_path)
    destination = root / occupied
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"existing identity material")
    before = (root / "state/project.sqlite").read_bytes()
    with pytest.raises(ValueError, match="已有身份"):
        materialize(source, spec, digest, root, project_workspace=True)
    assert destination.read_bytes() == b"existing identity material"
    assert (root / "state/project.sqlite").read_bytes() == before


def test_invalid_source_does_not_change_existing_project_database(tmp_path):
    source, spec, digest, root = _project(tmp_path)
    before = (root / "state/project.sqlite").read_bytes()
    (source / "synthetic.pdf").write_bytes(b"invalid")
    with pytest.raises(ValueError, match="Source PDF"):
        materialize(source, spec, digest, root, project_workspace=True)
    assert (root / "state/project.sqlite").read_bytes() == before
    assert not (root / "evidence/library/portal-identity-context.json").exists()
