"""Streaming preprocessing pipeline and JSONL output."""

import json
import os
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .document import Document
from .html_cleaner import clean_html
from .normalizer import normalize_text
from .tokenizer import tokenize
from .xml_parser import iter_post_rows


@dataclass
class ProcessingStats:
    total_records: int = 0
    question_records: int = 0
    processed_documents: int = 0
    skipped_records: int = 0
    empty_titles: int = 0
    empty_bodies: int = 0
    empty_titles_or_bodies: int = 0
    questions_with_empty_title_or_body: int = 0
    duplicate_document_ids: int = 0
    documents_with_tags: int = 0
    documents_without_tags: int = 0
    average_length: float = 0.0
    median_length: float = 0.0
    minimum_length: Optional[int] = None
    maximum_length: Optional[int] = None
    average_document_length_words: float = 0.0
    median_document_length_words: float = 0.0
    minimum_document_length_words: Optional[int] = None
    maximum_document_length_words: Optional[int] = None
    total_title_tokens: int = 0
    total_body_tokens: int = 0
    duration_seconds: float = 0.0


def parse_optional_int(value: str | None) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def process_row(row: dict[str, str]) -> Optional[Document]:
    post_type = row.get("PostTypeId")
    if post_type != "1":
        return None
    title = clean_html(row.get("Title"))
    body = clean_html(row.get("Body"))
    return _process_cleaned_row(row, title, body)


def _process_cleaned_row(
    row: dict[str, str], title: str, body: str
) -> Optional[Document]:
    post_type = row.get("PostTypeId")
    if post_type != "1":
        return None
    doc_id = parse_optional_int(row.get("Id"))
    if doc_id is None:
        return None

    if not title and not body:
        return None

    tags = parse_tags(row.get("Tags"))
    title_tokens = tokenize(title)
    body_tokens = tokenize(body)
    tag_tokens = [tag for tag in (normalize_text(tag) for tag in tags) if tag]

    return Document(
        doc_id=doc_id,
        title=title,
        body=body,
        tags=tags,
        score=parse_optional_int(row.get("Score")) or 0,
        view_count=parse_optional_int(row.get("ViewCount")) or 0,
        creation_date=row.get("CreationDate"),
        accepted_answer_id=parse_optional_int(row.get("AcceptedAnswerId")),
        title_tokens=title_tokens,
        body_tokens=body_tokens,
        tag_tokens=tag_tokens,
        normalized_title=normalize_text(title),
        normalized_body=normalize_text(body),
        document_length=len(title_tokens) + len(body_tokens),
        title_word_count=len(title.split()),
        body_word_count=len(body.split()),
        document_length_words=len(title.split()) + len(body.split()),
    )


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    if "|" in value:
        return [tag for tag in value.strip("|").split("|") if tag]
    return [tag for tag in re.findall(r"<([^<>]+)>", value) if tag]


def document_to_dict(document: Document) -> dict:
    return {
        "doc_id": document.doc_id,
        "title": document.title,
        "body": document.body,
        "tags": document.tags,
        "score": document.score,
        "view_count": document.view_count,
        "creation_date": document.creation_date,
        "accepted_answer_id": document.accepted_answer_id,
        "title_tokens": document.title_tokens or [],
        "body_tokens": document.body_tokens or [],
        "tag_tokens": document.tag_tokens or [],
        "normalized_title": document.normalized_title or "",
        "normalized_body": document.normalized_body or "",
        "document_length": document.document_length,
        "title_word_count": document.title_word_count,
        "body_word_count": document.body_word_count,
        "document_length_words": document.document_length_words,
    }


def run_pipeline(input_path: Path, output_path: Path, report_path: Path) -> ProcessingStats:
    input_path = Path(input_path)
    output_path = Path(output_path)
    report_path = Path(report_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input XML file does not exist: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.name + ".tmp")
    stats = ProcessingStats()
    lengths: list[int] = []
    word_lengths: list[int] = []
    seen_ids: set[int] = set()
    start = time.perf_counter()

    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as output:
            for row in iter_post_rows(str(input_path)):
                stats.total_records += 1
                if row.get("PostTypeId") != "1":
                    continue
                stats.question_records += 1
                title = clean_html(row.get("Title"))
                body = clean_html(row.get("Body"))
                if not title:
                    stats.empty_titles += 1
                if not body:
                    stats.empty_bodies += 1
                if not title or not body:
                    stats.questions_with_empty_title_or_body += 1

                document = _process_cleaned_row(row, title, body)
                if document is None:
                    stats.skipped_records += 1
                    continue
                if document.doc_id in seen_ids:
                    stats.skipped_records += 1
                    stats.duplicate_document_ids += 1
                    continue
                seen_ids.add(document.doc_id)
                json.dump(document_to_dict(document), output, ensure_ascii=False)
                output.write("\n")

                stats.processed_documents += 1
                lengths.append(document.document_length)
                word_lengths.append(document.document_length_words)
                stats.total_title_tokens += len(document.title_tokens or [])
                stats.total_body_tokens += len(document.body_tokens or [])
                if document.tags:
                    stats.documents_with_tags += 1
                else:
                    stats.documents_without_tags += 1

        os.replace(temp_path, output_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    stats.duration_seconds = time.perf_counter() - start
    stats.empty_titles_or_bodies = stats.questions_with_empty_title_or_body
    if lengths:
        stats.average_length = sum(lengths) / len(lengths)
        stats.median_length = statistics.median(lengths)
        stats.minimum_length = min(lengths)
        stats.maximum_length = max(lengths)
    if word_lengths:
        stats.average_document_length_words = (
            sum(word_lengths) / len(word_lengths)
        )
        stats.median_document_length_words = statistics.median(word_lengths)
        stats.minimum_document_length_words = min(word_lengths)
        stats.maximum_document_length_words = max(word_lengths)

    report = {
        "phase": "Phase 2 - Dataset Processing and Preprocessing",
        "document_scope": "PostTypeId=1 questions only; answers are not combined",
        "document_length_definitions": {
            "token_count": "len(title_tokens) + len(body_tokens); title and body use the project's reproducible tokenizer",
            "whitespace_word_count": "Number of whitespace-separated words in cleaned title + cleaned body",
        },
        "statistic_definitions": {
            "empty_titles": "Question records whose cleaned title is empty",
            "empty_bodies": "Question records whose cleaned body is empty",
            "questions_with_empty_title_or_body": "Question records with an empty cleaned title or body; both-empty records count once",
            "duplicate_document_ids": "Additional question records skipped because their document ID had already been processed",
            "skipped_records": "Question records not written, including invalid IDs, both-empty questions and duplicate IDs",
        },
        "word_count_requirement_note": "The 100-word requirement is ambiguous about word counting; this report does not redefine it as a token requirement.",
        "input_file": str(input_path),
        "output_file": str(output_path),
        "statistics": stats.__dict__,
        "requirements": {
            "minimum_documents": 45000,
            "minimum_median_length": 100,
            "document_count_satisfied": stats.processed_documents >= 45000,
            "median_token_count_satisfied": stats.median_length >= 100,
            "median_whitespace_word_count_satisfied": (
                stats.median_document_length_words >= 100
            ),
            "word_count_requirement_interpretation": "Requires instructor confirmation",
        },
    }
    temp_report = report_path.with_name(report_path.name + ".tmp")
    try:
        with temp_report.open("w", encoding="utf-8", newline="\n") as report_file:
            json.dump(report, report_file, ensure_ascii=False, indent=2)
        os.replace(temp_report, report_path)
    except Exception:
        if temp_report.exists():
            temp_report.unlink()
        raise
    return stats
