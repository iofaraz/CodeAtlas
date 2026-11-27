"""Unit tests for ForwardIndex (Phase 3, owner: Asadullah).

These tests use small fake Lexicons so they do not depend on Rafay's
lexicon.py. Both unknown-lookup styles (return None / raise KeyError) are
covered because the Lexicon's behaviour for unknown terms is not fixed yet.
"""

import json

import pytest

from backend.search_engine.indexing.forward_index import (
    FORWARD_INDEX_REL_PATH,
    ForwardIndex,
    TermEntry,
    UnknownTermError,
    iter_documents_jsonl,
)


class FakeLexicon:
    """Sorted-vocabulary lexicon; unknown lookups return None."""

    def __init__(self, terms):
        self._t2i = {t: i for i, t in enumerate(sorted(set(terms)), start=1)}
        self._i2t = {i: t for t, i in self._t2i.items()}

    def get_term_id(self, term):
        return self._t2i.get(term)

    def get_term(self, term_id):
        return self._i2t.get(term_id)


class RaisingLexicon(FakeLexicon):
    """Same, but unknown lookups raise KeyError."""

    def get_term_id(self, term):
        return self._t2i[term]

    def get_term(self, term_id):
        return self._i2t[term_id]


def doc(doc_id, title=(), body=(), tags=()):
    return {
        "doc_id": doc_id,
        "title_tokens": list(title),
        "body_tokens": list(body),
        "tag_tokens": list(tags),
    }


# Vocabulary sorted: algorithm=1, array=2, list=3, python=4
VOCAB = ["algorithm", "array", "list", "python"]


@pytest.fixture
def lexicon():
    return FakeLexicon(VOCAB)


def entries(index, doc_id):
    return [tuple(e) for e in index.get_document_terms(doc_id)]


def test_single_document_known_frequencies(lexicon):
    index = ForwardIndex.build(
        [doc(10, title=["python", "list"], body=["python", "list", "array"], tags=["python"])],
        lexicon,
    )
    assert entries(index, 10) == [
        (2, 0, 1, 0),  # array
        (3, 1, 1, 0),  # list
        (4, 1, 1, 1),  # python
    ]


def test_repeated_tokens_are_counted_per_field(lexicon):
    index = ForwardIndex.build(
        [doc(1, title=["python", "python"], body=["python"] * 5 + ["list"], tags=[])],
        lexicon,
    )
    assert entries(index, 1) == [(3, 0, 1, 0), (4, 2, 5, 0)]


def test_same_term_in_multiple_fields_is_one_record(lexicon):
    index = ForwardIndex.build([doc(1, title=["list"], body=["list"], tags=["list"])], lexicon)
    assert entries(index, 1) == [(3, 1, 1, 1)]
    assert len(index.get_document_terms(1)) == 1


def test_empty_fields(lexicon):
    index = ForwardIndex.build(
        [
            doc(1, title=["python"]),                 # body and tags empty
            doc(2, body=["list"]),                    # title and tags empty
            doc(3, tags=["array"]),                   # title and body empty
            doc(4),                                   # everything empty
        ],
        lexicon,
    )
    assert entries(index, 1) == [(4, 1, 0, 0)]
    assert entries(index, 2) == [(3, 0, 1, 0)]
    assert entries(index, 3) == [(2, 0, 0, 1)]
    assert index.get_document_terms(4) == []
    assert 4 in index
    assert len(index) == 4  # empty document still gets a record


def test_null_token_list_treated_as_empty(lexicon):
    record = {"doc_id": 1, "title_tokens": None, "body_tokens": ["list"], "tag_tokens": None}
    index = ForwardIndex.build([record], lexicon)
    assert entries(index, 1) == [(3, 0, 1, 0)]


def test_no_zero_frequency_entries(lexicon):
    index = ForwardIndex.build([doc(1, title=["python"], body=["list"])], lexicon)
    for _, (term_id, t, b, g) in enumerate(entries(index, 1)):
        assert (t, b, g) != (0, 0, 0)
    assert [e.term_id for e in index.get_document_terms(1)] == [3, 4]  # no algorithm/array


def test_terms_sorted_by_term_id_regardless_of_token_order(lexicon):
    index = ForwardIndex.build([doc(1, body=["python", "list", "array", "algorithm"])], lexicon)
    ids = [e.term_id for e in index.get_document_terms(1)]
    assert ids == sorted(ids) == [1, 2, 3, 4]


def test_multiple_documents_sorted_doc_ids(lexicon):
    index = ForwardIndex.build(
        [doc(30, body=["list"]), doc(5, body=["python"]), doc(17, body=["array"])], lexicon
    )
    assert index.doc_ids() == [5, 17, 30]
    assert [d for d, _ in index.iter_documents()] == [5, 17, 30]


