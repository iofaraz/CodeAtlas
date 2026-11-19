
# CodeAtlas — Project Roadmap

## 1. Project Overview

**Project Title:** Design and Implementation of a Scalable
Search Engine for Stack Exchange Knowledge

**Project Name:** CodeAtlas

**Tagline:** Navigate the World of Technical Knowledge

**Course:** CS-250 — Data Structures and Algorithms

**University:** NUST

**Class:** BESE-2025

**Semester:** Fall 2026

## 2. Project Goal

The goal of CodeAtlas is to develop a technical knowledge
search engine using Data Structures and Algorithms.

The system will process Stack Exchange data and provide:

- Efficient keyword-based searching.
- Relevance-based result ranking.
- Semantic search.
- Trie-based autocomplete.
- File-based indexing and barrel partitioning.
- Dynamic document addition.
- A professional web interface.

The core search and indexing algorithms will be implemented
by the project team.

## 3. Official Submission Milestones

| Milestone | Deadline | Expected Deliverable |
|---|---|---|
| Project Proposal | 15 November 2026 | Proposal document |
| Core Indexing | 29 November 2026 | Lexicon, Forward Index and Inverted Index |
| Barrels | 6 December 2026 | Barrel implementation |
| Complete Project | 16 December 2026 | Complete source code and documentation |
| Presentation and Viva | 18 December 2026 | Demonstration and explanation |

## 4. Development Phases

### Phase 1 — Project Foundation

**Objective:** Establish the development environment,
repository structure and initial backend.

**Tasks:**
- Create the GitHub repository.
- Establish the project directory structure.
- Configure Git and .gitignore.
- Set up the Python virtual environment.
- Install backend dependencies.
- Initialize the FastAPI application.
- Define the Document data model.
- Establish architecture and roadmap documentation.

**Deliverables:**
- Organized repository.
- Working Python environment.
- Running FastAPI application.
- Initial Document model.
- Architecture documentation.

**Completion Criteria:**
- Backend starts successfully.
- Health-check endpoint works.
- Document objects can be created and tested.

### Phase 2 — Dataset Processing and Preprocessing

**Objective:** Convert the original Stack Exchange XML
dataset into clean, structured searchable documents.

**Tasks:**
- Read Posts.xml using lxml.
- Identify question records.
- Extract document IDs and titles.
- Extract and clean question bodies.
- Remove HTML markup while preserving useful text.
- Extract and normalize tags.
- Extract available metadata.
- Tokenize and normalize text.
- Handle punctuation and stop words where appropriate.
- Validate processed documents.
- Save processed data in suitable files.

**Deliverables:**
- XML parser.
- HTML cleaning module.
- Text normalization pipeline.
- Processed document collection.
- Dataset validation report.

**Completion Criteria:**
- Documents are extracted correctly.
- Invalid and incomplete records are handled.
- Document IDs remain unique.
- Dataset size and document-length requirements
  are rechecked after preprocessing.

### Phase 3 — Core Indexing Structures

**Objective:** Implement the three foundational indexing
structures required by the project.

**Tasks:**

#### 3.1 Lexicon
- Extract unique terms.
- Assign each term a unique term ID.
- Support efficient term lookup.
- Store the lexicon in files.

#### 3.2 Forward Index
- Map each document to its terms.
- Preserve term frequencies and positions where required.
- Store the forward index in files.

#### 3.3 Inverted Index
- Map terms to documents containing those terms.
- Store posting information.
- Support efficient document retrieval.
- Store the inverted index in files.

**Deliverables:**
- Lexicon implementation.
- Forward index implementation.
- Inverted index implementation.
- Index serialization and loading.
- Unit tests and sample index files.

**Completion Criteria:**
- All three structures work correctly.
- Term-to-document relationships are accurate.
- Indexes can be saved and loaded.
- Indexing data is not stored in a database.

**Official Milestone:** 29 November 2026.

### Phase 4 — Index Partitioning Using Barrels

**Objective:** Divide the inverted index into smaller
partitions to improve index access and memory efficiency.

