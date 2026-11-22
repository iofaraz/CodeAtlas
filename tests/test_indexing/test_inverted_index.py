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


def test_build_from_forward_records_rejects_duplicate_document_ids():
    record = {
        "doc_id": 101,
        "terms": [
            {"term_id": 1, "title_tf": 1, "body_tf": 0, "tag_tf": 0},
        ],
    }

    with pytest.raises(ValueError, match="already been added"):
        InvertedIndex().build_from_forward_records([record, record])


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
