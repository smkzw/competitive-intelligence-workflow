"""内容寻址存储：来源原始字节按 sha256 落盘，事实只引用摘要。"""

from __future__ import annotations

import hashlib
from pathlib import Path


class CAS:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        return self.root / digest[:2] / digest

    def put(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self._path(digest)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        return digest

    def get(self, digest: str) -> bytes:
        return self._path(digest).read_bytes()

    def get_text(self, digest: str) -> str:
        return self.get(digest).decode("utf-8", errors="replace")

    def exists(self, digest: str) -> bool:
        return self._path(digest).exists()
