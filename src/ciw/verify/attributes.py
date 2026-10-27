"""Fill only missing product attributes from independently checked source passages."""

from __future__ import annotations

import json
from collections import defaultdict

from ciw.models import Locator, Product, Trial
from ciw.normalize.products import ProductResolver
from ciw.store import Workspace
from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck, task_id_for
from ciw.verify.llm import Backend
from ciw.verify.schemas import ProductAttrItem


def enrich_attributes(
    ws: Workspace,
    products: dict[str, Product],
    trials: list[Trial],
    resolver: ProductResolver,
    roles: dict[str, Backend] | None,
    *, log=None,
) -> list[dict]:
    if roles is None:
        return []
    missing = {pid for pid, p in products.items() if not p.target or not p.modality}
    sources = {s.source_id: s for s in ws.sources()}
    candidates, issues, seen = defaultdict(list), [], set()
    instruction = "只抽取原文明确写出的产品靶点与分子类型；产品名逐字照抄，不凭药名或外部知识推断。"
    entries = [r for t in trials for r in (t, *t.registrations)]
    for index, trial in enumerate(entries, 1):
        if not (set(trial.product_ids) & missing) or trial.locator.source_id in seen:
            continue
        if log:
            log(f"[attributes] {index}/{len(entries)}")
        source = sources[trial.locator.source_id]
        seen.add(source.source_id)
        raw = json.loads(ws.read_source(source.source_id))
        text = json.dumps(
            raw.get("protocolSection", {}).get("armsInterventionsModule", {})
            if trial.registry == "ctgov"
            else {
                "title": trial.title,
                "interventions": [{"names": a.interventions, "description": a.description} for a in trial.arms],
            },
            ensure_ascii=False,
        )
        task = ExtractionTask(
            task_id_for(source.sha256, "ProductAttrItem", instruction),
            source.source_id,
            text,
            instruction,
            ProductAttrItem,
            ("product_mention",),
            ("target", "modality"),
            key_fn=lambda it: (resolver.find_in_text(it["product_mention"]) or it["product_mention"].casefold(),),
        )
        try:
            checked = crosscheck(task, roles)
        except CrosscheckFailed as exc:
            issues.append(dict(kind="attribute_extract_failed", ref=source.source_id, note=str(exc)))
            continue
        for item in checked:
            pid = resolver.find_in_text(item.item["product_mention"])
            if pid not in set(trial.product_ids) & missing:
                continue
            if resolver.find_in_text(item.item["quote"]) != pid:
                item.status, item.note = "needs_review", "引语未唯一指向该产品"
            ws.save_verification(
                f"attr:{source.source_id}:{pid}",
                item.status,
                dict(calls=item.calls, task=task.task_id, item=item.item, source_id=source.source_id),
            )
            if item.status == "needs_review":
                issues.append(dict(kind="attribute_needs_review", ref=pid, note=item.note))
                continue
            for field in ("target", "modality"):
                value = item.item[field].strip()
                if value and not getattr(products[pid], field):
                    candidates[(pid, field)].append(
                        (value, item.status, Locator(source_id=source.source_id, quote=item.item["quote"]))
                    )
    _apply(products, candidates, issues)
    return issues


def _apply(products, candidates, issues):
    for (pid, field), values in candidates.items():
        if field == "modality":
            values = [v for v in values if v[0].casefold().strip() not in
                      {"biological", "drug", "生物制品", "生物药", "药物"}]
            if not values:
                continue
            shortest = min(values, key=lambda v: len(v[0]))
            if all(shortest[0].casefold().strip() in v[0].casefold().strip() for v in values):
                values = [shortest]
        if len({v.casefold().strip() for v, _, _ in values}) != 1:
            issues.append(
                dict(kind="attribute_conflict", ref=f"{pid}:{field}", note="来源属性存在不同表述，保留空值待核")
            )
            continue
        value, status, locator = values[0]
        product = products[pid]
        setattr(product, field, value)
        product.attribute_locators[field] = locator
        product.attribute_status = status
