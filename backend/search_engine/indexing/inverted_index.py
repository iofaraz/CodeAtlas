"""In-memory inverted index foundation.

The Lexicon is expected to translate normalized terms to positive integer
term IDs.  The Forward Index may provide per-field term counts or term-ID
sequences; this module deliberately does not depend on either teammate's
implementation.
"""

import json
import os
from pathlib import Path
from collections import Counter
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence
from typing import Iterable, Iterator, Mapping, TypedDict


class Posting(TypedDict):
    doc_id: int
    title_tf: int
    body_tf: int
    tag_tf: int


TermFrequency = Mapping[str, int]

INVERTED_INDEX_REL_PATH = Path("indexes/inverted/inverted_index.jsonl")


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

    @staticmethod
    def _posting_position(
        postings: list[Posting], doc_id: int
    ) -> tuple[int, bool]:
        """Return the insertion point and whether doc_id already has a posting."""
        low = 0
        high = len(postings)
        while low < high:
            middle = (low + high) // 2
            if postings[middle]["doc_id"] < doc_id:
                low = middle + 1
            else:
                high = middle
        return low, low < len(postings) and postings[low]["doc_id"] == doc_id

    @staticmethod
    def _make_posting(
        doc_id: int, title_tf: int, body_tf: int, tag_tf: int
    ) -> Posting:
        return {
            "doc_id": doc_id,
            "title_tf": title_tf,
            "body_tf": body_tf,
            "tag_tf": tag_tf,
        }

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
            raise ValueError("posting must have at least one non-zero TF")

        postings = self._index.setdefault(term_id, [])
        position, exists = self._posting_position(postings, doc_id)
        if exists:
            existing = postings[position]
            if (
                existing["title_tf"],
                existing["body_tf"],
                existing["tag_tf"],
            ) == (title_tf, body_tf, tag_tf):
                return
            raise ValueError(
                f"posting already exists for term_id={term_id}, "
                f"doc_id={doc_id}; use one consistent frequency"
            )

        postings.insert(
            position, self._make_posting(doc_id, title_tf, body_tf, tag_tf)
        )

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

        insertions: list[tuple[int, int, bool]] = []
        for term_id, frequencies in merged.items():
            title_tf = frequencies["title_tf"]
            body_tf = frequencies["body_tf"]
            tag_tf = frequencies["tag_tf"]
            if title_tf + body_tf + tag_tf == 0:
                continue

            postings = self._index.get(term_id, [])
            position, exists = self._posting_position(postings, doc_id)
            if exists:
                existing = postings[position]
                if (
                    existing["title_tf"],
                    existing["body_tf"],
                    existing["tag_tf"],
                ) != (title_tf, body_tf, tag_tf):
                    raise ValueError(
                        f"posting already exists for term_id={term_id}, "
                        f"doc_id={doc_id}; use one consistent frequency"
                    )
            insertions.append((term_id, position, exists))

        for term_id, position, exists in insertions:
            if exists:
                continue
            frequencies = merged[term_id]
            title_tf = frequencies["title_tf"]
            body_tf = frequencies["body_tf"]
            tag_tf = frequencies["tag_tf"]
            postings = self._index.setdefault(term_id, [])
            postings.insert(
                position,
                self._make_posting(doc_id, title_tf, body_tf, tag_tf),
            )

        self._document_ids.add(doc_id)

    @classmethod
    def _parse_forward_record(
        cls, record: object
    ) -> tuple[int, list[tuple[int, int, int, int]]]:
        """Validate one Forward record and return its document and term data."""
        if not isinstance(record, MappingABC):
            raise ValueError("record must be a mapping")

        if "doc_id" not in record:
            raise ValueError("Forward Index record is missing doc_id")
        if "terms" not in record:
            raise ValueError("Forward Index record is missing terms")
        unexpected_fields = set(record) - {"doc_id", "terms"}
        if unexpected_fields:
            raise ValueError(
                f"Forward Index record has unexpected fields: "
                f"{sorted(unexpected_fields)}"
            )

        doc_id = record["doc_id"]
        cls._validate_doc_id(doc_id)

        terms = record["terms"]
        if (
            not isinstance(terms, Sequence)
            or isinstance(terms, (str, bytes, bytearray))
        ):
            raise ValueError("terms must be a sequence")

        parsed_terms: list[tuple[int, int, int, int]] = []
        previous_term_id = 0
        seen_term_ids: set[int] = set()

        for term_entry in terms:
            if not isinstance(term_entry, MappingABC):
                raise ValueError("each term entry must be a mapping")
            required_term_fields = {
                "term_id",
                "title_tf",
                "body_tf",
                "tag_tf",
            }
            missing_fields = required_term_fields - set(term_entry)
            if "term_id" in missing_fields:
                raise ValueError("term entry is missing term_id")
            for field_name in ("title_tf", "body_tf", "tag_tf"):
                if field_name in missing_fields:
                    raise ValueError(f"term entry is missing {field_name}")
            unexpected_fields = set(term_entry) - required_term_fields
            if unexpected_fields:
                raise ValueError(
                    f"term entry has unexpected fields: "
                    f"{sorted(unexpected_fields)}"
                )

            term_id = term_entry["term_id"]
            cls._validate_term_id(term_id)
            if term_id in seen_term_ids:
                raise ValueError(
                    f"duplicate term_id in Forward Index record: {term_id}"
                )
            if term_id <= previous_term_id:
                raise ValueError("Forward Index terms must be sorted by ascending term_id")
            seen_term_ids.add(term_id)
            previous_term_id = term_id

            frequencies: list[int] = []
            for field_name in ("title_tf", "body_tf", "tag_tf"):
                if field_name not in term_entry:
                    raise ValueError(
                        f"term entry is missing {field_name}"
                    )
                value = term_entry[field_name]
                cls._validate_tf(value, field_name)
                frequencies.append(value)

            if sum(frequencies) == 0:
                raise ValueError(
                    "Forward Index term entries must have at least one non-zero TF"
                )

            parsed_terms.append((term_id, *frequencies))

        return doc_id, parsed_terms

    def add_forward_record(self, record: object) -> None:
        """Adapt one Forward Index record and add it to the inverted index."""
        doc_id, parsed_terms = self._parse_forward_record(record)
        term_frequencies = {
            term_id: {
                "title_tf": title_tf,
                "body_tf": body_tf,
                "tag_tf": tag_tf,
            }
            for term_id, title_tf, body_tf, tag_tf in parsed_terms
        }
        self.add_document(doc_id, term_frequencies=term_frequencies)

    def build_from_forward_records(self, records: Iterable[object]) -> None:
        """Replace the index with postings built from Forward Index records.

        Ascending document IDs append directly to each posting list. If input
        documents are out of order, each list is sorted once after ingestion.
        The current index is left unchanged if iteration or validation fails.
        """
        new_index = InvertedIndex()
        previous_doc_id = 0
        requires_sort = False
        for record in records:
            doc_id, terms = self._parse_forward_record(record)
            if doc_id in new_index._document_ids:
                raise ValueError(f"document {doc_id} has already been added")
            if doc_id < previous_doc_id:
                requires_sort = True

            new_index._document_ids.add(doc_id)
            for term_id, title_tf, body_tf, tag_tf in terms:
                new_index._index.setdefault(term_id, []).append(
                    self._make_posting(doc_id, title_tf, body_tf, tag_tf)
                )
            previous_doc_id = doc_id

        if requires_sort:
            for postings in new_index._index.values():
                postings.sort(key=lambda posting: posting["doc_id"])

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

        return True

    def validate_against_forward_records(
        self,
        records: Iterable[object],
    ) -> bool:
        """Validate exact consistency without constructing a second full index."""
        self.validate()

        forward_docs: set[int] = set()
        forward_df: Counter[int] = Counter()
        posting_cursors: dict[int, int] = {}
        current_docs = set(self._document_ids)
        for postings in self._index.values():
            for posting in postings:
                current_docs.add(posting["doc_id"])
        previous_doc_id = 0
        forward_is_sorted = True
        first_mismatch: ValueError | None = None

        for record in records:
            doc_id, terms = self._parse_forward_record(record)
            if doc_id in forward_docs:
                raise ValueError(f"document {doc_id} has already been added")
            if doc_id < previous_doc_id:
                forward_is_sorted = False
            forward_docs.add(doc_id)

            for term_id, title_tf, body_tf, tag_tf in terms:
                postings = self._index.get(term_id)
                if postings is None:
                    if first_mismatch is None:
                        first_mismatch = ValueError(
                            f"missing posting for term_id={term_id}, doc_id={doc_id}"
                        )
                    forward_is_sorted = False
                    forward_df[term_id] += 1
                    continue

                if forward_is_sorted:
                    position = posting_cursors.get(term_id, 0)
                    if (
                        position < len(postings)
                        and postings[position]["doc_id"] == doc_id
                    ):
                        posting = postings[position]
                        posting_cursors[term_id] = position + 1
                    else:
                        position, exists = self._posting_position(
                            postings, doc_id
                        )
                        forward_is_sorted = False
                        if not exists:
                            if first_mismatch is None:
                                first_mismatch = ValueError(
                                    f"missing posting for term_id={term_id}, "
                                    f"doc_id={doc_id}"
                                )
                            forward_df[term_id] += 1
                            continue
                        posting = postings[position]
                else:
                    position, exists = self._posting_position(postings, doc_id)
                    if not exists:
                        if first_mismatch is None:
                            first_mismatch = ValueError(
                                f"missing posting for term_id={term_id}, "
                                f"doc_id={doc_id}"
                            )
                        forward_df[term_id] += 1
                        continue
                    posting = postings[position]

                expected = (title_tf, body_tf, tag_tf)
                actual = (
                    posting["title_tf"],
                    posting["body_tf"],
                    posting["tag_tf"],
                )
                if actual != expected:
                    if first_mismatch is None:
                        for field_name, expected_tf, actual_tf in zip(
                            ("title_tf", "body_tf", "tag_tf"), expected, actual
                        ):
                            if expected_tf != actual_tf:
                                first_mismatch = ValueError(
                                    f"incorrect {field_name} for term_id={term_id}, "
                                    f"doc_id={doc_id}: expected {expected_tf}, "
                                    f"got {actual_tf}"
                                )
                                break

                forward_df[term_id] += 1
            previous_doc_id = doc_id

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

        if first_mismatch is not None:
            raise first_mismatch

        for term_id, postings in self._index.items():
            observed_df = forward_df.get(term_id, 0)
            if observed_df != len(postings):
                if observed_df < len(postings) and forward_is_sorted:
                    extra_position = posting_cursors.get(term_id, 0)
                    if extra_position < len(postings):
                        raise ValueError(
                            f"extra posting for term_id={term_id}, "
                            f"doc_id={postings[extra_position]['doc_id']}"
                        )
                raise ValueError(
                    f"document frequency mismatch for term_id={term_id}: "
                    f"forward df={observed_df}, inverted df={len(postings)}"
                )

        return True

    def validate_against_lexicon(self, lexicon: object) -> bool:
        """Validate term IDs and DFs against every Lexicon entry."""
        self.validate()
        get_term = getattr(lexicon, "get_term", None)
        if get_term is None:
            raise TypeError("lexicon has no get_term(term_id)")

        for term_id, postings in self._index.items():
            if get_term(term_id) is None:
                raise ValueError(
                    f"term_id {term_id} not in the Lexicon"
                )

        lexicon_document_frequency = getattr(
            lexicon, "document_frequency", None
        )
        if isinstance(lexicon_document_frequency, MappingABC):
            for term_id, lexicon_df in lexicon_document_frequency.items():
                index_df = len(self._index.get(term_id, []))
                if lexicon_df != index_df:
                    raise ValueError(
                        f"document frequency mismatch for term_id={term_id}: "
                        f"lexicon df={lexicon_df}, inverted df={index_df}"
                    )
        else:
            get_df = getattr(lexicon, "get_document_frequency", None)
            if get_df is not None:
                for term_id, postings in self._index.items():
                    lexicon_df = get_df(term_id)
                    if lexicon_df != len(postings):
                        raise ValueError(
                            f"document frequency mismatch for term_id={term_id}: "
                            f"lexicon df={lexicon_df}, inverted df={len(postings)}"
                        )
        return True

    def iter_jsonl_lines(self) -> Iterator[str]:
        """Yield deterministic serialized records without copying the full index."""
        for term_id in sorted(self._index):
            postings = self._index[term_id]
            record = {
                "term_id": term_id,
                "df": len(postings),
                "postings": postings,
            }
            yield json.dumps(
                record, ensure_ascii=False, separators=(",", ":")
            ) + "\n"

    def save(self, output_dir: str | os.PathLike[str]) -> Path:
        """Atomically write the inverted index as sorted JSONL."""
        self.validate()
        final_path = Path(output_dir) / INVERTED_INDEX_REL_PATH
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = final_path.with_name(final_path.name + ".tmp")
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                for line in self.iter_jsonl_lines():
                    handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, final_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
        return final_path

    @classmethod
    def load(
        cls,
        input_dir: str | os.PathLike[str],
        lexicon: object | None = None,
    ) -> "InvertedIndex":
        """Load and validate an inverted-index JSONL file."""
        path = Path(input_dir) / INVERTED_INDEX_REL_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Inverted Index file not found at: {path}")

        index = cls()
        previous_term_id = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                where = f"{path}:{line_number}"
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{where}: invalid JSON ({exc})") from exc
                if not isinstance(record, dict):
                    raise ValueError(f"{where}: record must be an object")
                required_record_fields = {"term_id", "df", "postings"}
                missing_fields = required_record_fields - set(record)
                if missing_fields:
                    raise ValueError(
                        f"{where}: missing required fields "
                        f"{sorted(missing_fields)}"
                    )
                extra_fields = set(record) - required_record_fields
                if extra_fields:
                    raise ValueError(
                        f"{where}: unexpected fields {sorted(extra_fields)}"
                    )

                term_id = record["term_id"]
                try:
                    cls._validate_term_id(term_id)
                except ValueError as exc:
                    raise ValueError(f"{where}: {exc}") from exc
                if term_id <= previous_term_id:
                    raise ValueError(
                        f"{where}: term IDs must be strictly increasing"
                    )
                previous_term_id = term_id

                postings = record["postings"]
                if not isinstance(postings, list):
                    raise ValueError(f"{where}: postings must be a list")
                df = record["df"]
                if isinstance(df, bool) or not isinstance(df, int) or df < 1:
                    raise ValueError(
                        f"{where}: df must be a positive integer"
                    )
                if df != len(postings):
                    raise ValueError(
                        f"{where}: df {df} does not match {len(postings)} postings"
                    )

                previous_doc_id = 0
                for posting in postings:
                    if not isinstance(posting, MappingABC):
                        raise ValueError(
                            f"{where}: each posting must be an object"
                        )
                    required_posting_fields = {
                        "doc_id",
                        "title_tf",
                        "body_tf",
                        "tag_tf",
                    }
                    missing_fields = required_posting_fields - set(posting)
                    if missing_fields:
                        raise ValueError(
                            f"{where}: posting missing required fields "
                            f"{sorted(missing_fields)}"
                        )
                    extra_fields = set(posting) - required_posting_fields
                    if extra_fields:
                        raise ValueError(
                            f"{where}: posting has unexpected fields "
                            f"{sorted(extra_fields)}"
                        )
                    doc_id = posting["doc_id"]
                    try:
                        cls._validate_doc_id(doc_id)
                    except ValueError as exc:
                        raise ValueError(f"{where}: {exc}") from exc
                    if doc_id <= previous_doc_id:
                        raise ValueError(
                            f"{where}: posting doc_ids must be strictly increasing"
                        )
                    previous_doc_id = doc_id
                    frequencies = tuple(
                        posting[field_name]
                        for field_name in ("title_tf", "body_tf", "tag_tf")
                    )
                    for field_name, frequency in zip(
                        ("title_tf", "body_tf", "tag_tf"), frequencies
                    ):
                        try:
                            cls._validate_tf(frequency, field_name)
                        except ValueError as exc:
                            raise ValueError(f"{where}: {exc}") from exc
                    if sum(frequencies) == 0:
                        raise ValueError(
                            f"{where}: posting must have a non-zero TF"
                        )
                    index._index.setdefault(term_id, []).append(
                        cls._make_posting(
                            doc_id,
                            *frequencies,
                        )
                    )
                    index._document_ids.add(doc_id)

        if lexicon is not None:
            index.validate_against_lexicon(lexicon)
        else:
            index.validate()
        return index

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
