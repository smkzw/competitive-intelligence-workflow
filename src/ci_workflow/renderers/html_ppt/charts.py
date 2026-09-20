"""Inline SVG charts for HTML-PPT. Brand fills stay on bars/bubbles for FX."""

from __future__ import annotations

import html
import math
from collections.abc import Sequence
from typing import Any


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _label_lines(label: str, *, max_chars: int = 12) -> list[str]:
    """Keep product identity explicit while fitting a two-line SVG label."""
    if len(label) <= max_chars + 4:
        return [label]
    for marker in ("（", "("):
        if marker in label:
            head, tail = label.split(marker, 1)
            tail = marker + tail
            if head and tail:
                head = head.strip()
                if any("\u4e00" <= char <= "\u9fff" for char in head):
                    return [head]
                return [head, tail[: max_chars - 1] + "…" if len(tail) > max_chars else tail]
    if label.isascii() and len(label) <= 18:
        return [label]
    if len(label) <= max_chars:
        return [label]
    cut = max_chars
    if len(label) - cut < 4:
        cut = max(4, len(label) - 4)
    first = label[:cut]
    rest = label[cut : cut + max_chars]
    if len(label) > max_chars * 2:
        rest += "…"
    return [first, rest]


def _label_width(text: str) -> float:
    return sum(15.5 if "\u4e00" <= char <= "\u9fff" else 8.5 for char in text)


def grouped_bar_chart(
    series: Sequence[dict[str, Any]],
    *,
    title: str,
    width: int = 1168,
    height: int = 360,
    treatment_label: str = "治疗组",
    control_label: str = "对照组",
    y_name: str = "",
    show_legend: bool = True,
    value_decimals: int = 1,
) -> str:
    """Treatment/control grouped bars. Missing control is skipped, never zero-filled."""
    if not series:
        raise ValueError("grouped_bar_chart 不能在无系列时绘图")
    left, right, top, bottom = (78 if y_name else 56), 24, 48, 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(series)
    group_w = plot_w / n
    bar_w = min(28.0, group_w * 0.32)
    raw_max = 1.0
    for item in series:
        raw_max = max(raw_max, float(item.get("treatment") or 0))
        if item.get("control") is not None:
            raw_max = max(raw_max, float(item["control"]))
    if "%" in y_name:
        ymax = max(100.0, float(math.ceil(raw_max * 1.08 / 10.0) * 10))
    else:
        ymax = max(10.0, float(math.ceil(raw_max * 1.12 / 5.0) * 5))

    ticks = []
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_h - frac * plot_h
        raw_tick = ymax * frac
        val = f"{raw_tick:.1f}".rstrip("0").rstrip(".")
        ticks.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="#D6D2CD" stroke-width="1"/>'
            f'<text x="{left - 8}" y="{y + 5:.1f}" text-anchor="end" '
            f'fill="#808080" font-size="16">{val}</text>'
        )

    bars: list[str] = []
    labels: list[str] = []
    for index, item in enumerate(series):
        cx = left + group_w * index + group_w / 2
        treat = item.get("treatment")
        ctrl = item.get("control")
        if treat is not None:
            th = float(treat) / ymax * plot_h
            x = cx - bar_w - 3
            y = top + plot_h - th
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{th:.1f}" '
                f'fill="#FF9900" rx="2"/>'
            )
            bars.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
                f'fill="#0F1115" font-size="16" font-weight="700">'
                f'{float(treat):.{value_decimals}f}</text>'
            )
        if ctrl is not None:
            ch = float(ctrl) / ymax * plot_h
            x = cx + 3
            y = top + plot_h - ch
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{ch:.1f}" '
                f'fill="#407AAA" rx="2"/>'
            )
            bars.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
                f'fill="#0F1115" font-size="16" font-weight="700">'
                f'{float(ctrl):.{value_decimals}f}</text>'
            )
        label = str(item.get("label_zh") or "")
        line1, *more = _label_lines(label, max_chars=10)
        line2 = more[0] if more else ""
        labels.append(
            f'<text x="{cx:.1f}" y="{height - 44}" text-anchor="middle" fill="#404040" '
            f'aria-label="{_esc(label)}" '
            f'font-size="16">{_esc(line1)}</text>'
        )
        if line2:
            labels.append(
                f'<text x="{cx:.1f}" y="{height - 26}" text-anchor="middle" fill="#404040" '
                f'font-size="16">{_esc(line2)}</text>'
            )
        note = item.get("note_zh")
        if note:
            labels.append(
                f'<text x="{cx:.1f}" y="{height - 10}" text-anchor="middle" fill="#808080" '
                f'font-size="16">{_esc(note)}</text>'
            )

    legend_items: list[tuple[str, str]] = []
    has_treatment = any(item.get("treatment") is not None for item in series)
    has_control = any(item.get("control") is not None for item in series)
    if show_legend and treatment_label and has_treatment:
        legend_items.append(("#FF9900", treatment_label))
    if show_legend and control_label and has_control:
        legend_items.append(("#407AAA", control_label))
    legend_x = width - right - sum(42 + _label_width(label) for _fill, label in legend_items)
    legend_parts = ['<g font-size="16">']
    for fill, label in legend_items:
        legend_parts.append(
            f'<rect x="{legend_x:.1f}" y="10" width="14" height="14" fill="{fill}"/>'
        )
        legend_parts.append(
            f'<text x="{legend_x + 20:.1f}" y="22" fill="#404040">{_esc(label)}</text>'
        )
        legend_x += 42 + _label_width(label)
    legend_parts.append("</g>")
    y_axis_name = (
        f'<text x="18" y="{top + plot_h / 2:.1f}" text-anchor="middle" '
        f'transform="rotate(-90 18 {top + plot_h / 2:.1f})" fill="#606060" '
        f'font-size="16">{_esc(y_name)}</text>'
        if y_name
        else ""
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{_esc(title)}">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>'
        + "".join(ticks)
        + "".join(bars)
        + "".join(labels)
        + y_axis_name
        + "".join(legend_parts)
        + "</svg>"
    )