**Tasks:**
- Design a barrel partitioning strategy.
- Divide the inverted index into barrels.
- Store barrels in separate files.
- Implement barrel metadata.
- Identify relevant barrels for queries.
- Load only the required index partitions.
- Test retrieval across multiple barrels.

**Deliverables:**
- Barrel generation module.
- Barrel file structure.
- Barrel loading and selection logic.
- Retrieval tests.

**Completion Criteria:**
- Documents are partitioned correctly.
- Queries retrieve results across relevant barrels.
- Unnecessary barrels are not loaded.

**Official Milestone:** 6 December 2026.

### Phase 5 — Keyword Search and Result Ranking

**Objective:** Implement query processing, document
retrieval and relevance-based ranking.

**Tasks:**
- Normalize and tokenize user queries.
- Look up query terms in the lexicon.
- Retrieve matching documents from the inverted index.
- Support single-word searches.
- Support multi-word searches.
- Retrieve documents containing query terms even
  when those terms are not adjacent.
- Calculate term frequency and inverse document frequency.
- Consider document length and query coverage.
- Incorporate title and tag matches.
- Incorporate relevant metadata such as score,
  view count and creation date.
- Rank results by relevance.

**Deliverables:**
- Query processor.
- Keyword retrieval module.
- Ranking algorithm.
- Search tests and relevance evaluation.

**Completion Criteria:**
- Single-word and multi-word queries work.
- Results are ranked consistently.
- Metadata contributes to ranking.
- Popularity does not overwhelm textual relevance.

### Phase 6 — Semantic Search

**Objective:** Retrieve documents based on conceptual
similarity, not only exact keyword matches.

**Tasks:**
- Evaluate permitted pretrained embeddings.
- Select a suitable Word2Vec, GloVe or FastText model.
- Implement embedding-based text representation.
- Implement similarity calculations.
- Generate semantic candidate documents.
- Integrate semantic retrieval with search results.
- Evaluate results using representative queries.

**Deliverables:**
- Embedding integration.
- Semantic similarity module.
- Semantic retrieval functionality.
- Evaluation report.

**Completion Criteria:**
- Conceptually related documents can be retrieved.
- Semantic search is implemented by the team.
- No prohibited LLM or transformer embeddings are used.

### Phase 7 — Trie-Based Autocomplete

**Objective:** Provide fast query suggestions while users
enter search terms.

**Tasks:**
- Implement a Trie data structure.
- Insert relevant terms into the Trie.
- Support prefix-based lookup.
- Generate 3–5 suggestions.
- Optimize suggestion retrieval.
- Connect autocomplete to the backend API.

**Deliverables:**
- Trie implementation.
- Suggestion generation module.
- Autocomplete API endpoint.
- Performance tests.

**Completion Criteria:**
- Suggestions are relevant to the entered prefix.
- Autocomplete responds within 100 ms.

### Phase 8 — Dynamic Content Addition

**Objective:** Allow new documents to be added without
rebuilding the entire search engine.

**Tasks:**
- Support JSON document input.
- Support plain-text document input.
- Support manual document entry.
- Validate new documents.
- Assign unique document IDs.
- Process newly added content.
- Update indexing structures.
- Handle index updates without blocking searches.
- Verify that newly added documents are searchable.

**Deliverables:**
- Document ingestion module.
- Validation logic.
- Incremental indexing functionality.
- Dynamic update tests.

**Completion Criteria:**
- New documents can be added successfully.
- Newly added documents become searchable.
- Index updates do not block ongoing searches.
- Indexing a new document completes within one minute.

### Phase 9 — Frontend Development and Integration

**Objective:** Build a professional user interface and
connect it to the search engine backend.

**Tasks:**
- Set up Next.js and TypeScript.
- Configure Tailwind CSS.
- Design the main search page.
- Implement the search input.
- Display ranked search results.
- Add autocomplete suggestions.
- Provide semantic search functionality.
- Create a document submission interface.
- Display document metadata.
- Integrate frontend components with FastAPI.
- Handle loading states and errors.

**Deliverables:**
- Responsive web interface.
- Search results interface.
- Autocomplete interface.
- Document submission interface.
- Frontend-backend integration.

**Completion Criteria:**
- Users can search through the interface.
- Results are displayed correctly.
- Autocomplete works.
- Dynamic document submission works.

