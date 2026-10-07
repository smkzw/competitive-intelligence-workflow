from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlencode
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NCT_ID = re.compile(r"\bNCT[0-9]{8}\b", re.IGNORECASE)
PublicationRole = Literal[
    "unclassified",
    "primary_report",
    "ad_hoc_analysis",
    "review",
    "supporting_publication",
    "unrelated",
]
EvidenceFieldDomain = Literal["trial_design", "efficacy", "safety"]
EvidenceSourceRole = Literal[
    "clinical_trial_registry",
    "primary_publication",
    "regulatory_material",
    "supplementary_material",
]


class PubMedIdentifierCandidate(BaseModel):
    """One own native identifier occurrence, not a resolved identity verdict.

    Preserve conflicts/empty values and their exact locations for recovery;
    consumers must not choose the first DOI/PMC or borrow bibliography IDs.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    id_type: str
    value: str
    field_path: str


class PubMedRelationCandidate(BaseModel):
    """Own citation relationship, preserving incomplete/conflicting native evidence.

    NLM RefType conveys direction; a comment is not an erratum. The target is
    not another retrieved article or an identity alias, even when its PMID is
    missing. Unknown future types remain recoverable rather than first-wins.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    ref_type: str
    pmid: str
    reference: str
    note: str
    field_path: str


