"""Text normalization for preprocessing."""

import re
import unicodedata


def normalize_text(text: str | None) -> str:
    """Lowercase and whitespace-normalize text while retaining punctuation."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\r\n?|\n", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.lower()
