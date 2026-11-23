"""In-memory inverted index foundation.

The Lexicon is expected to translate normalized terms to positive integer
term IDs.  The Forward Index may provide per-field term counts or term-ID
sequences; this module deliberately does not depend on either teammate's
implementation.
"""

from collections import Counter
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence
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

    def add_forward_record(self, record: object) -> None:
        """Adapt one Forward Index record and add it to the inverted index."""
        if not isinstance(record, MappingABC):
            raise ValueError("record must be a mapping")

        if "doc_id" not in record:
            raise ValueError("Forward Index record is missing doc_id")
        doc_id = record["doc_id"]
        self._validate_doc_id(doc_id)

        if "terms" not in record:
            raise ValueError("Forward Index record is missing terms")
        terms = record["terms"]
        if (
            not isinstance(terms, Sequence)
            or isinstance(terms, (str, bytes, bytearray))
        ):
            raise ValueError("terms must be a sequence")

        term_frequencies: dict[int, dict[str, int]] = {}
        previous_term_id = 0
        seen_term_ids: set[int] = set()

        for term_entry in terms:
            if not isinstance(term_entry, MappingABC):
                raise ValueError("each term entry must be a mapping")
            if "term_id" not in term_entry:
                raise ValueError("term entry is missing term_id")

            term_id = term_entry["term_id"]
            self._validate_term_id(term_id)
            if term_id in seen_term_ids:
                raise ValueError(
                    f"duplicate term_id in Forward Index record: {term_id}"
                )
            if term_id <= previous_term_id:
                raise ValueError("Forward Index terms must be sorted by ascending term_id")
            seen_term_ids.add(term_id)
            previous_term_id = term_id

            frequencies: dict[str, int] = {}
            for field_name in ("title_tf", "body_tf", "tag_tf"):
                if field_name not in term_entry:
                    raise ValueError(
                        f"term entry is missing {field_name}"
                    )
                value = term_entry[field_name]
                self._validate_tf(value, field_name)
                frequencies[field_name] = value

            if (
                frequencies["title_tf"]
                + frequencies["body_tf"]
                + frequencies["tag_tf"]
                == 0
            ):
                raise ValueError(
                    "Forward Index term entries must have at least one non-zero TF"
                )

            term_frequencies[term_id] = frequencies

        self.add_document(doc_id, term_frequencies=term_frequencies)

    def build_from_forward_records(self, records: Iterable[object]) -> None:
        """Replace the index with postings built from Forward Index records.

        The current index is left unchanged if iteration or record validation
        fails.
        """
        new_index = InvertedIndex()
        for record in records:
            new_index.add_forward_record(record)

        self._index = new_index._index
        self._document_ids = new_index._document_ids

    def validate(self) -> bool:
        """Validate the in-memory index structure.

        Returns ``True`` for a valid index.  Corruption raises ``ValueError``.
        This method is read-only and never exposes or modifies index internals.
        """
        if not isinstance(self._index, dict):
            raise ValueError("internal index must be a dictionary")
        if not isinstance(self._document_ids, set):
            raise ValueError("internal document ID collection must be a set")

        for doc_id in self._document_ids:
            self._validate_doc_id(doc_id)

        derived_df: dict[int, int] = {}
        for term_id, postings in self._index.items():
            self._validate_term_id(term_id)
            if not isinstance(postings, list):
                raise ValueError(
                    f"postings for term_id={term_id} must be a list"
                )
            if not postings:
                raise ValueError(
                    f"term_id={term_id} has an empty postings list"
                )

            previous_doc_id = 0
            seen_doc_ids: set[int] = set()
            for posting in postings:
                if not isinstance(posting, MappingABC):
                    raise ValueError(
                        f"posting for term_id={term_id} must be a mapping"
                    )

                expected_fields = {
                    "doc_id",
                    "title_tf",
                    "body_tf",
                    "tag_tf",
                }
                if set(posting) != expected_fields:
                    raise ValueError(
                        f"posting for term_id={term_id} has unexpected or "
                        "missing fields"
                    )

                doc_id = posting["doc_id"]
                self._validate_doc_id(doc_id)
                if doc_id in seen_doc_ids:
                    raise ValueError(
                        f"duplicate document ID {doc_id} in postings "
                        f"for term_id={term_id}"
                    )
                if doc_id <= previous_doc_id:
                    raise ValueError(
                        f"posting document IDs are not strictly increasing "
                        f"for term_id={term_id}"
                    )
                seen_doc_ids.add(doc_id)
                previous_doc_id = doc_id

                tf_values = {}
                for field_name in ("title_tf", "body_tf", "tag_tf"):
                    value = posting[field_name]
                    self._validate_tf(value, field_name)
                    tf_values[field_name] = value

                if (
                    tf_values["title_tf"]
                    + tf_values["body_tf"]
                    + tf_values["tag_tf"]
                    == 0
                ):
                    raise ValueError(
                        f"posting for term_id={term_id}, doc_id={doc_id} "
                        "must have at least one non-zero TF"
                    )

            derived_df[term_id] = len(postings)

        if self.df != derived_df:
            raise ValueError("document frequency entries are inconsistent")
        return True

    def validate_against_forward_records(
        self,
        records: Iterable[object],
    ) -> bool:
        """Validate exact consistency between the index and Forward records."""
        self.validate()

        forward = InvertedIndex()
        try:
            for record in records:
                forward.add_forward_record(record)
        except Exception:
            raise

        forward_docs = forward._document_ids
        current_docs = set(self._document_ids)
        for postings in self._index.values():
            for posting in postings:
                current_docs.add(posting["doc_id"])

        missing_documents = sorted(forward_docs - current_docs)
        if missing_documents:
            raise ValueError(
                "missing document(s) in Inverted Index: "
                + ", ".join(str(doc_id) for doc_id in missing_documents)
            )

        extra_documents = sorted(current_docs - forward_docs)
        if extra_documents:
            raise ValueError(
                "extra document(s) in Inverted Index: "
                + ", ".join(str(doc_id) for doc_id in extra_documents)
            )

        forward_index = forward.get_index()
        current_index = self.get_index()

        for term_id in sorted(set(forward_index) | set(current_index)):
            forward_postings = forward_index.get(term_id, [])
            current_postings = current_index.get(term_id, [])
            forward_by_doc = {
                posting["doc_id"]: posting
                for posting in forward_postings
            }
            current_by_doc = {
                posting["doc_id"]: posting
                for posting in current_postings
            }

            for doc_id in sorted(set(forward_by_doc) - set(current_by_doc)):
                raise ValueError(
                    f"missing posting for term_id={term_id}, doc_id={doc_id}"
                )
            for doc_id in sorted(set(current_by_doc) - set(forward_by_doc)):
                raise ValueError(
                    f"extra posting for term_id={term_id}, doc_id={doc_id}"
                )

            for doc_id in sorted(set(forward_by_doc) & set(current_by_doc)):
                for field_name in ("title_tf", "body_tf", "tag_tf"):
                    forward_value = forward_by_doc[doc_id][field_name]
                    current_value = current_by_doc[doc_id][field_name]
                    if forward_value != current_value:
                        raise ValueError(
                            f"incorrect {field_name} for term_id={term_id}, "
                            f"doc_id={doc_id}: expected {forward_value}, "
                            f"got {current_value}"
                        )

        for term_id in set(forward_index) | set(current_index):
            forward_df = len(forward_index.get(term_id, []))
            current_df = len(current_index.get(term_id, []))
            if forward_df != current_df:
                raise ValueError(
                    f"document frequency mismatch for term_id={term_id}: "
                    f"expected {forward_df}, got {current_df}"
                )

        return True

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