class PubMedRecord(BaseModel):
    """由 PubMed EFetch 原文解析得到的最小不可变记录。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pmid: str
    title: str
    abstract: str
    publication_types: tuple[str, ...]
    registry_nct_ids: tuple[str, ...] = ()
    identifier_candidates: tuple[PubMedIdentifierCandidate, ...] = Field(
        default=(), exclude_if=lambda value: not value,
    )
    relation_candidates: tuple[PubMedRelationCandidate, ...] = Field(
        default=(), exclude_if=lambda value: not value,
    )

    @field_validator("registry_nct_ids")
    @classmethod
    def _registry_identifiers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip().upper() for item in values)
        if any(re.fullmatch(r"NCT[0-9]{8}", item) is None for item in normalized):
            raise ValueError("PubMed 登记关联需要完整 NCT 标识")
        return tuple(dict.fromkeys(normalized))

    @field_validator("pmid")
    @classmethod
    def _pmid_is_numeric(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit():
            raise ValueError("PubMed 标识必须为数字")
        return normalized

    @field_validator("title")
    @classmethod
    def _title_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("PubMed 题名不能为空")
        return normalized

    @field_validator("abstract")
    @classmethod
    def _normalize_abstract(cls, value: str) -> str:
        return " ".join(value.split())


class ClassifiedPublication(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record: PubMedRecord
    role: PublicationRole
    matched_nct_ids: tuple[str, ...]
    classification_signals: tuple[str, ...]
    rationale_zh: str
    can_replace_primary_report: bool


class EvidenceContribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    field_domain: EvidenceFieldDomain
    source_role: EvidenceSourceRole
    source_record_id: str

    @field_validator("field_id", "source_record_id")
    @classmethod
    def _contribution_text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("证据字段和来源记录标识不能为空")
        return normalized


class RejectedContribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contribution: EvidenceContribution
    rationale_zh: str


class KeyFieldCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_contributions: tuple[EvidenceContribution, ...]
    rejected_contributions: tuple[RejectedContribution, ...]
    missing_fields: tuple[str, ...]
    supplement_state: Literal["not_required", "required"]
    rationale_zh: str


def build_pubmed_nct_search_url(nct_id: str) -> str:
    normalized = nct_id.strip().upper()
    if re.fullmatch(r"NCT[0-9]{8}", normalized) is None:
        raise ValueError("PubMed NCT 检索需要有效 NCT 号")
    query = urlencode(
        {
            "db": "pubmed",
            "term": f"{normalized}[All Fields]",
            "retmode": "json",
            "retmax": "10000",
        }
    )
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{query}"


def _element_text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _own_identifier_candidates(
    article_node: ElementTree.Element, *, is_book: bool,
) -> tuple[PubMedIdentifierCandidate, ...]:
    # NLM ArticleIdList also occurs under Reference and Book: never descend
    # through those. BookDocument direct lists identify the chapter/monograph.
    # https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-ArticleIdList.html
    container_tags = ("BookDocument", "PubmedBookData") if is_book else ("PubmedData",)
    candidates: list[PubMedIdentifierCandidate] = []
    for tag in container_tags:
        for container_index, container in enumerate(article_node.findall(f"./{tag}"), 1):
            for list_index, identifier_list in enumerate(container.findall("./ArticleIdList"), 1):
                for identifier_index, node in enumerate(identifier_list.findall("./ArticleId"), 1):
                    candidates.append(PubMedIdentifierCandidate(
                        # The DTD default is pubmed; an explicit empty attribute
                        # remains empty, not defaulted to a fabricated valid type.
                        id_type=node.get("IdType", "pubmed"),
                        value=_element_text(node),
                        field_path=(f"./{tag}[{container_index}]/ArticleIdList[{list_index}]"
                                    f"/ArticleId[{identifier_index}]"),
                    ))
    return tuple(candidates)


def _own_relation_candidates(
    article_node: ElementTree.Element, *, is_book: bool,
) -> tuple[PubMedRelationCandidate, ...]:
    # Exact own-citation paths only; do not descend into bibliography IDs.
    # https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-CommentsCorrections.html
    tag = "BookDocument" if is_book else "MedlineCitation"
    candidates: list[PubMedRelationCandidate] = []
    for citation_index, citation in enumerate(article_node.findall(f"./{tag}"), 1):
        for list_index, relation_list in enumerate(
            citation.findall("./CommentsCorrectionsList"), 1,
        ):
            for index, node in enumerate(relation_list.findall("./CommentsCorrections"), 1):
                candidates.append(PubMedRelationCandidate(
                    ref_type=node.get("RefType", ""),
                    pmid=_element_text(node.find("./PMID")),
                    reference=_element_text(node.find("./RefSource")),
                    note=_element_text(node.find("./Note")),
                    field_path=(f"./{tag}[{citation_index}]/CommentsCorrectionsList[{list_index}]"
                                f"/CommentsCorrections[{index}]"),
                ))
    return tuple(candidates)


def parse_pubmed_efetch_xml(xml_text: str) -> tuple[PubMedRecord, ...]:
    """Parse own journal/book citation identity, never nested relation PMIDs."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("PubMed EFetch XML 无法解析") from exc
    records: list[PubMedRecord] = []
    for article_node in root:
        is_book = article_node.tag == "PubmedBookArticle"
        if article_node.tag not in {"PubmedArticle", "PubmedBookArticle"}:
            continue
        citation = article_node.find("./BookDocument" if is_book else "./MedlineCitation")
        if citation is None:
            continue
        pmid = _element_text(citation.find("./PMID"))
        article = citation if is_book else citation.find("./Article")
        if article is None:
            raise ValueError(f"PubMed 记录 {pmid or '未知'} 缺少 Article")
        title = _element_text(article.find("./ArticleTitle"))
        if is_book and not title:
            # ArticleTitle is optional for a monograph in NLM's BookDocument.
            title = _element_text(article.find("./Book/BookTitle"))
        abstract_parts: list[str] = []
        for abstract_node in article.findall("./Abstract/AbstractText"):
            text = _element_text(abstract_node)
            if not text:
                continue
            label = " ".join(abstract_node.attrib.get("Label", "").split())
            abstract_parts.append(f"{label}: {text}" if label else text)
        publication_types = tuple(
            text
            for item in article.findall(
                "./PublicationType" if is_book else "./PublicationTypeList/PublicationType"
            )
            if (text := _element_text(item))
        )
        # NLM's output XML declares registration associations here, separately
        # from the abstract. Never borrow IDs from comments or references.
        # https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-DataBank.html
        registry_nct_ids = tuple(dict.fromkeys(
            accession
            for bank in article.findall("./DataBankList/DataBank")
            if _element_text(bank.find("./DataBankName")).casefold() == "clinicaltrials.gov"
            for node in bank.findall("./AccessionNumberList/AccessionNumber")
            if re.fullmatch(r"NCT[0-9]{8}", accession := _element_text(node).upper())
        ))
        records.append(
            PubMedRecord(
                pmid=pmid,
                title=title,
                abstract=" ".join(abstract_parts),
                publication_types=publication_types,
                registry_nct_ids=registry_nct_ids,
                identifier_candidates=_own_identifier_candidates(article_node, is_book=is_book),
                relation_candidates=_own_relation_candidates(article_node, is_book=is_book),
            )
        )
    return tuple(records)