def test_unknown_doc_id_raises_keyerror(lexicon):
    index = ForwardIndex.build([doc(1, body=["list"])], lexicon)
    assert 999 not in index
    with pytest.raises(KeyError):
        index.get_document_terms(999)


@pytest.mark.parametrize("lex_class", [FakeLexicon, RaisingLexicon])
def test_unknown_term_in_document_is_rejected(lex_class):
    lexicon = lex_class(VOCAB)
    with pytest.raises(UnknownTermError):
        ForwardIndex.build([doc(1, body=["python", "notinlexicon"])], lexicon)


def test_term_id_zero_from_lexicon_counts_as_unknown():
    class ZeroLexicon(FakeLexicon):
        def get_term_id(self, term):
            return 0

    with pytest.raises(UnknownTermError):
        ForwardIndex.build([doc(1, body=["python"])], ZeroLexicon(VOCAB))


def test_duplicate_doc_id_rejected(lexicon):
    with pytest.raises(ValueError, match="duplicate doc_id 7"):
        ForwardIndex.build([doc(7, body=["list"]), doc(7, body=["python"])], lexicon)


@pytest.mark.parametrize("bad_id", ["12", 1.5, None, True])
def test_non_integer_doc_id_rejected(lexicon, bad_id):
    with pytest.raises(ValueError):
        ForwardIndex.build([doc(bad_id, body=["list"])], lexicon)


def test_missing_field_and_string_tokens_rejected(lexicon):
    with pytest.raises(ValueError, match="body_tokens"):
        ForwardIndex.build([{"doc_id": 1, "title_tokens": [], "tag_tokens": []}], lexicon)
    with pytest.raises(ValueError, match="list of tokens"):
        raw = {"doc_id": 1, "title_tokens": [], "body_tokens": "python list", "tag_tokens": []}
        ForwardIndex.build([raw], lexicon)


def test_accepts_objects_with_attributes(lexicon):
    class Doc:
        doc_id = 1
        title_tokens = ["python"]
        body_tokens = []
        tag_tokens = []

    index = ForwardIndex.build([Doc()], lexicon)
    assert entries(index, 1) == [(4, 1, 0, 0)]


def test_empty_collection(lexicon, tmp_path):
    index = ForwardIndex.build([], lexicon)
    assert len(index) == 0 and index.doc_ids() == []
    index.save(tmp_path)
    assert ForwardIndex.load(tmp_path, lexicon).doc_ids() == []


def test_term_entry_to_dict_and_unpacking():
    entry = TermEntry(3, 1, 2, 0)
    assert entry.to_dict() == {"term_id": 3, "title_tf": 1, "body_tf": 2, "tag_tf": 0}
    assert tuple(entry) == (3, 1, 2, 0)


# ------------------------------------------------------------ save / load
def sample_index(lexicon):
    return ForwardIndex.build(
        [
            doc(123, title=["python", "list"], body=["python", "python", "array"], tags=["python"]),
            doc(45, body=["algorithm"]),
            doc(7),
        ],
        lexicon,
    )


def test_save_load_round_trip(lexicon, tmp_path):
    original = sample_index(lexicon)
    path = original.save(tmp_path / "forward")
    assert path == tmp_path / "forward" / FORWARD_INDEX_REL_PATH and path.exists()

    loaded = ForwardIndex.load(tmp_path / "forward", lexicon)
    assert loaded.doc_ids() == original.doc_ids() == [7, 45, 123]
    for doc_id in original.doc_ids():
        assert loaded.get_document_terms(doc_id) == original.get_document_terms(doc_id)


def test_saved_file_format(lexicon, tmp_path):
    sample_index(lexicon).save(tmp_path)
    lines = (tmp_path / FORWARD_INDEX_REL_PATH).read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert [r["doc_id"] for r in records] == [7, 45, 123]  # ascending doc_id
    assert records[0] == {"doc_id": 7, "terms": []}
    assert records[2]["terms"][-1] == {"term_id": 4, "title_tf": 1, "body_tf": 2, "tag_tf": 1}
    for record in records:
        ids = [t["term_id"] for t in record["terms"]]
        assert ids == sorted(ids)
        for term in record["terms"]:
            assert set(term) == {"term_id", "title_tf", "body_tf", "tag_tf"}  # no term strings


def test_save_leaves_no_temp_file_and_overwrites(lexicon, tmp_path):
    sample_index(lexicon).save(tmp_path)
    ForwardIndex.build([doc(1, body=["list"])], lexicon).save(tmp_path)
    assert sorted(p.name for p in (tmp_path / FORWARD_INDEX_REL_PATH).parent.iterdir()) == ["forward_index.jsonl"]
    assert ForwardIndex.load(tmp_path, lexicon).doc_ids() == [1]


