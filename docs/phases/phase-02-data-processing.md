# Phase 2 - Dataset Processing and Preprocessing

## A. Phase Overview

**Phase name:** Dataset Processing and Preprocessing

**Purpose:** Convert the Stack Exchange `Posts.xml` dump into clean,
structured question documents suitable for later indexing.

**Scope:** Read question records (`PostTypeId = 1`), clean HTML, normalize
text, tokenize title and body, preserve metadata and tags, write JSONL,
and report dataset statistics. Answers and other post types are not
combined into searchable documents.

## B. Files Created

- `backend/search_engine/preprocessing/__init__.py` - package marker.
- `backend/search_engine/preprocessing/html_cleaner.py` - HTML removal,
  entity decoding, code-text preservation and whitespace normalization.
- `backend/search_engine/preprocessing/normalizer.py` - Unicode and
  whitespace normalization with lowercase conversion.
- `backend/search_engine/preprocessing/tokenizer.py` - dependency-free
  reproducible tokenization that preserves practical technical forms.
- `backend/search_engine/preprocessing/xml_parser.py` - streaming
  `lxml.etree.iterparse` row extraction.
- `backend/search_engine/preprocessing/pipeline.py` - question processing,
  JSONL serialization, statistics and machine-readable report generation.
- `scripts/preprocess_dataset.py` - project-root-relative command-line entry point.
- `tests/conftest.py` - test import-path setup.
- `tests/test_preprocessing/test_html_cleaner.py` - HTML cleaner tests.
- `tests/test_preprocessing/test_normalizer_tokenizer.py` - normalizer
  and tokenizer tests.
- `tests/test_preprocessing/test_xml_parser.py` - streaming XML fixture tests.
- `tests/test_preprocessing/test_document_output.py` - JSONL and pipeline tests.
- `data/processed/documents.jsonl` - generated processed dataset.
- `data/processed/dataset_processing_report.json` - generated statistics report.

## C. Files Modified

- `backend/search_engine/preprocessing/document.py` - retains document
  metadata and token fields and also records title/body whitespace word counts.
- `backend/search_engine/preprocessing/html_cleaner.py` - replaced
  regular-expression-only cleaning with `lxml.html` DOM traversal and a
  conservative fallback for malformed or unparseable input.
- `backend/search_engine/preprocessing/pipeline.py` - cleaned each question
  title and body once, corrected empty-field statistics, tracked duplicates,
  added both length measurements and hardened temporary-file handling.
- `backend/search_engine/preprocessing/tokenizer.py` - retained technical
  forms and expanded Unicode word handling.
- `backend/search_engine/preprocessing/xml_parser.py` - retained streaming
  `iterparse` and clear error propagation.
- `scripts/preprocess_dataset.py` - reports both median length measures.
- Preprocessing tests - expanded HTML, tokenizer, XML, pipeline, cleanup,
  Unicode and output-replacement coverage.
- `docs/roadmap/project-roadmap.md` - updated Phase 2 measurement status.
- `docs/roadmap/requirements-traceability.md` - separated token and word
  interpretations and kept the 100-word rule pending confirmation.

## D. Preprocessing Workflow

1. `scripts/preprocess_dataset.py` resolves `data/raw/Posts.xml` from the
   repository root.
2. `xml_parser.py` streams each `<row>` with `lxml.etree.iterparse`,
   yields attributes and clears processed elements.
3. `pipeline.py` ignores non-question rows and validates question IDs.
4. `html_cleaner.py` uses `lxml.html` to decode entities and traverse markup,
   preserves code text and adds whitespace around block boundaries. Standalone
   programming-style angle expressions such as `<vector>` are protected. If
   parsing fails, it uses entity decoding and block-tag fallback cleaning.
5. `normalizer.py` applies NFC Unicode normalization, whitespace
   normalization and lowercase conversion.
6. `tokenizer.py` creates separate title and body token lists. Technical
   forms such as C++, C#, dotted names, namespace identifiers and O(n)
   are preserved where practical. No stemming or stop-word removal is used.
7. Tags are extracted into separate tags and tag tokens.
8. `pipeline.py` writes one JSON object per line to a temporary `.jsonl`
   file and replaces the final JSONL after successful document processing.
   The report is written and replaced separately afterward; the two output
   files are not updated as one atomic transaction.

## E. Technical Decisions