_SECONDARY_ANALYSIS = re.compile(
    r"\b(?:post[- ]hoc|ad[- ]hoc|subgroup analys(?:is|es)|exploratory analys(?:is|es))\b"
)
_SECONDARY_FRAMING = re.compile(
    r"\b(?:(?:in this|this|(?:here )?we (?:performed|conducted|presented|"
    r"report|present|describe))\s+(?:\w+[ -]){0,3}(?:post[- ]hoc|ad[- ]hoc|subgroup|"
    r"exploratory)\b|(?:a|an)\s+(?:post[- ]hoc|ad[- ]hoc|subgroup|exploratory)\s+"
    r"analys(?:is|es)\s+of\b)", re.IGNORECASE,
)
_ABSTRACT_SECTION = re.compile(
    r"\b(?:background|importance|introduction|objectives?|aims?|methods?|"
    r"design(?:, setting, and participants)?|interventions?|main outcomes? and measures|"
    r"results|findings|conclusions?(?: and relevance)?|interpretation|meaning|funding)\s*:",
    re.IGNORECASE,
)


def _result_regions(abstract: str) -> tuple[tuple[int, str], ...]:
    sections = tuple(_ABSTRACT_SECTION.finditer(abstract))
    result_sections = [
        (match.end(),
         abstract[match.end():sections[index + 1].start() if index + 1 < len(sections) else None])
        for index, match in enumerate(sections)
        if match.group().split(":", 1)[0].strip().casefold() in {"results", "findings"}
    ]
    # A methods-only structured record does not report outcomes merely because
    # it includes statistical assumptions. Unstructured records remain reviewable.
    return tuple(result_sections) if sections else ((0, abstract),)


def _is_observed_result(sentence: str) -> bool:
    text = sentence.casefold()
    if _SECONDARY_ANALYSIS.search(text) or re.search(
        r"\b(?:will|planned|planning|anticipated|expected|assumed|projected|"
        r"previous|previously|prior)\b", text,
    ):
        return False
    if re.search(
        r"\b(?:results (?:are reported|were reported|showed|show)|"
        r"trial findings|findings (?:suggested|showed|demonstrated))\b", text,
    ):
        return True
    measured_result = re.search(
        r"\b(?:mean difference|hazard ratio|risk ratio|odds ratio|"
        r"least[- ]squares|least squares|adjusted difference|response rate|improved|reduced|"
        r"increased|decreased)\b", text,
    )
    # Observed responder outcomes can be reported as achieved/had a response,
    # not just "response rate". Restrict the verb to an outcome noun in the
    # same clause; enrollment counts and planned responses remain excluded.
    responder_result = re.search(
        r"\b(?:achieved|attained|had)\s+(?:\w+[ -]){0,6}"
        r"(?:response|reduction|improvement|remission|success)\b|"
        r"\b(?:response|reduction|improvement|remission|success)\b"
        r"[^.!?;]{0,100}\b(?:was|were)\s+(?:achieved|attained|observed)\b", text,
    )
    outcome_statistic = re.search(
        r"(?:\d(?:\.\d+)?\s*%|\d\s*/\s*\d|\b\d+(?:\.\d+)?\s*%?\s*ci\b|"
        r"\bp\s*[=<]\s*\.?\d)", text,
    )
    return bool((measured_result or responder_result) and outcome_statistic)


