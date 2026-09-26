"""Export a verified committed current generation as portable HTML sites.

This is a report share, not a Skill installation bundle or a new acceptance
decision. The exporter never reads an old accepted site in place of current.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import posixpath
import re
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import urlencode, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ci_workflow.application.latest_delivery import read_current_delivery

ReportCode = Literal["A", "B", "C"]
_SHAREABLE_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".png", ".webp", ".woff2"}
_PRIVATE_DATA = re.compile(
    rb"(?:/Users/|/home/|file://|[A-Za-z]:\\Users\\|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|"
    rb"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,})\b|"
    rb'"(?:access_token|refresh_token|session_token|api_key)"\s*:)'
)
_QUERY_KEY = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")


class ShareViewSelection(BaseModel):
    """One saved view, bound to its report within the committed current bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    revision: int = Field(ge=0)
    entry_page: str = "overview.html"
    query: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @field_validator("entry_page")
    @classmethod
    def _safe_page(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute() or not value.endswith(".html") or "\\" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or ":" in value or "%" in value or "?" in value or "#" in value
        ):
            raise ValueError("分享入口页面路径无效")
        return value

    @field_validator("query")
    @classmethod
    def _closed_query(cls, value: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
        if len(value) > 32:
            raise ValueError("分享视图筛选项过多")
        for key, items in value.items():
            if _QUERY_KEY.fullmatch(key) is None or len(items) > 60:
                raise ValueError("分享视图筛选键或数量无效")
            if any(
                not isinstance(item, str) or len(item) > 240
                or any(ord(character) < 32 for character in item)
                for item in items
            ):
                raise ValueError("分享视图筛选值无效")
        return value


@dataclass(frozen=True)
class ShareExportReceipt:
    output: Path
    sha256: str
    current_revision: int
    reports: tuple[ReportCode, ...]


def _entry_href(selection: ShareViewSelection) -> str:
    pairs = [
        (key, item)
        for key in sorted(selection.query)
        for item in selection.query[key]
    ]
    suffix = "?" + urlencode(pairs) if pairs else ""
    return f"{selection.report}/{selection.entry_page}{suffix}"


class _FilterInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, str | None]] = []
        self.values: dict[str, set[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        dimension = attributes.get("data-filter-dimension")
        inherited = next((item for _tag, item in reversed(self._stack) if item), None)
        active = dimension or inherited
        value = attributes.get("data-filter-value")
        if active and value:
            self.values.setdefault(active, set()).add(value)
        if dimension:
            self.values.setdefault(dimension, set())
        self._stack.append((tag, dimension))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break


def _validate_view_selection(selection: ShareViewSelection, page: bytes) -> None:
    if not selection.query:
        return
    inventory = _FilterInventory()
    inventory.feed(page.decode("utf-8"))
    special: dict[str, set[str] | None] = {}
    if selection.report == "A":
        special = {
            "matrix_x": {"value", "difference"},
            "matrix_y": {"teae", "sae"},
            "matrix_size": {"treatment", "total"},
            "matrix_facet": None,
            "focus": None,
        }
    elif selection.report == "C":
        special = {"criteria_q": None, "criteria_hide": None, "focus": None}
    for key, values in selection.query.items():
        allowed = inventory.values.get(key, special.get(key))
        if key not in inventory.values and key not in special:
            raise ValueError(f"分享视图筛选键不属于{selection.report}入口页面：{key}")
        if allowed is not None and any(value not in allowed for value in values):
            raise ValueError(f"分享视图筛选值不属于{selection.report}入口页面：{key}")


class _ResourceInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        reference: str | None = None
        if tag in {"script", "img", "source"}:
            reference = attributes.get("src")
        elif tag == "link" and any(
            kind in (attributes.get("rel") or "").split()
            for kind in ("stylesheet", "icon", "preload")
        ):
            reference = attributes.get("href")
        if reference:
            self.references.append(reference)


def _check_local_reference(
    relative_page: str, reference: str, available: set[str],
) -> None:
    if reference.startswith("#") or reference == "data:,":
        return
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or parsed.path.startswith(("/", "\\")):
        raise ValueError("分享页面依赖外部或绝对路径资源")
    target = posixpath.normpath(posixpath.join(
        posixpath.dirname(relative_page), parsed.path,
    ))
    if target.startswith("../") or target not in available:
        raise ValueError(f"分享页面缺少本地资源：{relative_page} -> {reference}")


def _validate_static_resources(files: dict[str, bytes]) -> None:
    available = set(files)
    for relative, content in files.items():
        if relative.endswith(".html"):
            inventory = _ResourceInventory()
            inventory.feed(content.decode("utf-8"))
            for reference in inventory.references:
                _check_local_reference(relative, reference, available)
        elif relative.endswith(".css"):
            css = content.decode("utf-8")
            if re.search(r"@import\b", css, re.IGNORECASE):
                raise ValueError("离线分享不接受CSS远程或嵌套导入")
            for match in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", css, re.IGNORECASE):
                _check_local_reference(relative, match.group(1).strip(), available)


def _zip_write(archive: ZipFile, name: str, payload: bytes) -> None:
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, payload)


def _launcher(selections: tuple[ShareViewSelection, ...], revision: int) -> bytes:
    links = "".join(
        '<li><a href="' + html.escape(_entry_href(selection), quote=True)
        + '">打开 ' + selection.report + " 报告</a></li>"
        for selection in selections
    )
    return (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>离线报告入口</title><body><main><h1>离线报告入口</h1>'
        f"<p>当前事实版本 {revision}。三类报告各自独立；外部来源链接需要联网。</p>"
        f"<ul>{links}</ul></main></body></html>"
    ).encode()


def export_current_html_share(
    project_root: Path,
    output: Path,
    *,
    selections: tuple[ShareViewSelection, ...],
) -> ShareExportReceipt:
    """Copy only verified current HTML bytes; never overwrite an existing export."""
    if not selections or len({item.report for item in selections}) != len(selections):
        raise ValueError("分享包必须选择至少一份且不得重复报告")
    current = read_current_delivery(project_root)
    if current is None:
        raise ValueError("当前交付不存在，不能从旧HTML拼装分享包")
    available = {item.report: item for item in current.reports}
    if any(item.report not in available for item in selections):
        raise ValueError("分享配置包含当前未交付报告")
    if any(item.revision != available[item.report].revision for item in selections):
        raise ValueError("分享配置revision与当前报告版本不一致")
    root = project_root.expanduser().resolve()
    destination = output.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("分享包目标已存在，禁止覆盖")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("分享包父目录不存在或不是普通目录")

    manifest_reports: dict[str, object] = {}
    members: list[tuple[str, bytes]] = []
    for selection in selections:
        delivery = available[selection.report]
        if selection.entry_page not in delivery.file_hashes:
            raise ValueError("分享配置入口页面不属于当前报告")
        site = root / delivery.site_relative_path
        _validate_view_selection(selection, (site / selection.entry_page).read_bytes())
        copied_hashes: dict[str, str] = {}
        site_files: dict[str, bytes] = {}
        for relative, expected in sorted(delivery.file_hashes.items()):
            if relative == "data/consumer-receipt.json":
                continue  # engineering receipt, not required for offline reading
            path = site / relative
            if path.suffix.lower() not in _SHAREABLE_SUFFIXES:
                raise ValueError("当前站点含不可分享的文件类型")
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("当前站点文件哈希漂移")
            if (
                (path.suffix.lower() in {".html", ".json"} or relative.startswith("data/"))
                and _PRIVATE_DATA.search(content)
            ):
                raise ValueError("当前站点含本地绝对路径或凭据样式内容，拒绝分享")
            copied_hashes[relative] = expected
            site_files[relative] = content
            members.append((f"{selection.report}/{relative}", content))
        _validate_static_resources(site_files)
        manifest_reports[selection.report] = {
            "report_revision": delivery.revision,
            "report_version": delivery.report_version,
            "source_site_file_sha256": delivery.file_hashes,
            "file_sha256": copied_hashes,
            "entry_href": _entry_href(selection),
            "view_config": selection.model_dump(mode="json"),
        }
    manifest = {
        "schema_version": "1.0",
        "kind": "current-html-report-share",
        "project_id": current.project_id,
        "current_revision": current.revision,
        "current_generation_sha256": hashlib.sha256(
            (current.model_dump_json() + "\n").encode("utf-8")
        ).hexdigest(),
        "fact_revision_digest": current.fact_revision_digest,
        "reports": manifest_reports,
        "external_sources_require_network": True,
        "status": "user_current_not_scientific_release_acceptance",
    }
    metadata = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n").encode("utf-8")
    launcher = _launcher(selections, current.revision)
    file_descriptor, temporary = tempfile.mkstemp(
        prefix=".html-share-", suffix=".zip", dir=destination.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as stream:
            with ZipFile(stream, "w") as archive:
                _zip_write(archive, "打开报告.html", launcher)
                _zip_write(archive, "share-manifest.json", metadata)
                for name, content in members:
                    _zip_write(archive, name, content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)  # fail closed if another writer claimed the path
    finally:
        Path(temporary).unlink(missing_ok=True)
    return ShareExportReceipt(
        output=destination,
        sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        current_revision=current.revision,
        reports=tuple(item.report for item in selections),
    )
