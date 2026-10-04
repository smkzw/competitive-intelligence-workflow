"""分组生产调用测试：原生 JATS XML 身份/正文巡检的有界行为。

用便携合成 XML 直接调用生产 API，不触碰私有方法、不读取 r24-187 私有路径、
不注入测试时钟或身份旁路。真实 CAS 回放只在独立运行时回执中进行，正文
不进入本文件或 Git。
"""

from __future__ import annotations

import hashlib

import pytest

from ci_workflow.sources.connectors.linked_jats import (
    LinkedJatsBoundsError,
    LinkedJatsIdentityError,
    LinkedJatsInspection,
    LinkedJatsStructureError,
    LinkedJatsXmlError,
    inspect_linked_jats_xml,
)

DOI = "10.1234/example.2026.001"
PMCID = "PMC7654321"
PMID = "31415926"

_NESTED_UNRELATED_IDS = (
    '<related-article related-article-type="companion">'
    '<article-id pub-id-type="doi">10.9999/nested-wrong-doi</article-id>'
    '<pub-id pub-id-type="pmid">88888888</pub-id>'
    "</related-article>"
)

_REFERENCE_IDS = (
    "<back><ref-list><ref><mixed-citation>"
    '<pub-id pub-id-type="doi">10.9999/unrelated.reference</pub-id>'
    '<pub-id pub-id-type="pmid">99999999</pub-id>'
    '<pub-id pub-id-type="pmcid">PMC0000000</pub-id>'
    "</mixed-citation></ref></ref-list></back>"
)

_PERMISSIONS = (
    "<permissions><copyright-statement>© The Author(s) 2026</copyright-statement>"
    '<license license-type="open-access"><license-p>This article is licensed under a '
    "Creative Commons Attribution 4.0 International License.</license-p></license>"
    "</permissions>"
)


def _article(
    *,
    doi: str | None = DOI,
    pmcid: str | None = PMCID,
    pmid: str | None = PMID,
    body: str | None = None,
    meta_extra: str = "",
    permissions: str | None = _PERMISSIONS,
) -> str:
    ids = ""
    if doi is not None:
        ids += f'<article-id pub-id-type="doi">{doi}</article-id>'
    if pmcid is not None:
        ids += f'<article-id pub-id-type="pmcid">{pmcid}</article-id>'
    if pmid is not None:
        ids += f'<article-id pub-id-type="pmid">{pmid}</article-id>'
    return (
        "<article><front><journal-meta><journal-title-group>"
        "<journal-title>Test Journal</journal-title></journal-title-group></journal-meta>"
        "<article-meta><title-group><article-title>A randomized clinical trial"
        "</article-title></title-group>"
        f"{ids}{meta_extra}{permissions or ''}"
        "</article-meta></front>"
        f"{body or ''}{_REFERENCE_IDS}</article>"
    )


def _wrapped(inner: str, wrapper: str = "pmc-articleset") -> str:
    return f"<{wrapper}>{inner}</{wrapper}>"


def _inspect(xml: str) -> LinkedJatsInspection:
    return inspect_linked_jats_xml(
        xml.encode("utf-8"),
        expected_pmid=PMID,
        expected_pmcid=PMCID,
        expected_doi=DOI,
    )