def _main_result_offset(abstract: str) -> int | None:
    # Retain original offsets: an opening secondary-paper frame differs from
    # a later analysis attached to an already reported primary comparison.
    for offset, region in _result_regions(abstract):
        start = 0
        for boundary in re.finditer(r"(?<=[.!?。！？])\s+", region):
            if _is_observed_result(region[start:boundary.start()]):
                return offset + start
            start = boundary.end()
        if _is_observed_result(region[start:]):
            return offset + start
    return None


def _classify(record: PubMedRecord, matched: tuple[str, ...]) -> ClassifiedPublication:
    combined = f"{record.title}\n{record.abstract}".casefold()
    title = record.title.casefold()
    publication_types = {item.casefold() for item in record.publication_types}
    review_signals = (
        bool(publication_types & {"review", "meta-analysis", "systematic review"})
        or "systematic review" in title
        or "meta-analysis" in title
    )
    ad_hoc_title = bool(_SECONDARY_ANALYSIS.search(title))
    ad_hoc_abstract = bool(_SECONDARY_ANALYSIS.search(record.abstract.casefold()))
    randomized_signal = (
        "randomized controlled trial" in publication_types
        or "randomised" in combined
        or "randomized" in combined
        or "phase 2" in combined
        or "phase 3" in combined
    )
    protocol_signal = (
        "clinical trial protocol" in publication_types
        or "study protocol" in combined
        or combined.startswith("protocol ")
        or bool(re.search(r"\b(?:rationale and (?:study )?design|"
                          r"design and rationale|design of)\b|"
                          r"\b(?:study|trial) design\s*:", title))
    )
    main_result_offset = _main_result_offset(record.abstract)
    framing = _SECONDARY_FRAMING.search(record.abstract)
    secondary_scope = framing is not None and (
        main_result_offset is None or framing.start() < main_result_offset
    )
    primary_endpoint_signal = bool(re.search(
        r"\b(?:co[- ]?)?primary (?:end ?points?|outcomes?)\b", combined,
    ))
    result_signal = main_result_offset is not None
    # This is an unresolved-integrity guard, not a final exclusion verdict or
    # proof of a successful freshness check. Existing independent publication
    # review must resolve the original paper and linked correction together.
    integrity_relation_types = {
        "ErratumIn", "ErratumFor", "RetractionIn", "RetractionOf",
        "ExpressionOfConcernIn", "ExpressionOfConcernFor",
        "CorrectedandRepublishedIn", "CorrectedandRepublishedFrom",
        "RetractedandRepublishedIn", "RetractedandRepublishedFrom", "UpdateIn", "UpdateOf",
    }
    integrity_publication_types = {
        "retracted publication", "retraction of publication", "expression of concern",
        "published erratum", "corrected and republished article",
    }
    integrity_signals = tuple(dict.fromkeys(
        [item.ref_type for item in record.relation_candidates
         if item.ref_type in integrity_relation_types]
        + [item for item in record.publication_types
           if item.casefold() in integrity_publication_types]
    ))
    signals: tuple[str, ...]
    if integrity_signals:
        role: PublicationRole = "unclassified"
        signals = (*integrity_signals, "更正/撤稿/关注或更新关系待核，保留独立复核")
        rationale = (
            "原始出版元数据标记更正、撤稿、关注或更新；须结合原文和关联材料复核。"
            "当前不得自动推荐替代主要结果，不等于排除整篇，也不改变原始来源。"
        )
    elif not matched:
        role = "unclassified"
        signals = ("未匹配目标 NCT", "关系未确定，保留模型及独立复核")
        rationale = (
            "当前元数据未匹配目标试验登记号，论文—试验关系未确定；"
            "缺少登记号不证明无关，不据此排除，也不能替代主要结果报告。"
        )
    elif review_signals:
        role = "review"
        signals = ("综述或荟萃分析出版类型",)
        rationale = "出版类型或题名摘要表明这是综述/荟萃分析，不能替代主要结果报告。"
    elif protocol_signal:
        role = "supporting_publication"
        signals = ("目标 NCT", "试验方案出版类型或用语")
        rationale = "这是试验方案或设计论文，不得按主要结果报告使用。"
    elif ad_hoc_title or secondary_scope or (ad_hoc_abstract and not result_signal):
        role = "ad_hoc_analysis"
        signals = ("事后、亚组或探索性分析用语",)
        rationale = "题名或整篇摘要范围标记事后、亚组或探索性分析，或未识别非次级主要结果。"
    elif randomized_signal and primary_endpoint_signal and result_signal:
        role = "primary_report"
        signals = ("目标 NCT", "随机/分期试验", "主要终点结果", "非次级分析的结果信号")
        rationale = (
            "论文匹配目标 NCT，识别到随机/分期试验的共同主要终点或主要终点结果；"
            "附带次级分析不排除整篇主要报告。规则建议仍需独立分类复核。"
        )
    else:
        role = "supporting_publication"
        signals = ("目标 NCT", "规则未识别充分主要结果信号", "需要模型及独立复核")
        rationale = (
            "论文与目标 NCT 有关，但规则未识别充分主要结果信号；"
            "这不等于没有结果或可以排除，须由模型和独立复核结合原文判断。"
        )
    return ClassifiedPublication(
        record=record,
        role=role,
        matched_nct_ids=matched,
        classification_signals=signals,
        rationale_zh=rationale,
        can_replace_primary_report=role == "primary_report",
    )


