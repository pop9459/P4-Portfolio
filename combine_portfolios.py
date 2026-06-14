#!/usr/bin/env python3
"""Combine subproject portfolio markdown files into the root PORTFOLIO.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import posixpath
import re


PREFERRED_FILENAMES = ("portfolio.md", "Portfolio.md", "PORTFOLIO.md")
EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def slugify_heading(text: str) -> str:
    """Create a GitHub-style heading anchor slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "section"


def extract_headings(markdown: str, max_level: int = 3) -> list[tuple[int, str, str]]:
    """Extract headings and generate unique anchors for a markdown TOC."""
    headings: list[tuple[int, str, str]] = []
    slug_counts: dict[str, int] = {}
    in_code_block = False

    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        match = re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if match is None:
            continue

        level = len(match.group(1))
        if level > max_level:
            continue

        title = match.group(2).strip()
        base_slug = slugify_heading(title)
        count = slug_counts.get(base_slug, 0)
        slug_counts[base_slug] = count + 1
        anchor = f"{base_slug}-{count}" if count else base_slug
        headings.append((level, title, anchor))

    return headings


def build_table_of_contents(markdown: str) -> list[str]:
    """Build TOC lines for top headings in the merged markdown."""
    headings = extract_headings(markdown, max_level=3)
    toc_lines = ["## Table of Contents", ""]

    if not headings:
        toc_lines.extend(["_No headings found._", ""])
        return toc_lines

    for level, title, anchor in headings:
        indent = "  " * (level - 1)
        toc_lines.append(f"{indent}- [{title}](#{anchor})")

    toc_lines.append("")
    return toc_lines


def is_external_path(path: str) -> bool:
    """Return True for URLs and anchors that should not be rewritten."""
    lowered = path.lower()
    return lowered.startswith(("http://", "https://", "data:", "mailto:", "#"))


def rewrite_image_path(path: str, source_dir: str) -> str:
    """Rewrite image path so it resolves from the repository root."""
    path = path.strip()
    if not path or is_external_path(path):
        return path

    match = re.match(r"^([^?#]*)([?#].*)?$", path)
    if match is None:
        return path

    raw_path = match.group(1)
    suffix = match.group(2) or ""

    # Already rooted at the correct source directory.
    if raw_path.startswith(f"{source_dir}/"):
        return path

    if raw_path.startswith("/"):
        rewritten = posixpath.normpath(posixpath.join(source_dir, raw_path.lstrip("/")))
    else:
        rewritten = posixpath.normpath(posixpath.join(source_dir, raw_path))

    return f"{rewritten}{suffix}"


def rewrite_image_paths_in_markdown(content: str, source_dir: str) -> str:
    """Rewrite image paths in markdown and HTML image tags."""

    def markdown_image_replacer(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        inner = match.group(2).strip()

        if not inner:
            return match.group(0)

        if inner.startswith("<") and ">" in inner:
            closing_index = inner.find(">")
            image_path = inner[1:closing_index].strip()
            trailing = inner[closing_index + 1 :].strip()
            rewritten = rewrite_image_path(image_path, source_dir)
            if trailing:
                return f"![{alt_text}](<{rewritten}> {trailing})"
            return f"![{alt_text}](<{rewritten}>)"

        parts = inner.split(maxsplit=1)
        image_path = parts[0]
        trailing = parts[1] if len(parts) > 1 else ""
        rewritten = rewrite_image_path(image_path, source_dir)
        if trailing:
            return f"![{alt_text}]({rewritten} {trailing})"
        return f"![{alt_text}]({rewritten})"

    def html_image_replacer(match: re.Match[str]) -> str:
        quote = match.group(1)
        image_path = match.group(2)
        rewritten = rewrite_image_path(image_path, source_dir)
        return f"src={quote}{rewritten}{quote}"

    content = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", markdown_image_replacer, content)
    content = re.sub(r"src\s*=\s*([\"'])([^\"']+)\1", html_image_replacer, content)
    return content


def find_portfolio_file(project_dir: Path) -> Path | None:
    """Return the first portfolio markdown file in a project directory."""
    for filename in PREFERRED_FILENAMES:
        candidate = project_dir / filename
        if candidate.is_file():
            return candidate

    # Fallback: search recursively for any case variation of portfolio.md.
    for candidate in sorted(project_dir.rglob("*.md")):
        if candidate.name.lower() == "portfolio.md":
            return candidate

    return None


def get_subprojects(root_dir: Path) -> list[Path]:
    """Return top-level directories that are likely project folders."""
    return sorted(
        [
            path
            for path in root_dir.iterdir()
            if path.is_dir() and path.name not in EXCLUDED_DIRS and not path.name.startswith(".")
        ],
        key=lambda path: path.name.lower(),
    )


def build_combined_markdown(root_dir: Path) -> str:
    """Generate merged markdown from all subproject portfolio files."""
    intro_lines: list[str] = [
        "# Computer Science Y1 P4 Combined Portfolio",
        "",
        "This file is auto-generated by `combine_portfolios.py`.",
        " - master repository: https://github.com/pop9459/P4-Portfolio",
        f" - updated at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
        "",
    ]
    content_lines: list[str] = []

    subprojects = get_subprojects(root_dir)
    if not subprojects:
        intro_lines.extend(["No subprojects were found.", ""])
        return "\n".join(intro_lines)

    for project_dir in subprojects:
        portfolio_file = find_portfolio_file(project_dir)

        if portfolio_file is None:
            content_lines.extend([f"_No portfolio.md found in {project_dir.name}._", ""])
            continue

        relative_path = portfolio_file.relative_to(root_dir)
        content = portfolio_file.read_text(encoding="utf-8", errors="replace").strip()
        source_dir = relative_path.parent.as_posix()
        content = rewrite_image_paths_in_markdown(content, source_dir)

        content_lines.append("")
        if content:
            content_lines.append(content)
            content_lines.append("")
        else:
            content_lines.extend(["_Portfolio file exists but is empty._", ""])

    content_markdown = "\n".join(content_lines).strip()
    toc_lines = build_table_of_contents(content_markdown)

    merged_lines = intro_lines + toc_lines + [content_markdown, ""]
    return "\n".join(merged_lines).rstrip() + "\n"


def main() -> None:
    root_dir = Path(__file__).resolve().parent
    output_file = root_dir / "PORTFOLIO.md"

    combined_markdown = build_combined_markdown(root_dir)
    output_file.write_text(combined_markdown, encoding="utf-8")

    print(f"Updated {output_file}")


if __name__ == "__main__":
    main()
