from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlencode
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, field_validator

_NCT_ID = re.compile(r"NCT[0-9]{8}", re.IGNORECASE)
PublicationRole = Literal[
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


class PubMedRecord(BaseModel):
    """由 PubMed EFetch 原文解析得到的最小不可变记录。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pmid: str
    title: str
    abstract: str
    publication_types: tuple[str, ...]

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


def parse_pubmed_efetch_xml(xml_text: str) -> tuple[PubMedRecord, ...]:
    """Parse article identities only from MedlineCitation, never nested relation PMIDs."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("PubMed EFetch XML 无法解析") from exc
    records: list[PubMedRecord] = []
    for article_node in root.findall("./PubmedArticle"):
        citation = article_node.find("./MedlineCitation")
        if citation is None:
            continue
        pmid = _element_text(citation.find("./PMID"))
        article = citation.find("./Article")
        if article is None:
            raise ValueError(f"PubMed 记录 {pmid or '未知'} 缺少 Article")
        title = _element_text(article.find("./ArticleTitle"))
        abstract_parts: list[str] = []
        for abstract_node in article.findall("./Abstract/AbstractText"):
            text = _element_text(abstract_node)
            if not text:
                continue
            label = " ".join(abstract_node.attrib.get("Label", "").split())
            abstract_parts.append(f"{label}: {text}" if label else text)
        publication_types = tuple(
            text
            for item in article.findall("./PublicationTypeList/PublicationType")
            if (text := _element_text(item))
        )
        records.append(
            PubMedRecord(
                pmid=pmid,
                title=title,
                abstract=" ".join(abstract_parts),
                publication_types=publication_types,
            )
        )
    return tuple(records)


def _classify(record: PubMedRecord, matched: tuple[str, ...]) -> ClassifiedPublication:
    combined = f"{record.title}\n{record.abstract}".casefold()
    publication_types = {item.casefold() for item in record.publication_types}
    review_signals = (
        bool(publication_types & {"review", "meta-analysis", "systematic review"})
        or "systematic review" in combined
        or "meta-analysis" in combined
    )
    ad_hoc_signals = any(
        marker in combined
        for marker in ("post hoc", "post-hoc", "subgroup analysis", "exploratory analysis")
    )
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
    )
    primary_endpoint_signal = any(
        marker in combined
        for marker in (
            "primary endpoint",
            "primary endpoints",
            "co-primary endpoint",
            "co-primary endpoints",
            "primary outcome",
            "primary outcomes",
        )
    )
    result_signal = any(
        marker in combined
        for marker in (
            "results are reported",
            "results showed",
            "we report",
            "efficacy and safety",
            "trial findings",
        )
    )
    signals: tuple[str, ...]
    if not matched:
        role: PublicationRole = "unrelated"
        signals = ("未匹配目标 NCT",)
        rationale = "正文未匹配目标试验登记号，不能据此建立论文—试验关系。"
    elif review_signals:
        role = "review"
        signals = ("综述或荟萃分析出版类型",)
        rationale = "出版类型或题名摘要表明这是综述/荟萃分析，不能替代主要结果报告。"
    elif ad_hoc_signals:
        role = "ad_hoc_analysis"
        signals = ("事后、亚组或探索性分析用语",)
        rationale = "题名或摘要明确标记事后、亚组或探索性分析。"
    elif protocol_signal:
        role = "supporting_publication"
        signals = ("目标 NCT", "试验方案出版类型或用语")
        rationale = "这是试验方案或设计论文，不得按主要结果报告使用。"
    elif randomized_signal and primary_endpoint_signal and result_signal:
        role = "primary_report"
        signals = ("目标 NCT", "随机/分期试验", "主要终点结果")
        rationale = "论文匹配目标 NCT，并报告随机/分期试验的共同主要终点或主要终点结果。"
    else:
        role = "supporting_publication"
        signals = ("目标 NCT", "未满足主要报告判定条件")
        rationale = "论文与目标 NCT 有关，但未同时提供主要报告所需的试验与主要终点信号。"
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
        mentioned = {item.upper() for item in _NCT_ID.findall(text)}
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
