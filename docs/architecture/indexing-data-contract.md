# CodeAtlas Shared Indexing Data Contract

## Status

This document defines the proposed shared data contract for the Lexicon,
Forward Index, and Inverted Index. It is an integration specification, not a
claim that every component has already been implemented.

All indexing structures are JSONL-based at the shared serialization boundary.
Each JSONL file contains one complete record per line. Strings must be
UTF-8 encoded, and `null` is not used for IDs or frequency values.

Normalization for Lexicon terms is the responsibility of the preprocessing
pipeline. The indexing contract receives normalized terms and/or the term IDs
derived from them.

## 1. Lexicon Contract

The Lexicon provides two logical mappings:

- `term_to_id`: normalized term to positive integer term ID.
- `id_to_term`: positive integer term ID to normalized term.

The following rules are mandatory:

1. IDs start at `1`.
2. Term ID `0` is reserved and must never be assigned or stored in an index.
3. The complete unique vocabulary is the set of normalized terms found in
   document titles, bodies, and tags.
4. The complete normalized vocabulary must be collected before final term IDs
   are assigned.
5. Sort the complete collected vocabulary lexicographically before assigning
   IDs.
6. Assign IDs in ascending order beginning at `1`.
7. Freeze the resulting `term_to_id` and `id_to_term` mappings before building
   the Forward and Inverted Indexes.
8. Existing term IDs must not silently change when new documents or terms are
   introduced.
9. Future dynamic indexing must use an explicitly versioned Lexicon or another
   controlled term-ID allocation strategy. No specific dynamic-allocation
   behavior is implemented or prescribed as an existing feature.
10. A term has exactly one ID in `term_to_id` and exactly one corresponding
   term in `id_to_term`.
11. The Lexicon also records document frequency (DF) for each term ID: the
   number of distinct documents containing the term in any field.

The Lexicon JSONL representation is one record per term, sorted by
`term_id`:

```json
{"term_id": 1, "term": "binary", "df": 1}
```

Lexicon JSONL fields are:

- `term_id`: positive integer.
- `term`: normalized vocabulary term.
- `df`: non-negative integer document frequency.

Lexicon records must include terms whose DF is greater than zero. Because the
complete vocabulary is derived from the corpus, an implementer should not
create an unrelated record with a zero DF.

## 2. Forward Index Contract

The Forward Index records the document-to-term relationship. It contains one
JSONL record per document, sorted by ascending `doc_id`:

```json
{
  "doc_id": 101,
  "terms": [
    {
      "term_id": 1,
      "title_tf": 0,
      "body_tf": 1,
      "tag_tf": 0
    }
  ]
}
```

Forward Index rules:

1. One record exists for each indexed document.
2. `doc_id` is a positive integer.
3. `terms` is sorted by ascending `term_id`.
4. Each term ID appears at most once in a document's `terms` array.
5. Every `term_id` is a positive integer that exists in the Lexicon.
6. `title_tf`, `body_tf`, and `tag_tf` are non-negative integers.
7. Count repeated occurrences separately in the title, body, and tags.
8. Include only terms for which at least one of the three TF fields is
   non-zero.
9. Forward and Inverted Index term frequencies must use the same field
   names and meanings:
   - `title_tf`: occurrences in the normalized document title.
   - `body_tf`: occurrences in the normalized document body.
   - `tag_tf`: occurrences in normalized document tags.

The complete term array may be represented on one JSONL line or formatted
across multiple lines in source; the serialized JSONL file must contain exactly
one JSON object per line. The compact worked examples in this document are
shown with readable line breaks.

## 3. Inverted Index Contract

The Inverted Index records the term-to-document relationship. It contains one
JSONL record per posting term, sorted by ascending `term_id`:

```json
{
  "term_id": 1,
  "df": 1,
  "postings": [
    {
      "doc_id": 101,
      "title_tf": 0,
      "body_tf": 1,
      "tag_tf": 0
    }
  ]
}
```

Inverted Index rules:

1. Store one record for each term that has at least one posting.
2. `term_id` is a positive integer that exists in the Lexicon.
3. `df` is the number of posting objects in `postings`.
4. `postings` is sorted by ascending `doc_id`.
5. Each term/document pair has exactly one posting.
6. `doc_id` is a positive integer.
7. `title_tf`, `body_tf`, and `tag_tf` are non-negative integers.
8. Every TF value must exactly match the corresponding Forward Index record.
9. Terms with no postings must not be stored.

## 4. Shared Consistency Invariants

Every producer and consumer must enforce the following mandatory checks:

1. Every term ID in a Forward Index record or Inverted Index record must exist
   in the Lexicon.
