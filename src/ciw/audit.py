"""抽样核对：从 current release 随机抽 B 的数值，回到 CAS 原件逐一比对。

- 组别数值：数值、该组 N（原件 class 级或 outcome 级 participants 分母）一致；
- 来源组间差：数值与 CI 一致；
- 计算值：重算 试验组−对照组。
每条样本同时给出原件里的终点名、class 标题与组名，供人工核对概念/时间点/角色归类（机器无法自证这一层）。
"""

from __future__ import annotations

import json
import random
import re
from typing import Any

from ciw.store import Workspace
from ciw.verify.quote import check_quote

_TOKEN = re.compile(r"([A-Za-z]+)(?:\[(\d+)\])?")


def follow(doc: Any, path: str) -> Any:
    cur = doc
    for part in path.removeprefix("$.").split("."):
        m = _TOKEN.fullmatch(part)
        if not m:
            raise KeyError(path)
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            cur = cur[int(m.group(2))]
    return cur


def _num(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def audit(ws: Workspace, n: int = 30, seed: int = 20261027) -> dict[str, Any]:
    d = ws.current_release_dir()
    if d is None:
        raise SystemExit("没有 current release")
    rel = json.loads((d / "release.json").read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    for q in rel["b"]["questions"]:
        for r in q["rows"]:
            items.append(
                {
                    "kind": "group_value",
                    "source_id": r["source_id"],
                    "path": r["path"],
                    "value": r["value"],
                    "n": r["n"],
                    "result_id": r["result_id"],
                    "source_kind": r.get("source_kind", "registry"),
                    "label": f"{r['acronym']} · {q['label']} · {q['time_label']} · {r['group_title']}",
                }
            )
        for c in q["comparisons"]:
            if c["kind"] == "reported":
                items.append(
                    {
                        "kind": "analysis",
                        "source_id": c["source_id"],
                        "path": c["path"],
                        "value": c["value"],
                        "ci": (c["ci_lower"], c["ci_upper"]),
                        "result_id": c["result_id"],
                        "source_kind": c.get("source_kind", "registry"),
                        "label": f"{c['acronym']} · {q['label']} · {q['time_label']} · "
                        f"{c['exp_group']} vs {c['ctrl_group']}",
                    }
                )
        for c in q["comparisons"]:
            if c["kind"] == "computed":
                rows = {r["group_title"]: r for r in q["rows"] if r["result_id"] == c["result_id"]}
                items.append(
                    {
                        "kind": "computed",
                        "value": c["value"],
                        "exp": rows.get(c["exp_group"]),
                        "ctrl": rows.get(c["ctrl_group"]),
                        "label": f"{c['acronym']} · {q['label']} · 计算值",
                    }
                )
    items.extend(_observation_samples(rel, items))
    random.Random(seed).shuffle(items)
    checked, errors = [], []
    cache: dict[str, Any] = {}
    for it in items[:n]:
        if it["kind"] == "computed":
            e, c = it["exp"], it["ctrl"]
            ok = bool(e and c) and abs(it["value"] - (e["value"] - c["value"])) < 1e-6
            (checked if ok else errors).append({**it, "exp": None, "ctrl": None, "ok": ok, "context": ""})
            continue
        doc = cache.get(it["source_id"]) or json.loads(ws.read_source(it["source_id"]))
        cache[it["source_id"]] = doc
        if it.get("source_kind") == "publication":
            ok, context = _publication(it, doc, rel["results"])
            (checked if ok else errors).append({**it, "ok": ok, "context": context})
            continue
        node = follow(doc, it["path"])
        context = _context(doc, it["path"])
        it["context"] = context["text"]
        if it["kind"] == "group_value":
            src = _num(node.get("value"))
            ok = src == it["value"] and context["n"] == it.get("n")
        else:
            src = _num(node.get("paramValue"))
            lo, hi = _num(node.get("ciLowerLimit")), _num(node.get("ciUpperLimit"))
            ok = src == it["value"] and (lo, hi) == tuple(it["ci"])
        row = {**it, "source_value": src, "ok": ok}
        (checked if ok else errors).append(row)
    return _report(rel["release_id"], checked, errors)


def _report(release_id, checked, errors):
    return {
        "release_id": release_id,
        "sampled": len(checked) + len(errors),
        "errors": errors,
        "examples": [f"{x['label']} = {x['value']}  ←  原件：{x.get('context', '')}" for x in checked[:8]],
    }


def _observation_samples(rel, existing):
    seen = {(i.get("source_id"), i.get("path"), i.get("result_id")) for i in existing}
    out = []
    for r in rel["b"].get("observations", []):
        for g in r["groups"]:
            key = (r["source_id"], g["path"], r["result_id"])
            if key in seen or g["value"] is None or not g["path"]:
                continue
            seen.add(key)
            out.append({"kind": "group_value", "source_id": r["source_id"], "path": g["path"],
                        "result_id": r["result_id"], "source_kind": r["source_kind"], "value": g["value"], "n": g["n"],
                        "label": f"{r['acronym']} · {r['domain_label']} · {r['title']} · {g['title']}"})
    return out


def _publication(item, doc, results):
    from lxml import html

    result = next((r for r in results if r["result_id"] == item["result_id"]), None)
    if result is None or result["kind"] != "publication" or result["locator"]["source_id"] != item["source_id"]:
        return False, "论文结果身份不一致"
    abstract = html.fragment_fromstring(follow(doc, item["path"]), create_parent="div").text_content()
    if item["kind"] == "group_value":
        matches = [g for g in result["groups"] if g["value"] == item["value"] and g["n"] == item["n"]]
        numbers = [item["value"], item["n"]]
    else:
        matches = [
            a
            for a in result["analyses"]
            if a["value"] == item["value"] and (a["ci_lower"], a["ci_upper"]) == tuple(item["ci"])
        ]
        numbers = [item["value"], *item["ci"]]
    quote = result["locator"]["quote"]
    return bool(matches) and check_quote(abstract, quote, numbers).ok, quote


def _context(doc: Any, path: str) -> dict[str, Any]:
    """原件中的终点名 / class 标题 / 组名，以及该组 N（class 级 participants 分母优先）。"""
    m = re.match(r"(resultsSection\.outcomeMeasuresModule\.outcomeMeasures\[\d+\])(?:\.classes\[(\d+)\])?", path)
    if not m:
        return {"text": "", "n": None}
    om = follow(doc, m.group(1))
    cls = om.get("classes", [])[int(m.group(2))] if m.group(2) else {}
    gid = follow(doc, path).get("groupId") if "measurements" in path else None
    gtitle = next((g.get("title") for g in om.get("groups", []) if g["id"] == gid), "")
    n = None
    for denoms in (cls.get("denoms"), om.get("denoms")):
        for d in denoms or []:
            if str(d.get("units", "")).lower() == "participants":
                n = next((_num(x.get("value")) for x in d.get("counts", []) if x["groupId"] == gid), None)
                break
        if n is not None:
            break
    text = f"{om.get('title', '')} | {cls.get('title') or om.get('timeFrame', '')} | {gtitle}"
    return {"text": text, "n": int(n) if n is not None else None}
