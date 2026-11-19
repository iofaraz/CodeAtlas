"""HTML cleaning utilities for Stack Exchange posts."""

import html
import re
import unicodedata

from lxml import etree
from lxml import html as lxml_html


BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "div", "dl",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "td", "tfoot", "th",
    "thead", "tr", "ul",
}
KNOWN_TAGS = set(BLOCK_TAGS) | {
    "a", "abbr", "b", "bdi", "bdo", "cite", "code", "em", "i", "img",
    "kbd", "mark", "q", "s", "small", "span", "strong", "sub", "sup",
    "time", "u", "var",
}
known_pattern = "|".join(sorted(KNOWN_TAGS, key=len, reverse=True))
UNKNOWN_ANGLE_EXPR = re.compile(
    r"<(?!(?:/)?(?:" + known_pattern + r")(?:[\s>/]|$))([A-Za-z_][^<>]*?)>"
)


def clean_html(text: str | None) -> str:
    """Convert HTML text to readable Unicode text without dropping code."""
    if not text:
        return ""

    source = UNKNOWN_ANGLE_EXPR.sub(
        lambda match: "&lt;" + match.group(1) + "&gt;",
        text,
    )
    try:
        fragments = lxml_html.fragments_fromstring(source)
        roots = fragments if isinstance(fragments, list) else [fragments]
        pieces: list[str] = []
        for fragment in roots:
            if isinstance(fragment, etree._Element):
                _collect_text(fragment, pieces)
            else:
                pieces.append(str(fragment))
        return _normalize_whitespace(" ".join(pieces))
    except (etree.LxmlError, ValueError, TypeError):
        separated = re.sub(
            r"<(?:br|/?p|/?div|/?li|/?tr|/?pre|/?blockquote|/?h[1-6])"
            r"(?:\s[^>]*)?>",
            "\n",
            text,
            flags=re.IGNORECASE,
        )
        plain = html.unescape(re.sub(r"<[^>]*>", "", separated))
        return _normalize_whitespace(plain)


def _collect_text(element: etree._Element, pieces: list[str]) -> None:
    tag = etree.QName(element).localname.lower()
    if tag in BLOCK_TAGS:
        pieces.append("\n")
    if tag == "br":
        pieces.append("\n")
    elif element.text:
        pieces.append(element.text)
    for child in element:
        _collect_text(child, pieces)
    if element.tail:
        pieces.append(element.tail)
    if tag in BLOCK_TAGS:
        pieces.append("\n")


def _normalize_whitespace(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return re.sub(r"\n", " ", text).strip()
