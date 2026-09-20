"""Single-file HTML-PPT assembler: theme, FX, runtime, logo, slides."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Sequence
from pathlib import Path

from ci_workflow.renderers.html_ppt.assets import InlineAssets, load_inline_assets
from ci_workflow.renderers.html_ppt.components import Slide, render_slide
from ci_workflow.renderers.html_ppt.notes import audience_is_clean, strip_tags, validate_notes_html
from ci_workflow.renderers.html_ppt.theme import KANGZHE_CSS

REMOTE_ATTR = re.compile(r"""(?:src|href)\s*=\s*['"](?:https?|wss?):""", re.IGNORECASE)
VIEWPORT_UNIT = re.compile(r"\d(?:vw|vh|dvw|dvh)\b")


def assemble_deck(
    slides: Sequence[Slide],
    *,
    title: str,
    footer_id: str,
    assets: InlineAssets | None = None,
    extra_meta: dict[str, str] | None = None,
) -> str:
    if not slides:
        raise ValueError("deck 不能为空")
    bundle = assets or load_inline_assets()
    total = len(slides)
    rendered: list[str] = []
    for index, slide in enumerate(slides, start=1):
        validate_notes_html(slide.notes_html, slide_id=slide.slide_id)
        markup = render_slide(
            slide,
            logo_src=bundle.logo_data_url,
            footer_id=footer_id,
            index=index,
            total=total,
        )
        if index == 1:
            markup = markup.replace('class="slide ', 'class="slide is-active ', 1)
        audience = strip_tags(re.sub(r"<aside class=\"notes\">.*?</aside>", "", markup, flags=re.S))
        audience_is_clean(audience, slide_id=slide.slide_id)
        rendered.append(markup)

    meta_comment = ""
    if extra_meta:
        payload = json.dumps(extra_meta, ensure_ascii=False, sort_keys=True)
        meta_comment = f"<!-- deck-manifest {html.escape(payload)} -->"

    document = f"""<!doctype html>
<html lang="zh-CN" class="tpl-kangzhe">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="only light">
  <title>{html.escape(title)}</title>
  {meta_comment}
  <style>
{KANGZHE_CSS}
  </style>
  <style>
{bundle.gx_fx_css}
  </style>
  <style>
{bundle.runtime_css}
  </style>
</head>
<body class="tpl-kangzhe">
  <div class="deck">
    {"".join(rendered)}
  </div>
  <div class="progress-bar" aria-hidden="true"><span></span></div>
  <script>
{bundle.runtime_js}
  </script>
  <script>
{bundle.gx_fx_js}
  </script>
</body>
</html>
"""
    if REMOTE_ATTR.search(document):
        raise ValueError("单文件 HTML 含外链资源属性")
    if "data:image/svg+xml;base64," not in document:
        raise ValueError("Logo 未以内联 Data URL 注入")
    if VIEWPORT_UNIT.search(KANGZHE_CSS):
        raise ValueError("主题 CSS 使用了视口字号或页内重排单位")
    return document


def write_deck(path: Path, html_text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")
    return path
