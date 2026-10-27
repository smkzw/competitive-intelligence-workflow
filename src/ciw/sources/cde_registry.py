"""CDE 药物临床试验登记与信息公示平台（chinadrugtrials.org.cn）。

两步：
1. capture()：经 ego-browser 专用空间采集列表页与详情页，原样落盘到 captures/cde/（需要浏览器，人工或定时触发）。
2. ingest()：流水线只读收件箱，校验后入 CAS，确定性解析为 Trial（registry="cde"）。没有采集时如实记 not_captured。
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from ciw.config import IndicationConfig
from ciw.models import Arm, Design, Locator, PlannedOutcome, Trial, TrialDates
from ciw.normalize.products import ProductResolver
from ciw.normalize.semantics import concept_of
from ciw.normalize.trials import registry_ids
from ciw.sources.browser import run_script
from ciw.sources.cde.detail import parse_capture as parse_detail
from ciw.sources.cde.listing import CaptureError
from ciw.sources.cde.listing import parse_capture as parse_listing
from ciw.store import Workspace, now_iso

DETAIL_URL = "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml"
_MISSING = ("登记人暂未填写该信息", "暂未填写此信息", "企业选择不公示")
_ROMAN = str.maketrans({"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV"})
_PHASE_RANK = {"I": 2, "II": 3, "III": 4, "IV": 5}
_STATUS = [
    ("尚未招募", "NOT_YET_RECRUITING"),
    ("招募中", "RECRUITING"),
    ("招募完成", "ACTIVE_NOT_RECRUITING"),
    ("已完成", "COMPLETED"),
    ("主动终止", "TERMINATED"),
    ("主动暂停", "SUSPENDED"),
    ("暂停", "SUSPENDED"),
]


def _status(text: str) -> str:
    """登记平台中文状态 → 与 CT.gov 一致的状态码；不认识的保留原文。"""
    t = (text or "").strip()
    return next((code for key, code in _STATUS if key in t), t)


# ------------------------------------------------------------------ 采集（浏览器）
def _run_script(name: str, config: dict[str, Any], timeout: float) -> tuple[list[dict], dict]:
    return run_script(name, config, timeout, package="ciw.sources.cde")


def capture(
    ws: Workspace,
    cfg: IndicationConfig,
    space_id: int,
    *,
    max_details: int | None = None,
    timeout: float = 900,
    pause_s: float = 2.0,
    log=print,
) -> dict[str, Any]:
    out_dir = ws.root / "captures" / "cde"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"queries": [], "details": 0, "detail_failures": []}
    rows: dict[str, dict[str, Any]] = {}
    for q in cfg.china.cde_queries:
        pages, end = _run_script("browser.mjs", {"space": space_id, "query": q}, timeout)
        stamp = now_iso().replace(":", "")
        (out_dir / f"list-{_safe(q)}-{stamp}.json").write_text(
            json.dumps({"query": q, "pages": pages, "end": end}, ensure_ascii=False), encoding="utf-8"
        )
        listing = parse_listing(pages, query=q, allow_partial=True) if pages else None
        summary["queries"].append(
            {
                "query": q,
                "status": end.get("status"),
                "pages": len(pages),
                "records": listing["total_records"] if listing else 0,
                "complete": bool(listing and listing["complete"]),
            }
        )
        log(f"[cde] list {q!r}: {summary['queries'][-1]}")
        for r in (listing or {}).get("results", []):
            if cfg.is_relevant_text(f"{r['indication']} {r['title']}"):
                rows.setdefault(r["ctr"], r)
    done = {p.stem.removeprefix("detail-") for p in out_dir.glob("detail-*.json")}
    todo = [r for ctr, r in sorted(rows.items()) if ctr not in done][:max_details]
    for r in todo:
        pages, end = _run_script(
            "detail.mjs", {"space": space_id, "query": r["ctr"], "detail_id": r["detail_id"]}, timeout=180
        )
        if end.get("status") == "ok" and len(pages) == 1:
            (out_dir / f"detail-{r['ctr']}.json").write_text(json.dumps(pages[0], ensure_ascii=False), encoding="utf-8")
            summary["details"] += 1
        else:
            summary["detail_failures"].append({"ctr": r["ctr"], "status": end.get("status")})
            if end.get("status") == "user_control":
                break
        time.sleep(pause_s)
    return summary


def _safe(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-鿿]+", "_", s)[:40]


# ------------------------------------------------------------------ 收件箱 → Trial
def ingest(ws: Workspace, cfg: IndicationConfig, resolver: ProductResolver) -> tuple[list[Trial], dict[str, Any]]:
    folder = ws.root / "captures" / "cde"
    lists = sorted(folder.glob("list-*.json")) if folder.exists() else []
    details = sorted(folder.glob("detail-*.json")) if folder.exists() else []
    if not lists and not details:
        return [], {"source": "cde", "status": "not_captured", "detail": "未采集；运行 `ciw capture cde` 后重跑流水线"}
    listed: dict[str, dict[str, Any]] = {}
    list_status = []
    for path in lists:
        doc = json.loads(path.read_text(encoding="utf-8"))
        try:
            parsed = parse_listing(doc["pages"], query=doc["query"], allow_partial=True)
        except (CaptureError, KeyError):
            list_status.append({"file": path.name, "status": "invalid"})
            continue
        src = ws.record_source(
            kind="cde",
            url=parsed["results"][0]["source_url"]
            if parsed["results"]
            else "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml",
            data=path.read_bytes(),
            ext="json",
            title=f"登记检索：{doc['query']}",
            publisher="药物临床试验登记与信息公示平台",
        )
        list_status.append({"query": doc["query"], "complete": parsed["complete"], "records": parsed["total_records"]})
        for r in parsed["results"]:
            listed.setdefault(r["ctr"], {**r, "list_source_id": src.source_id})
    trials, failures = [], []
    detailed = set()
    for path in details:
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            parsed = parse_detail(raw, ctr=raw.get("registry_id", ""), detail_id=raw.get("detail_id", ""))
        except (ValueError, KeyError):
            failures.append(path.name)
            continue
        src = ws.record_source(
            kind="cde",
            url=f"{DETAIL_URL}#{parsed['registry_id']}",
            data=path.read_bytes(),
            ext="json",
            title=f"{parsed['registry_id']} {parsed.get('title') or ''}".strip(),
            publisher="药物临床试验登记与信息公示平台",
            published_at=None,
        )
        trials.append(_trial_from_detail(raw, parsed, src.source_id, cfg, resolver))
        detailed.add(parsed["registry_id"])
    own = cfg.own_product_id
    for ctr, r in sorted(listed.items()):
        if ctr in detailed:
            continue
        if cfg.is_relevant_text(f"{r['indication']} {r['title']}"):
            trials.append(_trial_from_list(r, cfg, resolver))
        elif own and (resolver.resolve_intervention(r["drug_name"]) or resolver.find_in_text(r["drug_name"])) == own:
            t = _trial_from_list(r, cfg, resolver)  # 本品其他适应症：作为背景保留，不计入本适应症阶段
            trials.append(t.model_copy(update={"relevance": "background", "relevance_reason": "本品其他适应症登记"}))
    missing = sorted(
        ctr
        for ctr, r in listed.items()
        if ctr not in detailed and cfg.is_relevant_text(f"{r['indication']} {r['title']}")
    )
    complete = all(s.get("complete") for s in list_status) and not failures and not missing
    status = "ok" if complete and trials else ("partial" if trials else "failed")
    return trials, {
        "source": "cde",
        "status": status,
        "lists": list_status,
        "details": len(detailed),
        "list_only": len(trials) - len(detailed),
        "detail_parse_failures": failures,
        "detail_missing": missing,
    }


def _phase(text: str) -> tuple[str, int]:
    t = text.translate(_ROMAN).replace("期", "").replace(" ", "")
    # Ib / IIa / IIb 这类亚期按主期别计
    parts = [re.sub(r"(?<=I)[ab]$", "", p) for p in re.split(r"[/、,，]", t)]
    parts = [p for p in parts if p in _PHASE_RANK]
    if not parts:
        return ("其他" if t else ""), 0  # “其它其他说明：生物等效性/上市后观察”等
    return "/".join(parts), max(_PHASE_RANK[p] for p in parts)


def _absent(v: str) -> bool:
    return not v.strip() or any(w in v for w in _MISSING)


def _cells(tables: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for ti, table in enumerate(tables):
        for ri, row in enumerate(table["rows"]):
            for j in range(0, len(row) - 1, 2):
                nested = [n["rows"] for n in table.get("nested", []) if n["row"] == ri and n["column"] == j + 1]
                found.setdefault(
                    row[j].strip(),
                    {"value": row[j + 1], "nested": nested, "path": f"$.tables[{ti}].rows[{ri}][{j + 1}]"},
                )
    return found


def _names(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = re.fullmatch(r"(中文通用名|英文通用名|商品名称)\s*[:：](.*)", line.strip())
        if m and m[2].strip() and m[2].strip().upper() not in {"NA", "N/A", "无"}:
            out.append(m[2].strip())
    return out or [text.strip()]


def _foreign_ids(cells: dict[str, dict[str, Any]]) -> dict[str, str]:
    text = ";".join(
        node["value"] for label, node in cells.items() if re.fullmatch(r"(?:相关|国际|境外|其他).*登记号", label)
    )
    nct = registry_ids(text, "ctgov")
    return {"nct": ";".join(nct)} if nct else {}


def _trial_from_detail(
    raw: dict[str, Any], parsed: dict[str, Any], source_id: str, cfg: IndicationConfig, resolver: ProductResolver
) -> Trial:
    cells = _cells(parsed["tables"])
    basic = {r[i].strip(): r[i + 1] for r in raw["basic"] for i in range(0, len(r) - 1, 2)}
    get = lambda k: "" if k not in cells or _absent(cells[k]["value"]) else cells[k]["value"].strip()  # noqa: E731
    phase, rank = _phase(get("试验分期"))
    arms = _detail_arms(cells, cfg, resolver)
    drug_name = parsed["registered_drug_name"]
    pids = sorted(
        {p for a in arms for p in a.product_ids if a.role == "experimental"}
        | ({p} if (p := resolver.resolve_intervention(drug_name) or resolver.find_in_text(drug_name)) else set())
    )
    outcomes: list[PlannedOutcome] = []
    for label, kind in (("主要终点指标及评价时间", "primary"), ("次要终点指标及评价时间", "secondary")):
        for rows in (cells.get(label) or {}).get("nested", [])[:1]:
            for row in rows[1:]:
                if len(row) == 4 and row[1].strip():
                    outcomes.append(
                        PlannedOutcome(
                            kind=kind,
                            title=row[1].strip(),
                            timeframe=row[2].strip(),
                            concept_id=concept_of(row[1], cfg),
                        )
                    )
    criteria = "\n".join(f"{k}\n{cells[k]['value']}" for k in ("入选标准", "排除标准") if k in cells)
    enrollment_text = get("目标入组人数")
    enroll = re.findall(r"[0-9]+", enrollment_text)
    relevant = cfg.is_relevant_text(f"{parsed['indication']} {parsed.get('title') or ''}")
    return Trial(
        trial_id=parsed["registry_id"],
        registry="cde",
        ids={"ctr": parsed["registry_id"], **_foreign_ids(cells)},
        title=parsed.get("title") or "",
        official_title=get("试验专业题目") or "",
        phase=phase,
        phase_rank=rank,
        status=_status(basic.get("试验状态", "")),
        dates=TrialDates(
            start=_iso(get("第一例受试者签署知情同意书日期")), first_posted=_iso(basic.get("首次公示信息日期", ""))
        ),
        sponsor=parsed["applicant"].strip(),
        sponsor_class="INDUSTRY",
        countries=[],  # 中国登记不等于已取得完整研究国家/中心清单。
        china=True,
        conditions=[parsed["indication"]],
        design=Design(
            allocation=get("随机化"),
            masking=get("盲法"),
            enrollment=int(enroll[0]) if len(enroll) == 1 else None,
            enrollment_text=enrollment_text,
            enrollment_type="ESTIMATED",
            eligibility_text=criteria,
            sex=get("性别"),
            arm_count=len(arms),
        ),
        arms=arms,
        outcomes_planned=outcomes,
        product_ids=pids,
        has_results=False,
        relevance="core" if relevant and pids else "background",
        relevance_reason="适应症匹配且含竞品干预" if relevant and pids else "适应症或产品未匹配配置",
        url=f"{DETAIL_URL}?id={parsed['detail_id']}",
        locator=Locator(source_id=source_id, path="$"),
    )


def _trial_from_list(r: dict[str, Any], cfg: IndicationConfig, resolver: ProductResolver) -> Trial:
    pid = resolver.resolve_intervention(r["drug_name"]) or resolver.find_in_text(r["drug_name"])
    return Trial(
        trial_id=r["ctr"],
        registry="cde",
        ids={"ctr": r["ctr"]},
        title=r["title"],
        status=_status(r["status_text"]),
        countries=[],
        china=True,
        conditions=[r["indication"]],
        product_ids=[pid] if pid else [],
        relevance="core" if pid else "background",
        relevance_reason="仅列表信息（详情未采集）" + ("" if pid else "；产品未匹配配置"),
        url=r["source_url"],
        locator=Locator(source_id=r["list_source_id"], path=f"row:{r['ctr']}"),
    )


def _iso(text: str) -> str | None:
    m = re.search(r"(\d{4})[-年/.](\d{1,2})[-月/.](\d{1,2})", text or "")
    return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else None


def _detail_arms(cells, cfg, resolver) -> list[Arm]:
    arms: list[Arm] = []
    for label, role_default in (("试验药", "experimental"), ("对照药", "active_comparator")):
        node = cells.get(label)
        for rows in (node or {}).get("nested", [])[:1]:
            for row in rows[1:]:
                if len(row) != 3:
                    continue
                names = _names(row[1])
                if any(re.search(r"安慰剂|模拟剂|处方缓冲液|空白制剂|placebo|vehicle", n, re.I) for n in names):
                    role = "placebo"
                elif all(cfg.is_background(n) for n in names):
                    role = "other"  # 背景用药（如鼻用激素），不是试验药也不是对照
                else:
                    role = role_default
                pids = sorted({p for n in names if (p := resolver.resolve_intervention(n))})
                arms.append(
                    Arm(
                        arm_id=f"{label}{row[0]}",
                        label=f"{label} {row[0]}：{names[0]}",
                        type=label,
                        role=role,
                        description=row[2],
                        interventions=names,
                        product_ids=pids,
                    )
                )
    return arms
