from __future__ import annotations


def test_foreign_regulatory_documents_are_versioned_and_field_scoped() -> None:
    from ci_workflow.sources.connectors.regulators import RegulatoryDocumentVersion

    first = RegulatoryDocumentVersion.create(
        jurisdiction="US",
        authority="FDA",
        document_id="BLA-761055-approval-letter",
        title="Approval Letter",
        version_label="2019-06-26",
        published_at="2019-06-26T00:00:00-04:00",
        acquired_at="2026-08-10T09:00:00+08:00",
        content_sha256="1" * 64,
        source_url="https://www.accessdata.fda.gov/example/approval-letter.pdf",
        claim_scopes=(
            {
                "claim_domain": "regulatory_status",
                "field_path": "letter.approval_action",
                "locator_label": "第 1 页批准决定",
            },
            {
                "claim_domain": "approved_indication",
                "field_path": "letter.indication",
                "locator_label": "第 1 页适应症",
            },
        ),
    )
    revised = RegulatoryDocumentVersion.create(
        jurisdiction="US",
        authority="FDA",
        document_id="BLA-761055-approval-letter",
        title="Approval Letter, labeling supplement",
        version_label="2023-01-01",
        published_at="2023-01-01T00:00:00-05:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="2" * 64,
        source_url="https://www.accessdata.fda.gov/example/approval-letter-2023.pdf",
        claim_scopes=(
            {
                "claim_domain": "approved_indication",
                "field_path": "label.section_1",
                "locator_label": "说明书第 1 节",
            },
        ),
    )

    assert first.source_document_id == revised.source_document_id
    assert first.source_version_id != revised.source_version_id
    assert first.allows_claim("regulatory_status") is True
    assert first.allows_claim("efficacy") is False
    assert revised.allows_claim("approved_indication") is True
    assert first.claim_scopes[0].locator.field_path == "letter.approval_action"
    assert first.claim_scopes[0].locator.url == first.source_url
    assert first.published_at.isoformat() == "2019-06-26T00:00:00-04:00"


def test_fda_guidance_preserves_version_status_population_context_locator_and_supersession(  # noqa: E501
) -> None:
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    from ci_workflow.sources.connectors.regulators import (
        GuidelineBasis,
        select_current_guideline_basis,
        validate_guideline_lineage,
    )

    old_identity = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="chronic-rhinosinusitis-drug-development",
        title="Chronic Rhinosinusitis: Developing Drugs for Treatment",
        guidance_status="final",
        version_date="2021-06-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.fda.gov/example/final-2021",
        locator_label="第 5 页主要终点建议",
        locator_page=5,
        content_sha256="3" * 64,
        captured_at="2026-08-10T09:00:00+08:00",
        lifecycle_status="active",
    )
    new_final = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="chronic-rhinosinusitis-drug-development",
        title="Chronic Rhinosinusitis: Developing Drugs for Treatment",
        guidance_status="final",
        version_date="2025-02-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.fda.gov/example/final-2025",
        locator_label="第 7 页主要终点建议",
        locator_page=7,
        content_sha256="4" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
        supersedes_version_ids=(old_identity.guideline_version_id,),
    )
    old_final = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="chronic-rhinosinusitis-drug-development",
        title="Chronic Rhinosinusitis: Developing Drugs for Treatment",
        guidance_status="final",
        version_date="2021-06-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.fda.gov/example/final-2021",
        locator_label="第 5 页主要终点建议",
        locator_page=5,
        content_sha256="3" * 64,
        captured_at="2026-08-10T09:00:00+08:00",
        lifecycle_status="superseded",
        superseded_by_version_id=new_final.guideline_version_id,
    )
    draft = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="crs-endpoint-draft",
        title="Endpoints for CRS Trials",
        guidance_status="draft",
        version_date="2026-01-15",
        population_context="成人慢性鼻窦炎受试者",
        development_context="探索性终点建议",
        source_url="https://www.fda.gov/example/draft-2026",
        locator_label="第 3 页草案建议",
        locator_page=3,
        content_sha256="5" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
    )
    withdrawn = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="old-endpoint-guidance",
        title="Old Endpoint Guidance",
        guidance_status="final",
        version_date="2010-01-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="历史终点建议",
        source_url="https://www.fda.gov/example/withdrawn",
        locator_label="历史归档页",
        locator_page=1,
        content_sha256="6" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="withdrawn",
        withdrawn_at="2020-01-01",
    )

    assert old_final.guideline_series_id == new_final.guideline_series_id
    assert old_final.guideline_version_id != new_final.guideline_version_id
    assert old_final.can_drive_current_default is False
    assert draft.can_drive_current_default is False
    assert withdrawn.can_drive_current_default is False
    assert new_final.can_drive_current_default is True
    assert new_final.locator.page == 7
    assert new_final.locator.url == new_final.source_url
    assert new_final.population_context == "成人慢性鼻窦炎受试者"
    assert new_final.development_context == "确证性药物临床试验主要终点"
    validate_guideline_lineage((old_final, new_final, draft, withdrawn))

    import pytest

    duplicate_current = GuidelineBasis.create(
        jurisdiction="US",
        agency="FDA",
        document_id="chronic-rhinosinusitis-drug-development",
        title="Chronic Rhinosinusitis: Developing Drugs for Treatment",
        guidance_status="final",
        version_date="2026-02-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.fda.gov/example/final-2026",
        locator_label="第 8 页主要终点建议",
        locator_page=8,
        content_sha256="7" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
    )
    with pytest.raises(ValueError, match="多个当前版本"):
        validate_guideline_lineage((old_identity, duplicate_current))

    cycle_seed = tuple(
        GuidelineBasis.create(
            jurisdiction="US",
            agency="FDA",
            document_id=f"cycle-{name}",
            title=f"Cycle {name}",
            guidance_status="final",
            version_date=f"202{index}-01-01",
            population_context="成人受试者",
            development_context="循环攻击测试",
            source_url=f"https://www.fda.gov/example/cycle-{name}",
            locator_label="第 1 页",
            locator_page=1,
            content_sha256=str(index) * 64,
            captured_at="2026-08-11T09:00:00+08:00",
            lifecycle_status="active",
        )
        for index, name in enumerate(("a", "b", "c"), start=1)
    )
    cycle = tuple(
        GuidelineBasis.create(
            jurisdiction="US",
            agency="FDA",
            document_id=f"cycle-{name}",
            title=f"Cycle {name}",
            guidance_status="final",
            version_date=f"202{index}-01-01",
            population_context="成人受试者",
            development_context="循环攻击测试",
            source_url=f"https://www.fda.gov/example/cycle-{name}",
            locator_label="第 1 页",
            locator_page=1,
            content_sha256=str(index) * 64,
            captured_at="2026-08-11T09:00:00+08:00",
            lifecycle_status="superseded",
            supersedes_version_ids=(cycle_seed[index - 2].guideline_version_id,),
            superseded_by_version_id=cycle_seed[index % 3].guideline_version_id,
        )
        for index, name in enumerate(("a", "b", "c"), start=1)
    )
    with pytest.raises(ValueError, match="循环"):
        validate_guideline_lineage(cycle)
    assert select_current_guideline_basis(
        (old_final, draft, withdrawn, new_final),
        jurisdiction="US",
        population_context="成人慢性鼻窦炎受试者",
    ) == (new_final,)

    root = Path(__file__).resolve().parents[3]
    schema = json.loads((root / "schemas" / "guideline-basis.schema.json").read_text())
    for item in (old_final, new_final, draft, withdrawn):
        Draft202012Validator(schema).validate(item.model_dump(mode="json"))
