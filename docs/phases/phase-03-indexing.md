# CodeAtlas - Phase 3 Indexing

## 1. Phase Overview

Phase 3 implements the three core file-based indexing structures used for
keyword search: a Lexicon, a Forward Index, and an Inverted Index. The
implementations operate on preprocessed documents produced in Phase 2 and
exchange positive integer term IDs without storing a database. The current
structures preserve field-specific term frequencies; they do not store token
positions.

## 2. Objectives

- Build one deterministic term ID mapping for the complete normalized vocabulary.
- Preserve document-level title, body, and tag term frequencies.
- Produce the reverse term-to-document posting organization.
- Serialize all structures as deterministic JSONL.
- Validate each structure and cross-index consistency.
- Provide executable repository-root build scripts.

## 3. Scope

Implemented in this phase are:

- `Lexicon`
- `ForwardIndex`
- `InvertedIndex`
- Lexicon, Forward, and Inverted JSONL formats
- Cross-index validation
- Unit tests
- Separate build scripts for each structure

This phase does not implement barrels, ranking, search queries, dynamic
indexing, or index partitioning.

## 4. Indexing Architecture

The preprocessing pipeline writes normalized token lists to
`data/processed/documents.jsonl`. Construction then follows this dependency
chain:

1. `Lexicon.build()` collects the complete vocabulary and assigns IDs.
2. `ForwardIndex.build(documents, lexicon)` maps document IDs to term IDs and
   field frequencies.
3. `InvertedIndex.build_from_forward_records()` transposes Forward records
   into term-to-document postings.
4. Lexicon, Forward, and Inverted validations verify their shared invariants.

The classes and primary files are:

- Lexicon: `backend/search_engine/indexing/lexicon.py`
- Forward Index: `backend/search_engine/indexing/forward_index.py`
- Inverted Index: `backend/search_engine/indexing/inverted_index.py`
- Shared contract: `docs/architecture/indexing-data-contract.md`

## 5. Shared Data Contract

Term and document IDs are positive integers. Zero is reserved for an invalid or
unassigned term ID. JSONL strings use UTF-8 and the term-frequency fields are
named `title_tf`, `body_tf`, and `tag_tf`.

Ordering rules:

- Lexicon: ascending `term_id`
- Forward: ascending `doc_id`
- Each Forward document's terms: ascending `term_id`
- Inverted: ascending `term_id`
- Each posting list: ascending `doc_id`

## 6. Lexicon Implementation

`Lexicon.build(documents)` reads `title_tokens`, `body_tokens`, and
`tag_tokens`. For each document it creates a set of normalized terms, so a term
occurring repeatedly or in multiple fields contributes once to that document's
document frequency.

The `_normalize_term()` helper requires a string, strips surrounding whitespace,
and converts it to lowercase. The complete set of normalized terms is sorted
lexicographically and IDs are assigned starting at 1. This makes term-ID
assignment deterministic for a fixed complete vocabulary.

Public methods include:

- `Lexicon.build(documents)`
- `Lexicon.validate()`
- `Lexicon.get_term_id(term)`
- `Lexicon.get_term(term_id)`
- `Lexicon.get_document_frequency(term_id)`
- `Lexicon.save(output_dir)`
- `Lexicon.load(input_dir)`

Serialization and loading preserve both bidirectional mappings and DF values.
Loading rejects duplicate terms, duplicate IDs, invalid IDs or DF values,
malformed JSON, missing fields, and extra record fields.

## 7. Forward Index Implementation

`ForwardIndex.build(documents, lexicon)` creates one record for every unique
positive `doc_id`, including documents with no terms. It counts repeated
tokens separately for each field, merges the counts for a term that appears in
more than one field, and stores the term as the Lexicon-provided term ID.

Public methods include:

- `ForwardIndex.build(documents, lexicon)`
- `ForwardIndex.validate(lexicon)`
- `ForwardIndex.verify_document_frequencies(lexicon)`
- `ForwardIndex.doc_ids()`
- `ForwardIndex.get_document_terms(doc_id)`
- `ForwardIndex.iter_documents()`
- `ForwardIndex.save(output_dir)`
- `ForwardIndex.load(input_dir, lexicon)`

`ForwardIndex` has no term-tokenization or term-ID assignment logic. Its
`TermEntry` named tuple contains `term_id`, `title_tf`, `body_tf`, and
`tag_tf`. In memory each document uses a compact unsigned integer array,
sorted by term ID. Both `ForwardIndex.build()` and `ForwardIndex.load()`
materialize the complete Forward Index in the `_records` mapping. Reading the
input as an iterable or line by line does not make the resulting index
out-of-core; memory use grows with the indexed documents and term entries.
No Forward-only peak-memory measurement is recorded here.

