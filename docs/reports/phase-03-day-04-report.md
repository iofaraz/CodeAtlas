# Phase 3 - Day 4: Inverted Index Structural Validation

## 1. Day 4 Objective

Add read-only structural validation and exact Forward Index consistency
validation to the in-memory `InvertedIndex` without changing existing
index-building behavior or integrating any additional indexing component.

## 2. Files Changed

- `backend/search_engine/indexing/inverted_index.py`
- `tests/test_indexing/test_inverted_index.py`
- `docs/reports/phase-03-day-04-report.md`

No preprocessing, Lexicon, Forward Index implementation, persistence,
ranking, search, API, frontend, or barrel files were changed.

## 3. New Public Methods

### `validate() -> bool`

Validates the current internal index structure and returns `True` when valid.
Invalid structure raises a descriptive `ValueError`. The method only reads
the index and does not expose mutable internal structures.

### `validate_against_forward_records(records: Iterable[object]) -> bool`

Validates supplied Forward Index records and compares them exactly with the
current Inverted Index. It accepts iterables, including generators, and
returns `True` when all documents and postings match. Validation raises
`ValueError` for malformed or inconsistent records. Iterator exceptions are
propagated. The method is read-only with respect to the index and input
records.

## 4. Structural Validation Rules

`validate()` checks:

- `_index` and `_document_ids` have the expected internal container types.
- Internal document IDs are positive integers; booleans are rejected.
- Term keys are positive integers; booleans and `0` are rejected.
- Each term has a non-empty list of postings.
- Posting objects contain exactly `doc_id`, `title_tf`, `body_tf`, and
  `tag_tf`.
- Each posting `doc_id` is a positive integer.
- Each TF field is a non-negative integer and booleans are rejected.
- Every posting has at least one non-zero TF.
- Posting document IDs are strictly increasing.
- No duplicate document ID occurs for the same term.

Document frequency is not stored separately in the in-memory index. The `df`
property and `get_document_frequency()` derive it directly from the length of
each term's posting list. Consequently, structural validation does not contain
a redundant comparison against a separate derived DF mapping.

## 5. Forward Index Consistency Rules

`validate_against_forward_records()`:

- Reuses the existing Forward record validation path for mappings,
  document IDs, term sequences, term IDs, TF fields and TF values.
- Rejects duplicate document IDs and malformed records.
- Does not modify the current index or input records.
- Builds a temporary index only while iterating the supplied records.
- Propagates iterator exceptions without applying any temporary changes.
- Compares the complete current and Forward document sets.
- Detects missing and extra documents.
- Detects missing and extra postings.
- Compares `title_tf`, `body_tf`, and `tag_tf` independently.
- Checks corresponding term and document frequency counts.

The document set comparison also accounts for postings added through
`add_posting()`, while `add_document()` and Forward record ingestion retain
their existing document tracking behavior.

## 6. Tests Added

The focused test module now includes:

- Valid and empty index validation.
- Parameterized structural corruption checks.
- Boolean, negative, malformed, duplicate, unsorted and all-zero posting cases.
- Valid and generator-based Forward consistency checks.
- Missing and extra posting detection.
- Independent title, body and tag TF mismatch detection.
- Missing and extra document detection.
- Duplicate document and malformed record rejection.
- Iterator exception propagation.
- Index and input-record immutability checks.

## 7. Tests Executed and Exact Results

Focused inverted-index command:

```text
python -m pytest tests/test_indexing/test_inverted_index.py -q
107 passed in 0.40s
```

Combined preprocessing and indexing command:

```text
python -m pytest tests/test_preprocessing tests/test_indexing -q --basetemp=".pytest_tmp"
136 passed in 2.98s
```

Whitespace validation:

```text
git diff --check
```

Result: completed successfully with no output.

`.pytest_tmp` was removed after testing.

## 8. Known Limitations

- Validation operates only on the in-memory representation.
- Lexicon membership cannot be checked because no Lexicon is part of this
  scope or implementation.
- The method does not read or write JSONL or perform persistence operations.
- It does not implement barrels, search, ranking, semantic search,
  autocomplete, API/frontend behavior or dynamic indexing.
- Forward validation relies on the established in-memory record contract;
  JSONL parsing remains outside scope.

## 9. Outcome and Remaining Integration Work

Day 4 is complete: the Inverted Index now has a public structural validator
and a public exact Forward Index consistency validator. Both use
descriptive `ValueError` failures, preserve existing state, and reject
malformed or inconsistent data.

Remaining integration work is intentionally separate and includes final
Lexicon coordination, any teammate-owned Forward Index implementation,
JSONL persistence and Barrels. This report does not claim that those
components have been implemented or integrated.
