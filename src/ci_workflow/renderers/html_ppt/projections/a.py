"""A-class HTML-PPT visual narrative from locked research-content report_data."""

from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.projections.common import notes as _notes  # noqa: F401
from ci_workflow.renderers.html_ppt.projections.common import set_notes_date

EASI75_RE = re.compile(r"EASI[- ]?75", re.IGNORECASE)
IGA_RE = re.compile(
    r"(0\s*或\s*1|0 or 1|IGA 0).{0,80}(≥\s*2|>=\s*2|两分)|"
    r"(Investigator.?s Global Assessment).{0,80}(0 or 1).{0,80}(≥\s*2|>=\s*2)",
    re.IGNORECASE,
)
REQUIRED_IDS = [
    "a-cover",
    "a-toc",
    "a-summary",
    "a-landscape",
    "a-products",
    "a-clinical",
    "a-efficacy",
    "a-safety",
    "a-matrix",
    "a-regulatory",
    "a-companies",
    "a-patents",
    "a-history",
    "a-limitations",
    "a-ending",
]

def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _cutoff_zh(raw: object) -> str:
    text = str(raw or "")
    match = re.match(r"(\d{4})-(\d{2})", text)
    if not match:
        raise ValueError("A 类缺少可解析的资料截止年月")
    return f"{match.group(1)}年{int(match.group(2))}月"


def _phase_bucket(phase: str) -> str:
    if "已上市" in phase:
        return "已上市"
    if "申请" in phase:
        return "申请上市"
    if "III" in phase or "Ⅲ" in phase:
        return "III期"
    if "II" in phase or "Ⅱ" in phase:
        return "II期"
    if "I期" in phase or phase.startswith("I"):
        return "I期"
    return "其他"


def _timepoint_rank(timepoint: object) -> tuple[int, str]:
    text = str(timepoint or "")
    if text == "第16周":
        return (0, text)
    if re.search(r"Week\s*16", text, re.I) and "52" not in text:
        return (1, text)
    if "16" in text:
        return (2, text)
    return (9, text)


def _timepoint_zh(raw: object) -> str:
    text = str(raw or "")
    match = re.search(r"(?:第)?\s*(\d+)\s*周|Week\s*(\d+)", text, re.I)
    if match:
        week = match.group(1) or match.group(2)
        return f"第{week}周"
    return "时间点未单列"


def _stat(num: object, label: str) -> str:
    return (
        '<div class="stat-strip__item">'
        f'<div class="stat-strip__num">{_esc(num)}</div>'
        f'<div class="stat-strip__label">{_esc(label)}</div></div>'
    )


