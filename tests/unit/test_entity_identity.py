from __future__ import annotations


def test_stable_internal_identity_does_not_use_product_name_or_registry_number_as_primary_key(  # noqa: E501
) -> None:
    from ci_workflow.domain.entities import EntityIdentity, EntityType, ExternalIdentifier

    product = EntityIdentity.create(
        entity_type=EntityType.PRODUCT,
        canonical_name="测试创新药",
        identity_basis="sponsor-project-code-001",
        aliases=("测试创新药", "研发代号 A"),
        external_identifiers=(
            ExternalIdentifier(namespace="NCT", value="NCT00000001"),
        ),
    )
    renamed = EntityIdentity.create(
        entity_type=EntityType.PRODUCT,
        canonical_name="测试创新药新通用名",
        identity_basis="sponsor-project-code-001",
        aliases=("测试创新药新通用名", "研发代号 A"),
        external_identifiers=(
            ExternalIdentifier(namespace="NCT", value="NCT00000001"),
        ),
    )
    trial = EntityIdentity.create(
        entity_type=EntityType.TRIAL,
        canonical_name="关键试验",
        identity_basis="sponsor-project-code-001",
        aliases=("关键试验",),
        external_identifiers=(
            ExternalIdentifier(namespace="NCT", value="NCT00000001"),
        ),
    )
    assert product.entity_id == renamed.entity_id
    assert product.entity_id != trial.entity_id
    assert product.entity_id not in {product.canonical_name, "NCT00000001"}

    changed_registry_number = EntityIdentity.create(
        entity_type=EntityType.PRODUCT,
        canonical_name="测试创新药",
        identity_basis="sponsor-project-code-001",
        aliases=("测试创新药", "研发代号 A"),
        external_identifiers=(
            ExternalIdentifier(namespace="CTR", value="CTR20260009"),
        ),
    )
    assert changed_registry_number.entity_id == product.entity_id


def test_identity_basis_cannot_be_the_name_alias_or_external_identifier() -> None:
    import pytest

    from ci_workflow.domain.entities import EntityIdentity, EntityType, ExternalIdentifier

    identifier = ExternalIdentifier(namespace="NCT", value="NCT00000001")
    with pytest.raises(ValueError, match="身份依据不能直接使用名称、别名或外部登记号"):
        EntityIdentity.create(EntityType.TRIAL, "关键试验", "关键试验")
    with pytest.raises(ValueError, match="身份依据不能直接使用名称、别名或外部登记号"):
        EntityIdentity.create(
            EntityType.TRIAL,
            "关键试验",
            "共同别名",
            aliases=("共同别名",),
        )
    with pytest.raises(ValueError, match="身份依据不能直接使用名称、别名或外部登记号"):
        EntityIdentity.create(
            EntityType.TRIAL,
            "关键试验",
            "nct00000001",
            external_identifiers=(identifier,),
        )


def test_alias_conflict_is_preserved_instead_of_first_match_wins() -> None:
    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import EntityIdentityIndex

    index = EntityIdentityIndex()
    first = EntityIdentity.create(
        entity_type=EntityType.PRODUCT,
        canonical_name="项目甲",
        identity_basis="project-a",
        aliases=("共同别名",),
        external_identifiers=(),
    )
    second = EntityIdentity.create(
        entity_type=EntityType.PRODUCT,
        canonical_name="项目乙",
        identity_basis="project-b",
        aliases=("共同别名",),
        external_identifiers=(),
    )
    index.add(first, evidence_fragment_id="fragment-a")
    index.add(second, evidence_fragment_id="fragment-b")
    resolution = index.resolve_alias("共同别名", entity_type=EntityType.PRODUCT)
    assert resolution.state == "conflicting"
    assert set(resolution.candidate_entity_ids) == {first.entity_id, second.entity_id}
    assert resolution.selected_entity_id is None
    assert resolution.evidence_fragment_ids == ("fragment-a", "fragment-b")