- Streaming XML parsing avoids loading the approximately 194 MB XML file
  in memory and clears each processed element.
- JSON Lines was used because documents can be read and written sequentially
  without loading the collection as a whole.
- HTML entities are decoded, markup is removed, and code text is not
  separately deleted. Block-tag boundaries become whitespace.
- Tokenization uses a fixed regular-expression approach and no NLTK resource
  downloads. This keeps preprocessing reproducible and avoids runtime
  corpus-model failures.
- Missing optional integers become `None` or `0` according to the existing
  `Document` model conventions. Missing titles/bodies are cleaned safely;
  questions with neither usable title nor body are skipped.
- The existing document length is explicitly
  `len(title_tokens) + len(body_tokens)` and is reported as the token count.
- A separate whitespace-based length is
  `len(cleaned_title.split()) + len(cleaned_body.split())`.
  Duplicate IDs are counted as skipped records.

## F. Dataset Statistics

The latest successful full run measured:

- Input XML post records: 109,426
- Question records (`PostTypeId = 1`): 50,083
- Successfully processed documents: 50,083
- Skipped records: 0
- Empty titles: 0
- Empty bodies: 0
- Questions with empty title or body: 0
- Duplicate document IDs: 0
- Documents with tags: 50,083
- Documents without tags: 0
- Average title-plus-body token count: 165.586 tokens
- Median title-plus-body length: 130 tokens
- Minimum length: 12 tokens
- Maximum token count: 2,904 tokens
- Average whitespace-based title-plus-body word count: 159.479 words
- Median whitespace-based title-plus-body word count: 124 words
- Minimum whitespace-based word count: 10 words
- Maximum whitespace-based word count: 2,725 words
- Total title tokens: 493,880
- Total body tokens: 7,799,162
- Processing duration: 68.946 seconds

DR-01 was satisfied: 50,083 distinct documents, above 45,000.

The 45,000-document requirement is satisfied.

The 100-word median requirement has two interpretations:
- Existing tokenizer median: 130 tokens.
- Whitespace-separated cleaned title and body median: 124 words.

The whitespace-based result exceeds 100, but the 100-word requirement
still requires instructor confirmation of which counting method is intended.
This report does not claim that the token median alone proves the
whitespace-word requirement.

## G. Testing and Verification

Tests created cover HTML cleaning, entities, code text, malformed/empty
HTML, normalization, technical tokenization, XML question extraction,
optional metadata, tags, JSONL fields, Unicode and a pipeline smoke test.

Commands executed:

```text
python -m pytest tests/test_preprocessing -q --basetemp='.pytest_tmp'
```

Result: 29 tests passed in 0.38 seconds.

```text
python scripts/preprocess_dataset.py
```

Result: full preprocessing completed successfully.

## H. Performance

The full run took 68.946 seconds. It used streaming `iterparse` and did not
retain post objects or document objects. For duplicate detection and length
statistics, it retains processed document IDs and per-document token-count
and whitespace-word-count values in memory while writing JSONL sequentially.
RAM usage was not benchmarked.

## I. Requirements Traceability

**Implemented:** streaming XML extraction, question scope, HTML cleaning,
normalization, tokenization, metadata and tag preservation, JSONL output,
separate replacement of the JSONL and report files, statistics and CLI
execution. These two replacements are not one atomic transaction.

**Tested:** parser, cleaner, normalizer, tokenizer and JSONL behavior with
synthetic fixtures.

**Verified against the full dataset:** document count, median length,
average/minimum/maximum length, tags, skipped records and output creation.

**Pending:** Phase 3 indexing and ranking features are outside this phase.

## J. Known Limitations

- Tokenization is regex-based and may split unusual identifiers; it is
  intentionally conservative and does not use NLTK resources.
- HTML cleaning uses `lxml.html` DOM traversal for normal input and a
  conservative regex/entity fallback only when DOM parsing fails.
- Tag extraction supports both pipe-separated tags and angle-bracket Stack
  Exchange tag strings.
- Metadata ranking is not implemented in this phase.

## K. Phase Outcome

Phase 2 is complete for the requested preprocessing scope. The full dataset
run succeeded, 50,083 distinct question documents were written, and the
document-count requirement was satisfied. Both token and whitespace-word
length measurements exceed 100 under their respective medians. The intended
word-count interpretation remains an instructor clarification. The generated
JSONL collection and JSON statistics report are ready for later indexing work.
