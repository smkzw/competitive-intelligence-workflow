"""Current rebuild preserves verified identity, not a browser text patch."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.latest_delivery import CurrentReportDelivery
from ci_workflow.application.user_fact_edit import (
    CurrentDeliveryConflictError,
    build_current_report,
)
from tests.integration.test_1007_identity_source_replay import _inputs
from tools.materialize_identity_sources import load_identity_context, materialize


@pytest.mark.parametrize("kind", ["A", "B"])
@pytest.mark.parametrize("damage", [None, "context", "source", "missing_context"])
@pytest.mark.parametrize("operation", ["save", "clear"])
def test_bound_identity_survives_current_rebuild_or_fails_before_new_version(
    tmp_path, kind, damage, operation,
):
    from ci_workflow.renderers.portal.report_a import (
        ReportAPortalData,
        active_fact_binding_for_a,
        render_report_a_site,
    )
    from ci_workflow.renderers.portal.report_b import (
        ReportBPortalData,
        active_fact_binding_for_b,
        render_report_b_site,
    )

    source, spec_path, _digest, root = _inputs(tmp_path)
    fixture_root = Path(__file__).resolve().parents[2] / "fixtures"
    fixture = fixture_root / ("synthetic/a-complete/inputs/report-data.json" if kind == "A"
                              else "positive/b-pnh/inputs/report-data.json")
    raw = json.loads(fixture.read_text())
    spec = json.loads(spec_path.read_text())
    spec["product_entity_ids"] = {raw["products"][0]["id"]: "product"}
    spec_path.write_text(json.dumps(spec))
    receipt = materialize(
        source, spec_path, hashlib.sha256(spec_path.read_bytes()).hexdigest(), root,
    )
    context = load_identity_context(root, receipt["graph_asset"])
    raw["data_cutoff"] = datetime.now(UTC).isoformat()
    model, renderer = ((ReportAPortalData, render_report_a_site) if kind == "A"
                       else (ReportBPortalData, render_report_b_site))
    data = model.model_validate(raw)
    binding = (active_fact_binding_for_a if kind == "A" else active_fact_binding_for_b)(
        data, "safety", data.safety[0].row_id,
    )
    cleared = operation == "clear"
    fact = {**binding.model_dump(mode="json", exclude={
        "report", "collection", "row_id", "original_row_sha256", "source_pointer",
    }), "fact_id": "edited-fact", "fact_version_id": "edited-v1", "field_id": "safety.value",
        "primary_fragment_id": "synthetic-clinical-fragment",
        "source_locator": binding.source_pointer, "source_quote": "Synthetic original value",
        "raw_value": None if cleared else "61.0%", "normalized_value": None if cleared else 61.0,
        "disclosure_state": "user_cleared" if cleared else "reported_value",
        "consumer_bindings": [binding.model_dump(mode="json")], "review_state": "user_modified",
        "user_edit": {"request_id": "identity-rebuild", "revision": 1,
            "basis": "Synthetic rebuild regression", "saved_by": "test",
            "saved_at": datetime.now(UTC).isoformat(), "operation": "save"}}
    builder = root / "builder.json"
    builder.write_text(data.model_dump_json())
    site = root / "reports" / kind / "v1/html"
    renderer(data, site, identity_context=context)
    hashes = {p.relative_to(site).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in site.rglob("*") if p.is_file()}
    previous = CurrentReportDelivery(report=kind, revision=0, report_version="v1",
        site_relative_path=site.relative_to(root).as_posix(), file_hashes=hashes,
        fact_version_ids=(), fact_revision_digest=hashlib.sha256(b"[]").hexdigest(),
        builder_input_relative_path="builder.json",
        builder_input_sha256=hashlib.sha256(builder.read_bytes()).hexdigest())
    if damage == "context":
        (site / "data/identity-context.json").write_text("{}")
    elif damage == "missing_context":
        (site / "data/identity-context.json").unlink()
        (site / "data/identity-projection.json").write_text("{}")
    elif damage == "source":
        derivation = context.evidence.verified_fragments[0].source_version.text_derivation
        source_blob = derivation.raw_asset
        (root / source_blob.relative_path).write_bytes(b"tampered source")
    arguments = dict(revision=1, request_id="identity-rebuild", changed_fact_id="edited-fact",
                     fact_version_ids=("edited-v1",), public_facts={"edited-fact": fact},
                     report_version="v2")
    if damage:
        with pytest.raises(CurrentDeliveryConflictError):
            build_current_report(root, previous, **arguments)
        assert not (root / "reports" / kind / "v2").exists()
    else:
        current = build_current_report(root, previous, **arguments)
        new_site = root / current.site_relative_path
        assert "公司：Group Ltd｜中国MAH所属集团" in (new_site / "overview.html").read_text()
        assert (new_site / "data/identity-projection.json").read_bytes() == (
            site / "data/identity-projection.json"
        ).read_bytes()
        assert "data/identity-context.json" in current.file_hashes
        report_js = (new_site / "data/report.js").read_text()
        payload = json.loads(report_js.split("=", 1)[1].removesuffix(";\n"))
        assert payload["safety"][0]["value"] == (None if cleared else 61.0)
        assert not (root / "reports/current.json").exists()
