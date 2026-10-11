"""Replay native date structure; synthetic witnesses do not approve a paper."""

import hashlib

import pytest

from ci_workflow.application import source_research_service as service
from ci_workflow.storage.source_derivation import extract_locator_quote
from tests.integration.test_1007_fact_public_version_cutoff import CUTOFF, URL, _case


def _xml_case(declaration: str, *, path: str | None = None):
    source, fact, proof = _case()
    raw = (
        "<article><front><article-meta>" + declaration + "</article-meta></front>"
        "<body><p>14 (18.4)</p><p>Version1 includes this table</p>"
        "<p>Correction changes copyright only, not this table</p>"
        "<p>2023-05-04</p></body></article>"
    )
    source = source.model_copy(update={"content_text": raw, "media_type": "application/xml"})
    fact = fact.model_copy(update={"locator": fact.locator.model_copy(update={
        "field_path": "/article/body[1]/p[1]",
    })})
    locator = service.EvidenceLocator(document_role="synthetic", url=URL, field_path=path or
        "/article/front[1]/article-meta[1]/pub-date[1]")
    date_quote = extract_locator_quote(raw, media_type=source.media_type, locator=locator)
    proof.update(
        fact_material_sha256=service.fact_version_material_digest(fact),
        source_content_sha256={"paper": hashlib.sha256(raw.encode()).hexdigest()},
        public_by=proof["public_by"].model_copy(update={"locator": locator}),
        public_by_reference={**proof["public_by_reference"],
                             "locator": locator.model_dump(mode="json"),
                             "original_text": date_quote},
    )
    for field, index in [("version_references", 2), ("correction_references", 3)]:
        proof[field][0]["locator"]["field_path"] = f"/article/body[1]/p[{index}]"
    return source, fact, proof


@pytest.mark.parametrize("media", ["application/xml", "text/xml"])
@pytest.mark.parametrize("attributes", [
    'pub-type="epub"', 'date-type="pub" publication-format="electronic"',
])
def test_native_component_date_binds_without_fabricating_an_iso_quote(media, attributes):
    source, fact, proof = _xml_case(
        f"<pub-date {attributes}><year>2023</year><month>05</month><day>04</day></pub-date>",
    )
    source = source.model_copy(update={"media_type": media})
    quote = proof["public_by_reference"]["original_text"]
    assert quote == "20230504" and quote != "2023-05-04"
    before = source.model_dump(mode="json")
    service.validate_research_historical_availability([source], [fact], [proof], CUTOFF)
    assert source.model_dump(mode="json") == before
    assert source.first_disclosed_at is None and source.acquired_at > CUTOFF


@pytest.mark.parametrize("case", [
    "body_iso", "print_only", "partial", "conflicting_days", "wrong_component",
    "wrong_locator", "instant_from_day",
])
def test_native_date_does_not_borrow_text_dates_or_other_metadata(case):
    declaration = '<pub-date pub-type="epub"><year>2023</year><month>05</month><day>04</day>'
    declaration += "</pub-date>"
    path = None
    if case == "body_iso":
        path = "/article/body[1]/p[4]"
    elif case == "print_only":
        declaration = declaration.replace('pub-type="epub"', 'pub-type="ppub"')
    elif case == "partial":
        declaration = declaration.replace("<day>04</day>", "")
    elif case == "conflicting_days":
        declaration += declaration.replace("<day>04</day>", "<day>05</day>")
    elif case == "wrong_component":
        declaration = declaration.replace("<day>04</day>", "<day>05</day>")
    elif case == "wrong_locator":
        declaration = declaration.replace('pub-type="epub"', 'pub-type="ppub"') + declaration
    source, fact, proof = _xml_case(declaration, path=path)
    if case == "instant_from_day":
        proof["public_by"] = proof["public_by"].model_copy(update={"precision": "instant"})
    with pytest.raises(ValueError):
        service.validate_research_historical_availability([source], [fact], [proof], CUTOFF)