## 8. Inverted Index Implementation

`InvertedIndex` maps term IDs to sorted postings. It supports:

- `add_posting`
- `add_document`
- `add_forward_record`
- `build_from_forward_records`
- `validate`
- `validate_against_forward_records`
- `validate_against_lexicon`
- `save`
- `load`
- `get_postings`
- `get_document_frequency`
- `get_index`

`build_from_forward_records(records)` stages all work in a new index and only
replaces the current index after every record validates. `add_document` also
checks for conflicts before mutating existing postings. The index does not
tokenize text or assign IDs. Its postings store field-specific TF values, not
token positions.

## 9. Index Construction Workflow

The required build order is:

```powershell
python scripts/build_lexicon.py
python scripts/build_forward_index.py
python scripts/build_inverted_index.py
```

Alternative locations can be supplied to the Lexicon and Forward scripts with
their `--root` and `--documents` options. The Inverted script accepts
`--forward-index`.

The Lexicon must be complete before Forward construction starts. The Forward
Index must be complete before Inverted construction starts. No build script
assigns fallback term IDs independently.

## 10. JSONL Storage Formats

Lexicon JSONL:

```json
{"term_id": 1, "term": "binary", "df": 1}
{"term_id": 2, "term": "data", "df": 2}
```

Forward JSONL:

```json
{"doc_id":101,"terms":[{"term_id":1,"title_tf":0,"body_tf":1,"tag_tf":0},{"term_id":2,"title_tf":1,"body_tf":2,"tag_tf":1}]}
```

Inverted JSONL:

```json
{"term_id":1,"df":1,"postings":[{"doc_id":101,"title_tf":0,"body_tf":1,"tag_tf":0}]}
{"term_id":2,"df":2,"postings":[{"doc_id":101,"title_tf":1,"body_tf":2,"tag_tf":1},{"doc_id":205,"title_tf":0,"body_tf":1,"tag_tf":0}]}
```

Locations:

- `indexes/lexicon/lexicon.jsonl`
- `indexes/forward/forward_index.jsonl`
- `indexes/inverted/inverted_index.jsonl`

## 11. Data Validation and Cross-Index Invariants

Verified rules include:

- Every term ID is positive; ID 0 is never serialized.
- Lexicon mappings are bidirectional and one-to-one.
- Lexicon IDs are contiguous and assigned by lexicographic normalized-term
  order.
- Lexicon DF counts distinct documents.
- Forward document IDs are positive and unique.
- Forward term IDs exist in the Lexicon and are unique and sorted per document.
- Forward TF values are non-negative integers and never all zero.
- Inverted posting IDs exist in the Lexicon and are sorted by document ID.
- Inverted DF is exactly the number of posting objects.
- Each Forward term record produces exactly one matching Inverted posting.
- Every posting and Forward TF field matches exactly.
- Save operations write temporary files and replace the final file atomically.

## 12. Build Scripts and Execution Instructions

From the repository root:

```powershell
python scripts/build_lexicon.py
python scripts/build_forward_index.py
python scripts/build_inverted_index.py
```

The scripts verify input existence and report missing files or malformed
records with file and line context where JSON parsing is streamed. Forward and
Inverted scripts require the prior structures. Existing valid index files are
not replaced when construction or validation fails.

## 13. Testing Strategy

The indexing tests cover:

- Lexicon normalization and ID ordering, duplicate document IDs, DF across
  repeated and cross-field terms, empty input, malformed tokens, and loader
  rejection cases for JSON, fields, values, normalization, and ordering.
- Forward field TF counts, document and term ordering, duplicate IDs, unknown
  terms, save/load, and malformed JSONL cases including extra fields.
- Inverted insertion and duplicate behavior, bulk-build atomicity,
  Forward-record conversion, structural/cross-index validation, and JSONL
  rejection cases including extra fields and unsorted records.
- Invalid boolean, non-integer, zero, and negative IDs or frequencies where
  applicable.

The Lexicon save/load round trip is covered by the dataset-backed
`test_build_and_save_full_documents_jsonl` test. That test is skipped when the
processed dataset is absent and was deliberately excluded from the latest
focused indexing test run; there is no separate synthetic Lexicon round-trip
test.

## 14. Test Results

An earlier combined indexing and preprocessing run passed:

```text
python -m pytest tests\test_indexing tests\test_preprocessing --basetemp <unique-workspace-temp-dir> -q
```

Result:

```text
200 passed in 11.81s
```

The latest focused indexing run covered the Lexicon, Forward Index, and
Inverted Index test modules, excluding the dataset-backed Lexicon test:

```text
python -m pytest tests\test_indexing\test_lexicon.py tests\test_indexing\test_forward_index.py tests\test_indexing\test_inverted_index.py -k "not test_build_and_save_full_documents_jsonl" --basetemp <unique-workspace-temp-dir> -q
```