def test_direct_article_exact_identity_reports_ordered_nonempty_blocks() -> None:
    body = (
        "<body><sec><p>First paragraph.</p>"
        "<table-wrap><label>Table 1</label>"
        "<caption><p>Baseline characteristics.</p></caption>"
        "<table><tbody><tr><td>42</td></tr></tbody></table></table-wrap>"
        "<p>Second paragraph.</p></sec></body>"
    )
    xml = _article(body=body)
    result = _inspect(xml)
    assert result.doi == DOI
    assert result.pmcid == PMCID
    assert result.pmid == PMID
    assert result.title == "A randomized clinical trial"
    assert result.permissions_present is True
    assert result.body_state == "body_present"
    assert result.has_paragraphs is True
    assert result.has_tables is True
    assert [block.kind for block in result.blocks] == ["paragraph", "table", "paragraph"]
    assert [block.ordinal for block in result.blocks] == [0, 1, 2]
    assert result.blocks[0].text == "First paragraph."
    assert "Baseline characteristics." in result.blocks[1].text
    assert result.blocks[2].text == "Second paragraph."
    assert result.raw_byte_size == len(xml.encode("utf-8"))
    assert result.raw_sha256 == hashlib.sha256(xml.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("wrapper", ["pmc-articleset", "articleset", "article-set"])
def test_known_wrapper_with_single_direct_article_is_accepted(wrapper: str) -> None:
    xml = _wrapped(_article(body="<body><p>Prose.</p></body>"), wrapper)
    result = _inspect(xml)
    assert result.body_state == "body_present"
    assert result.has_paragraphs is True
    assert result.doi == DOI


@pytest.mark.parametrize("wrapper", ["pmc-articleset", "article-set"])
def test_wrapped_metadata_only_front_is_not_parse_failure_or_fulltext(wrapper: str) -> None:
    result = _inspect(_wrapped(_article(body=None), wrapper))
    assert result.body_state == "metadata_only"
    assert result.body_detail
    assert result.blocks == ()
    assert result.has_paragraphs is False
    assert result.has_tables is False
    assert result.doi == DOI
    assert result.pmcid == PMCID
    assert result.pmid == PMID


@pytest.mark.parametrize(
    "body",
    ["<body/>", "<body></body>", "<body><sec><title>Intro</title></sec></body>"],
)
def test_body_without_nonempty_content_is_metadata_only(body: str) -> None:
    result = _inspect(_article(body=body))
    assert result.body_state == "metadata_only"
    assert result.blocks == ()


def test_missing_front_pmid_is_explicit_and_not_borrowed() -> None:
    result = _inspect(_article(pmid=None))
    assert result.pmid is None
    assert any("PMID" in note for note in result.notes)
    assert result.doi == DOI
    assert result.pmcid == PMCID


def test_undeclared_expected_pmid_surfaces_front_pmid_without_mismatch() -> None:
    result = inspect_linked_jats_xml(
        _article().encode("utf-8"),
        expected_pmid=None,
        expected_pmcid=PMCID,
        expected_doi=DOI,
    )
    assert result.pmid == PMID


def test_nested_related_article_and_reference_ids_are_not_borrowed() -> None:
    result = _inspect(_article(meta_extra=_NESTED_UNRELATED_IDS))
    assert result.doi == DOI
    assert result.pmcid == PMCID
    assert result.pmid == PMID
    assert "10.9999" not in result.doi


def test_missing_front_doi_is_rejected_even_when_nested_identities_exist() -> None:
    with pytest.raises(LinkedJatsIdentityError):
        _inspect(_article(doi=None, meta_extra=_NESTED_UNRELATED_IDS))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("doi", "10.1234/some-other-article"),
        ("pmcid", "PMC0000001"),
        ("pmid", "10000002"),
    ],
)
def test_mismatched_front_identity_is_rejected(field: str, value: str) -> None:
    overrides: dict[str, str] = {field: value}
    with pytest.raises(LinkedJatsIdentityError) as excinfo:
        _inspect(_article(**overrides))
    assert excinfo.value.reason == "identity"
    assert excinfo.value.diagnostic


def test_missing_front_doi_is_rejected() -> None:
    with pytest.raises(LinkedJatsIdentityError):
        _inspect(_article(doi=None))


def test_missing_front_pmcid_is_rejected() -> None:
    with pytest.raises(LinkedJatsIdentityError):
        _inspect(_article(pmcid=None))


def test_front_without_any_article_ids_is_rejected() -> None:
    article_meta = (
        "<article-meta><title-group><article-title>No ids</article-title></title-group>"
        "</article-meta>"
    )
    xml = f"<article><front>{article_meta}</front>{_REFERENCE_IDS}</article>"
    with pytest.raises(LinkedJatsIdentityError):
        _inspect(xml)


def test_identical_duplicate_front_ids_are_accepted() -> None:
    extra = (
        f'<article-id pub-id-type="doi">{DOI}</article-id>'
        f'<article-id pub-id-type="pmcid">{PMCID}</article-id>'
    )
    result = _inspect(_article(meta_extra=extra))
    assert result.doi == DOI


@pytest.mark.parametrize(
    "conflict",
    [
        '<article-id pub-id-type="doi">10.9999/conflicting-doi</article-id>',
        '<article-id pub-id-type="pmcid">PMC0000000</article-id>',
        '<article-id pub-id-type="pmid">10000001</article-id>',
    ],
)
def test_conflicting_duplicate_front_identity_is_rejected(conflict: str) -> None:
    with pytest.raises(LinkedJatsIdentityError) as excinfo:
        _inspect(_article(meta_extra=conflict))
    assert excinfo.value.reason == "identity"


