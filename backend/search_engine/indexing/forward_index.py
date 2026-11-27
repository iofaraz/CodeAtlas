"""Forward Index for CodeAtlas (Phase 3, owner: Asadullah).

Maps each document ID to the terms present in that document, with separate
title / body / tag term frequencies. Terms are stored as Lexicon term IDs,
never as strings.

On-disk format (``<root>/indexes/forward/forward_index.jsonl``), one object per
document, ascending ``doc_id``; terms inside a document ascending ``term_id``::

    {"doc_id":123,"terms":[{"term_id":1,"title_tf":1,"body_tf":2,"tag_tf":0}]}

Public interface (agreed in the Phase 3 specification)::

    ForwardIndex.build(documents, lexicon)
    index.get_document_terms(doc_id)
    index.save(output_dir)
    ForwardIndex.load(input_dir, lexicon)

``save``/``load`` take the *repository root* (same convention as Rafay's
``Lexicon.save/load``) and add ``indexes/forward/forward_index.jsonl`` themselves,
so the integration code can call all three structures with the same directory.

The Lexicon is used only through ``get_term_id(term)`` and ``get_term(term_id)``.
An unknown lookup may return ``None`` or raise ``KeyError``/``IndexError``/
``LookupError``; both styles are handled, as is ``0`` (reserved as invalid).
"""

from __future__ import annotations

import json
import os
from array import array
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple

FORWARD_INDEX_REL_PATH = Path("indexes/forward/forward_index.jsonl")
_STRIDE = 4  # term_id, title_tf, body_tf, tag_tf
_FIELDS = ("title_tokens", "body_tokens", "tag_tokens")


class TermEntry(NamedTuple):
    """One term's frequencies inside one document."""

    term_id: int
    title_tf: int
    body_tf: int
    tag_tf: int

    def to_dict(self) -> dict[str, int]:
        return {
            "term_id": self.term_id,
            "title_tf": self.title_tf,
            "body_tf": self.body_tf,
            "tag_tf": self.tag_tf,
        }