### Phase 10 — Testing and Performance Optimization

**Objective:** Verify correctness, reliability and
performance against the instructor's requirements.

**Tasks:**
- Unit testing of individual modules.
- Integration testing.
- Search correctness testing.
- Ranking evaluation.
- Autocomplete latency testing.
- Dynamic indexing testing.
- Memory consumption measurement.
- Search response-time measurement.
- Identify bottlenecks.
- Optimize data structures and algorithms.

**Performance Targets:**

| Operation | Required Target |
|---|---|
| Single-word query | Under 500 ms |
| Five-word query | Under 1.5 seconds |
| Autocomplete | Under 100 ms |
| New document indexing | Within 1 minute |
| RAM below 100,000 documents | At most 2 GB |
| RAM above 100,000 documents | At most 4 GB |

**Deliverables:**
- Unit and integration test suites.
- Performance measurement results.
- Optimization report.
- Final test report.

**Completion Criteria:**
- Functional requirements pass testing.
- Performance targets are measured and evaluated.
- Known limitations are documented.

### Phase 11 — Deployment and Final Submission

**Objective:** Prepare the complete project for
demonstration, evaluation and final submission.

**Tasks:**
- Prepare production configuration.
- Deploy backend and frontend.
- Configure required environment variables.
- Verify deployed functionality.
- Update README.md.
- Complete technical documentation.
- Prepare final project report.
- Prepare presentation slides.
- Prepare demonstration scenarios.
- Review GitHub repository and commit history.

**Deliverables:**
- Deployed CodeAtlas application.
- Complete source code.
- Final technical documentation.
- Final project report.
- Presentation slides.
- Demonstration-ready application.

**Completion Criteria:**
- Application works in the deployment environment.
- Repository contains the required source code.
- Documentation reflects actual implementation.
- Demonstration scenarios are tested.

## 5. Requirements Traceability

| Instructor Requirement | Responsible Phase |
|---|---|
| Lexicon | Phase 3 |
| Forward Index | Phase 3 |
| Inverted Index | Phase 3 |
| File-based index storage | Phase 3 |
| Barrels | Phase 4 |
| Single-word search | Phase 5 |
| Multi-word search | Phase 5 |
| Relevance-based ranking | Phase 5 |
| Metadata-based ranking | Phase 5 |
| Semantic search | Phase 6 |
| Trie-based autocomplete | Phase 7 |
| 3–5 autocomplete suggestions | Phase 7 |
| Autocomplete under 100 ms | Phase 7, Phase 10 |
| Dynamic document addition | Phase 8 |
| JSON document input | Phase 8 |
| Plain-text document input | Phase 8 |
| Manual document input | Phase 8 |
| Non-blocking index updates | Phase 8 |
| New document indexing within 1 minute | Phase 8, Phase 10 |
| Professional user interface | Phase 9 |
| Search performance targets | Phase 10 |
| Memory consumption limits | Phase 10 |
| Deployment | Phase 11 |
| GitHub collaboration | All phases |

## 6. Development and Documentation Policy

Each phase will have its own documentation file.

A phase will only be marked complete after:
1. Implementation is finished.
2. Relevant tests are performed.
3. Expected behavior is verified.
4. Actual results are recorded.
5. Known limitations are documented.

Planned functionality must not be described as completed
functionality.

## 7. Current Project Status

| Phase | Status |
|---|---|
| Phase 1 — Foundation | In Progress |
| Phase 2 — Preprocessing | Not Started |
| Phase 3 — Core Indexing | Not Started |
| Phase 4 — Barrels | Not Started |
| Phase 5 — Search and Ranking | Not Started |
| Phase 6 — Semantic Search | Not Started |
| Phase 7 — Autocomplete | Not Started |
| Phase 8 — Dynamic Content | Not Started |
| Phase 9 — Frontend | Not Started |
| Phase 10 — Testing | Not Started |
| Phase 11 — Deployment | Not Started |

## 8. Final Objective

The final objective is to deliver CodeAtlas as a working,
efficient and documented technical knowledge search engine
that demonstrates the practical application of Data
Structures and Algorithms.
