"""Reproducible, dependency-free tokenization."""

import re

from .normalizer import normalize_text


TECHNICAL_TOKEN_PATTERN = re.compile(
    r"""
    c\+\+
    |c\#
    |o\([^)]+\)
    |!=|==|<=|>=
    |[a-z0-9_]+::[a-z0-9_:]+
    |[a-z0-9_]+\.[a-z0-9_.]+
    |[a-z0-9_]+\+\+
    |[^\W_][\w]*|_
    """,
    re.IGNORECASE | re.VERBOSE,
)

SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([+#])")


def tokenize(text: str | None) -> list[str]:
    """Tokenize normalized text without removing technical punctuation."""
    if not text:
        return []
    normalized = normalize_text(text)
    normalized = normalized.replace("c ++", "c++").replace("c #", "c#")
    tokens = []
    for match in TECHNICAL_TOKEN_PATTERN.finditer(normalized):
        token = match.group(0)
        token = re.sub(r"\s+", "", token)
        if token:
            tokens.append(token)
    return tokens
