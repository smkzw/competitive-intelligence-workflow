from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import cast

from ci_workflow.domain.evidence import (
    ContentBlob,
    DateEvidence,
    DateEvidenceState,
    DatePrecision,
    EvidenceFragmentRecord,
    EvidenceLocator,
    SourceTextDerivation,
    SourceVersionRecord,
    source_version_identity,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.sqlite import open_database


class ContentIntegrityError(RuntimeError):
    """内容寻址文件的路径或摘要与记录不一致。"""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _offset_label(value: datetime) -> str:
    raw = value.strftime("%z")
    return f"{raw[:3]}:{raw[3:]}"


class ContentAddressedStore:
    """项目内、可移动、内容寻址的不可变原文库。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.raw_root = self.project_root / "evidence/raw/sha256"

    def resolve_relative(self, relative_path: str) -> Path:
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in relative_path:
            raise ContentIntegrityError("内容路径必须留在项目目录内")
        path = self.project_root / Path(*pure.parts)
        for parent in (path, *path.parents):
            if parent == self.project_root:
                break
            if parent.is_symlink():
                raise ContentIntegrityError("内容寻址路径不得经过软链接")
        resolved = path.resolve()
        if not resolved.is_relative_to(self.project_root):
            raise ContentIntegrityError("内容路径必须留在项目目录内")
        return resolved

    def put_bytes(self, content: bytes, *, media_type: str) -> ContentBlob:
        if not content:
            raise ValueError("原文内容不能为空")
        if not media_type.strip():
            raise ValueError("原文媒体类型不能为空")
        digest = hashlib.sha256(content).hexdigest()
        relative = PurePosixPath(
            "evidence", "raw", "sha256", digest[:2], f"{digest}.bin"
        ).as_posix()
        destination = self.resolve_relative(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            existing_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            if existing_digest != digest:
                raise ContentIntegrityError("内容寻址文件摘要不一致")
        else:
            descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{digest}.", dir=destination.parent
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, destination)
            except BaseException:
                Path(temp_name).unlink(missing_ok=True)
                raise
        return ContentBlob(
            sha256=digest,
            relative_path=relative,
            byte_size=len(content),
            media_type=media_type.strip(),
        )

    def read_bytes(self, blob: ContentBlob) -> bytes:
        content = self.resolve_relative(blob.relative_path).read_bytes()
        if hashlib.sha256(content).hexdigest() != blob.sha256:
            raise ContentIntegrityError("内容寻址文件摘要不一致")
        if len(content) != blob.byte_size:
            raise ContentIntegrityError("内容寻址文件大小与记录不一致")
        return content


class EvidenceRepository:
    """把内容寻址原文、SQLite 来源版本和证据片段连成一条链。"""

    def __init__(self, database_path: Path, content_store: ContentAddressedStore) -> None:
        self.database_path = database_path
        self.content_store = content_store

    def add_source_version(
        self,
        *,
        source_id: str,
        content: bytes,
        media_type: str,
        acquired_at: datetime,
        published_at: DateEvidence,
        effective_at: DateEvidence,
        first_disclosed_at: DateEvidence,
        text_derivation: SourceTextDerivation | None = None,
    ) -> SourceVersionRecord:
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise ValueError("来源获取时间必须包含明确时区偏移")
        if text_derivation is not None:
            self.content_store.read_bytes(text_derivation.raw_asset)
            if hashlib.sha256(content).hexdigest() != text_derivation.text_sha256:
                raise ContentIntegrityError("入库文本与原始资产派生摘要不一致")
        blob = self.content_store.put_bytes(content, media_type=media_type)
        version_id = source_version_identity(
            source_id, blob.sha256, published_at=published_at,
            effective_at=effective_at, first_disclosed_at=first_disclosed_at,
            text_derivation=text_derivation,
        )
        with open_database(self.database_path) as database:
            exists = database.execute(
                "SELECT 1 FROM source_versions WHERE source_version_id = ?",
                (version_id,),
            ).fetchone()
            if exists is not None:
                return self._read_source_version(database, version_id)

            database.execute(
                """
                INSERT OR IGNORE INTO content_blobs (
                    content_sha256, relative_path, byte_size, media_type, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    blob.sha256,
                    blob.relative_path,
                    blob.byte_size,
                    blob.media_type,
                    acquired_at.isoformat(),
                ),
            )
            if text_derivation is not None:
                raw = text_derivation.raw_asset
                database.execute(
                    "INSERT OR IGNORE INTO content_blobs "
                    "(content_sha256, relative_path, byte_size, media_type, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        raw.sha256, raw.relative_path, raw.byte_size,
                        raw.media_type, acquired_at.isoformat(),
                    ),
                )
            database.execute(
                """
                INSERT INTO source_versions (
                    source_version_id, source_id, content_sha256, acquired_at,
                    published_at, effective_at, first_disclosed_at, source_locator,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    source_id,
                    blob.sha256,
                    acquired_at.isoformat(),
                    published_at.value.isoformat() if published_at.value else None,
                    effective_at.value.isoformat() if effective_at.value else None,
                    first_disclosed_at.value.isoformat()
                    if first_disclosed_at.value
                    else None,
                    _canonical_json(first_disclosed_at.locator.model_dump(mode="json")),
                    acquired_at.isoformat(),
                ),
            )
            if text_derivation is not None:
                database.execute(
                    "INSERT INTO source_text_derivations "
                    "(source_version_id, raw_content_sha256, derivation_json) VALUES (?, ?, ?)",
                    (version_id, text_derivation.raw_asset.sha256,
                     _canonical_json(text_derivation.model_dump(mode="json"))),
                )
            acquired_locator = EvidenceLocator(
                document_role="acquisition-receipt",
                field_path="acquired_at",
            )
            date_values = {
                "acquired_at": DateEvidence(
                    state="reported", value=acquired_at, locator=acquired_locator
                ),
                "published_at": published_at,
                "effective_at": effective_at,
                "first_disclosed_at": first_disclosed_at,
            }
            for role, date_evidence in date_values.items():
                value = date_evidence.value
                database.execute(
                    """
                    INSERT INTO source_date_assertions (
                        assertion_id, source_version_id, date_role, disclosure_state,
                        observed_at, timezone, date_precision, locator_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stable_id("source-date", version_id, role),
                        version_id,
                        role,
                        date_evidence.state,
                        value.isoformat() if value else None,
                        _offset_label(value if value else acquired_at),
                        date_evidence.precision,
                        _canonical_json(date_evidence.locator.model_dump(mode="json")),
                        acquired_at.isoformat(),
                    ),
                )
            return self._read_source_version(database, version_id)

    def _read_source_version(
        self, database: sqlite3.Connection, source_version_id: str
    ) -> SourceVersionRecord:
        row = database.execute(
            """
            SELECT sv.source_version_id, sv.source_id, sv.content_sha256,
                   sv.acquired_at, sv.created_at, cb.relative_path, cb.media_type
            FROM source_versions AS sv
            JOIN content_blobs AS cb ON cb.content_sha256 = sv.content_sha256
            WHERE sv.source_version_id = ?
            """,
            (source_version_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"来源版本不存在：{source_version_id}")
        assertions = {
            str(item[0]): (
                str(item[1]),
                item[2],
                str(item[3]),
                json.loads(str(item[4])),
            )
            for item in database.execute(
                """
                SELECT date_role, disclosure_state, observed_at, date_precision,
                       locator_json
                FROM source_date_assertions WHERE source_version_id = ?
                """,
                (source_version_id,),
            )
        }

        def date_evidence(role: str) -> DateEvidence:
            state, observed_at, precision, locator = assertions[role]
            return DateEvidence(
                state=cast(DateEvidenceState, state),
                value=datetime.fromisoformat(str(observed_at))
                if observed_at is not None
                else None,
                precision=cast(DatePrecision, precision),
                locator=EvidenceLocator.model_validate(locator),
            )

        acquired = date_evidence("acquired_at")
        if acquired.value is None:
            raise ContentIntegrityError("来源版本缺少获取时间")
        has_derivations = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'source_text_derivations'"
        ).fetchone() is not None
        derivation_row = (
            database.execute(
                "SELECT derivation_json FROM source_text_derivations WHERE source_version_id = ?",
                (source_version_id,),
            ).fetchone()
            if has_derivations else None
        )
        return SourceVersionRecord(
            schema_version="1.0",
            source_version_id=str(row[0]),
            source_id=str(row[1]),
            content_sha256=str(row[2]),
            content_relative_path=str(row[5]),
            media_type=str(row[6]),
            text_derivation=(
                SourceTextDerivation.model_validate_json(str(derivation_row[0]))
                if derivation_row is not None else None
            ),
            acquired_at=acquired.value,
            acquired_locator=acquired.locator,
            published_at=date_evidence("published_at"),
            effective_at=date_evidence("effective_at"),
            first_disclosed_at=date_evidence("first_disclosed_at"),
            created_at=datetime.fromisoformat(str(row[4])),
        )

    def add_fragment(
        self,
        *,
        source_version_id: str,
        locator: EvidenceLocator,
        original_text: str,
        created_at: datetime | None = None,
    ) -> EvidenceFragmentRecord:
        timestamp = created_at or datetime.now().astimezone()
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("证据片段创建时间必须包含明确时区偏移")
        digest = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
        locator_json = _canonical_json(locator.model_dump(mode="json"))
        fragment_id = stable_id(
            "evidence-fragment", source_version_id, locator_json, digest
        )
        record = EvidenceFragmentRecord(
            schema_version="1.0",
            fragment_id=fragment_id,
            source_version_id=source_version_id,
            locator=locator,
            original_text=original_text,
            content_sha256=digest,
            created_at=timestamp,
        )
        with open_database(self.database_path) as database:
            existing = database.execute(
                "SELECT 1 FROM evidence_fragments WHERE fragment_id = ?",
                (record.fragment_id,),
            ).fetchone()
            if existing is None:
                database.execute(
                    """
                    INSERT INTO evidence_fragments (
                        fragment_id, source_version_id, locator, content_text,
                        content_sha256, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.fragment_id,
                        record.source_version_id,
                        locator_json,
                        record.original_text,
                        record.content_sha256,
                        record.created_at.isoformat(),
                    ),
                )
        return record

    def read_fragment(self, fragment_id: str) -> EvidenceFragmentRecord:
        with open_database(self.database_path) as database:
            row = database.execute(
                """
                SELECT fragment_id, source_version_id, locator, content_text,
                       content_sha256, created_at
                FROM evidence_fragments WHERE fragment_id = ?
                """,
                (fragment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"证据片段不存在：{fragment_id}")
        return EvidenceFragmentRecord(
            schema_version="1.0",
            fragment_id=str(row[0]),
            source_version_id=str(row[1]),
            locator=EvidenceLocator.model_validate(json.loads(str(row[2]))),
            original_text=str(row[3]),
            content_sha256=str(row[4]),
            created_at=datetime.fromisoformat(str(row[5])),
        )

    def verify_reopened_fragment_record(
        self,
        fragment: EvidenceFragmentRecord,
        *,
        reopened_original_text: str,
        source_version_id: str,
    ) -> SourceVersionRecord:
        """从项目真源库重读来源、正文和片段，供科学注册表验真。"""

        stored_fragment = self.read_fragment(fragment.fragment_id)
        if stored_fragment != fragment:
            raise ContentIntegrityError("待验片段与项目真源库记录不一致")
        if fragment.source_version_id != source_version_id:
            raise ContentIntegrityError("重开来源版本与证据片段不一致")
        if reopened_original_text != stored_fragment.original_text:
            raise ContentIntegrityError("重开原文与项目真源库片段不一致")
        with open_database(self.database_path) as database:
            source_version = self._read_source_version(database, source_version_id)
            row = database.execute(
                """
                SELECT byte_size FROM content_blobs WHERE content_sha256 = ?
                """,
                (source_version.content_sha256,),
            ).fetchone()
        if row is None:
            raise ContentIntegrityError("来源版本缺少内容寻址正文")
        blob = ContentBlob(
            sha256=source_version.content_sha256,
            relative_path=source_version.content_relative_path,
            byte_size=int(row[0]),
            media_type=source_version.media_type,
        )
        source_content = self.content_store.read_bytes(blob)
        if source_version.text_derivation is not None:
            from ci_workflow.storage.source_derivation import (
                SourceDerivationError,
                verify_source_text_derivation,
            )

            try:
                verify_source_text_derivation(
                    self.content_store.project_root, source_version.text_derivation,
                    source_content.decode("utf-8"),
                )
            except (UnicodeDecodeError, SourceDerivationError) as error:
                raise ContentIntegrityError("原始资产与重开文本的派生链校验失败") from error
        if source_version.media_type.startswith("text/") or any(
            marker in source_version.media_type
            for marker in ("json", "xml", "javascript")
        ):
            decoded = source_content.decode("utf-8")
            if stored_fragment.original_text not in decoded:
                raise ContentIntegrityError("证据片段原文不存在于已保存来源正文")
        return source_version
