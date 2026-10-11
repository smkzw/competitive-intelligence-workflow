"""Native identity/version/copyright/change witnesses replay exactly; no adoption.

The storage locator must re-extract the declared native JATS metadata witness
nodes (front[1]/article-meta[1] rooted article-id / pmc-version / copyright
statement / pub-history event dates) with the same bounded byte, depth, path
and entity guards as body quotes. Replaying a change date proves only that
node's text and must never qualify a public date.
"""

import hashlib

import pytest

from ci_workflow.application import source_research_service as service
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    extract_locator_quote,
)
from tests.integration.test_1007_fact_public_version_cutoff import CUTOFF, URL, _case

META = "/article/front[1]/article-meta[1]"
RAW = (
    "<article><front><article-meta>"
    '<article-id pub-id-type="pmcid">PMC10202800</article-id>'
    '<article-id pub-id-type="pmcid-ver">PMC10202800.1</article-id>'
    '<article-id pub-id-type="pmid">37142763</article-id>'
    '<article-id pub-id-type="doi">10.1038/s41591-023-02320-9</article-id>'
    '<article-id pub-id-type="publisher-id">2320</article-id>'
    '<article-version article-version-type="pmc-version">1</article-version>'
    '<pub-date pub-type="epub"><year>2023</year><month>05</month><day>04</day></pub-date>'
    "<permissions>"
    "<copyright-statement>© The Author(s) 2023, corrected publication 2023</copyright-statement>"
    "<license><p>CC BY 4.0</p></license></permissions>"
    '<history><date date-type="accepted">01012023</date></history>'
    "<pub-history>"
    '<event event-type="pmc-release"><date>04052023</date></event>'
    '<event event-type="pmc-live"><date>24052023</date></event>'
    '<event event-type="pmc-last-change">'
    '<date iso-8601-date="2025-05-07 15:25:14.047">07052025</date></event>'
    "</pub-history>"
    "</article-meta></front>"
    "<body><p>14 (18.4)</p><p>Version1 includes this table</p>"
    "<p>Correction changes copyright only, not this table</p>"
    "<p>2023-05-04</p>"
    '<ref><article-id pub-id-type="doi">10.1000/reference-identity</article-id></ref>'
    "</body></article>"
)
WITNESSES = [
    (f"{META}/article-id[1]", "PMC10202800"),
    (f"{META}/article-id[2]", "PMC10202800.1"),
    (f"{META}/article-id[3]", "37142763"),
    (f"{META}/article-id[4]", "10.1038/s41591-023-02320-9"),
    (f"{META}/article-version[1]", "1"),
    (
        f"{META}/permissions[1]/copyright-statement[1]",
        "© The Author(s) 2023, corrected publication 2023",
    ),
    (f"{META}/pub-history[1]/event[1]/date[1]", "04052023"),
    (f"{META}/pub-history[1]/event[2]/date[1]", "24052023"),
    (f"{META}/pub-history[1]/event[3]/date[1]", "07052025"),
]


def quote(xml: str, path: str, media: str = "application/xml") -> str:
    return extract_locator_quote(xml, media_type=media, locator=EvidenceLocator(
        document_role="original_linked_publication", field_path=path,
    ))


@pytest.mark.parametrize("media", ["application/xml", "text/xml"])
@pytest.mark.parametrize("path,expected", WITNESSES)
def test_native_witness_nodes_replay_exact_text(media: str, path: str, expected: str) -> None:
    assert quote(RAW, path, media) == expected


def test_witness_path_replays_through_known_single_article_wrapper() -> None:
    assert quote("<pmc-articleset>" + RAW + "</pmc-articleset>",
                 f"{META}/article-version[1]") == "1"


@pytest.mark.parametrize("path", [
    f"{META}/article-id[6]",
    f"{META}/article-id[5]",
    f"{META}/article-version[2]",
    f"{META}/permissions[1]/copyright-statement[2]",
    f"{META}/permissions[2]/copyright-statement[1]",
    f"{META}/pub-history[1]/event[4]/date[1]",
    f"{META}/pub-history[1]/event[1]/date[2]",
    f"{META}/history[1]/date[1]",
    "/article/body[1]/ref[1]/article-id[1]",
    f"{META}/pub-history[1]/event[1]",
    META,
])
def test_wrong_scope_or_absent_index_never_falls_back_to_nearby_text(path: str) -> None:
    with pytest.raises(SourceDerivationError):
        quote(RAW, path)


