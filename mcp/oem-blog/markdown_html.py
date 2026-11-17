"""将 Markdown 转为博客 content 所需的 HTML。"""

from __future__ import annotations

import markdown

_EXTENSIONS = [
    "markdown.extensions.fenced_code",
    "markdown.extensions.tables",
    "markdown.extensions.nl2br",
    "markdown.extensions.sane_lists",
]


def markdown_to_html(source: str) -> str:
    text = (source or "").strip()
    if not text:
        return ""
    return markdown.markdown(text, extensions=_EXTENSIONS)
