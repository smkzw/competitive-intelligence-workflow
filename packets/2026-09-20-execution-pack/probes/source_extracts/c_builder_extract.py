"""Transcribed source function, not a full repository checkout.
Source: packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py @ d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca.
Git blob (full original file): 638046c6f9980eabafe3a4e5437d20abce74d6b9.
"""
from __future__ import annotations
import re


def _split_eligibility(text: str) -> tuple[list[str], list[str]]:
    """确定性切分登记入排原文：按节标题与短横线条目。"""
    inc_text, exc_text = text, ""
    marker = re.search(r"exclusion criteria\s*:", text, re.I)
    if marker:
        inc_text, exc_text = text[:marker.start()], text[marker.end():]
    inc_text = re.sub(r"^\s*inclusion criteria\s*:\s*", "", inc_text, flags=re.I)

    def bullets(chunk: str) -> list[str]:
        items = [
            part.strip(" \n-–;；")
            for part in re.split(r"\n\s*(?:[-–•]|\(\d+\)|\d+\.)\s*\n?", chunk)
            if len(part.strip(" \n-–;；")) >= 8
        ]
        if not items:
            joined = " ".join(chunk.split())
            return [joined] if joined else []
        return items

    return bullets(inc_text)[:10], bullets(exc_text)[:10]
