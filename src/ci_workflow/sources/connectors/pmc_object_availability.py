"""冻结的 PMC 官方对象可用见证：校验和绑定的 Last-Modified 只证明精确字节
按某个截止时刻可用；它不设定首次披露、发表或获取日期，也不构成事实、
更正或临床采纳结论。

本模块不下载、不建立新基础设施，也不接受任意来源地址：构建函数把既有
捕获的官方 XML 对象字节、官方元数据 JSON 与两份原始 HTTP 响应回执原样
导入调用方提供的隔离内容寻址库，并返回一个冻结的类型化见证；绝不重建
或推断任何时间戳。复核函数重开全部四项资产并重新校验，绝不信任模型
字段；仅当固定 XML 对象 Last-Modified 不晚于给定带时区截止时刻才接受。
最早公开日期仍然未知：Last-Modified 不是首次发表证据。撤稿与稿件标志
按官方元数据的严格布尔原样记录并连同许可代码一起保存；绝不据此推断
再分发许可或科学接受。内容/版本标签本身不是证明，也不出具整版本
无更正证书；XML 元数据声明实体即拒绝，官方 JATS DOCTYPE 可保留。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Literal
from urllib.parse import parse_qs, urlsplit, urlunsplit
from xml.etree import ElementTree as ET
from xml.parsers import expat

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.sources.connectors.linked_jats import (
    DEFAULT_MAX_BYTES,
    LinkedJatsInspectionError,
    _article_element,
    inspect_linked_jats_xml,
)
from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
from ci_workflow.storage.source_derivation import source_json_decoder

PMC_OBJECT_HOST = "pmc-oa-opendata.s3.amazonaws.com"
PMC_OA_BUCKET = "pmc-oa-opendata"
METADATA_MAX_BYTES = 1024 * 1024
RECEIPT_MAX_BYTES = 64 * 1024
XML_MAX_BYTES = DEFAULT_MAX_BYTES

_MD5_HEX = re.compile(r"[0-9a-f]{32}")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
_PMCID = re.compile(r"PMC[0-9]+")
_QUOTED_MD5 = re.compile(r'"([0-9a-f]{32})"')
_RECEIPT_HEADERS = frozenset(
    {"Content-Type", "ETag", "Last-Modified", "Content-Length", "Date"}
)
_RECEIPT_FIELDS = frozenset(
    {
        "url",
        "response_url",
        "status",
        "request_started_at",
        "response_completed_at",
        "headers",
        "sha256",
        "bytes",
        "relative_path",
    }
)
_METADATA_FIELDS = (
    "pmcid",
    "version",
    "pmid",
    "doi",
    "is_retracted",
    "is_manuscript",
    "license_code",
    "xml_url",
)


class PmcObjectAvailabilityError(ValueError):
    """PMC 官方对象见证不能成立或不能按截止时刻证明；失败必须封闭。"""


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PmcObjectAvailabilityError(f"{label}必须是非空文本")
    return value


def _aware_iso(value: object, label: str) -> datetime:
    text = _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise PmcObjectAvailabilityError(f"{label}不是可解析的ISO时间") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PmcObjectAvailabilityError(f"{label}缺少时区偏移")
    return parsed.astimezone(UTC)


def _http_instant(value: object, label: str) -> datetime:
    text = _require_text(value, label)
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError) as error:
        raise PmcObjectAvailabilityError(f"{label}不是可解析的HTTP时间") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PmcObjectAvailabilityError(f"{label}缺少时区偏移")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class _Receipt:
    url: str
    relative_path: str
    sha256: str
    byte_size: int
    etag_md5: str
    started_at: datetime
    completed_at: datetime
    response_date: datetime
    last_modified: datetime


def _parse_receipt(raw: bytes, label: str) -> _Receipt:
    if not raw or len(raw) > RECEIPT_MAX_BYTES:
        raise PmcObjectAvailabilityError(f"{label}回执为空或超出受控字节预算")
    try:
        payload: object = source_json_decoder().decode(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise PmcObjectAvailabilityError(f"{label}回执不是严格JSON") from error
    if not isinstance(payload, dict) or set(payload) != _RECEIPT_FIELDS:
        raise PmcObjectAvailabilityError(f"{label}回执字段与捕获协议不一致")
    headers = payload["headers"]
    if not isinstance(headers, dict) or set(headers) != _RECEIPT_HEADERS:
        raise PmcObjectAvailabilityError(f"{label}回执头与捕获协议不一致")
    for key in _RECEIPT_HEADERS:
        _require_text(headers[key], f"{label}回执头 {key}")
    content_type = headers["Content-Type"].split(";", 1)[0].strip().lower()
    # Official S3 captures use binary/octet-stream for both objects; their exact
    # JSON/XML structures are independently parsed below, not inferred from HTTP200.
    allowed_media = ({"application/json"} if label == "元数据" else {"application/xml", "text/xml"})
    allowed_media |= {"binary/octet-stream", "application/octet-stream"}
    if content_type not in allowed_media:
        raise PmcObjectAvailabilityError(f"{label}响应媒体类型与对象种类不一致")
    status = payload["status"]
    if type(status) is not int or status != 200:
        raise PmcObjectAvailabilityError(f"{label}回执不是HTTP 200完整获取")
    sha256 = _require_text(payload["sha256"], f"{label}回执 sha256")
    if _SHA256_HEX.fullmatch(sha256) is None:
        raise PmcObjectAvailabilityError(f"{label}回执 sha256 必须是64位小写十六进制")
    byte_size = payload["bytes"]
    if type(byte_size) is not int or byte_size < 1:
        raise PmcObjectAvailabilityError(f"{label}回执字节长度必须为正整数")
    url = _require_text(payload["url"], f"{label}回执请求地址")
    response_url = _require_text(payload["response_url"], f"{label}回执响应地址")
    if response_url != url:
        raise PmcObjectAvailabilityError(f"{label}回执的响应地址与请求地址不一致；不接受重定向")
    started_at = _aware_iso(payload["request_started_at"], f"{label}回执请求开始时刻")
    completed_at = _aware_iso(payload["response_completed_at"], f"{label}回执完成时刻")
    if started_at > completed_at:
        raise PmcObjectAvailabilityError(f"{label}回执的请求开始时刻晚于完成时刻")
    response_date = _http_instant(headers["Date"], f"{label}回执 Date 头")
    last_modified = _http_instant(headers["Last-Modified"], f"{label}回执 Last-Modified 头")
    if last_modified > response_date:
        raise PmcObjectAvailabilityError(f"{label}回执的 Last-Modified 晚于响应 Date")
    if last_modified > completed_at:
        raise PmcObjectAvailabilityError(f"{label}回执的 Last-Modified 晚于完成时刻")
    content_length = headers["Content-Length"]
    if (
        not isinstance(content_length, str)
        or not content_length.isascii()
        or not content_length.isdigit()
    ):
        raise PmcObjectAvailabilityError(f"{label}回执 Content-Length 必须是数字文本")
    if int(content_length) != byte_size:
        raise PmcObjectAvailabilityError(f"{label}回执 Content-Length 与字节长度不一致")
    etag_match = _QUOTED_MD5.fullmatch(str(headers["ETag"]))
    if etag_match is None:
        raise PmcObjectAvailabilityError(f"{label}回执 ETag 必须是带引号的单部分32位十六进制MD5")
    return _Receipt(
        url=url,
        relative_path=_require_text(payload["relative_path"], f"{label}回执相对路径"),
        sha256=sha256,
        byte_size=byte_size,
        etag_md5=etag_match[1],
        started_at=started_at,
        completed_at=completed_at,
        response_date=response_date,
        last_modified=last_modified,
    )


def _https_object_address(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != PMC_OBJECT_HOST:
        raise PmcObjectAvailabilityError("PMC对象地址必须是固定官方主机的HTTPS地址")
    if parts.fragment:
        raise PmcObjectAvailabilityError("PMC对象地址不得携带片段")
    return parts.path, parts.query


def _xml_object_md5(url: str, pmcid: str, version: int) -> str:
    path, query = _https_object_address(url)
    if path != f"/{pmcid}.{version}/{pmcid}.{version}.xml":
        raise PmcObjectAvailabilityError("XML对象路径必须精确对应PMCID与版本")
    try:
        parsed = parse_qs(query, strict_parsing=True, keep_blank_values=True)
    except ValueError as error:
        raise PmcObjectAvailabilityError("XML对象地址只允许精确的md5查询参数") from error
    if set(parsed) != {"md5"} or len(parsed["md5"]) != 1:
        raise PmcObjectAvailabilityError("XML对象地址只允许精确的md5查询参数")
    md5 = parsed["md5"][0]
    if _MD5_HEX.fullmatch(md5) is None:
        raise PmcObjectAvailabilityError("XML对象地址的md5参数必须是32位小写十六进制")
    if query != f"md5={md5}":
        raise PmcObjectAvailabilityError("XML对象地址只允许精确的md5查询参数")
    return md5


def _require_metadata_address(url: str, pmcid: str, version: int) -> None:
    path, query = _https_object_address(url)
    if query:
        raise PmcObjectAvailabilityError("元数据对象地址不得携带查询参数")
    if path != f"/metadata/{pmcid}.{version}.json":
        raise PmcObjectAvailabilityError("元数据对象路径必须精确对应PMCID与版本")


@dataclass(frozen=True)
class _Metadata:
    pmcid: str
    version: int
    pmid: str | None
    doi: str
    is_retracted: bool
    is_manuscript: bool
    license_code: str
    xml_url_https: str
    xml_url_md5: str


def _parse_metadata(raw: bytes) -> _Metadata:
    if not raw or len(raw) > METADATA_MAX_BYTES:
        raise PmcObjectAvailabilityError("官方元数据为空或超出受控字节预算")
    try:
        payload: object = source_json_decoder().decode(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise PmcObjectAvailabilityError("官方元数据不是严格UTF8 JSON") from error
    if not isinstance(payload, dict):
        raise PmcObjectAvailabilityError("官方元数据必须是JSON对象")
    for key in _METADATA_FIELDS:
        if key not in payload:
            raise PmcObjectAvailabilityError(f"官方元数据缺少必要字段 {key}")
    pmcid = payload["pmcid"]
    if not isinstance(pmcid, str) or _PMCID.fullmatch(pmcid) is None:
        raise PmcObjectAvailabilityError("官方元数据 PMCID 必须形如 PMC 加数字")
    version = payload["version"]
    if type(version) is not int or version < 1:
        raise PmcObjectAvailabilityError("官方元数据版本必须是正整数")
    pmid_value = payload["pmid"]
    if pmid_value is None:
        pmid: str | None = None
    elif type(pmid_value) is int and pmid_value >= 1:
        pmid = str(pmid_value)
    else:
        raise PmcObjectAvailabilityError("官方元数据 PMID 必须是正整数或空")
    doi = _require_text(payload["doi"], "官方元数据 DOI")
    is_retracted = payload["is_retracted"]
    is_manuscript = payload["is_manuscript"]
    if type(is_retracted) is not bool or type(is_manuscript) is not bool:
        raise PmcObjectAvailabilityError("is_retracted 与 is_manuscript 必须是严格布尔")
    license_code = _require_text(payload["license_code"], "官方元数据许可代码")
    xml_url = _require_text(payload["xml_url"], "官方元数据 xml_url")
    parts = urlsplit(xml_url)
    if parts.scheme != "s3" or parts.netloc != PMC_OA_BUCKET:
        raise PmcObjectAvailabilityError("官方元数据 xml_url 必须指向固定官方 bucket 的 s3 地址")
    if parts.fragment:
        raise PmcObjectAvailabilityError("官方元数据 xml_url 不得携带片段")
    if parts.path != f"/{pmcid}.{version}/{pmcid}.{version}.xml":
        raise PmcObjectAvailabilityError("官方元数据 xml_url 路径必须精确对应PMCID与版本")
    try:
        parsed_query = parse_qs(parts.query, strict_parsing=True, keep_blank_values=True)
    except ValueError as error:
        raise PmcObjectAvailabilityError("官方元数据 xml_url 查询只允许精确的md5参数") from error
    if set(parsed_query) != {"md5"} or len(parsed_query["md5"]) != 1:
        raise PmcObjectAvailabilityError("官方元数据 xml_url 查询只允许精确的md5参数")
    xml_url_md5 = parsed_query["md5"][0]
    if _MD5_HEX.fullmatch(xml_url_md5) is None:
        raise PmcObjectAvailabilityError("官方元数据 xml_url 的md5参数必须是32位小写十六进制")
    if parts.query != f"md5={xml_url_md5}":
        raise PmcObjectAvailabilityError("官方元数据 xml_url 查询只允许精确的md5参数")
    return _Metadata(
        pmcid=pmcid,
        version=version,
        pmid=pmid,
        doi=doi,
        is_retracted=is_retracted,
        is_manuscript=is_manuscript,
        license_code=license_code,
        xml_url_https=urlunsplit(("https", PMC_OBJECT_HOST, parts.path, parts.query, "")),
        xml_url_md5=xml_url_md5,
    )


def _reject_entity(*_arguments: object) -> None:
    raise PmcObjectAvailabilityError("XML声明了实体；拒绝实体展开")


def _require_front_version(raw: bytes, version: int) -> None:
    """按既有安全解析约定重放 front 的唯一 pmc-version 版本标签。"""
    try:
        safety_parser = expat.ParserCreate()
        safety_parser.EntityDeclHandler = _reject_entity
        safety_parser.Parse(raw, True)
        article = _article_element(ET.fromstring(raw))
        fronts = [child for child in article if child.tag == "front"]
        metas = (
            [child for child in fronts[0] if child.tag == "article-meta"]
            if len(fronts) == 1
            else []
        )
        versions = [
            " ".join("".join(node.itertext()).split())
            for meta in metas
            for node in meta
            if node.tag == "article-version"
            and (node.get("article-version-type") or "").strip() == "pmc-version"
        ]
    except PmcObjectAvailabilityError:
        raise
    except (ET.ParseError, expat.ExpatError, RecursionError) as error:
        raise PmcObjectAvailabilityError("XML 结构不能安全重放版本节点") from error
    if versions != [str(version)]:
        raise PmcObjectAvailabilityError("XML front 的 pmc-version 与元数据版本不一致")


def _verify_xml_identity(xml_bytes: bytes, metadata: _Metadata) -> None:
    if len(xml_bytes) > XML_MAX_BYTES:
        raise PmcObjectAvailabilityError("XML对象字节超出受控预算")
    try:
        inspection = inspect_linked_jats_xml(
            xml_bytes,
            expected_pmid=metadata.pmid,
            expected_pmcid=metadata.pmcid,
            expected_doi=metadata.doi,
            max_bytes=XML_MAX_BYTES,
        )
    except LinkedJatsInspectionError as error:
        raise PmcObjectAvailabilityError(
            f"XML front 身份或结构校验失败：{error.diagnostic}"
        ) from error
    if inspection.pmid != metadata.pmid:
        raise PmcObjectAvailabilityError("元数据 PMID 与 XML front 声明不一致或缺一")
    _require_front_version(xml_bytes, metadata.version)


@dataclass(frozen=True)
class _Derived:
    metadata: _Metadata
    xml_last_modified: datetime


def _derive(
    *,
    metadata_bytes: bytes,
    xml_bytes: bytes,
    metadata_receipt_bytes: bytes,
    xml_receipt_bytes: bytes,
) -> _Derived:
    metadata = _parse_metadata(metadata_bytes)
    metadata_receipt = _parse_receipt(metadata_receipt_bytes, "元数据")
    xml_receipt = _parse_receipt(xml_receipt_bytes, "XML")
    _require_metadata_address(metadata_receipt.url, metadata.pmcid, metadata.version)
    xml_query_md5 = _xml_object_md5(xml_receipt.url, metadata.pmcid, metadata.version)
    if metadata.xml_url_https != xml_receipt.url or metadata.xml_url_md5 != xml_query_md5:
        raise PmcObjectAvailabilityError("元数据 xml_url 无法映射到 XML 回执地址")
    if metadata_receipt.relative_path != f"{metadata.pmcid}.{metadata.version}.json":
        raise PmcObjectAvailabilityError("元数据回执相对路径与对象身份不一致")
    if xml_receipt.relative_path != f"{metadata.pmcid}.{metadata.version}.xml":
        raise PmcObjectAvailabilityError("XML回执相对路径与对象身份不一致")
    if (
        hashlib.sha256(metadata_bytes).hexdigest() != metadata_receipt.sha256
        or len(metadata_bytes) != metadata_receipt.byte_size
    ):
        raise PmcObjectAvailabilityError("元数据对象字节与回执摘要或长度不一致")
    if hashlib.md5(metadata_bytes, usedforsecurity=False).hexdigest() != metadata_receipt.etag_md5:
        raise PmcObjectAvailabilityError("元数据对象字节MD5与回执ETag不一致")
    xml_sha256 = hashlib.sha256(xml_bytes).hexdigest()
    xml_md5 = hashlib.md5(xml_bytes, usedforsecurity=False).hexdigest()
    if xml_sha256 != xml_receipt.sha256 or len(xml_bytes) != xml_receipt.byte_size:
        raise PmcObjectAvailabilityError("XML对象字节与回执摘要或长度不一致")
    if xml_md5 != xml_query_md5 or xml_md5 != xml_receipt.etag_md5:
        raise PmcObjectAvailabilityError("XML对象字节MD5与md5查询参数或ETag不一致")
    _verify_xml_identity(xml_bytes, metadata)
    return _Derived(metadata=metadata, xml_last_modified=xml_receipt.last_modified)


def _blob_for(content: bytes, media_type: str) -> ContentBlob:
    digest = hashlib.sha256(content).hexdigest()
    return ContentBlob(
        sha256=digest,
        relative_path=f"evidence/raw/sha256/{digest[:2]}/{digest}.bin",
        byte_size=len(content),
        media_type=media_type,
    )


def _require_asset(blob: ContentBlob, media_type: str) -> None:
    digest = blob.sha256
    if blob.relative_path != f"evidence/raw/sha256/{digest[:2]}/{digest}.bin":
        raise PmcObjectAvailabilityError("见证资产路径未按内容寻址绑定")
    if blob.byte_size < 1:
        raise PmcObjectAvailabilityError("见证资产不得为空")
    if blob.media_type != media_type:
        raise PmcObjectAvailabilityError("见证资产媒体类型与对象种类不一致")


class PmcObjectAvailabilityWitness(BaseModel):
    """一次冻结的 PMC 官方对象见证。

    只证明校验和绑定的 XML 对象按其官方 Last-Modified 在截止时刻精确可用；
    不是首次披露、发表或获取日期，不是事实、更正或临床采纳结论，也不得
    据此推断再分发许可或科学接受。撤稿/稿件标志按官方元数据严格布尔记录。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    pmcid: str
    version: int = Field(strict=True, ge=1)
    doi: str
    pmid: str | None = None
    is_retracted: bool = Field(strict=True)
    is_manuscript: bool = Field(strict=True)
    license_code: str
    xml_last_modified: datetime
    metadata_asset: ContentBlob
    xml_asset: ContentBlob
    metadata_receipt_asset: ContentBlob
    xml_receipt_asset: ContentBlob

    @field_validator("pmcid")
    @classmethod
    def _pmcid_shape(cls, value: str) -> str:
        if _PMCID.fullmatch(value) is None:
            raise ValueError("官方元数据 PMCID 必须形如 PMC 加数字")
        return value

    @field_validator("doi", "license_code")
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("文本不能为空")
        return value

    @field_validator("pmid")
    @classmethod
    def _pmid_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (value.isascii() and value.isdigit()):
            raise ValueError("官方元数据 PMID 必须是数字文本")
        return value

    @field_validator("xml_last_modified")
    @classmethod
    def _clock_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("XML 对象时钟必须包含明确时区偏移")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _assets_are_cas_bound(self) -> PmcObjectAvailabilityWitness:
        _require_asset(self.metadata_asset, "application/json")
        _require_asset(self.xml_asset, "application/xml")
        _require_asset(self.metadata_receipt_asset, "application/json")
        _require_asset(self.xml_receipt_asset, "application/json")
        return self