def _pick_series(
    rows: list[dict[str, Any]],
    products: dict[str, dict[str, Any]],
    trials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_product[str(row["product_id"])].append(row)
    series: list[dict[str, Any]] = []
    for product_id, group in by_product.items():
        product = products[product_id]
        ordered = sorted(
            group,
            key=lambda row: (
                _timepoint_rank(row.get("timepoint")),
                0 if trials.get(str(row.get("trial_id")), {}).get("role") == "核心" else 1,
                str(trials.get(str(row.get("trial_id")), {}).get("display_id") or ""),
            ),
        )
        treatment = next(
            (row for row in ordered if row.get("arm") == "治疗组" and row.get("value") is not None),
            next((row for row in ordered if row.get("arm") == "治疗组"), None),
        )
        if treatment is None:
            continue
        control = next(
            (
                row
                for row in group
                if row.get("trial_id") == treatment.get("trial_id")
                and row.get("timepoint") == treatment.get("timepoint")
                and row.get("arm") in {"对照组", "安慰剂组"}
                and row.get("value") is not None
            ),
            None,
        )
        trial = trials.get(str(treatment.get("trial_id")) or "")
        series.append(
            {
                "product_id": product_id,
                "label_zh": str(product.get("name") or product_id),
                "target": str(product.get("target") or "未标注靶点"),
                "treatment": treatment.get("value"),
                "control": None if control is None else control.get("value"),
                "note_zh": (
                    "无同期对照"
                    if control is None
                    else _timepoint_zh(treatment.get("timepoint"))
                ),
                "timepoint_zh": _timepoint_zh(treatment.get("timepoint")),
                "trial_zh": str((trial or {}).get("display_id") or "试验未单列"),
                "size": (trial or {}).get("treatment_sample_size")
                or (trial or {}).get("sample_size"),
            }
        )
    series.sort(key=lambda item: (-len(item["target"]), item["target"], item["label_zh"]))
    return series


def _pack_by_target(series: list[dict[str, Any]], *, max_n: int = 8) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series:
        groups[str(item["target"])].append(item)
    ordered = sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    slides: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for _target, group in ordered:
        if len(group) > max_n:
            if current:
                slides.append(current)
                current = []
            for offset in range(0, len(group), max_n):
                slides.append(group[offset : offset + max_n])
            continue
        if len(current) + len(group) > max_n:
            slides.append(current)
            current = list(group)
        else:
            current.extend(group)
    if current:
        slides.append(current)
    if not slides:
        raise ValueError("疗效族未形成任何可投影系列")
    return slides


def _report_data(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("report_data")
    if not isinstance(data, dict):
        raise ValueError("A 类必须投影 report_data")
    return data


def build_report_a_slides(data: dict[str, Any]) -> list[Slide]:
    indication = str(data.get("indication") or "")
    if indication != "特应性皮炎":
        raise ValueError("A 类适应症必须为特应性皮炎")
    date_zh = _cutoff_zh(data.get("data_cutoff"))
    set_notes_date(date_zh)
    products = {str(item["id"]): item for item in data.get("products") or []}
    trials = {str(item["id"]): item for item in data.get("trials") or []}
    if len(products) != 38 or len(trials) != 49:
        raise ValueError("A 类产品/试验计数与锁定快照不符")

    listed = [item for item in products.values() if item.get("phase") == "已上市"]
    targets = Counter(str(item.get("target") or "未标注") for item in products.values())
    phases = Counter(_phase_bucket(str(item.get("phase") or "")) for item in products.values())

    easi_rows = [
        row
        for row in data.get("efficacy") or []
        if EASI75_RE.search(str(row.get("endpoint") or ""))
    ]
    if len({row["product_id"] for row in easi_rows}) < 20:
        raise ValueError("EASI-75 族产品数过少，禁止改用字面终点过滤")
    if not any(str(row["product_id"]) == "dupilumab" for row in easi_rows):
        raise ValueError("EASI-75 族必须包含度普利尤单抗")
    easi_series = _pick_series(easi_rows, products, trials)
    easi_packs = _pack_by_target(easi_series)
    iga_rows = [
        row
        for row in data.get("efficacy") or []
        if IGA_RE.search(str(row.get("endpoint") or ""))
    ]
    iga_series = _pick_series(iga_rows, products, trials) if iga_rows else []
    iga_packs = _pack_by_target(iga_series) if iga_series else []

    landscape_cells: dict[tuple[str, str], int] = defaultdict(int)
    target_rows = [name for name, _count in targets.most_common(8)]
    phase_cols = ["已上市", "申请上市", "III期", "II期", "I期", "其他"]
    for item in products.values():
        target = str(item.get("target") or "未标注")
        if target not in target_rows:
            target = "其他靶点"
            if target not in target_rows:
                target_rows.append(target)
        landscape_cells[(target, _phase_bucket(str(item.get("phase") or "")))] += 1

    modality_cells: dict[tuple[str, str], int] = defaultdict(int)
    modality_counter = Counter(str(item.get("modality")) for item in products.values())
    modalities = [name for name, _count in modality_counter.most_common(6)]
    for item in products.values():
        modality = str(item.get("modality") or "未标注")
        if modality not in modalities:
            continue
        modality_cells[(modality, _phase_bucket(str(item.get("phase") or "")))] += 1

    trial_phase = Counter(_phase_bucket(str(item.get("phase") or "")) for item in trials.values())
    role_core = sum(1 for item in trials.values() if item.get("role") == "核心")

    safety_rows = list(data.get("safety") or [])
    heat_products = list(listed)
    heat_values: dict[tuple[str, str], float | None] = {}
    heat_cats = {
        "治疗期间不良事件": "治疗期间",
        "严重不良事件": "严重",
        "特别关注不良事件": "特别关注",
    }
    for product in heat_products:
        for cat, label in heat_cats.items():
            match = next(
                (
                    row
                    for row in safety_rows
                    if row.get("product_id") == product["id"]
                    and row.get("category") == cat
                    and row.get("arm", "治疗组") == "治疗组"
                    and row.get("value") is not None
                ),
                None,
            )
            heat_values[(str(product["name"]), label)] = (
                None if match is None else float(match["value"])
            )
    heat_cols = ["治疗期间", "严重", "特别关注"]

    teae_by_pid: dict[str, float] = {}
    for row in safety_rows:
        if (
            row.get("category") == "治疗期间不良事件"
            and row.get("arm", "治疗组") == "治疗组"
            and row.get("value") is not None
        ):
            teae_by_pid.setdefault(str(row["product_id"]), float(row["value"]))
    from ci_workflow.renderers.html_ppt.projections.a_pages import finish_a_slides
    return finish_a_slides(
        data=data,
        products=products,
        listed=listed,
        targets=targets,
        phases=phases,
        easi_series=easi_series,
        easi_packs=easi_packs,
        iga_packs=iga_packs,
        landscape_cells=landscape_cells,
        target_rows=target_rows,
        phase_cols=phase_cols,
        modalities=modalities,

        modality_cells=modality_cells,
        trial_phase=trial_phase,
        role_core=role_core,
        heat_products=heat_products,
        heat_values=heat_values,
        heat_cols=heat_cols,
        teae_by_pid=teae_by_pid,
        indication=indication,
        date_zh=date_zh,
    )


def build_report_a_html_ppt(*, output_path: Path | str, root: Path | None = None) -> Path:
    from ci_workflow.renderers.html_ppt.projections.common import load_report, write_report_deck

    raw, digest = load_report("A", root=root)
    data = _report_data(raw)
    slides = build_report_a_slides(data)
    indication = str(data.get("indication") or "特应性皮炎")
    return write_report_deck(
        report="A",
        slides=slides,
        title=f"{indication}竞品全景",
        date_zh=_cutoff_zh(data.get("data_cutoff")),
        digest=digest,
        output_path=Path(output_path),
        root=root,
    )

