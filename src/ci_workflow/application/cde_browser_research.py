"""CDE public DOM captures into existing source/fact primitives, never approvals.

The browser owns acquisition. This small offline adapter checks the persisted
table, filters and pagination; it does not automate login, infer indications,
sign scientific receipts or create report consumers.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict

from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.source_derivation import capture_source_text, source_json_decoder

_ACCEPTANCE = "public-rendered-cde-acceptance-directory"
_REVIEW = "public-rendered-cde-review-task-directory"
_HEADERS = {
    _ACCEPTANCE: (
        "序号",
        "受理号",
        "药品名称",
        "药品类型",
        "申请类型",
        "注册分类",
        "企业名称",
        "承办日期",
    ),
    _REVIEW: (
        "序号",
        "受理号",
        "药品名称",
        "进入中心时间",
        "审评状态",
        "药理毒理",
        "临床",
        "药学",
        "统计",
        "临床药理",
        "合规",
        "备注",
    ),
}
_FIELDS = {
    _ACCEPTANCE: {
        1: "application_number",
        2: "product_name",
        3: "drug_type",
        4: "application_type",
        5: "registration_class",
        6: "applicant",
        7: "acceptance_handled_on",
    },
    _REVIEW: {3: "review_entered_on", 4: "review_status", 11: "review_remark"},
}
_NUMBER = re.compile(r"[A-Z]{1,6}[0-9]{7,12}")


class _Table(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    html: str
    rows: list[list[str]]


class _Pager(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    text: str
    page: str


class _Capture(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: str
    url: str
    acquired_at: str
    query: dict[str, str]
    tables: list[_Table]
    pager: list[_Pager]


class _HtmlRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


@dataclass(frozen=True)
class CdeCaptureGap:
    subject: str
    reason: str


@dataclass(frozen=True)
class CdeBrowserCandidateBatch:
    sources: tuple[SourceCapture, ...]
    facts: tuple[ResearchFact, ...]
    claims: tuple[ResearchClaim, ...]
    acceptance_numbers: tuple[str, ...]
    acceptance_directory_complete: bool
    gaps: tuple[CdeCaptureGap, ...]
    indication_lock: Literal["unresolved"] = "unresolved"
    scientifically_accepted: Literal[False] = False


def _parse(raw: bytes, checked_at: datetime) -> _Capture:
    capture = _Capture.model_validate(source_json_decoder().decode(raw.decode("utf-8")))
    parts = urlsplit(capture.url)
    if (
        parts.scheme != "https"
        or parts.hostname not in {"www.cde.org.cn", "cde.org.cn"}
        or parts.username
        or parts.password
        or capture.kind not in _HEADERS
    ):
        raise ValueError("CDE捕获来源或页面类型不符合合同")
    acquired = datetime.fromisoformat(capture.acquired_at)
    if acquired.tzinfo is None or acquired.utcoffset() is None or acquired > checked_at:
        raise ValueError("CDE实际获取时间缺少时区或晚于本次核验")
    if len(capture.tables) != 1 or not capture.tables[0].rows:
        raise ValueError("CDE捕获必须保留一个明确的完整结果表")
    table = capture.tables[0]
    if tuple(table.rows[0]) != _HEADERS[capture.kind]:
        raise ValueError("CDE表头变化，须重新解析而非猜测列含义")
    parser = _HtmlRows()
    parser.feed(table.html)
    normalized = [[" ".join(value.split()) for value in row] for row in table.rows]
    if parser.rows != normalized:
        raise ValueError("CDE表格字段与原始DOM表不一致")
    width = len(table.rows[0])
    for row in table.rows[1:]:
        if len(row) != width or not row[0].isdigit() or _NUMBER.fullmatch(row[1]) is None:
            raise ValueError("CDE结果行截断或缺少完整受理号")
        if not row[2].strip():
            raise ValueError("CDE结果行缺少药品原名")
        date.fromisoformat(row[7] if capture.kind == _ACCEPTANCE else row[3])
    if capture.kind == _ACCEPTANCE:
        if set(capture.query) != {"year", "drug_name", "drug_type", "application_type"}:
            raise ValueError("CDE受理查询字段不符合公开捕获合同")
        query = capture.query.get("drug_name", "")
        if not query.strip() or any(query not in row[2] for row in table.rows[1:]):
            raise ValueError("CDE受理结果与药名查询不一致")
        if len(capture.pager) != 1 or not capture.pager[0].page.isdigit():
            raise ValueError("CDE受理目录缺少真实分页状态")
    else:
        if set(capture.query) != {"acceptance_number", "sequence", "application_type", "drug_type"}:
            raise ValueError("CDE审评查询字段不符合公开捕获合同")
        query_id = capture.query.get("acceptance_number", "")
        if _NUMBER.fullmatch(query_id) is None:
            raise ValueError("CDE审评查询缺少完整受理号")
        matching = [row for row in table.rows[1:] if row[1] == query_id]
        if len(matching) > 1:
            raise ValueError("同一CDE审评查询返回多个冲突目标")
        if matching and capture.query.get("sequence") == "生物":
            if capture.query.get("drug_type") not in {"治疗用生物制品", "预防用生物制品"}:
                raise ValueError("生物制品审评查询缺少明确药品类型")
            if capture.query.get("application_type") not in {"BCSQ", "LCSYSQ", "SSSQ", "ZZC"}:
                raise ValueError("生物制品审评查询分类不符合实际页面合同")
    return capture


def build_cde_browser_candidates(
    project_root: Path,
    *,
    captures: Sequence[bytes],
    checked_at: datetime,
) -> CdeBrowserCandidateBatch:
    """Persist exact public captures and extract only neutral, precisely located facts.

    Completeness here means this one acceptance-directory query, NOT an indication
    universe. Indication-specific events require separate proof and review.
    """
    if (
        checked_at.tzinfo is None
        or checked_at.utcoffset() is None
        or checked_at > datetime.now(UTC)
        or not captures
    ):
        raise ValueError("CDE核验必须使用真实有时区时间与已取得内容")
    parsed = [_parse(raw, checked_at) for raw in captures]
    numbers: list[str] = []
    ordinals: list[int] = []
    counts: set[int] = set()
    queries: set[tuple[tuple[str, str], ...]] = set()
    pages: set[str] = set()
    selected: list[list[tuple[int, list[str]]]] = []
    gaps: list[CdeCaptureGap] = []
    acceptance_rows: dict[str, list[str]] = {}
    for capture in parsed:
        rows = list(enumerate(capture.tables[0].rows[1:], start=1))
        if capture.kind == _ACCEPTANCE:
            queries.add(tuple(sorted(capture.query.items())))
            page = capture.pager[0].page
            if page in pages:
                raise ValueError("CDE目录分页重复，不能累计为完整记录")
            pages.add(page)
            count_match = re.search(r"共\s*([0-9]+)\s*条", capture.pager[0].text)
            if count_match is None:
                raise ValueError("CDE目录缺少本次查询总数")
            counts.add(int(count_match.group(1)))
            for _, row in rows:
                if row[1] in numbers:
                    raise ValueError("CDE完整受理号重复，不得先到先得")
                numbers.append(row[1])
                ordinals.append(int(row[0]))
                acceptance_rows[row[1]] = row
        else:
            target = capture.query["acceptance_number"]
            rows = [(index, row) for index, row in rows if row[1] == target]
            if not rows:
                gaps.append(CdeCaptureGap(target, "review_not_located"))
        selected.append(rows)
    if len(queries) > 1 or len(counts) > 1:
        raise ValueError("不同查询或查询总数变化不得拼为同一完整CDE目录")
    planned_fact_ids: set[str] = set()
    planned_source_ids: set[str] = set()
    for capture, rows in zip(parsed, selected, strict=True):
        identifier = (
            capture.query["drug_name"] + ":" + capture.pager[0].page
            if capture.kind == _ACCEPTANCE
            else capture.query["acceptance_number"]
        )
        source_id = stable_id("cde-browser-source", capture.kind, identifier)
        if source_id in planned_source_ids:
            raise ValueError("CDE捕获来源重复，不能合并为额外证据")
        planned_source_ids.add(source_id)
        for _, row in rows:
            accepted = acceptance_rows.get(row[1])
            if capture.kind == _REVIEW and accepted is not None:
                if row[2] != accepted[2]:
                    raise ValueError("CDE受理目录与审评目标药名不一致")
                if accepted[3] in {"治疗用生物制品", "预防用生物制品"} and (
                    capture.query["sequence"] != "生物" or capture.query["drug_type"] != accepted[3]
                ):
                    raise ValueError("CDE审评药品类型与受理原文不一致")
                explicit_category = {"补充申请": "BCSQ", "进口再注册": "ZZC"}.get(accepted[4])
                if explicit_category and capture.query["application_type"] != explicit_category:
                    raise ValueError("CDE审评申请分类与受理原文不一致")
            for column, field in _FIELDS[capture.kind].items():
                if not row[column].strip():
                    continue
                fact_id = stable_id("cde-browser-fact", row[1], field)
                if fact_id in planned_fact_ids:
                    raise ValueError("CDE事实重复或冲突，需显式裁决")
                planned_fact_ids.add(fact_id)
    unrestricted = all(
        capture.query.get(key) == ""
        for capture in parsed
        if capture.kind == _ACCEPTANCE
        for key in ("year", "drug_type", "application_type")
    )
    total = next(iter(counts), None)
    complete = (
        total is not None
        and unrestricted
        and len(numbers) == total
        and sorted(ordinals) == list(range(1, total + 1))
    )
    if not complete:
        gaps.append(CdeCaptureGap("acceptance_directory", "pagination_incomplete"))
    gaps.extend(CdeCaptureGap(number, "indication_unresolved") for number in numbers)
    sources: list[SourceCapture] = []
    facts: list[ResearchFact] = []
    for raw, capture, rows in zip(captures, parsed, selected, strict=True):
        text, derivation = capture_source_text(project_root, raw, media_type="application/json")
        identifier = (
            capture.query["drug_name"] + ":" + capture.pager[0].page
            if capture.kind == _ACCEPTANCE
            else capture.query["acceptance_number"]
        )
        source_id = stable_id("cde-browser-source", capture.kind, identifier)
        source = SourceCapture(
            source_id=source_id,
            route_id="cde-public-browser",
            source_type="regulatory_document",
            title="CDE公开目录：" + identifier,
            url=capture.url,
            query_or_identifier=identifier,
            language="zh",
            access_method="public-browser",
            media_type="application/json",
            content_text=text,
            text_derivation=derivation,
            acquired_at=datetime.fromisoformat(capture.acquired_at),
            published_at=None,
            effective_at=None,
            first_disclosed_at=None,
            locator=EvidenceLocator(
                document_role="CDE公开目录浏览器捕获",
                field_path="$.tables[0].rows",
                url=capture.url,
            ),
        )
        sources.append(source)
        for row_index, row in rows:
            for column, field in _FIELDS[capture.kind].items():
                value = row[column]
                if not value.strip():
                    continue
                fact_id = stable_id("cde-browser-fact", row[1], field)
                facts.append(
                    ResearchFact(
                        fact_id=fact_id,
                        row_ref="china-application:" + row[1],
                        entity_id=stable_id("china-application", row[1]),
                        entity_type="regulatory_application",
                        canonical_name=row[2],
                        field_id="cde." + field,
                        raw_value=value,
                        normalized_value=None,
                        disclosure_state="reported_value",
                        source_id=source_id,
                        locator=EvidenceLocator(
                            document_role="CDE公开目录原始表单元格",
                            field_path=f"$.tables[0].rows[{row_index}][{column}]",
                            url=capture.url,
                        ),
                        original_text=value,
                    )
                )
    claims = tuple(
        ResearchClaim(
            claim_id=stable_id("cde-browser-claim", fact.fact_id),
            claim_text=(
                f"CDE目录 {fact.row_ref.removeprefix('china-application:')} "
                f"{fact.field_id}: {fact.original_text}"
            ),
            claim_kind="direct_evidence",
            fact_ids=(fact.fact_id,),
        )
        for fact in facts
    )
    return CdeBrowserCandidateBatch(
        tuple(sources), tuple(facts), claims, tuple(numbers), complete, tuple(gaps)
    )
