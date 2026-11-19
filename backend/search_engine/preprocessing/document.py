
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    doc_id: int
    title: str
    body: str
    tags: list[str]
    score: int = 0
    view_count: int = 0
    creation_date: Optional[str] = None
    accepted_answer_id: Optional[int] = None
    title_tokens: list[str] = field(default_factory=list)
    body_tokens: list[str] = field(default_factory=list)
    tag_tokens: list[str] = field(default_factory=list)
    normalized_title: Optional[str] = None
    normalized_body: Optional[str] = None
    document_length: int = 0
    title_word_count: int = 0
    body_word_count: int = 0
    document_length_words: int = 0
