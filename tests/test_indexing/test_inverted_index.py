import pytest

from search_engine.indexing.inverted_index import InvertedIndex


def test_empty_index_initialization():
    index = InvertedIndex()

    assert len(index) == 0
    assert index.get_index() == {}
    assert index.get_postings(1) == []
    assert index.get_document_frequency(1) == 0


def test_document_counts_repeated_terms_in_each_field():
    index = InvertedIndex()
    index.add_document(
        101,
        title_term_ids=[1, 2, 1],
        body_term_ids=[1, 3, 1],
        tag_term_ids=[2, 2],
    )

    assert index.get_postings(1) == [
        {"doc_id": 101, "title_tf": 2, "body_tf": 2, "tag_tf": 0}
    ]
    assert index.get_postings(2) == [
        {"doc_id": 101, "title_tf": 1, "body_tf": 0, "tag_tf": 2}
    ]
    assert index.get_postings(3) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0}
    ]


def test_precomputed_term_frequencies_merge_across_fields():
    index = InvertedIndex()
    index.add_document(
        205,
        term_frequencies={
            7: {"title_tf": 2, "body_tf": 5, "tag_tf": 1},
            8: {"body_tf": 3},
        },
    )

    assert index.get_postings(7) == [
        {"doc_id": 205, "title_tf": 2, "body_tf": 5, "tag_tf": 1}
    ]
    assert index.get_postings(8) == [
        {"doc_id": 205, "title_tf": 0, "body_tf": 3, "tag_tf": 0}
    ]


def test_document_frequency_and_postings_sorted_by_doc_id():
    index = InvertedIndex()
    index.add_document(205, title_term_ids=[4])
    index.add_document(101, body_term_ids=[4])
    index.add_document(150, tag_term_ids=[4])

    assert index.get_postings(4) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
        {"doc_id": 150, "title_tf": 0, "body_tf": 0, "tag_tf": 1},
        {"doc_id": 205, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
    ]
    assert index.get_document_frequency(4) == 3
    assert index.df == {4: 3}


def test_zero_frequency_posting_is_not_created():
    index = InvertedIndex()
    index.add_posting(9, 1, 0, 0, 0)

    assert index.get_postings(9) == []
    assert index.get_document_frequency(9) == 0


@pytest.mark.parametrize("term_id", [0, -1, 1.5, True, "1"])
def test_invalid_term_ids_raise(term_id):
    index = InvertedIndex()

    with pytest.raises(ValueError):
        index.add_posting(term_id, 1, 1)


@pytest.mark.parametrize("frequency", [-1, 1.5, True, "2"])
def test_invalid_frequencies_raise(frequency):
    index = InvertedIndex()

    with pytest.raises(ValueError):
        index.add_posting(1, 1, title_tf=frequency)


@pytest.mark.parametrize("doc_id", [0, -1, 1.5, True, "1"])
def test_invalid_document_ids_raise(doc_id):
    index = InvertedIndex()

    with pytest.raises(ValueError):
        index.add_posting(1, doc_id, 1)


def test_duplicate_posting_is_not_created():
    index = InvertedIndex()
    index.add_posting(3, 20, title_tf=2)
    index.add_posting(3, 20, title_tf=2)

    assert index.get_postings(3) == [
        {"doc_id": 20, "title_tf": 2, "body_tf": 0, "tag_tf": 0}
    ]


def test_conflicting_duplicate_posting_is_rejected():
    index = InvertedIndex()
    index.add_posting(3, 20, title_tf=2)

    with pytest.raises(ValueError, match="posting already exists"):
        index.add_posting(3, 20, title_tf=3)


def test_duplicate_document_addition_is_rejected():
    index = InvertedIndex()
    index.add_document(10, title_term_ids=[1])

    with pytest.raises(ValueError, match="already been added"):
        index.add_document(10, body_term_ids=[2])


def test_add_document_is_atomic_when_a_later_posting_conflicts():
    index = InvertedIndex()
    index.add_posting(1, 20, title_tf=2)
    index_before = index.get_index()
    df_before = index.df

    with pytest.raises(ValueError, match="posting already exists"):
        index.add_document(
            20,
            term_frequencies={
                7: {"body_tf": 1},
                1: {"body_tf": 1},
            },
        )

    assert index.get_index() == index_before
    assert index.df == df_before


def test_get_postings_returns_defensive_copy():
    index = InvertedIndex()
    index.add_posting(3, 20, title_tf=2)

    postings = index.get_postings(3)
    postings[0]["title_tf"] = 99

    assert index.get_postings(3) == [
        {"doc_id": 20, "title_tf": 2, "body_tf": 0, "tag_tf": 0}
    ]