class UnknownTermError(ValueError):
    """A document contains a term that is not in the Lexicon."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _lexicon_term_id(lexicon: Any, term: str) -> int | None:
    try:
        term_id = lexicon.get_term_id(term)
    except LookupError:
        return None
    if term_id is None or not _is_int(term_id) or term_id <= 0:
        return None
    return term_id


def _lexicon_has_id(lexicon: Any, term_id: int) -> bool:
    if not _is_int(term_id) or term_id <= 0:
        return False
    try:
        return lexicon.get_term(term_id) is not None
    except LookupError:
        return False


def _read_field(document: Any, name: str) -> Any:
    if isinstance(document, dict):
        if name not in document:
            raise ValueError(f"document is missing required field {name!r}")
        return document[name]
    if not hasattr(document, name):
        raise ValueError(f"document is missing required field {name!r}")
    return getattr(document, name)


def _read_tokens(document: Any, name: str, doc_id: int) -> list[str]:
    tokens = _read_field(document, name)
    if tokens is None:  # tolerate null as "empty"
        return []
    if isinstance(tokens, (str, bytes)) or not isinstance(tokens, Iterable):
        raise ValueError(
            f"doc_id {doc_id}: field {name!r} must be a list of tokens, "
            f"got {type(tokens).__name__}"
        )
    return list(tokens)


def iter_documents_jsonl(path: str | os.PathLike[str]) -> Iterator[dict[str, Any]]:
    """Stream records from a Phase 2 ``documents.jsonl`` file (read-only)."""
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON ({exc})") from exc


class ForwardIndex:
    """doc_id -> per-term (title_tf, body_tf, tag_tf), keyed by Lexicon term IDs.

    Each document is kept as one flat ``array('I')`` of
    ``[term_id, title_tf, body_tf, tag_tf, ...]`` sorted by term_id. This is far
    smaller in RAM than millions of Python tuples, which matters for 50,083
    documents. Callers always see ``TermEntry`` objects.
    """

    def __init__(self) -> None:
        self._records: dict[int, array] = {}

    # ------------------------------------------------------------------ build
    @classmethod
    def build(cls, documents: Iterable[Any], lexicon: Any) -> "ForwardIndex":
        """Build from Phase 2 documents (dicts or objects) and a Lexicon.

        Frequencies are counted separately per field (token lists are *not*
        turned into sets). Only terms occurring in at least one field are
        stored. A document with no terms still gets an (empty) record so the
        record count equals the document count.
        """
        index = cls()
        term_id_cache: dict[str, int] = {}
        for document in documents:
            doc_id = _read_field(document, "doc_id")
            if not _is_int(doc_id):
                raise ValueError(f"doc_id must be an integer, got {doc_id!r}")
            if doc_id <= 0:
                raise ValueError(f"doc_id must be a positive integer, got {doc_id!r}")
            if doc_id in index._records:
                raise ValueError(f"duplicate doc_id {doc_id}")

            # Merge on term ID (not on the raw string): the Lexicon normalizes terms
            # (strip + lower), so two raw tokens could share one ID.
            per_term: dict[int, list[int]] = {}
            for slot, field in enumerate(_FIELDS):
                counts = Counter(_read_tokens(document, field, doc_id))
                for token, count in counts.items():
                    term_id = term_id_cache.get(token)
                    if term_id is None:
                        if isinstance(token, str) and not token.strip():
                            continue  # the Lexicon ignores empty terms too
                        term_id = _lexicon_term_id(lexicon, token)
                        if term_id is None:
                            raise UnknownTermError(
                                f"doc_id {doc_id}: term {token!r} is not in the Lexicon"
                            )
                        term_id_cache[token] = term_id
                    per_term.setdefault(term_id, [0, 0, 0])[slot] += count

            flat = array("I")
            for term_id in sorted(per_term):
                flat.extend((term_id, *per_term[term_id]))
            index._records[doc_id] = flat
        return index

    # ----------------------------------------------------------------- lookup
    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, doc_id: object) -> bool:
        return doc_id in self._records

    def doc_ids(self) -> list[int]:
        """All document IDs, ascending."""
        return sorted(self._records)

    def get_document_terms(self, doc_id: int) -> list[TermEntry]:
        """Terms of one document, ascending ``term_id``.

        Raises ``KeyError`` for an unknown ``doc_id``. A known document with no
        terms returns an empty list.
        """
        try:
            flat = self._records[doc_id]
        except KeyError:
            raise KeyError(f"unknown doc_id {doc_id!r}") from None
        return [TermEntry(*flat[i : i + _STRIDE]) for i in range(0, len(flat), _STRIDE)]

    def iter_documents(self) -> Iterator[tuple[int, list[TermEntry]]]:
        """Yield ``(doc_id, entries)`` in ascending doc_id order.

        Intended for the Inverted Index builder (transposition) so it does not
        need to touch private state.
        """
        for doc_id in self.doc_ids():
            yield doc_id, self.get_document_terms(doc_id)

    # ------------------------------------------------------------- validation
    def validate(self, lexicon: Any) -> None:
        """Raise ``ValueError`` unless all structural rules hold.

        Checks: unique doc IDs (guaranteed by the dict), term IDs exist in the
        Lexicon, terms strictly ascending (hence unique) per document,
        frequencies non-negative, and no all-zero entry.
        """
        known: set[int] = set()
        for doc_id, flat in self._records.items():
            if not _is_int(doc_id) or doc_id <= 0:
                raise ValueError(f"invalid doc_id {doc_id!r}; doc_id must be positive")
            previous = 0
            for i in range(0, len(flat), _STRIDE):
                term_id, title_tf, body_tf, tag_tf = flat[i : i + _STRIDE]
                if term_id <= previous:
                    raise ValueError(
                        f"doc_id {doc_id}: term IDs not strictly ascending "
                        f"({term_id} after {previous})"
                    )
                previous = term_id
                if term_id not in known:
                    if not _lexicon_has_id(lexicon, term_id):
                        raise ValueError(
                            f"doc_id {doc_id}: term_id {term_id} not in the Lexicon"
                        )
                    known.add(term_id)
                if title_tf == 0 and body_tf == 0 and tag_tf == 0:
                    raise ValueError(
                        f"doc_id {doc_id}: term_id {term_id} has all-zero frequencies"
                    )

    def document_frequencies(self) -> dict[int, int]:
        """term_id -> number of documents containing it (each document counts once)."""
        counter: Counter = Counter()
        for flat in self._records.values():
            counter.update(flat[0::_STRIDE])  # term IDs only; unique within a document
        return dict(counter)

    def verify_document_frequencies(self, lexicon: Any) -> None:
        """Raise ``ValueError`` if document frequencies disagree with the Lexicon.

        Compares the df derived from this index with ``lexicon.get_document_frequency``.
        If the Lexicon exposes a ``document_frequency`` dict, terms the Lexicon
        lists but this index never uses are reported as well.
        """
        get_df = getattr(lexicon, "get_document_frequency", None)
        if get_df is None:
            raise TypeError("lexicon has no get_document_frequency(term_id)")
        own = self.document_frequencies()
        problems = [
            f"term_id {term_id}: forward index df={df}, lexicon df={get_df(term_id)}"
            for term_id, df in own.items()
            if get_df(term_id) != df
        ]
        lexicon_df = getattr(lexicon, "document_frequency", None)
        if isinstance(lexicon_df, dict):
            problems += [
                f"term_id {term_id}: in the Lexicon (df={lexicon_df[term_id]}) but in no document"
                for term_id in sorted(set(lexicon_df) - set(own))
            ]
        if problems:
            shown = "; ".join(problems[:5])
            raise ValueError(f"{len(problems)} df mismatch(es), e.g. {shown}")

    # -------------------------------------------------------------- save/load
    def save(self, output_dir: str | os.PathLike[str]) -> Path:
        """Write ``<output_dir>/indexes/forward/forward_index.jsonl`` atomically.

        Data goes to a temporary file first; the final file is replaced only
        after the write completes, so a failed save never leaves a half-written
        index. Returns the final path.
        """
        final_path = Path(output_dir) / FORWARD_INDEX_REL_PATH
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = final_path.with_name(final_path.name + ".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
                for doc_id in self.doc_ids():
                    record = {
                        "doc_id": doc_id,
                        "terms": [e.to_dict() for e in self.get_document_terms(doc_id)],
                    }
                    handle.write(json.dumps(record, separators=(",", ":")))
                    handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, final_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
        return final_path

    @classmethod
    def load(cls, input_dir: str | os.PathLike[str], lexicon: Any) -> "ForwardIndex":
        """Read ``<input_dir>/indexes/forward/forward_index.jsonl`` and validate it.

        Raises ``FileNotFoundError`` if missing and ``ValueError`` (with the
        line number) for malformed JSON, wrong field types, duplicate or
        out-of-order doc IDs, or terms that violate the format rules.
        """
        path = Path(input_dir) / FORWARD_INDEX_REL_PATH
        index = cls()
        previous_doc = None
        with open(path, "r", encoding="utf-8") as handle:
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
                required_record_fields = {"doc_id", "terms"}
                missing_fields = required_record_fields - set(record)
                if missing_fields:
                    raise ValueError(
                        f"{where}: expected exactly {{'doc_id', 'terms'}} fields; "
                        "missing required fields "
                        f"{sorted(missing_fields)}"
                    )
                extra_fields = set(record) - required_record_fields
                if extra_fields:
                    raise ValueError(
                        f"{where}: unexpected fields {sorted(extra_fields)}; "
                        "expected exactly {'doc_id', 'terms'}"
                    )
                if not isinstance(record["terms"], list):
                    raise ValueError(f"{where}: terms must be a list")
                doc_id = record["doc_id"]
                if not _is_int(doc_id):
                    raise ValueError(f"{where}: doc_id must be an integer")
                if doc_id <= 0:
                    raise ValueError(f"{where}: doc_id must be a positive integer")
                if doc_id in index._records:
                    raise ValueError(f"{where}: duplicate doc_id {doc_id}")
                if previous_doc is not None and doc_id <= previous_doc:
                    raise ValueError(
                        f"{where}: doc_ids are not in strictly ascending order"
                    )
                previous_doc = doc_id

                flat = array("I")
                previous_term_id = 0
                for entry in record["terms"]:
                    if not isinstance(entry, dict):
                        raise ValueError(f"{where}: term entry must be an object")
                    required_term_fields = {
                        "term_id",
                        "title_tf",
                        "body_tf",
                        "tag_tf",
                    }
                    missing_fields = required_term_fields - set(entry)
                    if missing_fields:
                        raise ValueError(
                            f"{where}: malformed term entry; missing required fields "
                            f"{sorted(missing_fields)}"
                        )
                    extra_fields = set(entry) - required_term_fields
                    if extra_fields:
                        raise ValueError(
                            f"{where}: malformed term entry; unexpected fields "
                            f"{sorted(extra_fields)}"
                        )
                    values = [
                        entry["term_id"],
                        entry["title_tf"],
                        entry["body_tf"],
                        entry["tag_tf"],
                    ]
                    if not all(_is_int(v) for v in values) or min(values) < 0:
                        raise ValueError(f"{where}: non-integer or negative value in {entry!r}")
                    term_id = values[0]
                    if term_id == 0:
                        raise ValueError(f"{where}: term_id must be positive")
                    if term_id <= previous_term_id:
                        raise ValueError(
                            f"{where}: term IDs are not in strictly ascending order"
                        )
                    previous_term_id = term_id
                    if sum(values[1:]) == 0:
                        raise ValueError(
                            f"{where}: all-zero term entry is not allowed"
                        )
                    flat.extend(values)
                index._records[doc_id] = flat
        index.validate(lexicon)
        return index