def test_wrapper_with_two_articles_is_rejected_as_ambiguous() -> None:
    xml = f"<pmc-articleset>{_article()}{_article()}</pmc-articleset>"
    with pytest.raises(LinkedJatsStructureError):
        _inspect(xml)


def test_wrapper_with_non_direct_article_is_rejected() -> None:
    xml = f"<pmc-articleset><response>{_article()}</response></pmc-articleset>"
    with pytest.raises(LinkedJatsStructureError):
        _inspect(xml)


def test_unknown_root_or_namespaced_article_is_rejected() -> None:
    roots = (
        "<html><body>not jats</body></html>",
        '<jats:article xmlns:jats="http://example.invalid/jats">x</jats:article>',
    )
    for xml in roots:
        with pytest.raises(LinkedJatsStructureError):
            _inspect(xml)


def test_multiple_article_meta_is_rejected() -> None:
    article_meta = (
        "<article-meta><title-group><article-title>Duplicate</article-title></title-group>"
        f'<article-id pub-id-type="doi">{DOI}</article-id>'
        f'<article-id pub-id-type="pmcid">{PMCID}</article-id></article-meta>'
    )
    xml = f"<article><front>{article_meta}{article_meta}</front></article>"
    with pytest.raises(LinkedJatsStructureError):
        _inspect(xml)


def test_empty_bytes_are_rejected_before_parsing() -> None:
    with pytest.raises(LinkedJatsBoundsError):
        inspect_linked_jats_xml(
            b"",
            expected_pmid=PMID,
            expected_pmcid=PMCID,
            expected_doi=DOI,
        )


def test_bytes_over_budget_are_rejected_before_parsing() -> None:
    raw = _article().encode("utf-8")
    with pytest.raises(LinkedJatsBoundsError):
        inspect_linked_jats_xml(
            raw,
            expected_pmid=PMID,
            expected_pmcid=PMCID,
            expected_doi=DOI,
            max_bytes=len(raw) - 1,
        )


@pytest.mark.parametrize(
    "raw",
    [
        b"<article><front></front>",
        b"not xml at all",
        b"<article><front><article-meta></article-meta></front></article",
        b"\x00\x01\x02",
    ],
)
def test_malformed_bytes_are_rejected(raw: bytes) -> None:
    with pytest.raises(LinkedJatsXmlError):
        inspect_linked_jats_xml(
            raw,
            expected_pmid=PMID,
            expected_pmcid=PMCID,
            expected_doi=DOI,
        )


def test_official_nlm_doctype_declaration_is_accepted() -> None:
    prolog = (
        '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and '
        'Interchange DTD v1.4 20241031//EN" "JATS-journalpublishing1-4.dtd">'
    )
    xml = f"{prolog}{_article(body='<body><p>Prose.</p></body>')}"
    result = _inspect(xml)
    assert result.body_state == "body_present"
    assert result.has_paragraphs is True
    assert result.doi == DOI


def test_entity_declaration_is_rejected() -> None:
    raw = (
        b'<?xml version="1.0"?><!DOCTYPE article [<!ENTITY boom "expanded">]>'
        b"<article><front>&boom;</front></article>"
    )
    with pytest.raises(LinkedJatsXmlError) as excinfo:
        inspect_linked_jats_xml(
            raw,
            expected_pmid=PMID,
            expected_pmcid=PMCID,
            expected_doi=DOI,
        )
    assert excinfo.value.reason == "malformed_xml"


def test_table_cell_and_figure_paragraphs_are_not_paragraph_blocks() -> None:
    body = (
        "<body><table-wrap><caption><p>Caption prose.</p></caption>"
        "<table><tbody><tr><td><p>Cell prose.</p></td></tr></tbody></table></table-wrap>"
        "<fig><caption><p>Figure caption.</p></caption></fig></body>"
    )
    result = _inspect(_article(body=body))
    assert result.has_tables is True
    assert result.has_paragraphs is False
    assert [block.kind for block in result.blocks] == ["table"]
    assert "Caption prose." in result.blocks[0].text
    assert "Cell prose." in result.blocks[0].text


def test_table_rows_without_caption_preserve_content_in_a_table_block() -> None:
    body = "<body><table-wrap><table><tbody><tr><td>1</td></tr></tbody></table></table-wrap></body>"
    result = _inspect(_article(body=body))
    assert result.body_state == "body_present"
    assert result.has_tables is True
    assert len(result.blocks) == 1
    assert result.blocks[0].kind == "table"
    assert result.blocks[0].text == "1"