def build_pmc_object_witness(
    store: ContentAddressedStore,
    *,
    metadata_bytes: bytes,
    xml_bytes: bytes,
    metadata_receipt_bytes: bytes,
    xml_receipt_bytes: bytes,
) -> PmcObjectAvailabilityWitness:
    """把既有捕获的官方对象字节与两份原始回执原样导入调用方隔离 CAS。

    先完成全部封闭校验再写入 CAS；绝不重建或推断任何时间戳，绝不发起
    下载，也不接受任意来源地址。
    """
    derived = _derive(
        metadata_bytes=metadata_bytes,
        xml_bytes=xml_bytes,
        metadata_receipt_bytes=metadata_receipt_bytes,
        xml_receipt_bytes=xml_receipt_bytes,
    )
    metadata = derived.metadata
    return PmcObjectAvailabilityWitness(
        pmcid=metadata.pmcid,
        version=metadata.version,
        doi=metadata.doi,
        pmid=metadata.pmid,
        is_retracted=metadata.is_retracted,
        is_manuscript=metadata.is_manuscript,
        license_code=metadata.license_code,
        xml_last_modified=derived.xml_last_modified,
        metadata_asset=store.put_bytes(metadata_bytes, media_type="application/json"),
        xml_asset=store.put_bytes(xml_bytes, media_type="application/xml"),
        metadata_receipt_asset=store.put_bytes(
            metadata_receipt_bytes, media_type="application/json"
        ),
        xml_receipt_asset=store.put_bytes(xml_receipt_bytes, media_type="application/json"),
    )


