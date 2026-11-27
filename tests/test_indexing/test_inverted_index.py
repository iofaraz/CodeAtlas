import json

import pytest

from search_engine.indexing.inverted_index import (
    INVERTED_INDEX_REL_PATH,
    InvertedIndex,
)


def write_inverted_lines(directory, lines):
    path = directory / INVERTED_INDEX_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inverted_posting(doc_id, title_tf=1, body_tf=0, tag_tf=0):
    return {
        "doc_id": doc_id,
        "title_tf": title_tf,
        "body_tf": body_tf,
        "tag_tf": tag_tf,
    }


def inverted_record(term_id, postings, **extra_fields):
    record = {"term_id": term_id, "df": len(postings), "postings": postings}
    record.update(extra_fields)
    return record


@pytest.mark.parametrize(
    "lines, message",
    [
        (["{not json"], "invalid JSON"),
        ([json.dumps(["not", "an", "object"])], "record must be an object"),
        ([json.dumps({"term_id": 1, "df": 1})], "missing required fields"),
        (
            [json.dumps(inverted_record(1, [inverted_posting(1)], extra=1))],
            "unexpected fields",
        ),
        (
            [
                json.dumps(
                    inverted_record(
                        1,
                        [{**inverted_posting(1), "extra": 1}],
                    )
                )
            ],
            "unexpected fields",
        ),
        (
            [
                json.dumps(
                    inverted_record(
                        1,
                        [{"doc_id": 1, "title_tf": 1, "body_tf": 0}],
                    )
                )
            ],
            "missing required fields",
        ),
        (
            [
                json.dumps(inverted_record(2, [inverted_posting(1)])),
                json.dumps(inverted_record(1, [inverted_posting(1)])),
            ],
            "strictly increasing",
        ),
        (
            [
                json.dumps(inverted_record(0, [inverted_posting(1)]))
            ],
            "positive integer",
        ),
        (
            [
                json.dumps(inverted_record(True, [inverted_posting(1)]))
            ],
            "positive integer",
        ),
        (
            [
                json.dumps(
                    inverted_record(
                        1,
                        [inverted_posting(2), inverted_posting(1)],
                    )
                )
            ],
            "strictly increasing",
        ),
        (
            [
                json.dumps(
                    inverted_record(
                        1,
                        [inverted_posting(0)],
                    )
                )
            ],
            "positive integer",
        ),
        (
            [
                json.dumps(inverted_record(1, [inverted_posting(1)])),
                json.dumps(inverted_record(1, [inverted_posting(2)])),
            ],
            "strictly increasing",
        ),
        (
            [
                json.dumps(
                    inverted_record(
                        1,
                        [inverted_posting(1), inverted_posting(1)],
                    )
                )
            ],
            "strictly increasing",
        ),
        (
            [
                json.dumps(
                    inverted_record(1, [inverted_posting(1, title_tf=0)])
                )
            ],
            "non-zero TF",
        ),
        (
            [
                json.dumps(
                    inverted_record(1, [inverted_posting(1, title_tf=True)])
                )
            ],
            "non-negative integer",
        ),
        (
            [
                json.dumps(inverted_record(1, []))
            ],
            "df must be a positive integer",
        ),
        (
            [
                json.dumps(
                    inverted_record(1, [inverted_posting(1, title_tf=-1)])
                )
            ],
            "non-negative integer",
        ),
        (
            [
                json.dumps(
                    {
                        "term_id": 1,
                        "df": 2,
                        "postings": [inverted_posting(1)],
                    }
                )
            ],
            "does not match",
        ),
    ],
)
def test_load_rejects_malformed_or_contract_violating_records(
    tmp_path, lines, message
):
    write_inverted_lines(tmp_path, lines)

    with pytest.raises(ValueError, match=message):
        InvertedIndex.load(tmp_path)


def test_load_accepts_empty_file(tmp_path):
    write_inverted_lines(tmp_path, [])

    assert InvertedIndex.load(tmp_path).get_index() == {}


def test_empty_index_initialization():
    index = InvertedIndex()

    assert len(index) == 0
    assert index.get_index() == {}
    assert index.get_postings(1) == []
    assert index.get_document_frequency(1) == 0


