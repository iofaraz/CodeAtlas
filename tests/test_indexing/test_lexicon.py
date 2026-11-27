from pathlib import Path
import json
import pytest

from backend.search_engine.indexing.lexicon import LEXICON_REL_PATH, Lexicon

DOCUMENTS_JSONL_PATH = Path("data/processed/documents.jsonl")  # update path if needed


def test_build_rejects_duplicate_document_ids():
    documents = [
        {"doc_id": 7, "title_tokens": ["first"], "body_tokens": [], "tag_tokens": []},
        {"doc_id": 7, "title_tokens": ["second"], "body_tokens": [], "tag_tokens": []},
    ]

    with pytest.raises(ValueError, match="duplicate doc_id 7"):
        Lexicon.build(documents)


def test_build_rejects_unhashable_document_ids():
    with pytest.raises(ValueError, match="doc_id must be hashable"):
        Lexicon.build(
            [{"doc_id": [], "title_tokens": [], "body_tokens": [], "tag_tokens": []}]
        )


def test_document_frequency_counts_repeated_term_once_per_document():
    lexicon = Lexicon.build(
        [
            {
                "doc_id": 1,
                "title_tokens": ["echo", "echo", "echo"],
                "body_tokens": [],
                "tag_tokens": [],
            }
        ]
    )

    term_id = lexicon.get_term_id("echo")
    assert lexicon.get_document_frequency(term_id) == 1


def test_document_frequency_counts_term_once_across_fields():
    lexicon = Lexicon.build(
        [
            {
                "doc_id": 1,
                "title_tokens": ["echo"],
                "body_tokens": ["echo", "echo"],
                "tag_tokens": ["echo"],
            }
        ]
    )

    term_id = lexicon.get_term_id("echo")
    assert lexicon.get_document_frequency(term_id) == 1


def test_document_frequency_counts_distinct_documents():
    lexicon = Lexicon.build(
        [
            {
                "doc_id": 1,
                "title_tokens": ["echo", "echo"],
                "body_tokens": [],
                "tag_tokens": [],
            },
            {
                "doc_id": 2,
                "title_tokens": [],
                "body_tokens": ["echo"],
                "tag_tokens": ["other"],
            },
        ]
    )

    assert lexicon.get_document_frequency(lexicon.get_term_id("echo")) == 2
    assert lexicon.get_document_frequency(lexicon.get_term_id("other")) == 1


def test_empty_input_builds_empty_lexicon():
    lexicon = Lexicon.build([])

    assert lexicon.term_to_id == {}
    assert lexicon.id_to_term == {}
    assert lexicon.document_frequency == {}
    lexicon.validate()


def test_build_normalizes_terms_and_assigns_lexicographic_ids():
    lexicon = Lexicon.build(
        [
            {
                "doc_id": 1,
                "title_tokens": [" Zulu ", "ALPHA", "alpha"],
                "body_tokens": [],
                "tag_tokens": [],
            }
        ]
    )

    assert lexicon.term_to_id == {"alpha": 1, "zulu": 2}
    assert lexicon.id_to_term == {1: "alpha", 2: "zulu"}
    assert lexicon.get_term_id(" ALPHA ") == 1
    assert lexicon.get_term(0) is None


def test_build_rejects_non_string_tokens():
    documents = [
        {
            "doc_id": 1,
            "title_tokens": ["valid", None],
            "body_tokens": [],
            "tag_tokens": [],
        }
    ]

    with pytest.raises(ValueError, match="Term must be a string"):
        Lexicon.build(documents)


def test_build_preserves_support_for_documents_without_ids():
    lexicon = Lexicon.build(
        [{"title_tokens": ["term"], "body_tokens": [], "tag_tokens": []}]
    )

    assert lexicon.get_term_id("term") == 1
    assert lexicon.get_document_frequency(1) == 1


def write_lexicon_lines(directory, lines):
    path = directory / LEXICON_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    "lines, message",
    [
        (["{not json"], "invalid JSON"),
        ([json.dumps(["not", "an", "object"])], "record must be an object"),
        ([json.dumps({"term_id": 1, "term": "alpha"})], "missing required fields"),
        ([json.dumps({"term_id": 1, "term": "alpha", "df": 1, "extra": 1})], "unexpected fields"),
        ([json.dumps({"term_id": 1, "term": " Alpha ", "df": 1})], "normalized"),
        (
            [
                json.dumps({"term_id": 2, "term": "beta", "df": 1}),
                json.dumps({"term_id": 1, "term": "alpha", "df": 1}),
            ],
            "strictly increasing",
        ),
        ([json.dumps({"term_id": 2, "term": "beta", "df": 1})], "contiguous"),
        (
            [
                json.dumps({"term_id": 1, "term": "beta", "df": 1}),
                json.dumps({"term_id": 2, "term": "alpha", "df": 1}),
            ],
            "lexicographic order",
        ),
        (
            [
                json.dumps({"term_id": 1, "term": "alpha", "df": 1}),
                json.dumps({"term_id": 1, "term": "beta", "df": 1}),
            ],
            "duplicate term_id",
        ),
        (
            [
                json.dumps({"term_id": 1, "term": "alpha", "df": 1}),
                json.dumps({"term_id": 2, "term": "alpha", "df": 1}),
            ],
            "duplicate term",
        ),
        ([json.dumps({"term_id": True, "term": "alpha", "df": 1})], "term_id"),
        ([json.dumps({"term_id": 1, "term": "alpha", "df": 0})], "df"),
    ],
)
def test_load_rejects_malformed_or_contract_violating_records(
    tmp_path, lines, message
):
    write_lexicon_lines(tmp_path, lines)

    with pytest.raises(ValueError, match=message):
        Lexicon.load(tmp_path)


def test_load_accepts_empty_file(tmp_path):
    write_lexicon_lines(tmp_path, [])

    lexicon = Lexicon.load(tmp_path)

    assert lexicon.term_to_id == {}
    assert lexicon.id_to_term == {}
    assert lexicon.document_frequency == {}


def _read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


@pytest.mark.skipif(not DOCUMENTS_JSONL_PATH.exists(), reason="documents.jsonl not found")
def test_build_and_save_full_documents_jsonl(tmp_path):
    docs = list(_read_jsonl(DOCUMENTS_JSONL_PATH))
    assert len(docs) > 0

    lex = Lexicon.build(docs)
    assert len(lex.term_to_id) > 0

    # Every df must be between 1 and total number of documents
    for term_id, df in lex.document_frequency.items():
        term = lex.get_term(term_id)
        assert term is not None
        assert lex.get_term_id(term) == term_id
        assert lex.get_document_frequency(term_id) == df
        assert 1 <= df <= len(docs)

    # Round-trip save and load on the full dataset
    lex.save(tmp_path)
    loaded = Lexicon.load(tmp_path)
    assert loaded.term_to_id == lex.term_to_id
    assert loaded.id_to_term == lex.id_to_term
    assert loaded.document_frequency == lex.document_frequency