def count_matrix_chart(
    rows: Sequence[str],
    cols: Sequence[str],
    cells: dict[tuple[str, str], int],
    *,
    title: str,
    width: int = 1168,
    height: int = 360,
) -> str:
    left, top = 140, 48
    plot_w = width - left - 24
    plot_h = height - top - 24
    cw = plot_w / max(len(cols), 1)
    rh = plot_h / max(len(rows), 1)
    max_v = max(cells.values(), default=1) or 1
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{_esc(title)}">'
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
    ]
    for i, col in enumerate(cols):
        parts.append(
            f'<text x="{left + cw * i + cw / 2:.1f}" y="28" text-anchor="middle" '
            f'fill="#404040" font-size="16" font-weight="700">{_esc(col)}</text>'
        )
    for r, row in enumerate(rows):
        y = top + rh * r
        parts.append(
            f'<text x="8" y="{y + rh / 2 + 6:.1f}" fill="#404040" font-size="16">{_esc(row)}</text>'
        )
        for c, col in enumerate(cols):
            v = cells.get((row, col), 0)
            x = left + cw * c
            alpha = 0.12 + 0.72 * (v / max_v) if v else 0.04
            parts.append(
                f'<rect x="{x + 4:.1f}" y="{y + 4:.1f}" width="{cw - 8:.1f}" height="{rh - 8:.1f}" '
                f'rx="6" fill="rgba(255,153,0,{alpha:.2f})" stroke="#D6D2CD"/>'
            )
            parts.append(
                f'<text x="{x + cw / 2:.1f}" y="{y + rh / 2 + 6:.1f}" text-anchor="middle" '
                f'fill="#0F1115" font-size="19" font-weight="700">{v}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def heatmap_chart(
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    values: dict[tuple[str, str], float | None],
    *,
    title: str,
    width: int = 900,
    height: int = 420,
) -> str:
    left, top = 220, 40
    plot_w = width - left - 16
    plot_h = height - top - 16
    cw = plot_w / max(len(col_labels), 1)
    rh = plot_h / max(len(row_labels), 1)
    maxima = {
        col: max(
            (
                float(value)
                for row in row_labels
                if (value := values.get((row, col))) is not None
            ),
            default=1.0,
        )
        for col in col_labels
    }
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{_esc(title)}">'
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
    ]
    for i, col in enumerate(col_labels):
        parts.append(
            f'<text x="{left + cw * i + cw / 2:.1f}" y="24" text-anchor="middle" '
            f'fill="#404040" font-size="16">{_esc(col)}</text>'
        )
    for r, row in enumerate(row_labels):
        y = top + rh * r
        parts.append(
            f'<text x="8" y="{y + rh / 2 + 5:.1f}" fill="#404040" '
            f'font-size="16">{_esc(row)}</text>'
        )
        for c, col in enumerate(col_labels):
            v = values.get((row, col))
            x = left + cw * c
            if v is None:
                fill = "#EEECE1"
                label = "未公开"
                color = "#808080"
                stroke = "#C8C3BC"
            else:
                alpha = 0.18 + 0.70 * (float(v) / max(maxima[col], 1.0))
                fill = f"rgba(192,0,0,{alpha:.2f})"
                label = f"{float(v):.1f}"
                color = "#FFFFFF" if alpha >= 0.62 else "#0F1115"
                stroke = "#C00000" if float(v) == 0 else "#D6D2CD"
            parts.append(
                f'<rect x="{x + 3:.1f}" y="{y + 3:.1f}" width="{cw - 6:.1f}" height="{rh - 6:.1f}" '
                f'rx="4" fill="{fill}" stroke="{stroke}"/>'
            )
            parts.append(
                f'<text x="{x + cw / 2:.1f}" y="{y + rh / 2 + 5:.1f}" text-anchor="middle" '
                f'fill="{color}" font-size="16">{_esc(label)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def bubble_chart(
    points: Sequence[dict[str, Any]],
    *,
    title: str,
    x_name: str,
    y_name: str,
    width: int = 780,
    height: int = 420,
) -> str:
    if not points:
        raise ValueError("bubble_chart 无配对点时不得绘图")
    left, right, top, bottom = 72, 30, 34, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [float(p["x"]) for p in points]
    ys = [float(p["y"]) for p in points]
    xmin, xmax = min(0.0, min(xs)), max(xs + [1.0])
    ymin, ymax = min(0.0, min(ys)), max(ys + [1.0])
    if xmin == 0:
        x_step = max(1.0, float(math.ceil(xmax / 20.0) * 5))
        xmax = x_step * 4
    else:
        xmax += max((xmax - xmin) * 0.08, 1.0)
    if ymin == 0:
        y_step = max(1.0, float(math.ceil(ymax / 20.0) * 5))
        ymax = y_step * 4
    else:
        ymax += max((ymax - ymin) * 0.16, 1.0)
    sizes = [math.sqrt(max(float(p.get("size") or 1.0), 1.0)) for p in points]
    smax = max(sizes) or 1.0

    def sx(v: float) -> float:
        return left + (v - xmin) / (xmax - xmin or 1) * plot_w

    def sy(v: float) -> float:
        return top + plot_h - (v - ymin) / (ymax - ymin or 1) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{_esc(title)}">'
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" '
        f'stroke="#AAA6A1"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#AAA6A1"/>'
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" text-anchor="middle" '
        f'fill="#404040" font-size="16">{_esc(x_name)}</text>'
        f'<text x="18" y="{top + plot_h / 2:.1f}" fill="#404040" font-size="16" '
        f'transform="rotate(-90 18 {top + plot_h / 2:.1f})">{_esc(y_name)}</text>'
    ]
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        x_value = xmin + (xmax - xmin) * fraction
        y_value = ymin + (ymax - ymin) * fraction
        x = left + plot_w * fraction
        y = top + plot_h - plot_h * fraction
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" '
                f'y2="{top + plot_h + 5}" stroke="#AAA6A1"/>',
                f'<text x="{x:.1f}" y="{top + plot_h + 44}" text-anchor="middle" '
                f'fill="#808080" font-size="13">{x_value:.0f}</text>',
                f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" '
                f'stroke="#AAA6A1"/>',
                f'<text x="{left - 9}" y="{y + 4:.1f}" text-anchor="end" '
                f'fill="#808080" font-size="13">{y_value:.0f}</text>',
            ]
        )
    bubbles = [
        (sx(float(point["x"])), sy(float(point["y"])), 8 + 18 * (size / smax))
        for point, size in zip(points, sizes, strict=True)
    ]
    placed_labels: list[tuple[float, float, float, float]] = []
    label_entries = list(zip(points, bubbles, strict=True))
    label_entries.sort(key=lambda item: _label_width(str(item[0]["label_zh"])), reverse=True)
    for point, (cx, cy, r) in label_entries:
        label = str(point["label_zh"])
        lines = _label_lines(label)
        widest = max((_label_width(line) for line in lines), default=0.0)
        line_tail = 18 * (len(lines) - 1)
        y_candidates = [
            cy - r - 8 - line_tail,
            cy + r + 20,
            cy - r - 32 - line_tail,
            cy + r + 44,
            cy - r - 56 - line_tail,
            cy + r + 68,
        ]
        if point.get("label_position") == "below":
            y_candidates = [cy + r + 20, cy + r + 44, cy + r + 68]
        x_candidates = [
            cx,
            cx - widest * 0.65 - 12,
            cx + widest * 0.65 + 12,
            cx - widest - 20,
            cx + widest + 20,
        ]
        scored: list[tuple[int, float, float, tuple[float, float, float, float]]] = []
        for rank, (candidate_x, candidate_y) in enumerate(
            pair for y in y_candidates for pair in ((x, y) for x in x_candidates)
        ):
            label_x = min(
                max(candidate_x, left + widest / 2),
                left + plot_w - widest / 2,
            )
            candidate = (
                label_x - widest / 2 - 8,
                candidate_y - 15,
                label_x + widest / 2 + 8,
                candidate_y + 4 + line_tail,
            )
            penalty = rank
            if candidate[1] < top or candidate[3] > top + plot_h:
                penalty += 1000
            for other in placed_labels:
                if (
                    candidate[0] < other[2]
                    and candidate[2] > other[0]
                    and candidate[1] < other[3]
                    and candidate[3] > other[1]
                ):
                    penalty += 1000
            for bx, by, br in bubbles:
                if bx == cx and by == cy:
                    continue
                if (
                    candidate[0] < bx + br
                    and candidate[2] > bx - br
                    and candidate[1] < by + br
                    and candidate[3] > by - br
                ):
                    penalty += 80
            scored.append((penalty, label_x, candidate_y, candidate))
        _penalty, label_x, label_y, box = min(scored, key=lambda item: item[0])
        placed_labels.append(box)
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{r:.1f}" fill="#FF9900" fill-opacity="0.45" stroke="#E07C00"/>'
        )
        label_anchor_y = label_y + line_tail / 2
        if abs(label_x - cx) > 4 or abs(label_anchor_y - cy) > r + 16:
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{label_x:.1f}" '
                f'y2="{label_anchor_y:.1f}" stroke="#AAA6A1" stroke-width="1.2"/>'
            )
        tspans = "".join(
            f'<tspan x="{label_x:.1f}" dy="{0 if index == 0 else 18}">{_esc(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        parts.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'fill="#0F1115" font-size="16" aria-label="{_esc(label)}">{tspans}</text>'
        )
    legend_x = left + plot_w - 195
    parts.append(
        f'<g aria-label="气泡大小表示治疗组样本量"><circle cx="{legend_x:.1f}" '
        f'cy="17" r="8" fill="#FF9900" fill-opacity="0.25" '
        f'stroke="#E07C00"/><text x="{legend_x + 16:.1f}" y="22" '
        f'fill="#606060" font-size="13">'
        "气泡大小：治疗组样本量</text></g>"
    )
    parts.append("</svg>")
    return "".join(parts)