def verify_pmc_object_availability(
    store: ContentAddressedStore,
    witness: PmcObjectAvailabilityWitness,
    cutoff: datetime,
) -> bytes:
    """重开全部四项 CAS 资产并重新校验；仅当固定 XML Last-Modified <= 截止才接受。

    返回重开的精确 XML 字节。截止早于固定对象时钟即失败：按该截止不可证
    可用，且最早公开日期仍未知。本函数不证明当前可用性，也不重写任何
    来源身份或事实采纳状态。
    """
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise PmcObjectAvailabilityError("复核截止时刻缺少时区偏移")
    cutoff_at = cutoff.astimezone(UTC)
    _require_asset(witness.metadata_asset, "application/json")
    _require_asset(witness.xml_asset, "application/xml")
    _require_asset(witness.metadata_receipt_asset, "application/json")
    _require_asset(witness.xml_receipt_asset, "application/json")
    try:
        metadata_bytes = store.read_bytes(witness.metadata_asset)
        xml_bytes = store.read_bytes(witness.xml_asset)
        metadata_receipt_bytes = store.read_bytes(witness.metadata_receipt_asset)
        xml_receipt_bytes = store.read_bytes(witness.xml_receipt_asset)
    except (OSError, ContentIntegrityError) as error:
        raise PmcObjectAvailabilityError("见证资产缺失、篡改或摘要漂移") from error
    derived = _derive(
        metadata_bytes=metadata_bytes,
        xml_bytes=xml_bytes,
        metadata_receipt_bytes=metadata_receipt_bytes,
        xml_receipt_bytes=xml_receipt_bytes,
    )
    metadata = derived.metadata
    redone = PmcObjectAvailabilityWitness(
        pmcid=metadata.pmcid,
        version=metadata.version,
        doi=metadata.doi,
        pmid=metadata.pmid,
        is_retracted=metadata.is_retracted,
        is_manuscript=metadata.is_manuscript,
        license_code=metadata.license_code,
        xml_last_modified=derived.xml_last_modified,
        metadata_asset=_blob_for(metadata_bytes, "application/json"),
        xml_asset=_blob_for(xml_bytes, "application/xml"),
        metadata_receipt_asset=_blob_for(metadata_receipt_bytes, "application/json"),
        xml_receipt_asset=_blob_for(xml_receipt_bytes, "application/json"),
    )
    if redone != witness:
        raise PmcObjectAvailabilityError("重开的见证与提交见证不一致；不得信任模型字段")
    if derived.xml_last_modified > cutoff_at:
        raise PmcObjectAvailabilityError(
            "复核截止时刻早于固定XML对象时钟；按该截止不可证可用，最早公开日期仍未知"
        )
    return xml_bytes