def test_save_load_round_trip(tmp_path):
    index = InvertedIndex()
    index.add_posting(4, 205, title_tf=1)
    index.add_posting(4, 101, body_tf=2)

    path = index.save(tmp_path)
    assert path.exists()

    loaded = InvertedIndex.load(tmp_path)
    assert loaded.get_index() == index.get_index()
    assert loaded.df == {4: 2}


def test_loaded_index_rejects_duplicate_document_without_overlapping_terms(tmp_path):
    index = InvertedIndex()
    index.add_document(
        101,
        term_frequencies={
            1: {"title_tf": 2, "body_tf": 3, "tag_tf": 1},
            2: {"body_tf": 4},
        },
    )
    index.save(tmp_path)

    loaded = InvertedIndex.load(tmp_path)
    expected_index = loaded.get_index()
    expected_df = loaded.df

    with pytest.raises(ValueError, match="document 101 has already been added"):
        loaded.add_document(101, term_frequencies={3: {"title_tf": 1}})

    assert loaded.get_index() == expected_index
    assert loaded.df == expected_df
    assert loaded.get_postings(1) == [
        {"doc_id": 101, "title_tf": 2, "body_tf": 3, "tag_tf": 1}
    ]
    assert loaded.get_postings(2) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 4, "tag_tf": 0}
    ]


def test_loaded_index_accepts_new_document_and_preserves_existing_postings(tmp_path):
    index = InvertedIndex()
    index.add_document(
        101,
        term_frequencies={
            1: {"title_tf": 2, "body_tf": 3, "tag_tf": 1},
            2: {"body_tf": 4},
        },
    )
    index.save(tmp_path)

    loaded = InvertedIndex.load(tmp_path)
    loaded.add_document(
        205,
        term_frequencies={
            1: {"tag_tf": 2},
            3: {"title_tf": 1},
        },
    )

    assert loaded.get_postings(1) == [
        {"doc_id": 101, "title_tf": 2, "body_tf": 3, "tag_tf": 1},
        {"doc_id": 205, "title_tf": 0, "body_tf": 0, "tag_tf": 2},
    ]
    assert loaded.get_postings(2) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 4, "tag_tf": 0}
    ]
    assert loaded.get_postings(3) == [
        {"doc_id": 205, "title_tf": 1, "body_tf": 0, "tag_tf": 0}
    ]
    assert loaded.df == {1: 2, 2: 1, 3: 1}


def test_empty_document_id_is_not_preserved_by_inverted_jsonl(tmp_path):
    index = InvertedIndex()
    index.add_document(101)
    index.save(tmp_path)

    loaded = InvertedIndex.load(tmp_path)

    assert loaded.get_index() == {}
    with pytest.raises(ValueError, match="missing document"):
        loaded.validate_against_forward_records(
            [{"doc_id": 101, "terms": []}]
        )


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


def test_df_is_derived_from_posting_list_lengths():
    index = InvertedIndex()
    index.add_document(
        101,
        term_frequencies={
            1: {"title_tf": 1},
            2: {"body_tf": 2},
        },
    )
    index.add_document(
        102,
        term_frequencies={
            1: {"tag_tf": 1},
        },
    )

    assert index.get_document_frequency(1) == len(index.get_postings(1)) == 2
    assert index.get_document_frequency(2) == len(index.get_postings(2)) == 1
    assert index.df == {1: 2, 2: 1}


def test_zero_frequency_posting_is_rejected_without_mutation():
    index = InvertedIndex()
    index.add_posting(3, 20, title_tf=2)
    index_before = index.get_index()
    df_before = index.df

    with pytest.raises(ValueError, match="at least one non-zero TF"):
        index.add_posting(9, 1, 0, 0, 0)

    assert index.get_index() == index_before
    assert index.df == df_before


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


def test_add_forward_record_creates_postings_and_preserves_tf():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
                {"term_id": 2, "title_tf": 2, "body_tf": 3, "tag_tf": 1},
            ],
        }
    )

    assert index.get_postings(1) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0}
    ]
    assert index.get_postings(2) == [
        {"doc_id": 101, "title_tf": 2, "body_tf": 3, "tag_tf": 1}
    ]
    assert index.get_document_frequency(1) == 1
    assert index.get_document_frequency(2) == 1


