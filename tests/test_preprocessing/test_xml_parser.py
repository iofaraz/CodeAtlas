from io import BytesIO
import pytest

from search_engine.preprocessing.pipeline import process_row, parse_tags
from search_engine.preprocessing.xml_parser import iter_post_rows


def synthetic_xml():
    return BytesIO(
        b"""<posts>
        <row Id="10" PostTypeId="1" Title="C++ &amp; Algorithms"
             Body="&lt;p&gt;Use code&lt;/p&gt;" Tags="&lt;c++&gt;&lt;algorithms&gt;"
             Score="7" ViewCount="42" CreationDate="2026-01-02"
             AcceptedAnswerId="11"/>
        <row Id="11" PostTypeId="2" Title="Answer" Body="Answer body"/>
        <row Id="12" PostTypeId="1" Title="" Body="" Score="0"/>
        <row Id="13" PostTypeId="1" Title="Missing metadata" Body="Body"/>
        </posts>"""
    )


def test_xml_parser_extracts_question_and_ignores_answer():
    rows = list(iter_post_rows(synthetic_xml()))
    assert len(rows) == 4
    document = process_row(rows[0])
    assert document is not None
    assert document.doc_id == 10
    assert document.accepted_answer_id == 11
    assert document.score == 7
    assert document.view_count == 42
    assert process_row(rows[1]) is None
    assert process_row(rows[2]) is None


def test_missing_optional_fields():
    document = process_row({
        "Id": "13",
        "PostTypeId": "1",
        "Title": "Missing metadata",
        "Body": "Body",
    })
    assert document is not None
    assert document.tags == []
    assert document.creation_date is None
    assert document.accepted_answer_id is None
    assert document.score == 0
    assert document.view_count == 0


def test_tags_and_metadata():
    document = process_row({
        "Id": "10",
        "PostTypeId": "1",
        "Title": "Title",
        "Body": "Body",
        "Tags": "<c++><algorithms>",
        "Score": "7",
        "ViewCount": "42",
        "CreationDate": "2026-01-02",
        "AcceptedAnswerId": "11",
    })
    assert parse_tags("<c++><algorithms>") == ["c++", "algorithms"]
    assert document.tags == ["c++", "algorithms"]
    assert document.creation_date == "2026-01-02"


def test_empty_xml_raises_clear_value_error():
    with pytest.raises(ValueError, match="Invalid or unreadable XML input"):
        list(iter_post_rows(BytesIO(b"")))


def test_malformed_xml_raises_clear_value_error():
    with pytest.raises(ValueError, match="Invalid or unreadable XML input"):
        list(iter_post_rows(BytesIO(b"<posts><row Id='1'></posts>")))


def test_missing_xml_file_raises_clear_value_error(tmp_path):
    missing = tmp_path / "missing.xml"
    with pytest.raises(ValueError, match="Invalid or unreadable XML input"):
        list(iter_post_rows(str(missing)))
