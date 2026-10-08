"""生产回归族 1007：声明电子出版日的可选精确读取。

显式开关开启时，生产桥只读取身份已核验原件 ``front/article-meta`` 直接子
``pub-date`` 中完整的电子出版自然日；默认调用保持原行为。旧版
``pub-type="epub"`` 与现代 ``date-type="pub" publication-format="electronic"``
是同一声明的两代写法。部分日期保持未知（不补 1 日），互不相同的完整日期与
非法完整日期在写入原件前显式拒绝；history、pmc-release、印刷日、参考文献与
正文日期从不借用。只使用便携合成 XML 与 tmp_path，不读取真实来源回执或私有路径。
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from ci_workflow.application import source_research_service as service
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.sources.connectors.linked_jats import (
    LinkedJatsIdentityError,
    LinkedJatsInspection,
    LinkedJatsXmlError,
)
from ci_workflow.storage.source_derivation import SourceDerivationError, extract_locator_quote

PMID = "31415926"
PMC = "PMC7654321"
DOI = "10.1234/example"
ACQUIRED = datetime(2026, 10, 4, tzinfo=UTC)
URL = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{PMC}/fullTextXML"
PUB_DATE_PATH = "/article/front[1]/article-meta[1]/pub-date[{index}]"
_PATH_STEP = re.compile(r"([A-Za-z][A-Za-z0-9_-]*)\[([1-9][0-9]*)\]")


def _epub(year: int, month: int, day: int) -> str:
    return (
        '<pub-date pub-type="epub">'
        f"<year>{year}</year><month>{month:02d}</month><day>{day:02d}</day>"
        "</pub-date>"
    )


def _modern(year: int, month: int, day: int) -> str:
    return (
        '<pub-date date-type="pub" publication-format="electronic">'
        f"<year>{year}</year><month>{month:02d}</month><day>{day:02d}</day>"
        "</pub-date>"
    )


def _ppub(year: int, month: int, day: int) -> str:
    return (
        '<pub-date pub-type="ppub">'
        f"<year>{year}</year><month>{month:02d}</month><day>{day:02d}</day>"
        "</pub-date>"
    )


def _raw(
    *,
    meta_extra: str = "",
    body: str = "<body><p>Observed content.</p></body>",
    back: str = "",
) -> bytes:
    return (
        "<pmc-articleset><article><front><article-meta>"
        f'<article-id pub-id-type="pmid">{PMID}</article-id>'
        f'<article-id pub-id-type="pmc">{PMC}</article-id>'
        f'<article-id pub-id-type="doi">{DOI}</article-id>'
        "<title-group><article-title>Declared date source</article-title></title-group>"
        f"{meta_extra}"
        "</article-meta></front>"
        f"{body}{back}"
        "</article></pmc-articleset>"
    ).encode()


def _capture(
    root: Path,
    raw: bytes,
    *,
    declared: bool | None = None,
    expected_doi: str = DOI,
    expected_pmid: str | None = PMID,
    expected_pmcid: str = PMC,
) -> tuple[LinkedJatsInspection, service.SourceCapture | None]:
    """调用生产桥；declared=None 时按默认签名调用，验证默认行为逐字不变。"""
    options = {} if declared is None else {"use_declared_publication_date": declared}
    return service.source_capture_from_linked_jats_xml(
        root,
        raw,
        expected_pmid=expected_pmid,
        expected_pmcid=expected_pmcid,
        expected_doi=expected_doi,
        url=URL,
        acquired_at=ACQUIRED,
        media_type="application/xml",
        **options,
    )


def _resolve_xml_path(raw: bytes, field_path: str) -> ET.Element:
    """按既有精确 JATS 定位约定重放路径：同名直接子元素一基序号。"""
    node = next(element for element in ET.fromstring(raw).iter() if element.tag == "article")
    for part in field_path.removeprefix("/article/").split("/"):
        match = _PATH_STEP.fullmatch(part)
        assert match is not None
        node = [child for child in node if child.tag == match.group(1)][
            int(match.group(2)) - 1
        ]
    return node


def test_default_call_never_reads_declared_electronic_date(tmp_path: Path) -> None:
    raw = _raw(meta_extra=_epub(2023, 5, 4))
    inspection, capture = _capture(tmp_path, raw)
    assert inspection.body_state == "body_present"
    assert capture is not None
    assert capture.published_at is None
    assert capture.effective_at is None
    assert capture.first_disclosed_at is None
    dumped = capture.model_dump(mode="json")
    assert "date_precisions" not in dumped
    assert "date_locators" not in dumped
    assert not capture.is_available_by(ACQUIRED)


def test_opt_in_flag_must_be_an_explicit_bool(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="布尔"):
        service.source_capture_from_linked_jats_xml(
            tmp_path,
            _raw(),
            expected_pmid=PMID,
            expected_pmcid=PMC,
            expected_doi=DOI,
            url=URL,
            acquired_at=ACQUIRED,
            use_declared_publication_date="yes",  # type: ignore[arg-type]
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("declaration", "expected_day"),
    [
        pytest.param(_epub(2023, 5, 4), date(2023, 5, 4), id="legacy-epub"),
        pytest.param(_modern(2025, 12, 17), date(2025, 12, 17), id="modern-electronic"),
    ],
)
def test_opt_in_reads_complete_declared_electronic_calendar_day(
    tmp_path: Path, declaration: str, expected_day: date
) -> None:
    raw = _raw(meta_extra=declaration)
    inspection, capture = _capture(tmp_path, raw, declared=True)
    assert capture is not None and capture.text_derivation is not None
    assert capture.text_derivation.raw_asset.sha256 == inspection.raw_sha256
    evidence = capture.date_evidence("published_at")
    assert evidence.state == "reported"
    assert evidence.precision == "calendar_day"
    assert evidence.value == datetime.combine(expected_day, time.min, tzinfo=UTC)
    assert capture.published_at == evidence.value


def test_declared_day_is_precise_to_the_calendar_day(tmp_path: Path) -> None:
    _, capture = _capture(tmp_path, _raw(meta_extra=_epub(2023, 5, 4)), declared=True)
    assert capture is not None
    published = capture.date_evidence("published_at")
    assert not published.is_known_by(datetime(2023, 5, 4, 12, tzinfo=UTC))
    assert published.is_known_by(datetime(2023, 5, 4, 23, 59, 59, 999999, tzinfo=UTC))


def test_declared_publication_never_becomes_disclosure_or_availability(
    tmp_path: Path,
) -> None:
    _, capture = _capture(tmp_path, _raw(meta_extra=_epub(2023, 5, 4)), declared=True)
    assert capture is not None
    assert capture.first_disclosed_at is None
    assert capture.effective_at is None
    disclosure = capture.date_evidence("first_disclosed_at")
    assert disclosure.state == "not_publicly_disclosed"
    assert disclosure.value is None
    assert capture.date_evidence("published_at").value != capture.acquired_at
    assert not capture.is_available_by(ACQUIRED)
    assert not capture.is_available_by(datetime(2099, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    ("meta_extra", "index"),
    [
        pytest.param(_epub(2023, 5, 4), 1, id="single-legacy"),
        pytest.param(_ppub(2022, 3, 3) + _epub(2023, 5, 4), 2, id="after-print-declaration"),
        pytest.param(_epub(2023, 5, 4) + _epub(2023, 5, 4), 1, id="identical-duplicate"),
        pytest.param(
            _ppub(2022, 3, 3) + _epub(2023, 5, 4) + _epub(2023, 5, 4),
            2,
            id="duplicate-after-print",
        ),
    ],
)
def test_exact_deterministic_locator_identifies_the_declared_pub_date(
    tmp_path: Path, meta_extra: str, index: int
) -> None:
    raw = _raw(meta_extra=meta_extra)
    _, capture = _capture(tmp_path, raw, declared=True)
    assert capture is not None and capture.date_locators is not None
    locator = capture.date_locators.published_at
    assert locator is not None
    assert locator.document_role == "original_linked_publication"
    assert locator.field_path == PUB_DATE_PATH.format(index=index)
    assert locator.url == URL
    assert capture.published_at == datetime(2023, 5, 4, tzinfo=UTC)
    node = _resolve_xml_path(raw, locator.field_path or "")
    assert [child.tag for child in node] == ["year", "month", "day"]
    assert [child.text for child in node] == ["2023", "05", "04"]


@pytest.mark.parametrize(
    "meta_extra",
    [
        pytest.param(_epub(2023, 5, 4) + _epub(2024, 6, 5), id="two-legacy-dates"),
        pytest.param(_epub(2023, 5, 4) + _modern(2023, 5, 5), id="legacy-and-modern"),
        pytest.param(_modern(2025, 12, 17) + _modern(2025, 12, 18), id="two-modern-dates"),
    ],
)
def test_conflicting_distinct_complete_electronic_dates_fail_before_storage(
    tmp_path: Path, meta_extra: str
) -> None:
    with pytest.raises(service.ResearchPackageError, match="电子出版日期"):
        _capture(tmp_path, _raw(meta_extra=meta_extra), declared=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "declaration",
    [
        pytest.param(
            '<pub-date pub-type="epub"><year>2023</year><month>05</month></pub-date>',
            id="missing-day",
        ),
        pytest.param('<pub-date pub-type="epub"><year>2023</year></pub-date>', id="year-only"),
        pytest.param(
            '<pub-date pub-type="epub"><year>2023</year><month>05</month><day/></pub-date>',
            id="blank-day",
        ),
        pytest.param(
            '<pub-date date-type="pub" publication-format="electronic">'
            "<year>2025</year><month>12</month></pub-date>",
            id="modern-missing-day",
        ),
    ],
)
def test_partial_declared_date_stays_unknown_without_filling_day_one(
    tmp_path: Path, declaration: str
) -> None:
    _, capture = _capture(tmp_path, _raw(meta_extra=declaration), declared=True)
    assert capture is not None
    assert capture.published_at is None
    assert capture.date_evidence("published_at").state == "not_publicly_disclosed"
    dumped = capture.model_dump(mode="json")
    assert "date_precisions" not in dumped
    assert "date_locators" not in dumped
    assert not capture.is_available_by(datetime(2099, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    "declaration",
    [
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>2023</year><month>02</month><day>30</day>"
            "</pub-date>",
            id="impossible-calendar-day",
        ),
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>2023</year><month>13</month><day>04</day>"
            "</pub-date>",
            id="month-out-of-range",
        ),
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>2023</year><month>05</month><day>00</day>"
            "</pub-date>",
            id="zero-day",
        ),
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>23</year><month>05</month><day>04</day>"
            "</pub-date>",
            id="two-digit-year",
        ),
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>2023</year><month>May</month><day>04</day>"
            "</pub-date>",
            id="non-numeric-month",
        ),
        pytest.param(
            "<pub-date pub-type=\"epub\"><year>2023</year><year>2024</year><month>05</month>"
            "<day>04</day></pub-date>",
            id="duplicated-year-field",
        ),
    ],
)
def test_malformed_complete_declared_date_fails_before_storage(
    tmp_path: Path, declaration: str
) -> None:
    with pytest.raises(service.ResearchPackageError, match="pub-date"):
        _capture(tmp_path, _raw(meta_extra=declaration), declared=True)
    assert not list(tmp_path.iterdir())


def test_history_print_and_scheduled_release_dates_are_not_publication(
    tmp_path: Path,
) -> None:
    misleading = (
        "<history>"
        '<date date-type="received"><year>2020</year><month>01</month><day>01</day></date>'
        '<date date-type="accepted"><year>2021</year><month>02</month><day>02</day></date>'
        "</history>"
        + _ppub(2022, 3, 3)
        + "<pmc-release><year>2024</year><month>04</month><day>04</day></pmc-release>"
    )
    _, without = _capture(tmp_path, _raw(meta_extra=misleading), declared=True)
    assert without is not None and without.published_at is None
    _, with_epub = _capture(
        tmp_path, _raw(meta_extra=misleading + _epub(2023, 5, 4)), declared=True
    )
    assert with_epub is not None
    assert with_epub.published_at == datetime(2023, 5, 4, tzinfo=UTC)


def test_reference_and_body_dates_are_never_borrowed(tmp_path: Path) -> None:
    reference = (
        "<back><ref-list><ref><mixed-citation>"
        '<pub-date pub-type="epub"><year>1999</year><month>09</month><day>09</day></pub-date>'
        '<date date-type="pub"><year>1998</year><month>08</month><day>08</day></date>'
        "</mixed-citation></ref></ref-list></back>"
    )
    body = (
        '<body><sec><date date-type="pub"><year>2020</year><month>05</month><day>04</day>'
        "</date><p>Prose only.</p></sec></body>"
    )
    inspection, capture = _capture(tmp_path, _raw(body=body, back=reference), declared=True)
    assert inspection.body_state == "body_present"
    assert capture is not None
    assert capture.published_at is None
    assert "date_precisions" not in capture.model_dump(mode="json")


def test_mismatched_identity_is_rejected_before_any_date_read(tmp_path: Path) -> None:
    raw = _raw(meta_extra=_epub(2023, 5, 4))
    with pytest.raises(LinkedJatsIdentityError):
        _capture(tmp_path, raw, declared=True, expected_doi="10.9999/wrong")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("declared", [False, True])
def test_entity_or_malformed_bytes_are_rejected_with_opt_in(
    tmp_path: Path, declared: bool
) -> None:
    entity_raw = (
        b'<?xml version="1.0"?><!DOCTYPE pmc-articleset [<!ENTITY boom "2020">]>'
        + _raw(meta_extra=_epub(2023, 5, 4), body="<body><p>&boom;</p></body>")
    )
    with pytest.raises(LinkedJatsXmlError):
        _capture(tmp_path, entity_raw, declared=declared)
    with pytest.raises(LinkedJatsXmlError):
        _capture(tmp_path, b"<pmc-articleset><article>", declared=declared)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("body", ["", "<body/>"])
def test_metadata_only_with_declared_date_still_returns_no_capture(
    tmp_path: Path, body: str
) -> None:
    inspection, capture = _capture(
        tmp_path, _raw(meta_extra=_epub(2023, 5, 4), body=body), declared=True
    )
    assert inspection.body_state == "metadata_only"
    assert capture is None
    assert not list(tmp_path.iterdir())


def test_date_locator_reopens_through_production_source_quote(tmp_path: Path) -> None:
    raw = _raw(meta_extra=_ppub(2022, 3, 3) + _epub(2023, 5, 4))
    _, capture = _capture(tmp_path, raw, declared=True)
    assert capture is not None and capture.date_locators is not None
    locator = capture.date_locators.published_at
    assert locator is not None
    assert extract_locator_quote(
        capture.content_text, media_type=capture.media_type, locator=locator
    ) == "20230504"


@pytest.mark.parametrize("path", [
    "/article/body[1]/pub-date[1]",
    "/article/front[1]/article-meta[1]/history[1]/date[1]",
    "/article/front[1]/article-meta[1]",
])
def test_date_quote_does_not_allow_body_history_or_coarse_metadata(path: str) -> None:
    raw = _raw(meta_extra=_epub(2023, 5, 4), body=f"<body>{_epub(2000, 1, 1)}</body>")
    with pytest.raises(SourceDerivationError):
        extract_locator_quote(raw.decode(), media_type="application/xml", locator=EvidenceLocator(
            document_role="original_linked_publication", field_path=path,
        ))