def test_failed_save_keeps_previous_file(lexicon, tmp_path, monkeypatch):
    sample_index(lexicon).save(tmp_path)
    before = (tmp_path / FORWARD_INDEX_REL_PATH).read_bytes()

    import backend.search_engine.indexing.forward_index as module

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(module.os, "replace", boom)
    with pytest.raises(OSError):
        ForwardIndex.build([doc(1, body=["list"])], lexicon).save(tmp_path)
    assert (tmp_path / FORWARD_INDEX_REL_PATH).read_bytes() == before
    assert sorted(p.name for p in (tmp_path / FORWARD_INDEX_REL_PATH).parent.iterdir()) == ["forward_index.jsonl"]


def test_load_missing_file(lexicon, tmp_path):
    with pytest.raises(FileNotFoundError):
        ForwardIndex.load(tmp_path, lexicon)


def write_lines(directory, lines):
    (directory / FORWARD_INDEX_REL_PATH).parent.mkdir(parents=True, exist_ok=True)
    (directory / FORWARD_INDEX_REL_PATH).write_text("\n".join(lines) + "\n", encoding="utf-8")


def term(term_id, t=1, b=0, g=0):
    return {"term_id": term_id, "title_tf": t, "body_tf": b, "tag_tf": g}


@pytest.mark.parametrize(
    "lines, message",
    [
        (["{not json"], "invalid JSON"),
        ([json.dumps({"doc_id": 1})], "expected"),
        ([json.dumps({"doc_id": "1", "terms": []})], "doc_id must be an integer"),
        ([json.dumps({"doc_id": 1, "terms": []}), json.dumps({"doc_id": 1, "terms": []})], "duplicate doc_id"),
        ([json.dumps({"doc_id": 2, "terms": []}), json.dumps({"doc_id": 1, "terms": []})], "ascending"),
        ([json.dumps({"doc_id": 1, "terms": [{"term_id": 1}]})], "malformed"),
        ([json.dumps({"doc_id": 1, "terms": [term(1, t=-1)]})], "negative"),
        ([json.dumps({"doc_id": 1, "terms": [term(1, t=1.5)]})], "non-integer"),
        ([json.dumps({"doc_id": 1, "terms": [term(1, 0, 0, 0)]})], "all-zero"),
        ([json.dumps({"doc_id": 1, "terms": [term(2), term(1)]})], "ascending"),
        ([json.dumps({"doc_id": 1, "terms": [term(2), term(2)]})], "ascending"),
        ([json.dumps({"doc_id": 1, "terms": [term(99)]})], "not in the Lexicon"),
    ],
)
def test_load_rejects_bad_files(lexicon, tmp_path, lines, message):
    write_lines(tmp_path, lines)
    with pytest.raises(ValueError, match=message):
        ForwardIndex.load(tmp_path, lexicon)


def test_load_validates_against_lexicon_with_raising_lookup(tmp_path):
    lexicon = RaisingLexicon(VOCAB)
    write_lines(tmp_path, [json.dumps({"doc_id": 1, "terms": [term(99)]})])
    with pytest.raises(ValueError, match="not in the Lexicon"):
        ForwardIndex.load(tmp_path, lexicon)


def test_load_tolerates_crlf_and_blank_lines(lexicon, tmp_path):
    payload = json.dumps({"doc_id": 1, "terms": [term(3)]})
    (tmp_path / FORWARD_INDEX_REL_PATH).parent.mkdir(parents=True)
    (tmp_path / FORWARD_INDEX_REL_PATH).write_bytes(f"{payload}\r\n\r\n".encode())
    assert ForwardIndex.load(tmp_path, lexicon).doc_ids() == [1]


def test_non_ascii_terms_round_trip(tmp_path):
    lexicon = FakeLexicon(["ﬁrst", "ﬂexibility", "python"])
    index = ForwardIndex.build([doc(1, body=["ﬁrst", "ﬂexibility"])], lexicon)
    index.save(tmp_path)
    assert ForwardIndex.load(tmp_path, lexicon).get_document_terms(1) == index.get_document_terms(1)


# ------------------------------------------------------ consistency checks
def test_consistency_with_lexicon(lexicon):
    index = sample_index(lexicon)
    index.validate(lexicon)  # does not raise
    smaller = FakeLexicon(["algorithm", "array"])  # lacks list / python
    with pytest.raises(ValueError, match="not in the Lexicon"):
        index.validate(smaller)


