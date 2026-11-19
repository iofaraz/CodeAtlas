
# CodeAtlas — System Architecture

## 1. Project Overview

CodeAtlas is a technical knowledge search engine developed
as a semester project for CS-250: Data Structures and
Algorithms at NUST.

The system uses Computer Science Stack Exchange data to
provide efficient keyword searching, semantic searching,
relevance-based ranking, autocomplete, and dynamic
document addition.

The core search and indexing algorithms will be implemented
by the project team using suitable data structures and
algorithms.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3 |
| Backend | FastAPI |
| Frontend | Next.js |
| Frontend Language | TypeScript |
| Styling | Tailwind CSS |
| XML Parsing | lxml |
| Text Processing | NLTK |
| Version Control | Git and GitHub |

## 3. High-Level Architecture

```text
             Stack Exchange XML
                      |
                      v
              Data Extraction
                      |
                      v
              HTML Cleaning
                      |
                      v
              Text Processing
                      |
                      v
             Document Collection
                      |
                      v
        +-------------+-------------+
        |             |             |
        v             v             v
     Lexicon      Forward Index   Metadata
        |             |
        |             v
        |        Inverted Index
        |             |
        |             v
        |           Barrels
        |             |
        +-------------+
                      |
                      v
               Query Processing
                      |
             +--------+--------+
             |                 |
             v                 v
       Keyword Search     Semantic Search
             |                 |
             +--------+--------+
                      |
                      v
                Result Ranking
                      |
                      v
                FastAPI Backend
                      |
                      v
             Next.js Frontend
                      |
                      v
                  User
```

## 4. Major System Components

### 4.1 Data Processing

Responsible for reading the original dataset, extracting
relevant records, cleaning HTML content, normalizing text,
and preparing searchable documents.

### 4.2 Document Collection

Stores the processed document records and their metadata.

Each document will contain a unique identifier, title,
body, tags, score, view count, creation date, and other
relevant fields where available.

### 4.3 Lexicon

Stores unique terms from the processed collection.
Each term receives a distinct numerical identifier.

### 4.4 Forward Index

Stores the terms associated with each document.
It serves as an input for inverted-index generation.

### 4.5 Inverted Index

Maps terms to the documents containing those terms.
It supports keyword-based document retrieval.

All indexing structures will be stored in files rather
than a database.

### 4.6 Barrels

Divide the inverted index into smaller partitions.
Only relevant partitions should be loaded during search
to improve memory efficiency.

### 4.7 Query Processing

Normalizes and tokenizes user queries, identifies terms
through the lexicon, and retrieves candidate documents.

### 4.8 Keyword Search

Supports single-word and multi-word searches. Multi-word
queries retrieve documents containing the query terms
even when those terms are not adjacent.

### 4.9 Semantic Search

Uses permitted word embeddings and custom similarity
logic to identify conceptually related documents.

### 4.10 Ranking

Ranks retrieved documents using textual relevance,
frequency, position, and suitable metadata.

### 4.11 Autocomplete

Uses a Trie-based prefix-matching structure and query
patterns to suggest 3–5 relevant completions.

### 4.12 Dynamic Content Addition

Supports adding documents through:
- JSON files following the dataset format
- Plain-text files
- Manual entry through the user interface

New documents must become searchable without blocking
ongoing search operations.

### 4.13 Backend

FastAPI exposes endpoints for searching, autocomplete,
health checks, and document addition.

### 4.14 Frontend

Next.js, TypeScript, and Tailwind CSS provide the
user-facing search interface and document submission
interface.

## 5. Data Storage Strategy

The project will use files for:
- Lexicon
- Forward index
- Inverted index
- Barrels
- Other generated index artifacts

The processed document collection and ordinary
application metadata will be handled separately.

No database will be used to store indexing data.

## 6. Performance Considerations

The system will be evaluated against the following targets:

- Single-word query: under 500 ms
- Five-word query: under 1.5 seconds
- Autocomplete: under 100 ms
- New document indexing: within 1 minute
- RAM consumption: within the instructor's specified limits

Index updates must not block search operations.

## 7. Architecture Status

This document describes the planned architecture.
Individual components will be updated as they are
implemented, tested, and integrated.