Result: `221 passed, 1 deselected in 1.83s`. This count does not include the
preprocessing tests or a fresh full-dataset Lexicon round trip.

The default pytest temporary directory was inaccessible in one attempt
(`PermissionError` under the user's system temp directory). Using a unique
workspace temporary directory resolved the environment issue; no test failures
remained.

## 15. Dataset and Indexing Statistics

The completed full-dataset run processed 50,083 documents. The following are
measured results from this machine and run:

- Lexicon vocabulary: 87,183 unique terms
- Lexicon file: `indexes/lexicon/lexicon.jsonl`
- Forward document count: 50,083
- Forward term entries: 4,232,033
- Inverted term count: 87,183
- Inverted postings: 4,232,033
- Inverted construction time: 19.2 seconds
- Inverted build, full validation, save, and reload time: 159.1 seconds
- Inverted output size: 229,470,486 bytes (218.84 MiB)
- Peak process working set during the Inverted run: 1,007.5 MiB
- Earlier combined indexing and preprocessing run: 200 passed in 11.81 seconds
- Latest focused indexing run: 221 passed, 1 deselected (full-dataset Lexicon test)

The Inverted validation confirmed exact Forward-to-Inverted consistency,
including document-term pairs and separate `title_tf`, `body_tf`, and `tag_tf`
values. It also checked Lexicon term IDs and document frequencies. The staged
JSONL was loaded into a fresh Inverted Index and compared with the built
structure before atomic promotion.

## 16. Performance and Memory Considerations

The timings and working-set value above are measured observations from one
machine and one run; they are not performance guarantees for other machines or
datasets. The 1,007.5 MiB figure is the process high-water measurement during
the Inverted build and verification run. It is not a Forward-only memory
measurement and does not establish a RAM limit for Forward Index construction
or loading.

The Forward Index build and load paths retain all records in memory. The
compact integer arrays reduce per-entry overhead, but the structure is not
out-of-core and may constrain larger datasets. Assessing it against the
project's RAM targets requires a separate measurement; none is claimed here.

Theoretical expectation for sorted Forward records: bulk construction appends
postings in document order, so construction work grows linearly with the
number of documents and term entries, O(D + P), where D is the document count
and P is the number of document-term entries. This complexity expectation is
not a performance measurement. Validation and serialization add further
linear passes over the corpus/index.

## 17. Design Decisions

- Lexicographic term IDs make mappings reproducible.
- Field TFs remain separate instead of being merged, preserving ranking
  evidence.
- JSONL keeps the on-disk contract independent of a database.
- Atomic temporary-file replacement prevents partial save results.
- Forward-to-Inverted construction is used rather than independent retokenization.
- Posting DF is derived from posting count.

## 18. Known Limitations

- Dynamic term-ID allocation is not implemented.
- There is no barrel partitioning yet.
- Token positions are not stored. Phrase or proximity search would require a
  future positional-index design and is not part of the current Phase 3
  implementation.
- Forward Index construction and loading retain the complete index in memory;
  no Forward-specific peak RAM result has been measured.
- Generated full-corpus index files are local build outputs. Ignore rules
  exclude generated files while preserving `.gitkeep`. The previously tracked
  Lexicon JSONL has been removed from the Git index while its local file is
  preserved; that untracking takes effect in the next commit.
- The observed resource measurements apply only to the recorded machine and
  run.
- The Lexicon contract freezes IDs for the complete corpus; adding terms needs
  a controlled version or rebuild strategy.

## 19. Requirements Traceability

| ID | Requirement | Evidence |
|---|---|---|
| FR-01 | Lexicon | `Lexicon` implementation and tests |
| FR-02 | Forward Index | `ForwardIndex` implementation and tests |
| FR-03 | Inverted Index | `InvertedIndex` implementation and tests |
| FR-04 | File-based index storage | Lexicon and Forward save/load; Inverted JSONL save/load |
| DEV-01 | Team implementation | Source modules and build scripts |
| DEV-02 | Index files, not databases | JSONL files under `indexes/` |

Barrels, search, ranking, semantic search, autocomplete, dynamic updates,
performance verification, and deployment remain later-phase requirements.

## 20. Phase Outcome

Phase 3 source implementations, tests, shared JSONL formats, build scripts, and
full-corpus Lexicon, Forward, and Inverted builds have been verified. The
Inverted Index passed structural, Lexicon, and exact Forward consistency
validation, and its JSONL save/load round trip matched the built data. The
latest focused indexing run passed 221 tests with the dataset-backed Lexicon
round-trip test deselected. Token positions are not part of the current
Phase 3 contract.
