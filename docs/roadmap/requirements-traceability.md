
# CodeAtlas — Requirements Traceability Matrix

## 1. Purpose

This document tracks the instructor's requirements and
connects them to CodeAtlas implementation phases.

It will be updated throughout development to verify
that every required feature is implemented and tested.

## 2. Functional Requirements

| ID | Requirement | Phase | Verification |
|---|---|---|---|
| FR-01 | Lexicon implementation | 3 | Term lookup tests |
| FR-02 | Forward Index | 3 | Document-term mapping tests |
| FR-03 | Inverted Index | 3 | Term-document mapping tests |
| FR-04 | File-based index storage | 3 | Inspect saved index files |
| FR-05 | Barrel partitioning | 4 | Partition retrieval tests |
| FR-06 | Single-word search | 5 | Search test cases |
| FR-07 | Multi-word search | 5 | Multi-term query tests |
| FR-08 | Relevance ranking | 5 | Ranking evaluation |
| FR-09 | Metadata-based ranking | 5 | Metadata contribution tests |
| FR-10 | Semantic search | 6 | Similarity evaluation |
| FR-11 | Trie autocomplete | 7 | Prefix lookup tests |
| FR-12 | 3–5 suggestions | 7 | Suggestion count tests |
| FR-13 | Dynamic document addition | 8 | Ingestion tests |
| FR-14 | JSON input | 8 | JSON ingestion tests |
| FR-15 | Plain-text input | 8 | Text ingestion tests |
| FR-16 | Manual document input | 8 | UI submission tests |
| FR-17 | Non-blocking index updates | 8 | Concurrent search tests |
| FR-18 | Professional frontend | 9 | UI and integration tests |

## 3. Performance Requirements

| ID | Requirement | Target | Verification |
|---|---|---|---|
| PR-01 | Single-word search | Under 500 ms | Latency measurement |
| PR-02 | Five-word search | Under 1.5 seconds | Latency measurement |
| PR-03 | Autocomplete | Under 100 ms | Latency measurement |
| PR-04 | New document indexing | Within 1 minute | Indexing benchmark |
| PR-05 | RAM below 100,000 documents | At most 2 GB | Memory profiling |
| PR-06 | RAM above 100,000 documents | At most 4 GB | Memory profiling |

## 4. Dataset Requirements

| ID | Requirement | Verification |
|---|---|---|
| DR-01 | At least 45,000 distinct documents | Count processed documents |
| DR-02 | Median document length at least 100 words | Calculate median |
| DR-03 | At least two metadata fields contribute to ranking | Inspect ranking implementation and test |

Phase 2 verification:
- DR-01: **Satisfied** - 50,083 distinct question documents were processed.
- DR-02: **Interpretation pending** - median title-plus-body tokenizer
  length is 130 tokens; median whitespace-separated word count is 124
  words. The whitespace-based result exceeds 100 under that explicit
  interpretation, but instructor confirmation of the intended counting
  rule is still required.
- DR-03: **Pending** - ranking is outside Phase 2 scope.

## 5. Development Requirements

| ID | Requirement | Verification |
|---|---|---|
| DEV-01 | Core algorithms implemented by the team | Code review |
| DEV-02 | Indexing structures stored in files | Inspect storage implementation |
| DEV-03 | GitHub version control | Review repository history |
| DEV-04 | Complete technical documentation | Documentation review |
| DEV-05 | Deployment | Verify public application |

## 6. Status Definitions

- Not Started: Work has not begun.
- In Progress: Implementation is underway.
- Implemented: Code has been written.
- Tested: Relevant tests have passed.
- Complete: Implementation, testing and documentation are complete.

## 7. Current Status

| Requirement Group | Status |
|---|---|
| Project foundation and repository | Complete |
| Backend environment and FastAPI | Complete |
| Initial Document model | Complete |
| Dataset processing | Complete |
| Core indexing structures | Complete; full-corpus build and cross-index verification passed |
| Search and ranking | Not Started |
| Semantic search | Not Started |
| Autocomplete | Not Started |
| Dynamic content addition | Not Started |
| Frontend | Not Started |
| Performance verification | Not Started |
| Deployment | Not Started |

Only requirements that have been implemented and
verified should be marked Complete.

## 8. Phase 3 Full-Dataset Verification

Measured results from the completed Phase 3 run:

| Measure | Result |
|---|---:|
| Documents | 50,083 |
| Unique Lexicon terms | 87,183 |
| Forward term entries | 4,232,033 |
| Inverted postings | 4,232,033 |
| Inverted construction | 19.2 seconds |
| Complete Inverted build and verification | 159.1 seconds |
| Inverted JSONL output | 218.84 MiB |
| Peak process working set | 1,007.5 MiB |
| Earlier combined indexing and preprocessing run | 200 passed in 11.81 seconds |
| Latest focused Lexicon/Forward/Inverted test run | 221 passed, 1 deselected |

These are measurements from one machine and run, not guarantees for other
environments. Exact Forward-to-Inverted consistency and the Inverted save/load
round trip passed. The focused run excluded the dataset-backed Lexicon
save/load test and did not include preprocessing tests. The earlier combined
test count refers to a separate run and scope.

Phase 3 stores field-specific term frequencies, not token positions. Positional
search is not implemented or claimed complete. Forward Index build/load retain
the complete structure in memory; no Forward-only peak RAM measurement was
recorded. The Inverted-run working set does not establish the general memory
targets listed above. These results also do not establish search latency.