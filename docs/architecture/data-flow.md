
# CodeAtlas — Data Flow Architecture

## 1. Overview

This document explains how data moves through CodeAtlas,
from dataset extraction and preprocessing to indexing,
search processing, ranking and result presentation.

It also describes the flow for dynamically adding new
documents to the search engine.

## 2. Initial Dataset Flow

The initial dataset is obtained from Computer Science
Stack Exchange XML data dumps.

```text
Stack Exchange XML Files
          |
          v
     XML Parser
          |
          v
   Record Extraction
          |
          v
     HTML Cleaning
          |
          v
   Text Normalization
          |
          v
   Document Creation
          |
          v
  Dataset Validation
          |
          v
  Processed Documents
```

### Processing Steps

1. XML Parser reads the source files.
2. Record Extraction identifies relevant questions.
3. HTML Cleaning removes markup and extracts readable text.
4. Text Normalization prepares text for indexing.
5. Document Creation converts records into structured
   Document objects.
6. Dataset Validation checks document IDs, content,
   metadata and dataset requirements.
7. Processed Documents are saved for indexing.

## 3. Index Construction Flow

Processed documents are passed to the indexing system.

```text
  Processed Documents
          |
          v
     Tokenization
          |
          v
     Unique Terms
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
     Saved Index Files
```

### Indexing Steps

1. Tokenize document text.
2. Identify unique terms.
3. Assign term IDs through the Lexicon.
4. Build the Forward Index.
5. Generate the Inverted Index from document-term
   relationships.
6. Divide the Inverted Index into Barrels.
7. Save indexing structures in files.

## 4. Search Query Flow

When a user submits a search query, the following
process takes place.

```text
      User Query
          |
          v
   Query Normalization
          |
          v
      Tokenization
          |
          v
   Lexicon Lookup
          |
          v
   Barrel Selection
          |
          v
   Document Retrieval
          |
          v
   Ranking Algorithm
          |
          v
    Ranked Results
          |
          v
      FastAPI
          |
          v
    Next.js Frontend
          |
          v
        User
```

### Search Processing Steps

1. Receive the query from the frontend.
2. Normalize and tokenize the query.
3. Look up query terms in the Lexicon.
4. Identify relevant Barrels.
5. Retrieve candidate documents.
6. Calculate relevance scores.
7. Incorporate appropriate metadata signals.
8. Sort results by their final ranking scores.
9. Return results through the FastAPI backend.
10. Display results in the frontend.

## 5. Semantic Search Flow

Semantic search provides retrieval based on conceptual
similarity.

```text
      User Query
          |
          v
  Query Representation
          |
          v
  Embedding Generation
          |
          v
 Similarity Calculation
          |
          v
 Candidate Documents
          |
          v
  Semantic Ranking
          |
          v
   Search Results
```

The semantic retrieval implementation will use permitted
pretrained word embeddings and custom similarity logic.

Semantic results may be combined with keyword retrieval
during the ranking and integration phase.

## 6. Autocomplete Flow

```text
      User Input
          |
          v
    Prefix Extraction
          |
          v
       Trie Lookup
          |
          v
   Suggestion Generation
          |
          v
    Top 3–5 Suggestions
          |
          v
     Frontend Display
```

Autocomplete must meet the instructor's response-time
requirement of under 100 milliseconds.

## 7. Dynamic Document Addition Flow

New documents can enter the system through JSON files,
plain-text files or manual user submission.

```text
     New Document
           |
           v
    Input Validation
           |
           v
   Document Processing
           |
           v
    Unique ID Assignment
           |
           v
    Incremental Indexing
           |
           v
     Index Update
           |
           v
  Document Searchable
```

### Dynamic Update Considerations

- Existing search operations must continue during updates.
- Newly added documents must become searchable.
- Index files must remain consistent.
- New document indexing must complete within one minute.

The implementation strategy for safe concurrent updates
will be finalized during Phase 8.

## 8. Data Storage Flow

CodeAtlas uses files for its core indexing structures.

| Data | Storage |
|---|---|
| Original XML dataset | Raw data files |
| Processed documents | Processed data files |
| Lexicon | Index files |
| Forward Index | Index files |
| Inverted Index | Index files |
| Barrels | Index files |
| Ordinary application metadata | Separate storage strategy |

Indexing structures will not be stored in a database.

## 9. Final Output

The final system returns ranked technical knowledge
documents containing relevant information such as:

- Question title
- Question content or excerpt
- Tags
- Community score
- View count
- Creation date
- Original source reference

The frontend presents these results in a searchable
and user-friendly interface.

## 10. Documentation Status

This document describes the planned data flow.

Actual implementation details will be updated as the
individual modules are developed and tested.
