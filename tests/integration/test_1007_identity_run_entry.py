"""Ordinary run adapters bind the same portable identity input, not a demo path."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from ci_workflow.application.run_service import (
    RunContext,
    _render_html_a,
    _render_html_b,
    _render_html_c_minimal,
)
from tests.integration.test_1007_identity_source_replay import _inputs
from tools.materialize_identity_sources import materialize


def _run_input(tmp_path, kind):
    import hashlib

    source, path, _, project = _inputs(tmp_path)
    repo = Path(__file__).resolve().parents[2]
    fixture = ("fixtures/positive/c-atopic-dermatitis/inputs/report-data.json" if kind == "C"
               else "fixtures/synthetic/a-complete/inputs/report-data.json")
    raw = json.loads((repo / fixture).read_bytes())
    product_id = raw["products"][0]["id"]
    spec = json.loads(path.read_bytes())
    # A project-level map may cover products not used in this particular report.
    spec["product_entity_ids"] = {product_id: "product", "other-report-product": "product"}
    path.write_text(json.dumps(spec))
    receipt = materialize(source, path, hashlib.sha256(path.read_bytes()).hexdigest(), project)
    canonical = project / "evidence/library/portal-identity-context.json"
    canonical.parent.mkdir(parents=True)
    canonical.write_text(json.dumps({"schema_version": "portal-identity-context-1",
                                    "graph_asset": receipt["graph_asset"]}))
    raw.update(data_cutoff=datetime.now(UTC).isoformat(), report_version="v1-identity-entry")
    data_path = project / "evidence/library/report-data.json"
    data_path.write_text(json.dumps(raw))
    contract = SimpleNamespace(project_id="identity-entry", contract_version=1,
        indication=raw["indication"], reports=(SimpleNamespace(value=kind),),
        data_cutoff=datetime.fromisoformat(raw["data_cutoff"]))
    return project, canonical, receipt, RunContext(
        project_root=project, contract=contract, report_data_path=data_path,
    )


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_normal_run_artifacts_include_scoped_source_identity_and_input_hash(tmp_path, kind):
    import hashlib

    project, canonical, receipt, context = _run_input(tmp_path, kind)
    if kind == "A":
        site, manifest = _render_html_a(context, "run-identity-entry")
    elif kind == "B":
        site, manifest, _ = _render_html_b(context, "run-identity-entry")
    else:
        site, manifest = _render_html_c_minimal(context, "run-identity-entry",
                                              context.report_data_path)
    html = (project / site / "overview.html").read_text()
    assert "公司：Group Ltd｜中国MAH所属集团" in html
    assert "Holder Ltd" in html
    binding = json.loads((project / site / "data/identity-context.json").read_bytes())
    assert binding["graph_asset"] == receipt["graph_asset"]
    assert "other-report-product" not in binding["product_ids"]
    assert context.run_inputs[canonical.relative_to(project).as_posix()] == hashlib.sha256(
        canonical.read_bytes()).hexdigest()
    record = json.loads((project / manifest).read_bytes())
    assert record["accepted_by"] is None
    assert record["render_verdict"]["status"] == "rejected"


@pytest.mark.parametrize("damage", ["graph", "source", "schema"])
def test_invalid_identity_cannot_silently_downgrade_to_unknown_header(tmp_path, damage):
    project, canonical, receipt, context = _run_input(tmp_path, "A")
    if damage == "graph":
        (project / receipt["graph_asset"]["relative_path"]).write_bytes(b"wrong graph")
    elif damage == "source":
        (project / "state/project.sqlite").write_bytes(b"invalid evidence repository")
    else:
        canonical.write_text(json.dumps({"schema_version": "wrong", "graph_asset": None}))
    with pytest.raises((ValueError, RuntimeError)):
        _render_html_a(context, "run-invalid-identity")
    assert not (project / "reports/A/v1-identity-entry/html").exists()
