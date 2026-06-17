#!/usr/bin/env python3
"""Render the combined PORTFOLIO.md to a PDF.

The PDF has footer page numbers and a book-style table of contents whose entries
show the real page number (with dotted leaders) and link to that page. This relies
on WeasyPrint's CSS Paged Media support (`@page` counters and `target-counter()`).

Run inside the project venv:  .venv/bin/python export_pdf.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from weasyprint import HTML

# Reuse the same slug rule the combiner uses for its markdown TOC anchors.
from combine_portfolios import slugify_heading

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "PORTFOLIO.md"
OUTPUT = ROOT / "PORTFOLIO.pdf"

TOC_MAX_LEVEL = 3

# Pygments style for code blocks (a light theme that prints well on white).
PYGMENTS_STYLE = "default"


def highlight_code(code: str, lang: str, _attrs: str) -> str:
    """markdown-it `highlight` hook: colour a fenced block with Pygments.

    Returns only the highlighted token spans (`nowrap=True`); markdown-it wraps
    them in `<pre><code>…</code></pre>`. Returns "" for unknown/empty languages so
    markdown-it falls back to its own escaped, plain rendering.
    """
    if not lang:
        return ""
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return ""
    return pyg_highlight(code, lexer, HtmlFormatter(nowrap=True))


def split_front_matter(markdown: str) -> tuple[str, str]:
    """Split the title/intro (front matter) from the body content.

    The combined file is: title H1 + intro, then an auto-generated
    `## Table of Contents`, then the real content (first `# ` after the TOC).
    We drop the old markdown TOC and render our own page-numbered one instead.
    """
    toc_match = re.search(r"^## Table of Contents\s*$", markdown, flags=re.MULTILINE)
    if toc_match is None:
        # No generated TOC present; treat the first H1 block as front matter.
        body_match = re.search(r"^# .+$", markdown, flags=re.MULTILINE)
        if body_match is None:
            return "", markdown
        # Keep everything up to the *second* top-level heading as front matter.
        second = re.search(r"\n# ", markdown[body_match.end():])
        if second is None:
            return markdown, ""
        cut = body_match.end() + second.start() + 1
        return markdown[:cut], markdown[cut:]

    front = markdown[: toc_match.start()].rstrip()
    rest = markdown[toc_match.end():]
    body_match = re.search(r"\n# ", rest)
    body = rest[body_match.start() + 1:] if body_match else rest
    return front, body


def render_body_and_toc(body_md: str, md: MarkdownIt) -> tuple[str, list[tuple[int, str, str]]]:
    """Render body markdown to HTML, assigning heading ids, and collect TOC entries.

    A single token walk guarantees the TOC hrefs and the heading ids use identical
    (deduplicated) slugs.
    """
    tokens = md.parse(body_md)
    headings: list[tuple[int, str, str]] = []
    slug_counts: dict[str, int] = {}

    for i, tok in enumerate(tokens):
        if tok.type != "heading_open":
            continue
        level = int(tok.tag[1])
        title = tokens[i + 1].content.strip()

        base = slugify_heading(title)
        count = slug_counts.get(base, 0)
        slug_counts[base] = count + 1
        slug = f"{base}-{count}" if count else base

        tok.attrSet("id", slug)
        if level <= TOC_MAX_LEVEL:
            headings.append((level, title, slug))

    body_html = md.renderer.render(tokens, md.options, {})
    return body_html, headings


def build_toc_html(headings: list[tuple[int, str, str]]) -> str:
    """Build the page-numbered table-of-contents markup."""
    rows = [
        f'<a class="toc-entry lvl{level}" href="#{slug}">'
        f'<span class="toc-title">{html.escape(title)}</span></a>'
        for level, title, slug in headings
    ]
    return (
        '<section class="toc">\n'
        "<h1>Table of Contents</h1>\n" + "\n".join(rows) + "\n</section>"
    )


CSS = """
@page {
    size: A4;
    margin: 18mm 18mm 20mm;
    @bottom-center {
        content: counter(page);
        font-family: "Noto Sans", "DejaVu Sans", sans-serif;
        font-size: 9pt;
        color: #555;
    }
}

html {
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1a1a1a;
}

h1, h2, h3, h4, h5, h6 { line-height: 1.25; break-after: avoid; }
h1 { font-size: 20pt; break-before: page; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 15pt; margin-top: 1.1em; }
h3 { font-size: 12.5pt; }
h4 { font-size: 11pt; }

/* Title page and TOC should not force their own page break before. */
.title-page > h1, .toc > h1 { break-before: avoid; }

a { color: #0b5; text-decoration: none; }
p, li { orphans: 2; widows: 2; }

blockquote {
    margin: 0.6em 0;
    padding: 0.2em 0.9em;
    border-left: 3px solid #bbb;
    color: #333;
    background: #f6f6f6;
}

code {
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", "DejaVu Sans Mono", monospace;
    font-size: 9pt;
    background: #f0f0f0;
    padding: 0 2px;
    border-radius: 2px;
}

pre {
    font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", "DejaVu Sans Mono", monospace;
    font-size: 8.3pt;
    line-height: 1.35;
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 4px;
    padding: 8px 10px;
    white-space: pre-wrap;
    word-break: break-word;
}
pre code { background: none; padding: 0; font-size: inherit; }

hr { border: none; border-top: 1px solid #ddd; margin: 1.4em 0; }

/* ---- Title page ---- */
.title-page { break-after: page; }
.title-page h1 { font-size: 26pt; margin-top: 25vh; }

/* ---- Table of contents ---- */
.toc { break-after: page; }
.toc h1 { break-before: avoid; }
.toc-entry {
    display: block;
    color: #1a1a1a;
    margin: 2px 0;
}
.toc-entry::after {
    /* Dotted leader + the resolved page number of the target heading.
       Must sit on the <a> itself so attr(href) resolves the link target. */
    content: leader(". ") target-counter(attr(href), page);
}
.toc-entry.lvl1 { font-weight: 700; margin-top: 0.7em; }
.toc-entry.lvl2 { margin-left: 1.4em; }
.toc-entry.lvl3 { margin-left: 2.8em; color: #444; font-size: 9.8pt; }
"""


def build_html(front_html: str, toc_html: str, body_html: str) -> str:
    # Pygments token colours first, then CSS so the `pre` block styling (background,
    # border, wrapping, font) still wins; only per-token `color` rules are added.
    pygments_css = HtmlFormatter(style=PYGMENTS_STYLE).get_style_defs("pre")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Computer Science Y1 P4 Combined Portfolio</title>
<style>{pygments_css}</style>
<style>{CSS}</style>
</head>
<body>
<section class="title-page">
{front_html}
</section>
{toc_html}
<main>
{body_html}
</main>
</body>
</html>
"""


def main() -> None:
    if not SOURCE.exists():
        sys.exit(f"{SOURCE.name} not found. Run combine_portfolios.py first.")

    markdown = SOURCE.read_text(encoding="utf-8")
    front_md, body_md = split_front_matter(markdown)

    md = MarkdownIt("commonmark", {"highlight": highlight_code}).enable("table")

    front_html = md.render(front_md)
    body_html, headings = render_body_and_toc(body_md, md)
    toc_html = build_toc_html(headings)

    document = build_html(front_html, toc_html, body_html)
    HTML(string=document, base_url=str(ROOT)).write_pdf(str(OUTPUT))

    print(f"Wrote {OUTPUT}  ({len(headings)} TOC entries)")


if __name__ == "__main__":
    main()
