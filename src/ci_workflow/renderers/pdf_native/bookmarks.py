"""Shared native PDF bookmark helper for Task 8.2 (PDF09)."""

from __future__ import annotations

from typing import Any

from ci_workflow.renderers.pdf_native.flowables import BookmarkFlowable


def bookmark(story: list[Any], key: str, title: str, *, level: int = 0) -> None:
    """Append a zero-height outline/bookmark anchor to a Platypus story."""
    story.append(BookmarkFlowable(key, title, level=level))


__all__ = ["bookmark"]
