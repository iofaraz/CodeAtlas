
from dataclasses import dataclass
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
