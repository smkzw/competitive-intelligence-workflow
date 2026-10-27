"""Capture an explicitly chosen public article into the existing document inbox."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

from ciw.config import IndicationConfig
from ciw.sources.browser import run_script
from ciw.store import Workspace


def capture_document(ws: Workspace, cfg: IndicationConfig, space: int, url: str, kind: str) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("采集需明确的公开HTTPS文章地址")
    if kind not in {"company", "wechat"} or (kind == "wechat" and parsed.hostname != "mp.weixin.qq.com"):
        raise ValueError("公众号仅采集微信原文；公司公告请使用company")
    pages, end = run_script("document.mjs", {"space": space, "url": url}, 120, package="ciw.sources")
    if end.get("status") != "ok" or len(pages) != 1:
        return {"url": url, **end}
    doc = pages[0]
    text = doc["text"].strip()
    if len(text) < 200 or not cfg.is_relevant_text(text):
        return {"url": url, "status": "not_adopted", "reason": "文章正文不足或未匹配适应症"}
    if kind == "wechat" and doc["publisher"] not in cfg.china.wechat_accounts:
        return {"url": url, "status": "not_adopted", "reason": "公众号名称未匹配配置"}
    stamp = doc.get("published_at", "") or doc.get("date_text", "")
    date = re.search(r"\b(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", stamp)
    published = f"{date[1]}-{int(date[2]):02d}-{int(date[3]):02d}" if date else None
    folder = ws.root / "captures/docs"
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256((doc["url"] + "\0" + text).encode()).hexdigest()[:20]
    path = folder / f"{kind}-{digest}.txt"
    path.write_text(text, encoding="utf-8")
    meta = {k: doc[k] for k in ("url", "title", "fetched_at")}
    meta.update(kind=kind, publisher=doc["publisher"] or parsed.hostname, published_at=published)
    path.with_name(path.name + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "file": path.name, "title": doc["title"], "characters": len(text)}
