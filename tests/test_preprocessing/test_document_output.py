import json
import pytest

from search_engine.preprocessing.document import Document
from search_engine.preprocessing.pipeline import document_to_dict, run_pipeline
import search_engine.preprocessing.pipeline as pipeline_module


def test_jsonl_serialization_and_unicode(tmp_path):
    document = Document(
        doc_id=1,
        title="Résumé",
        body="Unicode café",
        tags=["python"],
        title_tokens=["résumé"],
        body_tokens=["unicode", "café"],
        tag_tokens=["python"],
        document_length=3,
    )
    data = document_to_dict(document)
    output = tmp_path / "documents.jsonl"
    output.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["doc_id"] == 1
    assert loaded["title"] == "Résumé"
    assert loaded["body"] == "Unicode café"
    assert isinstance(loaded["doc_id"], int)
    assert isinstance(loaded["document_length"], int)


def test_pipeline_writes_jsonl_and_report(tmp_path):
    xml = tmp_path / "Posts.xml"
    xml.write_text(
        '<posts><row Id="1" PostTypeId="1" Title="Test title" '
        'Body="Test body" Tags="&lt;test&gt;" Score="2" '
        'ViewCount="10" AcceptedAnswerId="3"/></posts>',
        encoding="utf-8",
    )
    output = tmp_path / "documents.jsonl"
    report = tmp_path / "report.json"
    stats = run_pipeline(xml, output, report)
    assert stats.processed_documents == 1
    assert output.exists()
    assert report.exists()
    assert json.loads(output.read_text(encoding="utf-8").strip())["doc_id"] == 1


def test_pipeline_tracks_empty_fields_duplicates_and_post_types(tmp_path):
    xml = tmp_path / "Posts.xml"
    xml.write_text(
        "<posts>"
        '<row Id="1" PostTypeId="1" Title="" Body="Body one"/>'
        '<row Id="2" PostTypeId="1" Title="Title two" Body=""/>'
        '<row Id="3" PostTypeId="1" Title="" Body=""/>'
        '<row Id="4" PostTypeId="1" Title="Answer-like" Body="Body four"/>'
        '<row Id="4" PostTypeId="1" Title="Duplicate" Body="Duplicate body"/>'
        '<row Id="5" PostTypeId="2" Title="Answer" Body="Answer body"/>'
        "</posts>",
        encoding="utf-8",
    )
    output = tmp_path / "documents.jsonl"
    report = tmp_path / "report.json"

    stats = run_pipeline(xml, output, report)
    lines = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert [item["doc_id"] for item in lines] == [1, 2, 4]
    assert stats.question_records == 5
    assert stats.processed_documents == 3
    assert stats.skipped_records == 2
    assert stats.empty_titles == 2
    assert stats.empty_bodies == 2
    assert stats.questions_with_empty_title_or_body == 3
    assert stats.duplicate_document_ids == 1
    assert stats.documents_with_tags == 0
    assert stats.documents_without_tags == 3
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["statistics"]["questions_with_empty_title_or_body"] == 3
    assert data["document_length_definitions"]["token_count"]
    assert data["document_length_definitions"]["whitespace_word_count"]


def test_successful_run_replaces_existing_output(tmp_path):
    xml = tmp_path / "Posts.xml"
    xml.write_text(
        '<posts><row Id="9" PostTypeId="1" Title="New" Body="Content"/></posts>',
        encoding="utf-8",
    )
    output = tmp_path / "documents.jsonl"
    output.write_text("old incomplete output", encoding="utf-8")
    report = tmp_path / "report.json"

    run_pipeline(xml, output, report)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["doc_id"] == 9


def test_processing_failure_cleans_temporary_output(tmp_path, monkeypatch):
    xml = tmp_path / "Posts.xml"
    xml.write_text(
        '<posts><row Id="1" PostTypeId="1" Title="Title" Body="Body"/></posts>',
        encoding="utf-8",
    )
    output = tmp_path / "documents.jsonl"
    report = tmp_path / "report.json"

    def failing_rows(_source):
        yield {"Id": "1", "PostTypeId": "1", "Title": "Title", "Body": "Body"}
        raise RuntimeError("stream failed")

    monkeypatch.setattr(pipeline_module, "iter_post_rows", failing_rows)
    with pytest.raises(RuntimeError, match="stream failed"):
        run_pipeline(xml, output, report)

    assert not output.with_name(output.name + ".tmp").exists()
