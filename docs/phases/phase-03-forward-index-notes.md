# Forward Index: design notes and test evidence

Owner: Asadullah. Paste this section into `docs/phases/phase-03-core-indexing.md`
(or send it to Faraz, who compiles the final report).

## Purpose

Maps each `doc_id` to the terms in that document with separate title, body and
tag term frequencies. Terms are stored as Lexicon term IDs, not strings.

## Files

| File | Role |
|---|---|
| `backend/search_engine/indexing/forward_index.py` | `ForwardIndex` implementation |
| `tests/test_indexing/test_forward_index.py` | 49 unit tests (one uses the real `Lexicon` and is skipped until `lexicon.py` is merged) |
| `scripts/build_forward_index.py` | Builds and reloads `indexes/forward/forward_index.jsonl` from real data |
| `indexes/forward/forward_index.jsonl` | Generated output (git-ignored) |

## Public interface

```python
ForwardIndex.build(documents, lexicon)      # documents: iterable of dicts/objects
index.get_document_terms(doc_id)            # list[TermEntry], KeyError if unknown
index.save(root_dir)                        # writes <root_dir>/indexes/forward/forward_index.jsonl
ForwardIndex.load(root_dir, lexicon)        # reads and validates
# helpers for the Inverted Index builder / integration
index.iter_documents()                      # (doc_id, entries), ascending doc_id
index.doc_ids(); len(index); doc_id in index
index.validate(lexicon)
index.document_frequencies()                # term_id -> df derived from this index
index.verify_document_frequencies(lexicon)  # must equal the Lexicon's df
```

`TermEntry` is a named tuple `(term_id, title_tf, body_tf, tag_tf)` with `.to_dict()`.
The Lexicon is used only through `get_term_id(term)`, `get_term(term_id)` and (for the df check) `get_document_frequency(term_id)`.

`save`/`load` take the repository root and add `indexes/forward/` themselves, the same convention as `Lexicon.save/load`, so the integration code can pass one directory to all three structures.

## File format (Section 5.2 of the specification)

One JSON object per line, ascending `doc_id`, terms ascending `term_id`:

```json
{"doc_id":123,"terms":[{"term_id":1,"title_tf":1,"body_tf":2,"tag_tf":0}]}
```

Compact separators are used to keep the file smaller. A document with no terms is
still written (`"terms":[]`) so record count equals document count.

## Design decisions

- Each field's tokens are counted with a `Counter` (never converted to a set), then
  the three counters are merged into one record per term per document.
- Counts are merged on term ID, not on the raw token string. The Lexicon strips and lowercases terms on lookup, so two raw tokens could share one ID. Empty tokens are ignored, as the Lexicon ignores them.
- Only terms present in at least one field are stored, so there are no
  zero-frequency entries.
- A term missing from the Lexicon raises `UnknownTermError`. Silently skipping it
  would make the structures disagree with each other.
- Internally each document is one flat `array('I')` of
  `[term_id, title_tf, body_tf, tag_tf, ...]`. This uses far less RAM than millions
  of Python tuples. Callers still receive `TermEntry` objects.
- `save` writes `forward_index.jsonl.tmp`, fsyncs, then `os.replace`s it, so a failed
  save never corrupts an existing index.
- `load` validates: JSON, field types, duplicate or out-of-order `doc_id`, ascending
  and unique `term_id`, non-negative integer frequencies, no all-zero entry, and
  every `term_id` exists in the Lexicon. Errors include the line number.
- `null` token lists are treated as empty; a string where a list is expected is
  rejected.

## Test evidence

Unit tests cover: known frequencies, repeated tokens, the same term in several
fields, empty title/body/tags, empty collection, sorted terms and doc IDs, unknown
doc ID, unknown term (both a `None`-returning and a `KeyError`-raising Lexicon),
duplicate and non-integer `doc_id`, missing fields, save/load round trip, file
format, atomic save (including a simulated failed replace), malformed-file
rejection (12 cases), CRLF input, non-ASCII terms, Lexicon consistency, and
byte-identical rebuilds, merging of tokens that normalize to one term, document-frequency verification, and a full build/save/load with the real `Lexicon` class.

Command: `python -m pytest tests/test_indexing/test_forward_index.py -q --basetemp=".pytest_tmp"`

Result in the development sandbox: **49 passed**. Re-run on the team machine and
record the result here: `__ passed`.

### Full dataset run (fill in after running on the real data)

Command: `python scripts/build_forward_index.py`

| Measure | Value |
|---|---|
| Documents indexed (expected 50,083) | |
| Term entries | |
| Build + validate time | |
| `forward_index.jsonl` size | |
| Peak RAM | |
| Reload identical | |
| Forward-index df equals Lexicon df for every term | |

## Limitations

- The whole index is held in memory while building and after loading, which is
  acceptable for 50,083 documents but is not a streaming design.
- Unit tests use small fake Lexicons plus one test with Rafay's real `Lexicon`. Rerun the suite after his module is merged.
- Field names (`doc_id`, `title_tokens`, `body_tokens`, `tag_tokens`) follow the
  specification's schema illustration and must be confirmed against the real
  Phase 2 `documents.jsonl`.
