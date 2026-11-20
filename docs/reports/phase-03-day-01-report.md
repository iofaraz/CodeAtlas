# Phase 3 - Day 1: Inverted Index Foundation

## 1. Day 1 Objective

Implement the initial in-memory Inverted Index representation and basic
posting-construction logic for CodeAtlas. This report covers only Day 1;
JSONL indexing, Lexicon, Forward Index, search, ranking, barrels and
database integration are intentionally outside scope.

## 2. Files Inspected

- `backend/search_engine/`
- `backend/search_engine/preprocessing/document.py`
- `backend/search_engine/preprocessing/` and its existing modules
- `data/processed/documents.jsonl`
- `docs/architecture/indexing-architecture.md`
- `docs/phases/phase-02-data-processing.md`
- Existing preprocessing tests and indexing directories

The actual JSONL schema uses integer `doc_id` values and list-valued
`title_tokens`, `body_tokens`, and `tag_tokens` fields.

## 3. Files Created or Modified

Created:

- `backend/search_engine/indexing/__init__.py`
- `backend/search_engine/indexing/inverted_index.py`
- `tests/test_indexing/test_inverted_index.py`
- `docs/reports/phase-03-day-01-report.md`

No preprocessing, processed-data or unrelated files were modified.

## 4. Inverted Index Representation and Design Decisions

`InvertedIndex` stores `term_id -> list[posting]` in a Python dictionary.
Each posting contains:

- `doc_id`
- `title_tf`
- `body_tf`
- `tag_tf`

`term_id` keys must be positive integers. Posting lists are sorted by
ascending `doc_id`. Postings are exposed through copies so callers cannot
accidentally mutate internal index state.

The module does not import or assume the Lexicon or Forward Index APIs.
It accepts integer term-ID sequences and/or an independent precomputed
term-frequency mapping. This leaves integration for later teammates to
adapt.

## 5. Posting Construction

`add_document()`:

1. Validates the document ID.
2. Counts repeated term IDs in title, body and tag sequences separately.
3. Optionally merges a precomputed mapping in the form
   `{term_id: {"title_tf": n, "body_tf": n, "tag_tf": n}}`.
4. Builds and validates every incoming posting before changing the index.
5. Checks existing postings for conflicts before applying any new posting.
6. Creates at most one posting for each `(term_id, doc_id)` pair.
7. Keeps a track of added document IDs to prevent accidental re-processing.

`add_posting()` supports direct one-posting insertion for focused or later
integration use. It rejects conflicting repeated postings rather than
silently creating a duplicate or applying an ambiguous update.

## 6. Field-Specific TF and DF Calculations

When term-ID sequences are supplied, `Counter` counts occurrences
separately for `title_term_ids`, `body_term_ids`, and `tag_term_ids`.
A term in multiple fields therefore has one posting whose three TF values
represent all fields.

With precomputed mappings, supplied TF values are validated and merged into
the same posting representation. Zero TF values are accepted in mappings,
but an all-zero posting is not added.

Document frequency is the number of distinct posting entries for the term.
It is calculated as `len(self._index.get(term_id, []))`.

## 7. Validation and Error Handling

The implementation validates:

- Positive integer `doc_id`; booleans are rejected.
- Positive integer `term_id`; `0` is reserved and rejected.
- Non-negative integer title, body and tag frequencies; booleans are rejected.
- Term-frequency mappings and known field names.
- Repeated documents and conflicting duplicate postings.

All-zero postings are not inserted. Invalid input raises `ValueError`;
structurally incorrect mappings raise `TypeError`.

## 8. Tests Executed and Actual Results

Command:

```text
python -m pytest tests/test_indexing/test_inverted_index.py -q --basetemp='.pytest_tmp'
```

Actual result:

```text
24 passed in 0.10s
```

Tests cover empty initialization, repeated title/body/tag occurrences,
cross-field same-term merging, precomputed frequencies, DF, ascending
doc-ID sorting, no-postings retrieval, invalid IDs and frequencies,
duplicate prevention, conflicting duplicate rejection, atomic document
addition and defensive-copy retrieval.

## 9. Known Limitations and Postponed Work

Implemented for Day 1:

- In-memory index representation
- Sequence-based field TF counting
- Precomputed TF mapping support
- Posting and DF retrieval
- Defensive index/DF inspection
- Validation and duplicate protection

Postponed to later days:

- JSONL dataset loading and full indexing
- Lexicon implementation and term-name-to-ID conversion
- Forward Index integration
- Persistence under `indexes/inverted/`
- Barrels
- Search/query processing
- Ranking
- Dataset or performance benchmarking

Teammate interfaces are not finalized, so integration is intentionally
left to subsequent work.

## 10. Recommended Next Steps for Day 2

1. Add JSONL iteration that transforms real processed records only after
   Lexicon and term-ID mapping decisions are available.
2. Coordinate with Rafay on the exact Lexicon lookup interface.
3. Coordinate with Asadullah on whether the Forward Index exposes term-ID
   sequences or precomputed field frequencies.
4. Add integration tests once those interfaces exist.
5. Consider persistence format and incremental construction requirements
   only after the data flow is confirmed.