def test_multiple_forward_records_have_sorted_postings_and_correct_df():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 205,
            "terms": [
                {"term_id": 4, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 4, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
            ],
        }
    )

    assert index.get_postings(4) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
        {"doc_id": 205, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
    ]
    assert index.get_document_frequency(4) == 2
    assert index.df == {4: 2}


@pytest.mark.parametrize("record", [None, [], 1, "record"])
def test_forward_record_requires_mapping(record):
    with pytest.raises(ValueError, match="record must be a mapping"):
        InvertedIndex().add_forward_record(record)


def test_forward_record_requires_doc_id():
    with pytest.raises(ValueError, match="missing doc_id"):
        InvertedIndex().add_forward_record({"terms": []})


@pytest.mark.parametrize("doc_id", [0, -1, 1.5, "101", True])
def test_forward_record_rejects_invalid_doc_id(doc_id):
    with pytest.raises(ValueError, match="doc_id"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": doc_id,
                "terms": [],
            }
        )


def test_forward_record_requires_terms():
    with pytest.raises(ValueError, match="missing terms"):
        InvertedIndex().add_forward_record({"doc_id": 101})


def test_forward_record_rejects_unexpected_top_level_fields():
    with pytest.raises(ValueError, match="unexpected fields"):
        InvertedIndex().add_forward_record(
            {"doc_id": 101, "terms": [], "extra": "not allowed"}
        )


@pytest.mark.parametrize("terms", [None, 1, "terms", {}, True])
def test_forward_record_rejects_invalid_terms_sequence(terms):
    with pytest.raises(ValueError, match="terms must be a sequence"):
        InvertedIndex().add_forward_record({"doc_id": 101, "terms": terms})


def test_forward_record_rejects_non_mapping_term_entry():
    with pytest.raises(ValueError, match="term entry must be a mapping"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [1],
            }
        )


def test_forward_record_requires_term_id():
    with pytest.raises(ValueError, match="missing term_id"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {"title_tf": 1, "body_tf": 0, "tag_tf": 0},
                ],
            }
        )


@pytest.mark.parametrize("term_id", [0, -1, 1.5, "1", True])
def test_forward_record_rejects_invalid_term_id(term_id):
    with pytest.raises(ValueError, match="term_id"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {
                        "term_id": term_id,
                        "title_tf": 1,
                        "body_tf": 0,
                        "tag_tf": 0,
                    },
                ],
            }
        )


@pytest.mark.parametrize("field_name", ["title_tf", "body_tf", "tag_tf"])
@pytest.mark.parametrize("value", [-1, 1.5, "2", True])
def test_forward_record_rejects_invalid_tf(field_name, value):
    entry = {"term_id": 1, "title_tf": 0, "body_tf": 0, "tag_tf": 0}
    entry[field_name] = value

    with pytest.raises(ValueError, match="frequency"):
        InvertedIndex().add_forward_record(
            {"doc_id": 101, "terms": [entry]}
        )


def test_forward_record_requires_tf_fields():
    with pytest.raises(ValueError, match="missing title_tf"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {"term_id": 1, "body_tf": 1, "tag_tf": 0},
                ],
            }
        )


def test_forward_record_rejects_unexpected_term_entry_fields():
    with pytest.raises(ValueError, match="unexpected fields"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {
                        "term_id": 1,
                        "title_tf": 1,
                        "body_tf": 0,
                        "tag_tf": 0,
                        "extra": "not allowed",
                    }
                ],
            }
        )


def test_forward_record_rejects_duplicate_term_ids():
    with pytest.raises(ValueError, match="duplicate term_id"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                    {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
                ],
            }
        )


@pytest.mark.parametrize(
    "terms",
    [
        [
            {"term_id": 2, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        ],
        [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
        ],
    ],
)
def test_forward_record_requires_sorted_unique_term_ids(terms):
    with pytest.raises(ValueError):
        InvertedIndex().add_forward_record({"doc_id": 101, "terms": terms})


def test_forward_record_rejects_all_zero_tf_entry():
    with pytest.raises(ValueError, match="non-zero TF"):
        InvertedIndex().add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {"term_id": 1, "title_tf": 0, "body_tf": 0, "tag_tf": 0},
                ],
            }
        )


