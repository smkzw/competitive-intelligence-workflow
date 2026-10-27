"""非结构化来源收件箱：药企公告、公众号文章、NMPA 页面、论文摘要等。

约定：captures/docs/<name>.<txt|md|html|pdf> + 同名 <name>.meta.json，字段：
  url、kind（company|wechat|nmpa|europepmc）、title、publisher、published_at、fetched_at
采集由 tools/capture/*.mjs（ego-browser）或人工放入完成；流水线只读收件箱。
抽取走异构交叉核对；没有配置模型时如实记 skipped，文档进入待核队列。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from lxml import html as lxml_html

from ciw.config import IndicationConfig
from ciw.models import Event, stable_id
from ciw.normalize.products import ProductResolver
from ciw.store import Workspace
from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck, task_id_for
from ciw.verify.events import validate_event_item
from ciw.verify.llm import Backend
from ciw.verify.schemas import EventItem

KINDS = {"company", "wechat", "nmpa", "europepmc"}
SUFFIXES = {".txt", ".md", ".html", ".htm", ".pdf"}
_REGION = [
    (r"中国|china|nmpa|cde|国家药品监督管理局|国家药监局", "中国"),
    (r"美国|\bus\b|usa|united states|fda", "美国"),
    (r"欧盟|欧洲|\beu\b|europe|ema|chmp", "欧盟"),
    (r"日本|japan|pmda", "日本"),
    (r"加拿大|canada", "加拿大"),
    (r"全球|global|worldwide", "全球"),
]


def norm_region(text: str) -> str:
    low = (text or "").casefold()
    return next((zh for rx, zh in _REGION if re.search(rx, low)), low.strip())


INSTRUCTION = (
    "抽取与适应症“{ind}”相关的药物研发里程碑：获批上市、上市申请受理/递交、关键试验顶线结果、"
    "关键试验启动（首例入组）、授权许可交易。按产品、事件类型及明确地区分别列出，不能每类只留一条。"
    "同一事件列明多个获批地区时，各地区分别保留；地区是监管/交易辖区，不是总部或试验开展地。"
    "产品别名不要重复计为两个事件。仅回顾已有研究数值、批准依据或获奖，不构成新的顶线结果公布。"
    "批准/受理日期只在原文明确属于该动作时填写，并以event_date_quote保存该同段原文。"
    "例：‘2025年1月3日，公司宣布该药已获批’只证明报道时间，批准日期留空；"
    "‘该药于2025年1月3日获批准’才支持批准日期。不要用新闻头日期、今日宣布或发布日期补批准日。"
)


def text_of(path: Path) -> str | None:
    suf = path.suffix.lower()
    if suf in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    if suf in (".html", ".htm"):
        doc = lxml_html.fromstring(path.read_bytes())
        for bad in doc.xpath("//script|//style|//noscript"):
            bad.drop_tree()
        return " ".join(doc.text_content().split())
    if suf == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            return None
        proc = subprocess.run([exe, "-layout", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=120)
        return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else None
    return None


def list_docs(ws: Workspace) -> list[tuple[Path, dict[str, Any]]]:
    folder = ws.root / "captures" / "docs"
    out = []
    for p in sorted(folder.glob("*")) if folder.exists() else []:
        if p.suffix.lower() not in SUFFIXES:
            continue
        meta_path = p.with_name(p.name + ".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        out.append((p, meta))
    return out


def _event_task(src, text, cfg, resolver) -> ExtractionTask:
    return ExtractionTask(
        task_id=task_id_for(
            src.sha256,
            json.dumps(EventItem.model_json_schema(), sort_keys=True),
            INSTRUCTION.format(ind=cfg.name_zh),
        ),
        source_id=src.source_id,
        source_text=text,
        instruction=INSTRUCTION.format(ind=cfg.name_zh),
        item_model=EventItem,
        key_fields=("product_mention", "event_type", "region"),
        value_fields=("date", "indication"),
        date_fields=("date",),
        item_check=validate_event_item,
        key_fn=lambda it, r=resolver: (
            r.find_in_text(it.get("product_mention", ""))
            or r.resolve_intervention(it.get("product_mention", ""))
            or it.get("product_mention", "").casefold().strip(),
            str(it.get("event_type", "")),
            norm_region(it.get("region", "")),
        ),
    )


def extract_events(
    ws: Workspace, cfg: IndicationConfig, resolver: ProductResolver, roles: dict[str, Backend] | None
) -> tuple[list[Event], list[dict[str, Any]], list[dict[str, Any]]]:
    docs = list_docs(ws)
    if not docs:
        return (
            [],
            [],
            [{"source": "docs", "status": "not_captured", "detail": "收件箱为空（药企公告、公众号、NMPA 页面未采集）"}],
        )
    events: list[Event] = []
    queue: list[dict[str, Any]] = []
    by_kind: dict[str, dict[str, int]] = {}
    for path, meta in docs:
        kind = meta.get("kind") if meta.get("kind") in KINDS else "company"
        stat = by_kind.setdefault(kind, {"docs": 0, "extracted": 0, "events": 0, "failed": 0})
        stat["docs"] += 1
        text = text_of(path)
        if not text or not meta.get("url"):
            stat["failed"] += 1
            queue.append(
                {
                    "kind": "doc_unreadable",
                    "ref": path.name,
                    "note": "无法读取正文或缺少 meta.url（PDF 需要 pdftotext）",
                }
            )
            continue
        src = ws.record_source(
            kind=kind,
            url=meta["url"],
            data=path.read_bytes(),
            ext=path.suffix.lstrip("."),
            title=meta.get("title", path.stem),
            publisher=meta.get("publisher", ""),
            published_at=meta.get("published_at"),
            fetched_at=meta.get("fetched_at"),
        )
        if roles is None:
            queue.append({"kind": "doc_not_extracted", "ref": src.source_id, "note": "未配置异构模型，未抽取"})
            continue
        task = _event_task(src, text, cfg, resolver)
        try:
            checked = crosscheck(task, roles)
        except CrosscheckFailed as exc:
            stat["failed"] += 1
            queue.append({"kind": "doc_extract_failed", "ref": src.source_id, "note": str(exc)})
            continue
        stat["extracted"] += 1
        for chk in checked:
            it = chk.item
            ev = _event(chk, src, resolver)
            ws.save_verification(
                ev.event_id,
                chk.status,
                {"calls": chk.calls, "note": chk.note, "task": task.task_id, "item": it, "source_id": src.source_id},
            )
            events.append(ev)
            stat["events"] += 1
            if chk.status == "needs_review":
                queue.append({"kind": "event_needs_review", "ref": ev.event_id, "note": chk.note})
    cov = [
        {
            "source": k,
            "status": ("partial" if roles is None or v["failed"] else "ok"),
            "extraction_status": "not_enabled" if roles is None else "attempted",
            **v,
        }
        for k, v in sorted(by_kind.items())
    ]
    return events, queue, cov


def _event(chk, src, resolver) -> Event:
    it = chk.item
    pid = resolver.find_in_text(it["product_mention"]) or resolver.resolve_intervention(it["product_mention"])
    return Event(
        event_id=stable_id("ev", src.source_id, chk.key),
        product_id=pid,
        product_mention=it["product_mention"],
        event_type=it["event_type"],
        region=norm_region(it.get("region", "")),
        date=it.get("date") or None,
        indication=it.get("indication", ""),
        detail=it.get("detail", ""),
        quote=it.get("quote", ""),
        status=chk.status,
        source_id=src.source_id,
    )