2. Lexicon DF equals the Inverted Index `df` for the same term ID.
3. The Inverted Index is the exact reverse organization of Forward Index term
   records:
   - A Forward record for document `D` and term `T` produces exactly one
     posting for term `T` and document `D`.
   - There are no posting pairs absent from the Forward Index.
   - There are no Forward term records absent from the Inverted Index.
4. For every term/document pair, the sum
   `title_tf + body_tf + tag_tf` matches in both indexes.
5. A document contributes at most one to a term's DF, regardless of repeated
   occurrences or the number of fields containing the term.
6. Document IDs and term IDs must be positive integers.
7. JSONL records must be deterministic and sorted:
   - Lexicon records: ascending `term_id`.
   - Forward records: ascending `doc_id`.
   - Forward `terms` arrays: ascending `term_id`.
   - Inverted records: ascending `term_id`.
   - Inverted `postings` arrays: ascending `doc_id`.

Validation should compare complete posting TF values, not only the sum of TF
values. For example, `title_tf=1, body_tf=0, tag_tf=0` must not be replaced
by an equal sum that does not preserve which field contains the occurrence.

## 5. Integration Responsibilities

The modules have distinct responsibilities:

- The Lexicon assigns term IDs by vocabulary-wide lexicographic sorting and
  resolves both normalized-term-to-ID and ID-to-normalized-term lookups.
- The Forward Index organizes term frequencies by document. It is responsible
  for the document-level TF mapping and document-sorted output.
- The Inverted Index organizes the same information by term. It builds
  posting lists, sorts them by document ID, and derives DF from the number of
  postings.
- The Inverted Index should consume Forward Index records or an equivalent
  per-document term-frequency mapping containing resolved term IDs and field
  TF values.
- The Forward Index JSONL record is not directly accepted by the current
  `InvertedIndex` API. That API's `add_document()` method accepts a
  `term_frequencies` mapping keyed by integer term IDs, with the shape:
  `{1: {"title_tf": 0, "body_tf": 1, "tag_tf": 0}}`.
- A dedicated adapter or ingestion method is required to convert a Forward
  Index record into this expected mapping. The adapter should read the
  record's `doc_id` and create the integer-keyed TF mapping from its `terms`
  array. Such an adapter does not yet exist.
- The Inverted Index must not independently tokenize documents or assign term
  IDs. ID assignment is delegated to the Lexicon, and source-text processing is
  delegated to preprocessing and/or the Forward Index builder.

An integration implementation should therefore provide:

1. A finalized Lexicon mapping for the complete corpus.
2. Forward Index records containing only resolved positive term IDs.
3. One pass over the Forward records to generate Inverted Index postings.
4. A consistency validation pass before publishing the final JSONL files.

## 6. Worked Example

Consider one document:

- `doc_id`: `101`
- Title tokens: `["data", "structure", "tree"]`
- Body tokens: `["tree", "binary", "tree"]`
- Tag tokens: `["tree"]`

The normalized and unique vocabulary from this document is:

```text
binary, data, structure, tree
```

Lexicographically sorted IDs are:

| term | term_id |
|---|---:|
| binary | 1 |
| data | 2 |
| structure | 3 |
| tree | 4 |

The Lexicon JSONL records are:

```json
{"term_id": 1, "term": "binary", "df": 1}
{"term_id": 2, "term": "data", "df": 1}
{"term_id": 3, "term": "structure", "df": 1}
{"term_id": 4, "term": "tree", "df": 1}
```

The Forward Index record is:

```json
{
  "doc_id": 101,
  "terms": [
    {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
    {"term_id": 2, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
    {"term_id": 3, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
    {"term_id": 4, "title_tf": 1, "body_tf": 2, "tag_tf": 1}
  ]
}
```

The Inverted Index JSONL records are:

```json
{"term_id": 1, "df": 1, "postings": [{"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0}]}
{"term_id": 2, "df": 1, "postings": [{"doc_id": 101, "title_tf": 1, "body_tf": 0, "tag_tf": 0}]}
{"term_id": 3, "df": 1, "postings": [{"doc_id": 101, "title_tf": 1, "body_tf": 0, "tag_tf": 0}]}
{"term_id": 4, "df": 1, "postings": [{"doc_id": 101, "title_tf": 1, "body_tf": 2, "tag_tf": 1}]}
```

For this example, one document contains every term, so each Lexicon DF and
Inverted Index `df` is `1`. In `tree`, repeated body occurrences are counted
separately, producing `body_tf=2`, and the title/tag occurrences remain
separate as `title_tf=1` and `tag_tf=1`.
