"""Acquisition cannot follow its completed snapshot or lie in the future.

These portable cases exercise the shared production entry for A/B/C. They do
not grant publication cutoff eligibility or read the real private source set.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import pytest

from ci_workflow.application.fresh_research_ingestion import (
    ResearchIngestionError,
    ingest_research_evidence,
)
from ci_workflow.application.source_research_service import (
    FreshAResearchPackage,
    compute_research_content_digest,
)
from tests.integration.test_research_package_submission import _project, _source_payload


@pytest.mark.parametrize("report", ["A", "B", "C"])
@pytest.mark.parametrize("failure", ["after_snapshot", "future_snapshot"])
def test_bad_capture_chronology_rejected_before_any_persistence(
    tmp_path: Path, report: Literal["A", "B", "C"], failure: str,
) -> None:
    root = _project(tmp_path)
    _, payload = _source_payload(tmp_path)
    package = FreshAResearchPackage.model_validate({
        **payload, "scientific_review": {
            **payload["scientific_review"],
            "reviewed_content_digest": compute_research_content_digest(payload),
        },
    })
    sources = package.sources
    created = min(s.acquired_at for s in sources) - timedelta(microseconds=1)
    if failure == "future_snapshot":
        created = datetime.now(UTC) + timedelta(days=2)
        sources = tuple(s.model_copy(update={"acquired_at": created}) for s in sources)
    before = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ResearchIngestionError, match="时间|时刻"):
        ingest_research_evidence(
            project_root=root, project_id=package.indication, contract_version=1,
            report_kind=report, data_cutoff=package.data_cutoff,
            scientific_content_digest=package.research_content_digest,
            created_at=created, sources=sources, route_attempts=(), facts=package.facts,
            claims=package.claims,
        )
    after = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob("*") if p.is_file()}
    assert after == before, "Fail before DB, CAS, lineage or snapshot changes"


def test_equal_acquisition_snapshot_and_replay_remain_legal(tmp_path: Path) -> None:
    root = _project(tmp_path)
    _, payload = _source_payload(tmp_path)
    package = FreshAResearchPackage.model_validate({
        **payload, "scientific_review": {
            **payload["scientific_review"],
            "reviewed_content_digest": compute_research_content_digest(payload),
        },
    })
    created = max(s.acquired_at for s in package.sources)
    args = dict(
        project_root=root, project_id=package.indication, contract_version=1,
        report_kind="A", data_cutoff=package.data_cutoff,
        scientific_content_digest=package.research_content_digest,
        created_at=created, sources=package.sources, route_attempts=(), facts=package.facts,
        claims=package.claims,
    )
    first = ingest_research_evidence(**args)
    second = ingest_research_evidence(**args)
    assert first == second