def test_organization_trial_cohort_and_arm_relationships_keep_distinct_identity() -> None:
    from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType

    graph = EntityGraph()
    organization = EntityIdentity.create(EntityType.ORGANIZATION, "企业甲", "org-a")
    trial = EntityIdentity.create(EntityType.TRIAL, "关键试验", "trial-a")
    cohort = EntityIdentity.create(EntityType.COHORT, "扩展队列", "trial-a-cohort-1")
    arm = EntityIdentity.create(EntityType.ARM, "治疗组", "trial-a-arm-1")
    for entity in (organization, trial, cohort, arm):
        graph.add_entity(entity)
    graph.add_relation(EntityRelation.create(organization, "sponsors", trial, "fragment-1"))
    graph.add_relation(EntityRelation.create(trial, "has_cohort", cohort, "fragment-2"))
    graph.add_relation(EntityRelation.create(cohort, "has_arm", arm, "fragment-3"))
    assert len({organization.entity_id, trial.entity_id, cohort.entity_id, arm.entity_id}) == 4
    assert graph.related(trial.entity_id, "has_cohort") == (cohort.entity_id,)
    assert graph.related(cohort.entity_id, "has_arm") == (arm.entity_id,)


def test_product_project_and_regimen_are_distinct_and_keep_nct_and_ctr_identifiers() -> None:
    from ci_workflow.domain.entities import (
        EntityGraph,
        EntityIdentity,
        EntityRelation,
        EntityType,
        ExternalIdentifier,
    )

    product = EntityIdentity.create(EntityType.PRODUCT, "创新药甲", "molecule-a")
    project = EntityIdentity.create(
        EntityType.DRUG_PROJECT,
        "创新药甲—目标适应症开发项目",
        "molecule-a-indication-x",
    )
    regimen = EntityIdentity.create(
        EntityType.REGIMEN,
        "创新药甲联合背景治疗",
        "regimen-a-background",
    )
    trial = EntityIdentity.create(
        EntityType.TRIAL,
        "国际关键试验",
        "trial-a",
        external_identifiers=(
            ExternalIdentifier(namespace="NCT", value="NCT01234567"),
            ExternalIdentifier(namespace="CTR", value="CTR20260001"),
        ),
    )
    graph = EntityGraph()
    for entity in (product, project, regimen, trial):
        graph.add_entity(entity)
    graph.add_relation(EntityRelation.create(product, "has_project", project, "fragment-1"))
    graph.add_relation(EntityRelation.create(project, "uses_regimen", regimen, "fragment-2"))
    graph.add_relation(EntityRelation.create(project, "studied_in", trial, "fragment-3"))

    assert len({product.entity_id, project.entity_id, regimen.entity_id, trial.entity_id}) == 4
    assert {item.namespace for item in trial.external_identifiers} == {"NCT", "CTR"}
    assert graph.related(product.entity_id, "has_project") == (project.entity_id,)
    assert graph.related(project.entity_id, "uses_regimen") == (regimen.entity_id,)


def test_external_identifier_conflict_is_preserved_without_automatic_entity_merge() -> None:
    from ci_workflow.domain.entities import EntityIdentity, EntityType, ExternalIdentifier
    from ci_workflow.ingestion.identity import EntityIdentityIndex

    shared_ctr = ExternalIdentifier(namespace="CTR", value="CTR20260001")
    first = EntityIdentity.create(
        EntityType.TRIAL,
        "登记试验甲",
        "trial-a",
        external_identifiers=(shared_ctr,),
    )
    second = EntityIdentity.create(
        EntityType.TRIAL,
        "登记试验乙",
        "trial-b",
        external_identifiers=(shared_ctr,),
    )
    index = EntityIdentityIndex()
    index.add(first, evidence_fragment_id="fragment-a")
    index.add(second, evidence_fragment_id="fragment-b")

    resolution = index.resolve_external_identifier(
        ExternalIdentifier(namespace="ctr", value="ctr20260001")
    )
    assert resolution.state == "conflicting"
    assert set(resolution.candidate_entity_ids) == {first.entity_id, second.entity_id}
    assert resolution.selected_entity_id is None
    assert resolution.evidence_fragment_ids == ("fragment-a", "fragment-b")


def test_identity_index_rejects_inconsistent_content_for_same_internal_identity() -> None:
    import pytest

    from ci_workflow.domain.entities import EntityIdentity, EntityType
    from ci_workflow.ingestion.identity import EntityIdentityIndex

    original = EntityIdentity.create(EntityType.PRODUCT, "创新药甲", "molecule-a")
    conflicting = EntityIdentity.create(EntityType.PRODUCT, "创新药甲错误名称", "molecule-a")
    index = EntityIdentityIndex()
    index.add(original, evidence_fragment_id="fragment-a")

    with pytest.raises(ValueError, match="同一实体身份对应了不同内容"):
        index.add(conflicting, evidence_fragment_id="fragment-b")
