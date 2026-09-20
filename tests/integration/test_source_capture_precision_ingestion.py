from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    FreshAResearchPackage,
    compute_research_content_digest,
    ingest_fresh_a_research_package,
)
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import _project, _source_payload


@pytest.mark.parametrize("generic", [False, True])
def test_day_precision_survives_persistent_ingestion(tmp_path: Path, generic: bool) -> None:
    from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
    from ci_workflow.application.project_service import verify_project_workspace

    project = _project(tmp_path)
    _, payload = _source_payload(tmp_path)
    payload["sources"][0].update(
        published_at="2026-07-01T00:00:00Z",
        first_disclosed_at="2026-07-01T00:00:00Z",
        date_precisions={"published_at": "calendar_day", "first_disclosed_at": "calendar_day"},
    )
    digest = compute_research_content_digest(payload)
    payload["scientific_review"]["reviewed_content_digest"] = digest
    package = FreshAResearchPackage.model_validate(payload)
    contract = verify_project_workspace(project).contract
    if generic:
        lineage = ingest_research_evidence(
            project_root=project, project_id=contract.project_id, contract_version=1,
            report_kind="A", data_cutoff=package.data_cutoff, scientific_content_digest=digest,
            created_at=package.scientific_review.reviewed_at, sources=package.sources,
            route_attempts=package.route_attempts, facts=package.facts, claims=package.claims,
        )
    else:
        lineage = ingest_fresh_a_research_package(
            project_root=project, project_id=contract.project_id,
            contract_version=1, package=package,
        )
    repository = EvidenceRepository(
        project / "state/project.sqlite", ContentAddressedStore(project),
    )
    with open_database(project / "state/project.sqlite") as database:
        versions = [repository._read_source_version(database, identity)
                    for identity in lineage.source_version_ids]
    changed = next(item for item in versions if item.source_id == package.sources[0].source_id)
    assert changed.published_at.precision == "calendar_day"
    assert changed.first_disclosed_at.precision == "calendar_day"


@pytest.mark.parametrize("cutoff,accepted", [
    ("2026-07-31T12:00:00+08:00", False),
    ("2026-07-31T23:59:59.999999+08:00", True),
])
def test_fresh_package_does_not_promote_day_precision_to_midnight_disclosure(
    tmp_path: Path, cutoff: str, accepted: bool,
) -> None:
    _, payload = _source_payload(tmp_path)
    payload["data_cutoff"] = cutoff
    payload["report_data"]["data_cutoff"] = cutoff
    payload["sources"][0].update(
        published_at="2026-07-31T00:00:00+08:00",
        first_disclosed_at="2026-07-31T00:00:00+08:00",
        date_precisions={"published_at": "calendar_day", "first_disclosed_at": "calendar_day"},
    )
    if not accepted:
        with pytest.raises(ValueError, match="截止"):
            compute_research_content_digest(payload)
    else:
        payload["scientific_review"]["reviewed_content_digest"] = (
            compute_research_content_digest(payload)
        )
        FreshAResearchPackage.model_validate(payload)
