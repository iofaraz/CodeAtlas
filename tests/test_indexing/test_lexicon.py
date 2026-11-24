from pathlib import Path
import json
import pytest

from backend.search_engine.indexing.lexicon import Lexicon

DOCUMENTS_JSONL_PATH = Path("data/processed/documents.jsonl")  # update path if needed


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