@pytest.mark.parametrize("xml,path", [
    (RAW.replace('article-version-type="pmc-version"', 'article-version-type="version"'),
     f"{META}/article-version[1]"),
    (RAW.replace(' article-version-type="pmc-version"', ""), f"{META}/article-version[1]"),
    (RAW.replace('event-type="pmc-last-change"', 'event-type="corrected"'),
     f"{META}/pub-history[1]/event[3]/date[1]"),
    (RAW.replace('<event event-type="pmc-live">', "<event>"),
     f"{META}/pub-history[1]/event[2]/date[1]"),
])
def test_unrecognized_version_or_event_attributes_are_rejected(xml: str, path: str) -> None:
    with pytest.raises(SourceDerivationError):
        quote(xml, path)


@pytest.mark.parametrize("xml", [
    '<!DOCTYPE article [<!ENTITY leak "PMC10202800">]>' + RAW,
    "<article><front><article-meta>" + '<article-id pub-id-type="doi">',
])
def test_entity_or_malformed_xml_stays_rejected_for_witness_paths(xml: str) -> None:
    with pytest.raises(SourceDerivationError):
        quote(xml, f"{META}/article-id[1]")


def test_existing_body_and_publication_date_paths_are_unchanged() -> None:
    assert quote(RAW, "/article/body[1]/p[1]") == "14 (18.4)"
    assert quote(RAW, f"{META}/pub-date[1]") == "20230504"


def _witness_ref(reference_id: str, path: str, text: str) -> dict[str, object]:
    return {
        "reference_id": reference_id,
        "source_id": "paper",
        "label_zh": "版本证据",
        "locator": {"document_role": "synthetic", "field_path": path, "url": URL},
        "original_text": text,
    }


def _native_case():
    source, fact, proof = _case()
    source = source.model_copy(update={"content_text": RAW, "media_type": "application/xml"})
    fact = fact.model_copy(update={"locator": fact.locator.model_copy(update={
        "field_path": "/article/body[1]/p[1]",
    })})
    proof.update(
        fact_material_sha256=service.fact_version_material_digest(fact),
        source_content_sha256={"paper": hashlib.sha256(RAW.encode()).hexdigest()},
        version_references=[
            _witness_ref("version", f"{META}/article-version[1]", "1"),
            _witness_ref("copyright", f"{META}/permissions[1]/copyright-statement[1]",
                         "© The Author(s) 2023, corrected publication 2023"),
        ],
        correction_references=[
            _witness_ref("change", f"{META}/pub-history[1]/event[3]/date[1]", "07052025"),
        ],
    )
    return source, fact, proof


def test_publication_date_witnesses_leave_inputs_immutable() -> None:
    source, fact, proof = _native_case()
    locator = EvidenceLocator(document_role="synthetic", url=URL, field_path=f"{META}/pub-date[1]")
    proof["public_by"] = proof["public_by"].model_copy(update={"locator": locator})
    proof["public_by_reference"] = {
        **proof["public_by_reference"],
        "locator": locator.model_dump(mode="json"),
        "original_text": "20230504",
    }
    before = (source.model_dump(mode="json"), fact.model_dump(mode="json"),
              dict(proof))
    service.validate_research_historical_availability([source], [fact], [proof], CUTOFF)
    assert (source.model_dump(mode="json"), fact.model_dump(mode="json"), dict(proof)) == before
    assert source.first_disclosed_at is None and source.acquired_at > CUTOFF


def test_replayed_change_date_never_qualifies_as_public_by() -> None:
    source, fact, proof = _native_case()
    locator = EvidenceLocator(
        document_role="synthetic", url=URL, field_path=f"{META}/pub-history[1]/event[3]/date[1]",
    )
    proof["public_by"] = proof["public_by"].model_copy(update={"locator": locator})
    proof["public_by_reference"] = {
        **proof["public_by_reference"],
        "locator": locator.model_dump(mode="json"),
        "original_text": "07052025",
    }
    with pytest.raises(ValueError, match="公开日与引用日期不一致"):
        service.validate_research_historical_availability([source], [fact], [proof], CUTOFF)
