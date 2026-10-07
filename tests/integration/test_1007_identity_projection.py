"""Source-backed common identity, not a renderer name/company dictionary."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from tests.integration.test_1007_identity_public_knowledge import (
    _published_registry as _evidence_registry,
)


@pytest.fixture
def identity_inputs(tmp_path: Path):
    registry = _evidence_registry(tmp_path, ("正式中文名", "mah", "group", "rights", "target"))
    fragments = [item.fragment.fragment_id for item in registry.verified_fragments]
    observed = registry.verified_fragments[0].source_version.acquired_at
    product = EntityIdentity.create(EntityType.PRODUCT, "Original-INN", "molecule-fixture")
    holder = EntityIdentity.create(EntityType.ORGANIZATION, "Foreign Legal Holder", "holder")
    group = EntityIdentity.create(EntityType.ORGANIZATION, "已核集团", "parent-group")
    graph = EntityGraph()
    for entity in (product, holder, group):
        graph.add_entity(entity)
    return graph, registry, fragments, observed, product, holder, group


def test_china_mah_uses_verified_group_without_replacing_foreign_legal_holder(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="已核中国上市许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, "controlled_by", group, fragments[2],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：已核集团｜中国MAH所属集团"
    assert result["companies"][0]["legal_entity_name"] == "Foreign Legal Holder"
    assert result["companies"][0]["evidence_fragment_ids"] == [fragments[1], fragments[2]]
    assert result["entity_id"] == product.entity_id


@pytest.mark.parametrize("predicate", ["collaborates_with", "minority_investment", "licensed_by"])
def test_commercial_relationship_never_becomes_controlling_parent(identity_inputs, predicate):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, predicate, group, fragments[2],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：Foreign Legal Holder｜集团归属待核"
    assert result["companies"][0]["group_entity_id"] is None


def test_unknown_or_future_source_does_not_borrow_sponsor_as_mah(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, _ = identity_inputs
    graph.add_relation(EntityRelation.create(product, "sponsored_by", holder, fragments[1]))
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, "not-reopened",
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司归属待核"
    assert result["companies"] == []
    assert result["unresolved_relations"][0]["reason"] == "source_not_verified"
    past = project_product_identity(product.entity_id, graph, registry,
        cutoff=observed - timedelta(days=1))
    assert past["companies"] == []


def test_official_chinese_name_needs_reopened_evidence_and_keeps_identity(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, _, _ = identity_inputs
    named = product.model_copy(update={"official_chinese_name": "正式中文名",
        "name_evidence_fragment_id": fragments[0]})
    graph.entities[product.entity_id] = named
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["display_name"] == "正式中文名"
    assert result["original_name"] == "Original-INN"
    graph.entities[product.entity_id] = product.model_copy(update={
        "official_chinese_name": "不应采用", "name_evidence_fragment_id": "unverified"})
    assert project_product_identity(product.entity_id, graph, registry,
        cutoff=observed)["display_name"] == "Original-INN"


def test_reopened_unrelated_fragment_does_not_verify_a_chinese_name(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, _, _ = identity_inputs
    graph.entities[product.entity_id] = product.model_copy(update={
        "official_chinese_name": "来源没有的中文名", "name_evidence_fragment_id": fragments[1]})
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["display_name"] == "Original-INN"
    assert result["entity_id"] == product.entity_id


def test_expired_china_license_falls_back_to_explicit_overseas_role(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, _ = identity_inputs
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed,
        effective_until=observed - timedelta(days=1)))
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[3],
        jurisdiction="US", authorization_scope="美国许可", observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：Foreign Legal Holder｜境外MAH（US）"


def test_scope_and_timezone_metadata_are_fail_closed_and_legacy_relation_bytes_stay_compatible():
    product = EntityIdentity.create(EntityType.PRODUCT, "INN", "fixture-legacy")
    holder = EntityIdentity.create(EntityType.ORGANIZATION, "Holder", "fixture-holder")
    legacy = EntityRelation.create(product, "has_mah", holder, "fragment")
    assert "observed_at" not in legacy.model_dump(mode="json")
    assert "official_chinese_name" not in product.model_dump(mode="json")
    with pytest.raises(ValueError, match="时区"):
        EntityRelation.create(product, "has_mah", holder, "fragment",
            observed_at=datetime(2026, 10, 7))
    dated = EntityRelation.create(product, "has_mah", holder, "fragment",
        jurisdiction="CN", observed_at=datetime(2026, 10, 7, tzinfo=UTC))
    assert dated.relation_id != legacy.relation_id


def test_ultimate_group_chain_keeps_all_control_sources_and_legal_holder(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    subsidiary = EntityIdentity.create(EntityType.ORGANIZATION, "Intermediate Legal", "middle")
    graph.add_entity(subsidiary)
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="已核中国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, "controlled_by", subsidiary, fragments[2],
        observed_at=observed))
    graph.add_relation(EntityRelation.create(subsidiary, "controlled_by", group, fragments[3],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：已核集团｜中国MAH所属集团"
    company = result["companies"][0]
    assert company["legal_entity_id"] == holder.entity_id
    assert company["group_entity_id"] == group.entity_id
    assert set(company["evidence_fragment_ids"]) == set(fragments[1:4])
    assert company["group_chain_entity_ids"] == [holder.entity_id, subsidiary.entity_id,
                                                group.entity_id]


@pytest.mark.parametrize("failure", ["conflict", "cycle", "missing_control_source"])
def test_unresolved_group_chain_does_not_claim_an_intermediate_or_guess_group(
    identity_inputs, failure,
):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    intermediate = EntityIdentity.create(EntityType.ORGANIZATION, "Intermediate", "unresolved")
    graph.add_entity(intermediate)
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, "controlled_by", intermediate, fragments[2],
        observed_at=observed))
    if failure == "conflict":
        graph.add_relation(EntityRelation.create(intermediate, "controlled_by", holder,
            fragments[3], observed_at=observed))
        graph.add_relation(EntityRelation.create(intermediate, "controlled_by", group,
            fragments[4], observed_at=observed))
    elif failure == "cycle":
        graph.add_relation(EntityRelation.create(intermediate, "controlled_by", holder,
            fragments[3], observed_at=observed))
    else:
        graph.add_relation(EntityRelation.create(intermediate, "controlled_by", group,
            "not-reopened", observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：Foreign Legal Holder｜集团归属待核"
    assert result["companies"][0]["group_entity_id"] is None
    assert result["unresolved_relations"]


def test_verified_group_itself_as_mah_has_explicit_role_not_subsidiary_label(identity_inputs):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, _, group = identity_inputs
    graph.add_relation(EntityRelation.create(product, "has_mah", group, fragments[1],
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(group, "controlled_by", group, fragments[2],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：已核集团｜中国MAH"
    assert result["companies"][0]["group_chain_entity_ids"] == [group.entity_id]


@pytest.mark.parametrize(("predicate", "jurisdiction", "role", "label"), [
    ("has_mah", "US", "境外MAH（US）", "已核集团｜境外MAH所属集团（US）"),
    ("has_development_rights_holder", "GLOBAL", "研发权益方", "已核集团｜研发权益方所属集团"),
])
def test_non_china_role_uses_verified_group_and_preserves_holder_scope(
    identity_inputs, predicate, jurisdiction, role, label,
):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    graph.add_relation(EntityRelation.create(product, predicate, holder, fragments[1],
        jurisdiction=jurisdiction, authorization_scope="已核许可或研发权益范围",
        observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, "controlled_by", group, fragments[2],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：" + label
    company = result["companies"][0]
    assert company["role"] == role and company["jurisdiction"] == jurisdiction
    assert company["legal_entity_name"] == holder.canonical_name
    assert company["group_entity_id"] == group.entity_id
    assert company["evidence_fragment_ids"] == [fragments[1], fragments[2]]
    assert "中国MAH" not in result["company_label"]


@pytest.mark.parametrize("predicate", ["collaborates_with", "minority_investment"])
def test_overseas_relationship_is_not_guessed_group(identity_inputs, predicate):
    from ci_workflow.reports.common.identity_projection import project_product_identity

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="US", authorization_scope="美国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, predicate, group, fragments[2],
        observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert result["company_label"] == "公司：Foreign Legal Holder｜境外MAH（US）"
    assert result["companies"][0]["group_entity_id"] is None


def test_identity_header_deduplicates_display_not_source_evidence(identity_inputs):
    from ci_workflow.reports.common.identity_projection import (
        project_product_identity,
        render_identity_headers,
    )

    graph, registry, fragments, observed, product, holder, group = identity_inputs
    target = EntityIdentity.create(EntityType.TARGET, "IL-31RA", "receptor-alpha")
    graph.add_entity(target)
    for fragment in fragments[1:3]:
        graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragment,
            jurisdiction="US", authorization_scope="许可范围相同", observed_at=observed))
        graph.add_relation(EntityRelation.create(product, "has_target", target, fragment,
            observed_at=observed))
    for fragment in fragments[3:5]:
        graph.add_relation(EntityRelation.create(holder, "controlled_by", group, fragment,
            authorization_scope="财报版本范围相同", observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    assert len(result["companies"]) == len(result["targets"]) == 2
    html = str(render_identity_headers({"drug": result}))
    assert html.count("IL-31RA") == 1
    assert html.count("持有人法律实体") == 1
    assert html.count("集团关系范围") == 1
    assert html.count("<blockquote>") == len(result["sources"]) == 4
    assert "关系记录日期（含义见范围）" in html and " · 观察于" not in html
    assert len(result["companies"]) == len(result["targets"]) == 2


def test_identity_header_keeps_distinct_authorization_scopes(identity_inputs):
    from ci_workflow.reports.common.identity_projection import (
        project_product_identity,
        render_identity_headers,
    )

    graph, registry, fragments, observed, product, holder, _ = identity_inputs
    for fragment, scope in zip(fragments[1:3], ("适应症甲", "适应症乙"), strict=True):
        graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragment,
            jurisdiction="US", authorization_scope=scope, observed_at=observed))
    result = project_product_identity(product.entity_id, graph, registry, cutoff=observed)
    html = str(render_identity_headers({"drug": result}))
    assert "适应症甲" in html and "适应症乙" in html
    assert html.count("持有人法律实体") == 2
