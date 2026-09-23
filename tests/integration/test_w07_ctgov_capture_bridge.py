"""CT.gov 原始分页切片到现有研究来源合同的最小接缝。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import CtgovRecordSelector
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.source_derivation import capture_source_text


def _derived(tmp_path: Path) -> DerivedCtgovStudy:
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT04558918", "briefTitle": "PNH study"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": []}},
    }
    raw = json.dumps({"studies": [record]}, ensure_ascii=False).encode()
    text, receipt = capture_source_text(
        tmp_path,
        raw,
        media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT04558918"),
    )
    return DerivedCtgovStudy(
        nct_id="NCT04558918",
        title="PNH study",
        record_url="https://clinicaltrials.gov/study/NCT04558918",
        registry_posted_version_date="2026-08-01",
        acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text,
        text_derivation=receipt,
    )


def test_ctgov_study_capture_reopens_raw_and_preserves_calendar_day(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    capture = source_capture_from_ctgov_study(tmp_path, study)
    assert capture.source_id == "ctgov-nct04558918"
    assert capture.source_type == "clinical_trial_registry"
    assert capture.text_derivation == study.text_derivation
    assert capture.date_evidence("published_at").precision == "calendar_day"
    assert capture.date_evidence("first_disclosed_at").precision == "calendar_day"
    assert capture.locator.field_path == "$.protocolSection.identificationModule.nctId"


def test_ctgov_study_capture_rejects_identity_date_or_raw_drift(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    for changed in (
        study.model_copy(update={"nct_id": "NCT00000001"}),
        study.model_copy(update={"registry_posted_version_date": "2026-08-02"}),
        study.model_copy(update={"content_text": study.content_text.replace("PNH", "ABC")}),
    ):
        with pytest.raises(ValueError):
            source_capture_from_ctgov_study(tmp_path, changed)