def test_forward_record_is_atomic_when_later_entry_is_invalid():
    index = InvertedIndex()
    index.add_posting(9, 50, title_tf=1)
    index_before = index.get_index()
    df_before = index.df

    with pytest.raises(ValueError, match="missing body_tf"):
        index.add_forward_record(
            {
                "doc_id": 101,
                "terms": [
                    {
                        "term_id": 1,
                        "title_tf": 1,
                        "body_tf": 0,
                        "tag_tf": 0,
                    },
                    {
                        "term_id": 2,
                        "title_tf": 0,
                        "tag_tf": 1,
                    },
                ],
            }
        )

    assert index.get_index() == index_before
    assert index.df == df_before
    assert index.get_postings(1) == []


def test_duplicate_forward_document_is_rejected():
    index = InvertedIndex()
    record = {
        "doc_id": 101,
        "terms": [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        ],
    }
    index.add_forward_record(record)

    with pytest.raises(ValueError, match="already been added"):
        index.add_forward_record(record)


def test_build_from_forward_records_preserves_tf_df_and_sorted_postings():
    index = InvertedIndex()
    records = [
        {
            "doc_id": 205,
            "terms": [
                {"term_id": 2, "title_tf": 1, "body_tf": 0, "tag_tf": 2},
                {"term_id": 5, "title_tf": 0, "body_tf": 3, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 2, "title_tf": 0, "body_tf": 2, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 150,
            "terms": [
                {"term_id": 2, "title_tf": 1, "body_tf": 1, "tag_tf": 0},
            ],
        },
    ]

    index.build_from_forward_records(records)

    assert index.get_postings(2) == [
        {"doc_id": 101, "title_tf": 0, "body_tf": 2, "tag_tf": 0},
        {"doc_id": 150, "title_tf": 1, "body_tf": 1, "tag_tf": 0},
        {"doc_id": 205, "title_tf": 1, "body_tf": 0, "tag_tf": 2},
    ]
    assert index.get_postings(5) == [
        {"doc_id": 205, "title_tf": 0, "body_tf": 3, "tag_tf": 0}
    ]
    assert index.get_document_frequency(2) == 3
    assert index.get_document_frequency(5) == 1
    assert index.df == {2: 3, 5: 1}


def test_build_from_empty_iterable_replaces_index_with_empty_index():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )

    index.build_from_forward_records([])

    assert index.get_index() == {}
    assert index.df == {}
    assert len(index) == 0


def test_build_from_forward_records_accepts_generator():
    records = (
        {
            "doc_id": doc_id,
            "terms": [
                {"term_id": 3, "title_tf": doc_id, "body_tf": 0, "tag_tf": 0},
            ],
        }
        for doc_id in (2, 1)
    )
    index = InvertedIndex()

    index.build_from_forward_records(records)

    assert index.get_postings(3) == [
        {"doc_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        {"doc_id": 2, "title_tf": 2, "body_tf": 0, "tag_tf": 0},
    ]
    assert index.get_document_frequency(3) == 2


def test_bulk_build_from_sorted_records_preserves_order_frequencies_and_df():
    records = [
        {
            "doc_id": 10,
            "terms": [
                {"term_id": 2, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                {"term_id": 7, "title_tf": 0, "body_tf": 2, "tag_tf": 1},
            ],
        },
        {"doc_id": 20, "terms": []},
        {
            "doc_id": 30,
            "terms": [
                {"term_id": 2, "title_tf": 0, "body_tf": 1, "tag_tf": 1},
                {"term_id": 7, "title_tf": 3, "body_tf": 0, "tag_tf": 0},
            ],
        },
    ]
    index = InvertedIndex()

    index.build_from_forward_records(records)

    assert index.get_postings(2) == [
        {"doc_id": 10, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        {"doc_id": 30, "title_tf": 0, "body_tf": 1, "tag_tf": 1},
    ]
    assert index.get_postings(7) == [
        {"doc_id": 10, "title_tf": 0, "body_tf": 2, "tag_tf": 1},
        {"doc_id": 30, "title_tf": 3, "body_tf": 0, "tag_tf": 0},
    ]
    assert index.get_document_frequency(2) == 2
    assert index.get_document_frequency(7) == 2
    assert index.validate() is True


def test_bulk_build_sorts_unsorted_documents_once_and_returns_sorted_postings():
    records = [
        {
            "doc_id": 30,
            "terms": [
                {"term_id": 4, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 10,
            "terms": [
                {"term_id": 4, "title_tf": 0, "body_tf": 2, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 20,
            "terms": [
                {"term_id": 4, "title_tf": 0, "body_tf": 0, "tag_tf": 3},
            ],
        },
    ]
    index = InvertedIndex()

    index.build_from_forward_records(records)

    assert index.get_postings(4) == [
        {"doc_id": 10, "title_tf": 0, "body_tf": 2, "tag_tf": 0},
        {"doc_id": 20, "title_tf": 0, "body_tf": 0, "tag_tf": 3},
        {"doc_id": 30, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
    ]
    assert index.get_document_frequency(4) == 3


def test_build_from_forward_records_rejects_duplicate_document_ids():
    record = {
        "doc_id": 101,
        "terms": [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        ],
    }

    with pytest.raises(ValueError, match="already been added"):
        InvertedIndex().build_from_forward_records([record, record])


def test_bulk_build_rejects_duplicate_term_entries():
    record = {
        "doc_id": 101,
        "terms": [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
        ],
    }

    with pytest.raises(ValueError, match="duplicate term_id"):
        InvertedIndex().build_from_forward_records([record])


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (
            {"doc_id": True, "terms": []},
            "doc_id",
        ),
        (
            {
                "doc_id": 1,
                "terms": [
                    {"term_id": True, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                ],
            },
            "term_id",
        ),
        (
            {
                "doc_id": 1,
                "terms": [
                    {"term_id": 1, "title_tf": True, "body_tf": 0, "tag_tf": 0},
                ],
            },
            "frequency",
        ),
        (
            {
                "doc_id": 1,
                "terms": [
                    {"term_id": 1, "title_tf": -1, "body_tf": 0, "tag_tf": 0},
                ],
            },
            "frequency",
        ),
        (
            {
                "doc_id": 1,
                "terms": [
                    {"term_id": 1, "title_tf": 0, "body_tf": 0, "tag_tf": 0},
                ],
            },
            "non-zero TF",
        ),
    ],
)
def test_bulk_build_rejects_invalid_record_values(record, message):
    with pytest.raises(ValueError, match=message):
        InvertedIndex().build_from_forward_records([record])


def test_build_from_forward_records_failure_is_atomic():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 50,
            "terms": [
                {"term_id": 9, "title_tf": 2, "body_tf": 1, "tag_tf": 0},
            ],
        }
    )
    index_before = index.get_index()
    df_before = index.df
    records = [
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 102,
            "terms": [
                {"term_id": 2, "title_tf": 0, "body_tf": 0, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 103,
            "terms": [
                {"term_id": 3, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
            ],
        },
    ]

    with pytest.raises(ValueError, match="non-zero TF"):
        index.build_from_forward_records(records)

    assert index.get_index() == index_before
    assert index.df == df_before
    assert index.get_postings(1) == []
    assert index.get_postings(3) == []


def test_build_from_forward_records_is_atomic_when_iterator_raises():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 50,
            "terms": [
                {"term_id": 9, "title_tf": 2, "body_tf": 1, "tag_tf": 0},
            ],
        }
    )
    index_before = index.get_index()
    df_before = index.df

    def records():
        yield {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
        raise RuntimeError("record iterator failed")

    with pytest.raises(RuntimeError, match="record iterator failed"):
        index.build_from_forward_records(records())

    assert index.get_index() == index_before
    assert index.df == df_before


def test_build_from_forward_records_rebuilds_instead_of_appending():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 50,
            "terms": [
                {"term_id": 9, "title_tf": 2, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )

    index.build_from_forward_records(
        [
            {
                "doc_id": 101,
                "terms": [
                    {"term_id": 1, "title_tf": 0, "body_tf": 4, "tag_tf": 0},
                ],
            }
        ]
    )

    assert index.get_index() == {
        1: [{"doc_id": 101, "title_tf": 0, "body_tf": 4, "tag_tf": 0}]
    }
    assert index.get_document_frequency(1) == 1
    assert index.get_postings(9) == []


def test_build_from_forward_records_does_not_modify_input_records():
    records = [
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 2, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 102,
            "terms": [
                {"term_id": 1, "title_tf": 0, "body_tf": 1, "tag_tf": 1},
            ],
        },
    ]
    records_before = [
        {"doc_id": record["doc_id"], "terms": [dict(term) for term in record["terms"]]}
        for record in records
    ]

    InvertedIndex().build_from_forward_records(records)

    assert records == records_before


def test_valid_index_passes_validate():
    index = InvertedIndex()
    index.add_document(
        101,
        term_frequencies={
            1: {"title_tf": 1, "body_tf": 2, "tag_tf": 0},
            2: {"tag_tf": 3},
        },
    )

    assert index.validate() is True


def test_empty_index_passes_validate():
    assert InvertedIndex().validate() is True


@pytest.mark.parametrize(
    ("corruption", "match"),
    [
        (lambda index: index._index.__setitem__(True, []), "term_id"),
        (lambda index: index._index.__setitem__(1, []), "empty postings"),
        (
            lambda index: index._index.__setitem__(
                1, [{"doc_id": 0, "title_tf": 1, "body_tf": 0, "tag_tf": 0}]
            ),
            "doc_id",
        ),
        (
            lambda index: index._index.__setitem__(
                1, [{"doc_id": 101, "title_tf": -1, "body_tf": 0, "tag_tf": 0}]
            ),
            "title_tf",
        ),
        (
            lambda index: index._index.__setitem__(
                1, [{"doc_id": 101, "title_tf": 0, "body_tf": 0, "tag_tf": 0}]
            ),
            "non-zero TF",
        ),
    ],
)
def test_validate_detects_corrupted_internal_state(corruption, match):
    index = InvertedIndex()
    index.add_document(
        101,
        term_frequencies={1: {"title_tf": 1, "body_tf": 0, "tag_tf": 0}},
    )
    corruption(index)

    with pytest.raises(ValueError, match=match):
        index.validate()


@pytest.mark.parametrize(
    ("postings", "match"),
    [
        (
            [{"doc_id": 101, "title_tf": True, "body_tf": 0, "tag_tf": 0}],
            "title_tf",
        ),
        (
            [{"doc_id": 101, "title_tf": 0, "body_tf": True, "tag_tf": 0}],
            "body_tf",
        ),
        (
            [{"doc_id": 101, "title_tf": 0, "body_tf": 0, "tag_tf": True}],
            "tag_tf",
        ),
        (
            [
                {"doc_id": 101, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
            ],
            "duplicate document ID",
        ),
        (
            [
                {"doc_id": 102, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                {"doc_id": 101, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
            ],
            "strictly increasing",
        ),
        (
            [{"doc_id": 101, "title_tf": 1, "body_tf": 0, "tag_tf": 0, "extra": 1}],
            "unexpected or missing fields",
        ),
    ],
)
def test_validate_detects_posting_invariants(postings, match):
    index = InvertedIndex()
    index._index = {1: postings}
    index._document_ids = {101, 102}

    with pytest.raises(ValueError, match=match):
        index.validate()


def test_valid_index_matches_forward_records():
    records = [
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 2, "tag_tf": 0},
                {"term_id": 2, "title_tf": 0, "body_tf": 0, "tag_tf": 3},
            ],
        }
    ]
    index = InvertedIndex()
    index.build_from_forward_records(records)

    assert index.validate_against_forward_records(records) is True


def test_validate_against_forward_records_accepts_unsorted_records():
    records = [
        {
            "doc_id": 30,
            "terms": [
                {"term_id": 1, "title_tf": 0, "body_tf": 2, "tag_tf": 0},
            ],
        },
        {
            "doc_id": 10,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        },
    ]
    index = InvertedIndex()
    index.build_from_forward_records(records)

    assert index.validate_against_forward_records(records) is True


def test_validate_against_lexicon_rejects_missing_lexicon_term():
    class Lexicon:
        document_frequency = {1: 1, 2: 1}

        def get_term(self, term_id):
            return {1: "first", 2: "second"}.get(term_id)

    index = InvertedIndex()
    index.add_posting(1, 10, title_tf=1)

    with pytest.raises(ValueError, match="term_id=2"):
        index.validate_against_lexicon(Lexicon())


def test_validate_against_forward_records_accepts_generator():
    records = (
        {
            "doc_id": doc_id,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
        for doc_id in (101, 102)
    )
    index = InvertedIndex()
    index.build_from_forward_records(
        [
            {
                "doc_id": 101,
                "terms": [
                    {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                ],
            },
            {
                "doc_id": 102,
                "terms": [
                    {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                ],
            },
        ]
    )

    assert index.validate_against_forward_records(records) is True


def test_validate_against_forward_records_detects_missing_posting():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )

    with pytest.raises(ValueError, match="missing posting"):
        index.validate_against_forward_records(
            [
                {
                    "doc_id": 101,
                    "terms": [
                        {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                        {"term_id": 2, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
                    ],
                }
            ]
        )


def test_validate_against_forward_records_detects_extra_posting():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                {"term_id": 2, "title_tf": 0, "body_tf": 1, "tag_tf": 0},
            ],
        }
    )

    with pytest.raises(ValueError, match="extra posting"):
        index.validate_against_forward_records(
            [
                {
                    "doc_id": 101,
                    "terms": [
                        {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                    ],
                }
            ]
        )


@pytest.mark.parametrize(
    ("field_name", "forward_value", "message"),
    [
        ("title_tf", 1, "incorrect title_tf"),
        ("body_tf", 1, "incorrect body_tf"),
        ("tag_tf", 1, "incorrect tag_tf"),
    ],
)
def test_validate_against_forward_records_detects_incorrect_field_tf(
    field_name,
    forward_value,
    message,
):
    index = InvertedIndex()
    index.add_posting(
        1,
        101,
        title_tf=2 if field_name == "title_tf" else 0,
        body_tf=2 if field_name == "body_tf" else 0,
        tag_tf=2 if field_name == "tag_tf" else 0,
    )
    term = {
        "term_id": 1,
        "title_tf": 0,
        "body_tf": 0,
        "tag_tf": 0,
    }
    term[field_name] = forward_value

    with pytest.raises(ValueError, match=message):
        index.validate_against_forward_records(
            [{"doc_id": 101, "terms": [term]}]
        )


def test_validate_against_forward_records_detects_missing_document():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )

    with pytest.raises(ValueError, match="missing document"):
        index.validate_against_forward_records(
            [
                {
                    "doc_id": 101,
                    "terms": [
                        {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                    ],
                },
                {
                    "doc_id": 102,
                    "terms": [
                        {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                    ],
                },
            ]
        )


def test_validate_against_forward_records_detects_extra_document():
    index = InvertedIndex()
    index.add_forward_record(
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )
    index.add_forward_record(
        {
            "doc_id": 102,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
    )

    with pytest.raises(ValueError, match="extra document"):
        index.validate_against_forward_records(
            [
                {
                    "doc_id": 101,
                    "terms": [
                        {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
                    ],
                }
            ]
        )


def test_validate_against_forward_records_rejects_duplicate_document_ids():
    record = {
        "doc_id": 101,
        "terms": [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        ],
    }

    with pytest.raises(ValueError, match="already been added"):
        InvertedIndex().validate_against_forward_records([record, record])


@pytest.mark.parametrize(
    "record",
    [
        None,
        {"terms": []},
        {"doc_id": 101},
        {"doc_id": True, "terms": []},
        {"doc_id": 101, "terms": "not-a-list"},
    ],
)
def test_validate_against_forward_records_rejects_malformed_records(record):
    with pytest.raises(ValueError):
        InvertedIndex().validate_against_forward_records([record])


def test_validate_against_forward_records_propagates_iterator_exception():
    def records():
        yield {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
            ],
        }
        raise RuntimeError("forward iterator failed")

    index = InvertedIndex()
    index.add_posting(1, 101, title_tf=1)

    with pytest.raises(RuntimeError, match="forward iterator failed"):
        index.validate_against_forward_records(records())


def test_validation_does_not_mutate_index():
    index = InvertedIndex()
    index.add_document(101, term_frequencies={1: {"body_tf": 2}})
    index_before = index.get_index()
    df_before = index.df

    assert index.validate() is True

    assert index.get_index() == index_before
    assert index.df == df_before


def test_validate_against_forward_records_does_not_mutate_input_records():
    records = [
        {
            "doc_id": 101,
            "terms": [
                {"term_id": 1, "title_tf": 1, "body_tf": 2, "tag_tf": 0},
            ],
        }
    ]
    records_before = [
        {"doc_id": record["doc_id"], "terms": [dict(term) for term in record["terms"]]}
        for record in records
    ]
    index = InvertedIndex()
    index.build_from_forward_records(records)

    assert index.validate_against_forward_records(records) is True
    assert records == records_before
