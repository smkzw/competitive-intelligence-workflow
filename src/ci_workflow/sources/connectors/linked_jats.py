"""有界原生 JATS XML 身份与正文巡检：有效元数据 HTTP200 不等于全文。

本模块只回答两个封闭问题：原生 front 元数据中的 DOI/PMC 是否与调用方
声明的精确身份一致（PMID 若在 front 出现则必须一致），以及 body 中是否
存在非空的段落或表格内容块。它不抽取医学值、不判定论文—试验关系、不推断
日期/论文类别/许可/历史，也不声明一次结果完整性或再分发权利。HTTP200 且
front 合法但无正文时必须得到 metadata_only 状态，而不是解析失败或全文。
未知包装、多文章、身份缺失/冲突/不符一律封闭拒绝；身份只从
``front/article-meta`` 的直接 ``article-id`` 读取，绝不借用参考文献等嵌套
位置的标识。带命名空间的根元素按未知结构拒绝。官方 NLM JATS 允许携带
标准 DOCTYPE 声明（含 PUBLIC 外部 DTD 引用，标准解析器不会抓取）；实体
声明（<!ENTITY）会带来展开攻击面，一律拒绝。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import ClassVar, Literal
from xml.etree import ElementTree as ET
from xml.parsers import expat

KNOWN_JATS_WRAPPERS = frozenset({"pmc-articleset", "articleset", "article-set"})
DEFAULT_MAX_BYTES = 8 * 1024 * 1024

BodyState = Literal["body_present", "metadata_only"]
BlockKind = Literal["paragraph", "table"]


class LinkedJatsInspectionError(ValueError):
    """巡检封闭拒绝的共同基类；reason 是稳定的机器可读拒绝类别。"""

    reason: ClassVar[str] = "rejected"

    def __init__(self, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic


class LinkedJatsBoundsError(LinkedJatsInspectionError):
    """原始字节为空或超出字节预算；拒绝未受控解析。"""

    reason: ClassVar[str] = "bounds"


class LinkedJatsXmlError(LinkedJatsInspectionError):
    """原始字节不是可安全解析的 XML，或声明了实体（<!ENTITY>）。"""

    reason: ClassVar[str] = "malformed_xml"


class LinkedJatsStructureError(LinkedJatsInspectionError):
    """根元素、包装或 front 结构不能唯一确定一篇文章。"""

    reason: ClassVar[str] = "structure"


class LinkedJatsIdentityError(LinkedJatsInspectionError):
    """front 身份缺失、冲突或与声明的精确身份不符。"""

    reason: ClassVar[str] = "identity"


@dataclass(frozen=True)
class JatsBodyBlock:
    """body 中一个非空文本块；ordinal 是文档顺序，不构成精确定位器。"""

    kind: BlockKind
    ordinal: int
    text: str


@dataclass(frozen=True)
class LinkedJatsInspection:
    """一次有界的原生 JATS 身份/正文巡检结果；是证据，不是采纳事实。"""

    schema_version: Literal["1.0"]
    expected_doi: str
    expected_pmcid: str
    expected_pmid: str | None
    doi: str
    pmcid: str
    pmid: str | None
    title: str
    root_element: str
    permissions_present: bool
    copyright_statement: str | None
    license_texts: tuple[str, ...]
    body_state: BodyState
    body_detail: str
    has_paragraphs: bool
    has_tables: bool
    blocks: tuple[JatsBodyBlock, ...]
    raw_sha256: str
    raw_byte_size: int
    notes: tuple[str, ...]
    limitations: tuple[str, ...]


_DOI_ID_TYPES = frozenset({"doi"})
_PMC_ID_TYPES = frozenset({"pmcid", "pmc", "pmc-uid", "pmcid-ver", "pmcaid", "pmcaiid"})
_PMID_ID_TYPES = frozenset({"pmid"})
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)
# 浮动块可锚定在段落内部（真实 NLM JATS 常见）；段落文本排除浮动子树，
# 但正文遍历仍须下钻发现被锚定的表格/图，避免漏报可用表格。
_FLOAT_SUBTREES = frozenset({"fig", "table-wrap", "supplementary-material"})
_SKIP_WALK_SUBTREES = frozenset({"fig", "supplementary-material"})
_TABLE_TEXT_CHILDREN = frozenset({"label", "caption", "table", "table-wrap-foot"})

_LIMITATIONS = (
    "身份匹配只对应 front DOI/PMC 的精确相等；PMID 仅在 front 出现时必须一致，"
    "不推断论文—试验关系、医学值、日期、论文类别或历史。",
    "body_present 只说明原始 XML 中存在非空段落或表格；不证明一次结果完整、"
    "科学内容正确或允许再分发。",
    "metadata_only 只说明本次原生响应未包含非空正文块；不能等同于来源不可用、"
    "全文不存在或获取失败。",
    "许可与版权文本按原始节点转述；不是再分发权利或其他权利结论。",
)


def _normalized_text(element: ET.Element) -> str:
    """元素全部可见文本的空白归一化结果；不做任何语义解释。"""
    return " ".join("".join(element.itertext()).split())


def _require_identity_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"期望 {label} 必须是非空字符串")
    return value.strip()


def _normalize_doi(value: str) -> str:
    text = value.strip()
    lowered = text.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return text.lower()


def _normalize_pmcid(value: str) -> str | None:
    text = value.strip().upper()
    if text.startswith("PMC"):
        text = text[3:]
    base, dot, version = text.partition(".")
    if dot and version.isascii() and version.isdigit():
        text = base
    if not (text.isascii() and text.isdigit()):
        return None
    return f"PMC{text}"


def _normalize_pmid(value: str) -> str | None:
    text = value.strip()
    if not (text.isascii() and text.isdigit()):
        return None
    return text


def _front_identity(article_meta: ET.Element) -> tuple[str, str, str | None]:
    """只读取 article-meta 的直接 article-id；绝不进入嵌套引用位置。"""
    doi_values: list[str] = []
    pmc_values: list[str] = []
    pmid_values: list[str] = []
    for node in article_meta:
        if node.tag != "article-id":
            continue
        kind = (node.get("pub-id-type") or "").strip().lower()
        if kind in _DOI_ID_TYPES:
            normalized_doi = _normalize_doi(_normalized_text(node))
            if not normalized_doi:
                raise LinkedJatsIdentityError("front DOI 节点为空；无法确认精确身份")
            doi_values.append(normalized_doi)
        elif kind in _PMC_ID_TYPES:
            normalized_pmc = _normalize_pmcid(_normalized_text(node))
            if normalized_pmc is None:
                raise LinkedJatsIdentityError("front PMC 标识格式无效；不能作为身份")
            pmc_values.append(normalized_pmc)
        elif kind in _PMID_ID_TYPES:
            normalized_pmid = _normalize_pmid(_normalized_text(node))
            if normalized_pmid is None:
                raise LinkedJatsIdentityError("front PMID 格式无效；不能作为身份")
            pmid_values.append(normalized_pmid)
    if not doi_values:
        raise LinkedJatsIdentityError("front 缺少 DOI；不能从嵌套引用借用身份")
    if len(set(doi_values)) != 1:
        raise LinkedJatsIdentityError("front 出现冲突的重复 DOI；身份有歧义")
    if not pmc_values:
        raise LinkedJatsIdentityError("front 缺少 PMC 标识；不能从嵌套引用借用身份")
    if len(set(pmc_values)) != 1:
        raise LinkedJatsIdentityError("front 出现冲突的重复 PMC 标识；身份有歧义")
    if len(set(pmid_values)) > 1:
        raise LinkedJatsIdentityError("front 出现冲突的重复 PMID；身份有歧义")
    pmid = pmid_values[0] if pmid_values else None
    return doi_values[0], pmc_values[0], pmid


def _table_text(table_wrap: ET.Element) -> str:
    parts: list[str] = []
    for child in table_wrap:
        if child.tag in _TABLE_TEXT_CHILDREN:
            if child.tag == "table":
                # Preserve source labels/cells/values as text, not derived facts.
                # Explicit cell boundaries avoid welding n, N and estimates.
                rows = [" | ".join(_normalized_text(cell) for cell in row
                                   if cell.tag in {"th", "td"})
                        for row in child.iter("tr")]
                text = "\n".join(row for row in rows if row.strip(" |"))
            else:
                text = _normalized_text(child)
            if text:
                parts.append(text)
    return " ".join(parts)


def _table_available(table_wrap: ET.Element) -> bool:
    return bool(_table_text(table_wrap))


def _paragraph_text(element: ET.Element) -> str:
    """段落自身可见文本；内嵌浮动块（表格/图/补充材料）不计入段落文本。"""
    parts: list[str] = []
    _collect_visible_text(element, parts)
    return " ".join("".join(parts).split())


def _collect_visible_text(node: ET.Element, parts: list[str]) -> None:
    if node.text:
        parts.append(node.text)
    for child in node:
        if child.tag in _FLOAT_SUBTREES:
            parts.append(" ")
        else:
            _collect_visible_text(child, parts)
        if child.tail:
            parts.append(child.tail)


def _collect_body_blocks(container: ET.Element, blocks: list[JatsBodyBlock]) -> bool:
    """按文档顺序收集非空段落/表格文本块；返回是否存在结构可用的表格。

    段落内的浮动块（table-wrap/fig）单独处理：段落文本排除浮动子树，
    浮动块本身照常计为表格可用或按跳过规则忽略。
    """
    has_table = False
    for child in container:
        tag = child.tag
        if tag == "p":
            text = _paragraph_text(child)
            if text:
                blocks.append(JatsBodyBlock(kind="paragraph", ordinal=len(blocks), text=text))
            if _collect_body_blocks(child, blocks):
                has_table = True
        elif tag == "table-wrap":
            if _table_available(child):
                has_table = True
            table_text = _table_text(child)
            if table_text:
                blocks.append(JatsBodyBlock(kind="table", ordinal=len(blocks), text=table_text))
        elif tag in _SKIP_WALK_SUBTREES:
            continue
        elif _collect_body_blocks(child, blocks):
            has_table = True
    return has_table


def _article_element(root: ET.Element) -> ET.Element:
    articles = [element for element in root.iter() if element.tag == "article"]
    if root.tag == "article":
        if len(articles) != 1:
            raise LinkedJatsStructureError("根 article 内出现多篇 article；多文章结构拒绝巡检")
        return root
    if root.tag in KNOWN_JATS_WRAPPERS:
        direct = [child for child in root if child.tag == "article"]
        if len(articles) != 1 or len(direct) != 1 or direct[0] is not articles[0]:
            raise LinkedJatsStructureError(
                f"包装 {root.tag} 未唯一确定一篇直接子 article；拒绝猜测或借用"
            )
        return direct[0]
    raise LinkedJatsStructureError(f"根元素 {root.tag!r} 不是 article 也不是已知包装；拒绝巡检")


def inspect_linked_jats_xml(
    raw: bytes,
    expected_pmid: str | None,
    expected_pmcid: str,
    expected_doi: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> LinkedJatsInspection:
    """巡检一份原生 JATS 原始字节的精确身份与正文可用边界。

    只接受根 ``article`` 或已知包装下唯一的直接 ``article``；身份只取
    ``article/front/article-meta`` 的直接 ``article-id``；DOI/PMC 必须与
    声明精确一致，PMID 若在 front 出现则必须一致，front 缺失 PMID 时显式
    记录 None 而不到其他位置借用。字节为空/超出预算、非良构 XML、
    实体声明、结构歧义或身份缺失/冲突/不符一律抛出对应拒绝异常；官方外部
    DOCTYPE 可保留但不抓取。安全校验按 XML 编码解析，不做 ASCII 子串猜测。
    """
    if not isinstance(raw, bytes):
        raise TypeError("raw 必须是 bytes")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("max_bytes 必须是正整数")
    expected_doi_normalized = _normalize_doi(_require_identity_text(expected_doi, "DOI"))
    if not expected_doi_normalized:
        raise ValueError("期望 DOI 归一化后为空")
    expected_pmcid_normalized = _normalize_pmcid(_require_identity_text(expected_pmcid, "PMC"))
    if expected_pmcid_normalized is None:
        raise ValueError("期望 PMC 标识格式无效")
    expected_pmid_normalized: str | None = None
    if expected_pmid is not None:
        expected_pmid_normalized = _normalize_pmid(_require_identity_text(expected_pmid, "PMID"))
        if expected_pmid_normalized is None:
            raise ValueError("期望 PMID 格式无效")

    if not raw:
        raise LinkedJatsBoundsError("原始字节为空；没有可巡检的 XML")
    if len(raw) > max_bytes:
        raise LinkedJatsBoundsError(f"原始字节 {len(raw)} 超出字节预算 {max_bytes}；拒绝未受控解析")
    def reject_entity(*_arguments: object) -> None:
        raise LinkedJatsXmlError("XML 声明了实体；为防实体展开拒绝解析")

    try:
        safety_parser = expat.ParserCreate()
        safety_parser.EntityDeclHandler = reject_entity
        safety_parser.Parse(raw, True)
        root = ET.fromstring(raw)
    except LinkedJatsXmlError:
        raise
    except (ET.ParseError, expat.ExpatError, RecursionError, ValueError) as error:
        raise LinkedJatsXmlError("原始字节不是良构 XML；不接纳为原生 JATS") from error

    article = _article_element(root)
    fronts = [child for child in article if child.tag == "front"]
    if len(fronts) != 1:
        raise LinkedJatsStructureError("article 未唯一包含 front；无法确认原生 front 元数据")
    article_metas = [child for child in fronts[0] if child.tag == "article-meta"]
    if len(article_metas) != 1:
        raise LinkedJatsStructureError("front 未唯一包含 article-meta；身份有歧义")
    article_meta = article_metas[0]
    doi, pmcid, pmid = _front_identity(article_meta)

    if doi != expected_doi_normalized:
        raise LinkedJatsIdentityError("front DOI 与声明身份不一致；拒绝巡检")
    if pmcid != expected_pmcid_normalized:
        raise LinkedJatsIdentityError("front PMC 标识与声明身份不一致；拒绝巡检")
    if (
        pmid is not None
        and expected_pmid_normalized is not None
        and pmid != expected_pmid_normalized
    ):
        raise LinkedJatsIdentityError("front PMID 与声明身份不一致；拒绝巡检")

    title_groups = [child for child in article_meta if child.tag == "title-group"]
    if len(title_groups) != 1:
        raise LinkedJatsStructureError("article-meta 未唯一包含 title-group；标题有歧义")
    titles = [child for child in title_groups[0] if child.tag == "article-title"]
    if len(titles) != 1:
        raise LinkedJatsStructureError("title-group 未唯一包含 article-title；标题有歧义")
    title = _normalized_text(titles[0])
    if not title:
        raise LinkedJatsStructureError("article-title 为空；无法确认文章标题")

    permissions_nodes = [child for child in article_meta if child.tag == "permissions"]
    if len(permissions_nodes) > 1:
        raise LinkedJatsStructureError("article-meta 出现多个 permissions；许可文本有歧义")
    permissions_present = bool(permissions_nodes)
    copyright_statement: str | None = None
    license_texts: list[str] = []
    if permissions_nodes:
        statements = [child for child in permissions_nodes[0] if child.tag == "copyright-statement"]
        if len(statements) > 1:
            raise LinkedJatsStructureError("permissions 出现多个 copyright-statement")
        if statements:
            statement = _normalized_text(statements[0])
            copyright_statement = statement or None
        for license_node in permissions_nodes[0]:
            if license_node.tag != "license":
                continue
            license_text = _normalized_text(license_node)
            if license_text:
                license_texts.append(license_text)

    bodies = [child for child in article if child.tag == "body"]
    if len(bodies) > 1:
        raise LinkedJatsStructureError("article 出现多个 body；正文结构有歧义")
    blocks: list[JatsBodyBlock] = []
    has_tables = False
    if bodies:
        try:
            has_tables = _collect_body_blocks(bodies[0], blocks)
        except RecursionError as error:
            raise LinkedJatsXmlError("body 嵌套过深；拒绝未受控解析") from error
    has_paragraphs = any(block.kind == "paragraph" for block in blocks)

    if not bodies:
        body_state: BodyState = "metadata_only"
        body_detail = "原生响应只有 front 元数据（无 body 元素）；确认 metadata_only，不是解析失败"
    elif not blocks and not has_tables:
        body_state = "metadata_only"
        body_detail = "body 元素存在但没有非空段落或结构可用的表格；确认 metadata_only"
    else:
        body_state = "body_present"
        body_detail = "body 中存在非空段落或表格；仅证明原始 XML 含正文内容，不证明一次结果完整"

    notes: list[str] = []
    if pmid is None:
        if expected_pmid_normalized is None:
            notes.append("front 未声明 PMID；调用方也未声明期望 PMID，未从其他位置借用标识")
        else:
            notes.append("front 未声明 PMID；该项显式缺失，未从嵌套引用或其他位置借用")

    return LinkedJatsInspection(
        schema_version="1.0",
        expected_doi=expected_doi_normalized,
        expected_pmcid=expected_pmcid_normalized,
        expected_pmid=expected_pmid_normalized,
        doi=doi,
        pmcid=pmcid,
        pmid=pmid,
        title=title,
        root_element=root.tag,
        permissions_present=permissions_present,
        copyright_statement=copyright_statement,
        license_texts=tuple(license_texts),
        body_state=body_state,
        body_detail=body_detail,
        has_paragraphs=has_paragraphs,
        has_tables=has_tables,
        blocks=tuple(blocks),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        raw_byte_size=len(raw),
        notes=tuple(notes),
        limitations=_LIMITATIONS,
    )
