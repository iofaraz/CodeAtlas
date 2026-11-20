"""In-memory inverted index foundation.

The Lexicon is expected to translate normalized terms to positive integer
term IDs.  The Forward Index may provide per-field term counts or term-ID
sequences; this module deliberately does not depend on either teammate's
implementation.
"""

from collections import Counter
from typing import Iterable, Mapping, TypedDict


class Posting(TypedDict):
    doc_id: int
    title_tf: int
    body_tf: int
    tag_tf: int


TermFrequency = Mapping[str, int]


class InvertedIndex:
    """Map positive term IDs to sorted per-document postings."""

    def __init__(self) -> None:
        self._index: dict[int, list[Posting]] = {}
        self._document_ids: set[int] = set()

    @staticmethod
    def _validate_doc_id(doc_id: int) -> None:
        if isinstance(doc_id, bool) or not isinstance(doc_id, int) or doc_id <= 0:
            raise ValueError("doc_id must be a positive integer")

    @staticmethod
    def _validate_term_id(term_id: int) -> None:
        if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id <= 0:
            raise ValueError("term_id must be a positive integer; 0 is reserved")

    @staticmethod
    def _validate_tf(value: int, field_name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} frequency must be a non-negative integer")

    def add_posting(
        self,
        term_id: int,
        doc_id: int,
        title_tf: int = 0,
        body_tf: int = 0,
        tag_tf: int = 0,
    ) -> None:
        """Add or safely confirm a single term/document posting."""
        self._validate_term_id(term_id)
        self._validate_doc_id(doc_id)
        self._validate_tf(title_tf, "title_tf")
        self._validate_tf(body_tf, "body_tf")
        self._validate_tf(tag_tf, "tag_tf")

        if title_tf + body_tf + tag_tf == 0:
            return

        postings = self._index.setdefault(term_id, [])
        for posting in postings:
            if posting["doc_id"] == doc_id:
                incoming = (title_tf, body_tf, tag_tf)
                existing = (
                    posting["title_tf"],
                    posting["body_tf"],
                    posting["tag_tf"],
                )
                if incoming == existing:
                    return
                raise ValueError(
                    f"posting already exists for term_id={term_id}, "
                    f"doc_id={doc_id}; use one consistent frequency"
                )

        postings.append(
            {
                "doc_id": doc_id,
                "title_tf": title_tf,
                "body_tf": body_tf,
                "tag_tf": tag_tf,
            }
        )
        postings.sort(key=lambda posting: posting["doc_id"])

    def add_document(
        self,
        doc_id: int,
        title_term_ids: Iterable[int] = (),
        body_term_ids: Iterable[int] = (),
        tag_term_ids: Iterable[int] = (),
        *,
        term_frequencies: Mapping[int, TermFrequency] | None = None,
    ) -> None:
        """Add a document from term-ID sequences or precomputed TF mappings.

        The sequence form counts repeated term IDs in each field separately.
        The optional mapping form has the shape::

            {term_id: {"title_tf": 2, "body_tf": 5, "tag_tf": 1}}

        Sequences and mappings may be combined; their frequencies are merged.
        """
        self._validate_doc_id(doc_id)
        if doc_id in self._document_ids:
            raise ValueError(f"document {doc_id} has already been added")

        title_counts = Counter(title_term_ids)
        body_counts = Counter(body_term_ids)
        tag_counts = Counter(tag_term_ids)

        for term_id in set(title_counts) | set(body_counts) | set(tag_counts):
            self._validate_term_id(term_id)

        merged: dict[int, dict[str, int]] = {}
        for term_id in set(title_counts) | set(body_counts) | set(tag_counts):
            merged[term_id] = {
                "title_tf": title_counts[term_id],
                "body_tf": body_counts[term_id],
                "tag_tf": tag_counts[term_id],
            }

        if term_frequencies is not None:
            if not isinstance(term_frequencies, Mapping):
                raise TypeError("term_frequencies must be a mapping")
            for term_id, frequencies in term_frequencies.items():
                self._validate_term_id(term_id)
                if not isinstance(frequencies, Mapping):
                    raise TypeError("each term frequency value must be a mapping")

                unknown_fields = set(frequencies) - {
                    "title_tf",
                    "body_tf",
                    "tag_tf",
                }
                if unknown_fields:
                    raise ValueError(
                        f"unknown term frequency fields: {sorted(unknown_fields)}"
                    )

                posting = merged.setdefault(
                    term_id,
                    {"title_tf": 0, "body_tf": 0, "tag_tf": 0},
                )
                for field_name in ("title_tf", "body_tf", "tag_tf"):
                    value = frequencies.get(field_name, 0)
                    self._validate_tf(value, field_name)
                    posting[field_name] += value

        for term_id, frequencies in merged.items():
            title_tf = frequencies["title_tf"]
            body_tf = frequencies["body_tf"]
            tag_tf = frequencies["tag_tf"]
            if title_tf + body_tf + tag_tf == 0:
                continue

            incoming = (title_tf, body_tf, tag_tf)
            for posting in self._index.get(term_id, []):
                if posting["doc_id"] != doc_id:
                    continue
                existing = (
                    posting["title_tf"],
                    posting["body_tf"],
                    posting["tag_tf"],
                )
                if incoming != existing:
                    raise ValueError(
                        f"posting already exists for term_id={term_id}, "
                        f"doc_id={doc_id}; use one consistent frequency"
                    )

        for term_id, frequencies in merged.items():
            title_tf = frequencies["title_tf"]
            body_tf = frequencies["body_tf"]
            tag_tf = frequencies["tag_tf"]
            self.add_posting(term_id, doc_id, title_tf, body_tf, tag_tf)

        self._document_ids.add(doc_id)

    def get_postings(self, term_id: int) -> list[Posting]:
        """Return a copy of postings for a term ID, sorted by document ID."""
        self._validate_term_id(term_id)
        return [dict(posting) for posting in self._index.get(term_id, [])]

    def get_document_frequency(self, term_id: int) -> int:
        """Return the number of distinct documents containing the term."""
        self._validate_term_id(term_id)
        return len(self._index.get(term_id, []))

    def get_df(self, term_id: int) -> int:
        """Short alias for get_document_frequency."""
        return self.get_document_frequency(term_id)

    def get_index(self) -> dict[int, list[Posting]]:
        """Expose a defensive copy of the current index representation."""
        return {
            term_id: [dict(posting) for posting in postings]
            for term_id, postings in self._index.items()
        }

    @property
    def index(self) -> dict[int, list[Posting]]:
        """A defensive copy of the complete index."""
        return self.get_index()

    @property
    def df(self) -> dict[int, int]:
        """Document frequencies keyed by term ID."""
        return {
            term_id: len(postings)
            for term_id, postings in self._index.items()
        }

    def __len__(self) -> int:
        return len(self._index)