def test_rebuild_is_reproducible(lexicon, tmp_path):
    documents = [doc(3, body=["list", "python"]), doc(1, title=["array"], tags=["python"])]
    a, b = tmp_path / "a", tmp_path / "b"
    ForwardIndex.build(documents, lexicon).save(a)
    ForwardIndex.build(list(reversed(documents)), lexicon).save(b)
    assert (a / FORWARD_INDEX_REL_PATH).read_bytes() == (b / FORWARD_INDEX_REL_PATH).read_bytes()


def test_iter_documents_jsonl(tmp_path):
    path = tmp_path / "documents.jsonl"
    path.write_text(
        json.dumps(doc(1, body=["list"])) + "\n\n" + json.dumps(doc(2, body=["python"])) + "\n",
        encoding="utf-8",
    )
    assert [d["doc_id"] for d in iter_documents_jsonl(path)] == [1, 2]
    path.write_text("{oops\n", encoding="utf-8")
    with pytest.raises(ValueError, match=":1:"):
        list(iter_documents_jsonl(path))


# ------------------------------------------- normalizing / empty-token cases
class CaseFoldingLexicon(FakeLexicon):
    """Like Rafay's Lexicon: lookups strip and lowercase the term."""

    def get_term_id(self, term):
        return self._t2i.get(term.strip().lower())


def test_tokens_that_normalize_to_same_term_are_merged():
    index = ForwardIndex.build(
        [doc(1, title=["Python"], body=["python", "python", " python "], tags=["PYTHON"])],
        CaseFoldingLexicon(VOCAB),
    )
    assert entries(index, 1) == [(4, 1, 3, 1)]  # one record, counts summed


def test_empty_and_whitespace_tokens_are_ignored(lexicon):
    index = ForwardIndex.build([doc(1, body=["", "  ", "list"])], lexicon)
    assert entries(index, 1) == [(3, 0, 1, 0)]


# ----------------------------------------------- document-frequency checks
def test_document_frequencies_count_each_document_once(lexicon):
    index = ForwardIndex.build(
        [
            doc(1, title=["python"], body=["python", "python"], tags=["python"]),
            doc(2, body=["python", "list"]),
            doc(3, body=["list"]),
        ],
        lexicon,
    )
    assert index.document_frequencies() == {3: 2, 4: 2}


class DfLexicon(FakeLexicon):
    def __init__(self, terms, df):
        super().__init__(terms)
        self.document_frequency = df

    def get_document_frequency(self, term_id):
        return self.document_frequency.get(term_id)


def test_verify_document_frequencies(lexicon):
    docs = [doc(1, body=["python", "list"]), doc(2, body=["python"])]
    index = ForwardIndex.build(docs, lexicon)
    index.verify_document_frequencies(DfLexicon(VOCAB, {3: 1, 4: 2}))  # matches

    with pytest.raises(ValueError, match="forward index df=2, lexicon df=5"):
        index.verify_document_frequencies(DfLexicon(VOCAB, {3: 1, 4: 5}))
    with pytest.raises(ValueError, match="in no document"):
        index.verify_document_frequencies(DfLexicon(VOCAB, {1: 1, 3: 1, 4: 2}))
    with pytest.raises(TypeError):
        index.verify_document_frequencies(FakeLexicon(VOCAB))


# ------------------------------------------- with Rafay's real Lexicon class
def test_with_real_lexicon(tmp_path):
    """Skipped automatically until Rafay's lexicon.py is in the repository."""
    lexicon_module = pytest.importorskip("backend.search_engine.indexing.lexicon")
    Lexicon = lexicon_module.Lexicon

    docs = [
        doc(10, title=["python", "list"], body=["python", "list", "array", "array"], tags=["python"]),
        doc(20, body=["algorithm", "python"]),
        doc(30),
    ]
    lexicon = Lexicon.build(docs)
    index = ForwardIndex.build(docs, lexicon)

    assert entries(index, 10) == [
        (lexicon.get_term_id("array"), 0, 2, 0),
        (lexicon.get_term_id("list"), 1, 1, 0),
        (lexicon.get_term_id("python"), 1, 1, 1),
    ]
    index.validate(lexicon)
    index.verify_document_frequencies(lexicon)

    # Same root directory for both, as the integration code will do.
    lexicon.save(tmp_path)
    index.save(tmp_path)
    reloaded_lexicon = Lexicon.load(tmp_path)
    reloaded = ForwardIndex.load(tmp_path, reloaded_lexicon)
    assert reloaded.doc_ids() == [10, 20, 30]
    for doc_id in reloaded.doc_ids():
        assert reloaded.get_document_terms(doc_id) == index.get_document_terms(doc_id)
    reloaded.verify_document_frequencies(reloaded_lexicon)
