"""A/B builder bytes must retain the scope consumed by current edit selection."""
import json

import pytest

from ci_workflow.application.user_fact_edit import UserFactEditService
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData
from tests.integration.reports.test_b_report_portal import _load_portal_payload
from tests.integration.test_w04_source_consumer_registry import CONTENT


@pytest.mark.parametrize("kind", ["A", "B"])
def test_builder_roundtrip_retains_source_scope_without_changing_legacy_payload(kind):
    model = ReportAPortalData if kind == "A" else ReportBPortalData
    raw = (json.loads(CONTENT.read_bytes())["report_data"]
           if kind == "A" else _load_portal_payload())
    old = model.model_validate(raw)
    assert "source_evidence_snapshot_id" not in old.model_dump(mode="json")
    scope = "evidence-snapshot_current-selected"
    current = model.model_validate({**old.model_dump(mode="json"),
                                   "source_evidence_snapshot_id": scope})
    assert UserFactEditService._portal_data_scope_from_bytes(
        current.model_dump_json().encode()
    ) == scope
    without_scope = current.model_dump(mode="json", exclude={"source_evidence_snapshot_id"})
    assert without_scope == old.model_dump(mode="json")


@pytest.mark.parametrize("scope", ["", "  ", "wrong-object-id", "../snapshots/old"])
def test_explicit_bad_scope_is_not_a_legacy_unscoped_payload(scope):
    raw = json.loads(CONTENT.read_bytes())["report_data"]
    with pytest.raises(ValueError):
        ReportAPortalData.model_validate({**raw, "source_evidence_snapshot_id": scope})