def test_table_anchored_inside_paragraph_is_still_available() -> None:
    body = (
        "<body><sec><p>Text before the float."
        "<table-wrap><caption><p>Anchored caption.</p></caption>"
        "<table><tbody><tr><td>7</td></tr></tbody></table></table-wrap>"
        "Text after the float.</p></sec></body>"
    )
    result = _inspect(_article(body=body))
    assert result.has_tables is True
    assert [block.kind for block in result.blocks] == ["paragraph", "table"]
    assert result.blocks[0].text == "Text before the float. Text after the float."
    assert "Anchored caption." in result.blocks[1].text


def test_permissions_license_and_copyright_text_are_preserved() -> None:
    result = _inspect(_article())
    assert result.permissions_present is True
    assert result.copyright_statement == "© The Author(s) 2026"
    assert len(result.license_texts) == 1
    assert "Creative Commons Attribution 4.0" in result.license_texts[0]


def test_missing_permissions_is_explicit_empty_not_guessed() -> None:
    result = _inspect(_article(permissions=None))
    assert result.permissions_present is False
    assert result.copyright_statement is None
    assert result.license_texts == ()


def test_invalid_expected_identity_arguments_are_rejected() -> None:
    raw = _article().encode("utf-8")
    with pytest.raises(ValueError):
        inspect_linked_jats_xml(raw, PMID, PMCID, "")
    with pytest.raises(ValueError):
        inspect_linked_jats_xml(raw, PMID, "PMC", DOI)
    with pytest.raises(ValueError):
        inspect_linked_jats_xml(raw, "", PMCID, DOI)


def test_non_bytes_raw_and_invalid_budget_are_rejected() -> None:
    with pytest.raises(TypeError):
        inspect_linked_jats_xml("not bytes", PMID, PMCID, DOI)  # type: ignore[arg-type]
    raw = _article().encode("utf-8")
    with pytest.raises(ValueError):
        inspect_linked_jats_xml(raw, PMID, PMCID, DOI, max_bytes=0)
    with pytest.raises(ValueError):
        inspect_linked_jats_xml(raw, PMID, PMCID, DOI, max_bytes=True)


def test_body_present_and_metadata_only_do_not_claim_completeness_or_rights() -> None:
    present = _inspect(_article(body="<body><p>Prose.</p></body>"))
    assert any("完整" in item for item in present.limitations)
    assert any("再分发" in item for item in present.limitations)
    metadata = _inspect(_article(body=None))
    assert any("不能等同" in item for item in metadata.limitations)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-be"])
def test_owner_encoded_entity_declaration_is_rejected_before_expansion(encoding: str) -> None:
    xml = ('<?xml version="1.0" encoding="UTF-16"?>'
           '<!DOCTYPE article [<!ENTITY clinical "invented clinical value">]>'
           + _article(body="<body><p>&clinical;</p></body>"))
    with pytest.raises(LinkedJatsXmlError, match="实体"):
        inspect_linked_jats_xml(xml.encode(encoding), PMID, PMCID, DOI)


def test_owner_empty_table_skeleton_is_not_body_content() -> None:
    result = _inspect(_article(body="<body><table-wrap><table><tr><td/>"
                                   "</tr></table></table-wrap></body>"))
    assert result.body_state == "metadata_only"
    assert result.has_tables is False
    assert result.blocks == ()


def test_owner_table_labels_cells_and_values_are_preserved_without_deriving_facts() -> None:
    body = ("<body><table-wrap><label>Table 2</label><caption><p>Response</p></caption>"
            "<table><thead><tr><th>Group</th><th>Estimate</th><th>n/N</th></tr></thead>"
            "<tbody><tr><td>Active</td><td>82.3%</td><td>51/60</td></tr>"
            "<tr><td>Control</td><td>not reported</td><td>0/0</td></tr></tbody></table>"
            "<table-wrap-foot><p>Model estimate is not a fraction.</p></table-wrap-foot>"
            "</table-wrap></body>")
    result = _inspect(_article(body=body))
    text = result.blocks[0].text
    for token in ("Table 2", "Response", "Group", "Estimate", "n/N", "Active",
                  "82.3%", "51/60", "Control", "not reported", "0/0",
                  "Model estimate is not a fraction."):
        assert token in text
    assert "Active | 82.3% | 51/60" in text
    assert "Control | not reported | 0/0" in text