def classify_pubmed_records(
    records: tuple[PubMedRecord, ...], *, target_nct_ids: tuple[str, ...]
) -> tuple[ClassifiedPublication, ...]:
    normalized_targets = tuple(dict.fromkeys(item.strip().upper() for item in target_nct_ids))
    if not normalized_targets or any(
        re.fullmatch(r"NCT[0-9]{8}", item) is None for item in normalized_targets
    ):
        raise ValueError("论文分类需要至少一个有效目标 NCT 号")
    target_set = set(normalized_targets)
    classified: list[ClassifiedPublication] = []
    for record in records:
        text = f"{record.title}\n{record.abstract}"
        mentioned = {item.upper() for item in _NCT_ID.findall(text)} | set(record.registry_nct_ids)
        matched = tuple(item for item in normalized_targets if item in mentioned & target_set)
        classified.append(_classify(record, matched))
    return tuple(classified)


def assess_key_field_coverage(
    contributions: tuple[EvidenceContribution, ...], *, required_fields: tuple[str, ...]
) -> KeyFieldCoverage:
    required = tuple(dict.fromkeys(" ".join(item.split()) for item in required_fields))
    if not required or any(not item for item in required):
        raise ValueError("关键字段清单不能为空")
    accepted: list[EvidenceContribution] = []
    rejected: list[RejectedContribution] = []
    for contribution in contributions:
        if contribution.field_domain == "trial_design" and contribution.source_role not in {
            "clinical_trial_registry",
            "regulatory_material",
        }:
            rejected.append(
                RejectedContribution(
                    contribution=contribution,
                    rationale_zh=(
                        "论文及其补充材料可用于结果交叉核验，但不能替代登记平台或监管材料中的方案字段。"
                    ),
                )
            )
            continue
        accepted.append(contribution)
    covered = {item.field_id for item in accepted}
    missing = tuple(item for item in required if item not in covered)
    if missing:
        state: Literal["not_required", "required"] = "required"
        rationale = "现有主要来源尚未覆盖全部关键字段，需要继续寻找适用材料。"
    else:
        state = "not_required"
        rationale = "登记结果、主要论文或监管材料已覆盖关键疗效、安全性和方案字段。"
    return KeyFieldCoverage(
        accepted_contributions=tuple(accepted),
        rejected_contributions=tuple(rejected),
        missing_fields=missing,
        supplement_state=state,
        rationale_zh=rationale,
    )
