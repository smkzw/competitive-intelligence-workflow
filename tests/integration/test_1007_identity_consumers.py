"""Ordinary portal consumers read one source-bound identity, never name guesses."""

import json
from pathlib import Path

import pytest

from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from tests.integration.test_1007_identity_public_knowledge import (
    _published_registry as _evidence_registry,
)


@pytest.fixture
def identity_context(tmp_path):
    from ci_workflow.reports.common.identity_projection import PortalIdentityContext

    evidence = _evidence_registry(tmp_path, ("正式中文名", "mah", "group", "IL-31RA"))
    fragments = [item.fragment.fragment_id for item in evidence.verified_fragments]
    observed = evidence.verified_fragments[0].source_version.acquired_at
    product = EntityIdentity.create(EntityType.PRODUCT, "Original-INN", "test-drug",
        official_chinese_name="正式中文名", name_evidence_fragment_id=fragments[0])
    holder = EntityIdentity.create(EntityType.ORGANIZATION, "Foreign Holder", "test-holder")
    group = EntityIdentity.create(EntityType.ORGANIZATION, "已核集团", "test-group")
    graph = EntityGraph()
    for entity in (product, holder, group):
        graph.add_entity(entity)
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, fragments[1],
        jurisdiction="CN", authorization_scope="中国许可", observed_at=observed))
    graph.add_relation(EntityRelation.create(holder, "controlled_by", group, fragments[2],
        observed_at=observed))
    return PortalIdentityContext(graph, evidence, {"fixture-product": product.entity_id}), observed


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_ordinary_summary_and_product_dossier_share_identity_without_changing_input(
    tmp_path: Path, identity_context, kind,
):
    from dataclasses import replace

    from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
    from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

    context, cutoff = identity_context
    root = Path(__file__).resolve().parents[2]
    fixture = ("fixtures/positive/c-atopic-dermatitis/inputs/report-data.json" if kind == "C"
               else "fixtures/synthetic/a-complete/inputs/report-data.json")
    raw = json.loads((root / fixture).read_text())
    raw["data_cutoff"] = cutoff.isoformat()
    model, render = {"A": (ReportAPortalData, render_report_a_site),
                     "B": (ReportBPortalData, render_report_b_site),
                     "C": (ReportCPortalData, render_report_c_site)}[kind]
    if kind == "C":
        context = replace(context, product_entity_ids={raw["products"][0]["id"]:
            context.product_entity_ids["fixture-product"]})
    data = model.model_validate(raw)
    before = data.model_dump_json()
    render(data, tmp_path / kind, identity_context=context)
    assert data.model_dump_json() == before
    detail = (f'trials/{raw["trials"][0]["id"]}.html' if kind == "C"
              else "products/fixture-product.html")
    for path in ("overview.html", detail):
        html = (tmp_path / kind / path).read_text()
        assert "正式中文名" in html and "Original-INN" in html
        assert "公司：已核集团｜中国MAH所属集团" in html
        assert "Foreign Holder" in html
        assert "持有人法律实体" in html and "中国许可" in html
    assert (tmp_path / kind / "data/identity-projection.json").exists()


def test_unknown_mapping_is_refused_without_creating_a_portal(tmp_path, identity_context):
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site

    context, cutoff = identity_context
    root = Path(__file__).resolve().parents[2]
    raw = json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    raw["data_cutoff"] = cutoff.isoformat()
    context.product_entity_ids["not-a-report-product"] = (
        context.product_entity_ids["fixture-product"]
    )
    with pytest.raises(ValueError, match="产品"):
        render_report_b_site(ReportBPortalData.model_validate(raw), tmp_path / "rejected",
                             identity_context=context)
    assert not (tmp_path / "rejected").exists()


def test_source_identity_strings_are_html_text_not_executable(tmp_path, identity_context):
    from ci_workflow.reports.common.identity_projection import render_identity_headers

    context, cutoff = identity_context
    headers = context.project(("fixture-product",), cutoff=cutoff)
    headers["fixture-product"]["company_label"] = '<img src=x onerror="attack()">'
    html = str(render_identity_headers(headers))
    assert "<img" not in html and "&lt;img" in html


def test_renderer_never_replaces_a_source_name_using_product_id_alone():
    from ci_workflow.renderers.portal.report_a import ReportAPortalData, _display_products

    root = Path(__file__).resolve().parents[2]
    raw = json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text())
    raw["products"][0].update(id="amlitelimab", name="Original development code")
    for collection in ("trials", "efficacy", "safety", "regulatory", "companies", "patents",
                       "history"):
        for row in raw[collection]:
            if row.get("product_id") == "fixture-product":
                row["product_id"] = "amlitelimab"
    data = ReportAPortalData.model_validate(raw)
    assert _display_products(data)[0].name == "Original development code"


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_verified_target_reaches_report_data_filters_and_search_not_just_header(
    tmp_path: Path, identity_context, kind,
):
    from dataclasses import replace

    from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
    from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

    context, cutoff = identity_context
    target = EntityIdentity.create(EntityType.TARGET, "IL-31RA", "target-test")
    context.graph.add_entity(target)
    fragment = context.evidence.verified_fragments[3].fragment.fragment_id
    entity = context.graph.entities[context.product_entity_ids["fixture-product"]]
    context.graph.add_relation(EntityRelation.create(
        entity, "has_target", target, fragment, observed_at=cutoff))
    root = Path(__file__).resolve().parents[2]
    fixture = ("fixtures/positive/c-atopic-dermatitis/inputs/report-data.json" if kind == "C"
               else "fixtures/synthetic/a-complete/inputs/report-data.json")
    raw = json.loads((root / fixture).read_text())
    raw["data_cutoff"] = cutoff.isoformat()
    raw["products"][0]["target"] = "靶点待核"
    if kind == "C":
        context = replace(context, product_entity_ids={raw["products"][0]["id"]: entity.entity_id})
    model, render = {"A": (ReportAPortalData, render_report_a_site),
                     "B": (ReportBPortalData, render_report_b_site),
                     "C": (ReportCPortalData, render_report_c_site)}[kind]
    data = model.model_validate(raw)
    original = data.model_dump_json()
    site = tmp_path / kind
    render(data, site, identity_context=context)
    report = json.loads((site / "data/report.js").read_text().split("=", 1)[1].rstrip(" ;\n"))
    assert report["products"][0]["target"] == "IL-31RA"
    assert "IL-31RA" in (site / "data/search-index.js").read_text()
    assert data.model_dump_json() == original


def test_display_target_projection_deduplicates_proofs_without_inventing_mechanism():
    from ci_workflow.reports.common.identity_projection import identity_product_display_updates

    headers = {"drug": {"display_name": "合成药", "targets": [
        {"entity_id": "t2", "name": "IL-31RA", "evidence_fragment_id": "f1"},
        {"entity_id": "t1", "name": "IL-4Rα", "evidence_fragment_id": "f2"},
        {"entity_id": "t2", "name": "IL-31RA", "evidence_fragment_id": "f3"}]}}
    updates = identity_product_display_updates("drug", headers)
    assert updates == {"name": "合成药", "target": "IL-4Rα；IL-31RA"}
    assert len(headers["drug"]["targets"]) == 3
    assert identity_product_display_updates("unbound", headers) == {}
    assert identity_product_display_updates("empty", {"empty": {
        "display_name": "Original-INN", "targets": []}}) == {"name": "Original-INN"}
