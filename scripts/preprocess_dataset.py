from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from search_engine.preprocessing.pipeline import run_pipeline


def main() -> int:
    input_path = PROJECT_ROOT / "data" / "raw" / "Posts.xml"
    output_path = PROJECT_ROOT / "data" / "processed" / "documents.jsonl"
    report_path = PROJECT_ROOT / "data" / "processed" / "dataset_processing_report.json"

    try:
        stats = run_pipeline(input_path, output_path, report_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Preprocessing failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Processed {stats.processed_documents} documents "
        f"from {stats.total_records} XML records "
        f"(median token count: {stats.median_length:.1f}; "
        f"median whitespace word count: "
        f"{stats.median_document_length_words:.1f})."
    )
    print(f"JSONL: {output_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
