"""Fixed Kangzhe slide chrome: cover, toc, section, content, ending."""

from __future__ import annotations

import html
from dataclasses import dataclass, field


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


@dataclass
class Slide:
    slide_id: str
    kind: str
    title: str
    responsibility: str
    notes_html: str
    body_html: str = ""
    department: str = "产品中心-医学部"
    date_zh: str = ""
    toc_items: list[tuple[str, str, str]] = field(default_factory=list)
    conclusion_html: str = ""
    section_number: str = ""
    cover_highlight: str = ""


def _logo_img(src: str) -> str:
    return f'<img src="{src}" alt="CMS 康哲药业">'


def _notes(html_fragment: str) -> str:
    return f'<aside class="notes">{html_fragment}</aside>'


def render_cover(slide: Slide, *, logo_src: str) -> str:
    title = slide.title
    if slide.cover_highlight and slide.cover_highlight in title:
        title_html = title.replace(
            slide.cover_highlight,
            f'<span class="hl">{_esc(slide.cover_highlight)}</span>',
            1,
        )
    else:
        title_html = _esc(title)
    return f"""
<section class="slide cover-slide" data-slide-id="{_esc(slide.slide_id)}"
  data-page-responsibility="{_esc(slide.responsibility)}" data-title="{_esc(slide.title)}"
  data-qc-id="cover-slide">
  <div class="cover-hero" aria-hidden="true"></div>
  <div class="cover-wordmark" data-qc-id="cover-wordmark">{_logo_img(logo_src)}</div>
  <div class="cover-main">
    <h1 data-qc-id="cover-title">{title_html}</h1>
    <p class="cover-department" data-qc-id="cover-department">{_esc(slide.department)}</p>
    <p class="cover-date" data-qc-id="cover-date">{_esc(slide.date_zh)}</p>
  </div>
  <div class="cover-rule" data-qc-id="cover-rule" aria-hidden="true"></div>
  <div class="cover-ribbon-fallback" data-qc-id="cover-ribbon" aria-label="CMS 康哲药业">
    <div class="ribbon-colorbar"><i></i><i></i><i></i></div>
    <div class="ribbon-lockup">{_logo_img(logo_src)}</div>
  </div>
  {_notes(slide.notes_html)}
</section>
"""


def render_toc(slide: Slide, *, logo_src: str) -> str:
    cards = []
    for index, (label, scope, _target) in enumerate(slide.toc_items, start=1):
        cards.append(
            '<article class="toc-item">'
            f'<span class="toc-index">{index:02d}</span>'
            f"<div><span class=\"toc-label\">{_esc(label)}</span>"
            f"<small>{_esc(scope)}</small></div></article>"
        )
    return f"""
<section class="slide toc-slide" data-slide-id="{_esc(slide.slide_id)}"
  data-page-responsibility="{_esc(slide.responsibility)}" data-title="汇报章节"
  data-qc-id="toc-slide">
  <div class="toc-wordmark" data-qc-id="toc-wordmark">{_logo_img(logo_src)}</div>
  <h1 class="toc-title" data-qc-id="toc-title">汇报章节</h1>
  <div class="toc-rule" data-qc-id="toc-rule" aria-hidden="true"></div>
  <p class="toc-meta">{_esc(slide.title)} · {_esc(slide.date_zh)}</p>
  <nav class="toc-board" data-qc-id="toc-board" aria-label="汇报章节">
    {"".join(cards)}
  </nav>
  {_notes(slide.notes_html)}
</section>
"""


def render_section(slide: Slide, *, logo_src: str) -> str:
    number = slide.section_number or "01"
    return f"""
<section class="slide section-slide" data-slide-id="{_esc(slide.slide_id)}"
  data-page-responsibility="{_esc(slide.responsibility)}" data-title="{_esc(slide.title)}"
  data-qc-id="section-slide">
  <div class="section-wordmark" data-qc-id="section-wordmark">{_logo_img(logo_src)}</div>
  <div class="section-number" data-qc-id="section-number"
    aria-label="第{number}章">{_esc(number)}</div>
  <div class="section-rule" data-qc-id="section-rule" aria-hidden="true"></div>
  <h1 class="section-title" data-qc-id="section-title">{_esc(slide.title)}</h1>
  {_notes(slide.notes_html)}
</section>
"""


def render_content(
    slide: Slide,
    *,
    logo_src: str,
    footer_id: str,
    index: int,
    total: int,
) -> str:
    conclusion = ""
    if slide.conclusion_html:
        conclusion = f'<div class="content-conclusion">{slide.conclusion_html}</div>'
    return f"""
<section class="slide content-slide" data-slide-id="{_esc(slide.slide_id)}"
  data-page-responsibility="{_esc(slide.responsibility)}" data-archetype="content"
  data-title="{_esc(slide.title)}" data-qc-id="content-slide">
  <div class="title-row" data-qc-id="content-title-row">
    <h1 class="page-title">{_esc(slide.title)}</h1>
  </div>
  <div class="brand-lockup" data-qc-id="content-logo">{_logo_img(logo_src)}</div>
  <main class="slide-body" data-qc-id="content-body">
    {slide.body_html}
    {conclusion}
  </main>
  <div class="deck-footer" data-qc-id="content-footer">
    <span class="footer-id" data-qc-id="content-footer-id">{_esc(footer_id)}</span>
    <span class="slide-number" data-qc-id="content-page-number"
      data-current="{index}" data-total="{total}"></span>
  </div>
  {_notes(slide.notes_html)}
</section>
"""


def render_ending(slide: Slide, *, logo_src: str) -> str:
    return f"""
<section class="slide ending-slide" data-slide-id="{_esc(slide.slide_id)}"
  data-page-responsibility="{_esc(slide.responsibility)}" data-title="谢谢"
  data-qc-id="ending-slide">
  <div class="ending-hero" aria-hidden="true"></div>
  <div class="ending-wordmark" data-qc-id="ending-wordmark">{_logo_img(logo_src)}</div>
  <div class="ending-focus" data-qc-id="ending-focus">
    <h1 class="ending-thanks">谢谢</h1>
  </div>
  <div class="ending-rule" data-qc-id="ending-rule" aria-hidden="true"></div>
  <p class="ending-meta" data-qc-id="ending-meta">
    {_esc(slide.department)} · {_esc(slide.date_zh)}
  </p>
  <div class="ending-ribbon-fallback" data-qc-id="ending-ribbon" aria-label="CMS 康哲药业">
    <div class="ribbon-colorbar"><i></i><i></i><i></i></div>
    <div class="ribbon-lockup">{_logo_img(logo_src)}</div>
  </div>
  {_notes(slide.notes_html)}
</section>
"""


def render_slide(
    slide: Slide,
    *,
    logo_src: str,
    footer_id: str,
    index: int,
    total: int,
) -> str:
    kind = slide.kind
    if kind == "cover":
        html_out = render_cover(slide, logo_src=logo_src)
    elif kind == "toc":
        html_out = render_toc(slide, logo_src=logo_src)
    elif kind == "section":
        html_out = render_section(slide, logo_src=logo_src)
    elif kind == "content":
        html_out = render_content(
            slide, logo_src=logo_src, footer_id=footer_id, index=index, total=total
        )
    elif kind == "ending":
        html_out = render_ending(slide, logo_src=logo_src)
    else:
        raise ValueError(f"未知页型 {kind}")
    return html_out
