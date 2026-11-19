
# CodeAtlas — Indexing Architecture

## 1. Introduction

The indexing system is responsible for organizing processed
documents so that search queries can retrieve relevant
information efficiently.

CodeAtlas will implement four major indexing components:

1. Lexicon
2. Forward Index
3. Inverted Index
4. Barrels

All core indexing structures will be implemented using
appropriate Data Structures and Algorithms and stored
in files rather than a database.

## 2. Indexing Pipeline

```text
       Processed Documents
               |
               v
          Tokenization
               |
               v
        Term Normalization
               |
               v
            Lexicon
               |
               v
         Forward Index
               |
               v
        Inverted Index
               |
               v
       Barrel Partitioning
               |
               v
          Index Files
```

## 3. Lexicon

### Purpose

The Lexicon maintains a collection of unique terms found
in the processed document collection.

Each unique term receives a numerical Term ID.

### Example

Suppose the processed documents contain:

Document 1:
"Python programming language"

Document 2:
"Python programming tutorial"

The Lexicon could look like:

| Term ID | Term |
|---|---|
| 1 | python |
| 2 | programming |
| 3 | language |
| 4 | tutorial |

### Responsibilities

- Store unique normalized terms.
- Assign unique Term IDs.
- Support efficient term lookup.
- Avoid duplicate term entries.
- Persist terms and IDs in files.

### Possible Data Structure

A Python dictionary can provide efficient in-memory
term-to-ID lookup during index construction.

The persistent representation will be file-based.

## 4. Forward Index

### Purpose

The Forward Index stores the terms associated with
each document.

It provides a document-to-terms relationship.

### Example

| Document ID | Terms |
|---|---|
| 1 | python, programming, language |
| 2 | python, programming, tutorial |

### Additional Information

The implementation may preserve:

- Term IDs
- Term frequencies
- Term positions
- Document length

Term positions can support proximity and positional
search features.

### Responsibilities

- Associate documents with their terms.
- Preserve information needed for retrieval and ranking.
- Support inverted-index construction.
- Persist document-term mappings in files.

## 5. Inverted Index

### Purpose

The Inverted Index maps each term to the documents
containing that term.

It is the primary structure used for keyword retrieval.

### Example

| Term | Document IDs |
|---|---|
| python | 1, 2 |
| programming | 1, 2 |
| language | 1 |
| tutorial | 2 |

### Posting Information

A posting may contain:

- Document ID
- Term frequency
- Term positions

Example:

```text
python:
    Document 1 -> frequency: 1
    Document 2 -> frequency: 1

programming:
    Document 1 -> frequency: 1
    Document 2 -> frequency: 1
```

### Responsibilities

- Map terms to their matching documents.
- Support efficient candidate retrieval.
- Provide posting information for ranking.
- Persist postings in files.

## 6. Barrels

### Purpose

Barrels divide the Inverted Index into smaller partitions.

Instead of loading the entire index for every query,
the search engine can identify and access relevant
partitions.

### Conceptual Example

```text
          Inverted Index
                |
       +--------+--------+
       |        |        |
       v        v        v
    Barrel 1 Barrel 2 Barrel 3
       |        |        |
       v        v        v
    Terms A  Terms B  Terms C
```

The exact partitioning strategy will be selected
during implementation.

### Responsibilities

- Partition the inverted index.
- Store partitions in separate files.
- Maintain barrel metadata.
- Identify relevant barrels for a query.
- Load only the required partitions.

## 7. Relationships Between Structures

| Structure | Relationship |
|---|---|
| Lexicon | Term to Term ID |
| Forward Index | Document to Terms |
| Inverted Index | Term to Documents |
| Barrels | Partitioned Inverted Index |

These structures work together to support efficient
document retrieval.

## 8. Example of Complete Index Construction

Input documents:

```text
Document 1: Python programming language
Document 2: Python programming tutorial
```

### Step 1 — Lexicon

```text
1 -> python
2 -> programming
3 -> language
4 -> tutorial
```

### Step 2 — Forward Index

```text
1 -> [1, 2, 3]
2 -> [1, 2, 4]
```

### Step 3 — Inverted Index

```text
1 -> [1, 2]
2 -> [1, 2]
3 -> [1]
4 -> [2]
```

### Step 4 — Barrels

The inverted index is divided into partitions
according to the selected barrel strategy.

## 9. File Storage Strategy

The indexing structures will be stored separately.

Planned directory:

```text
indexes/
├── lexicon/
│   └── lexicon.json
│
├── forward/
│   └── forward_index.json
│
├── inverted/
│   └── inverted_index.json
│
└── barrels/
    ├── barrel_001.json
    ├── barrel_002.json
    └── barrel_metadata.json
```

These are proposed filenames and formats. The final
serialization format will be chosen after considering
memory usage, file size and performance.

## 10. Search Integration

When a query is submitted:

1. Normalize the query.
2. Find Term IDs using the Lexicon.
3. Identify the relevant Barrels.
4. Retrieve matching postings.
5. Collect candidate document IDs.
6. Calculate relevance scores.
7. Return ranked documents.

## 11. Future Considerations

During implementation, we will evaluate:

- Efficient index serialization.
- Posting-list compression.
- Index partitioning strategy.
- Memory-efficient barrel loading.
- Incremental index updates.
- Concurrent search and index updates.

These optimizations will be introduced only when
they support the project requirements and can be
properly tested.

## 12. Documentation Status

This document describes the planned indexing architecture.

Actual data structures, file formats, partitioning
strategies and performance results will be documented
after implementation and testing.
