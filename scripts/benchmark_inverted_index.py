"""Compare legacy and optimized Inverted Index construction on synthetic data.

Run from the repository root:

    python scripts/benchmark_inverted_index.py
    python scripts/benchmark_inverted_index.py --documents 500 --terms-per-document 16

The timed sections cover construction only; data generation, equality checks,
validation, and serialization are excluded.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.search_engine.indexing.inverted_index import InvertedIndex


def make_records(document_count: int, terms_per_document: int) -> list[dict]:
    return [
        {
            "doc_id": doc_id,
            "terms": [
                {
                    "term_id": term_id,
                    "title_tf": 1 if doc_id % 2 == 0 else 0,
                    "body_tf": 1 if doc_id % 2 else 0,
                    "tag_tf": 1 if term_id % 3 == 0 else 0,
                }
                for term_id in range(1, terms_per_document + 1)
            ],
        }
        for doc_id in range(1, document_count + 1)
    ]


def build_legacy(records: list[dict]) -> dict[int, list[dict[str, int]]]:
    """Reproduce the old duplicate scans and per-posting list sort."""
    index: dict[int, list[dict[str, int]]] = {}
    seen_documents: set[int] = set()

    for record in records:
        doc_id = record["doc_id"]
        if doc_id in seen_documents:
            raise ValueError(f"duplicate document {doc_id}")

        terms = record["terms"]
        for term in terms:
            term_id = term["term_id"]
            for posting in index.get(term_id, []):
                if posting["doc_id"] == doc_id:
                    raise ValueError("duplicate posting")

        for term in terms:
            term_id = term["term_id"]
            postings = index.setdefault(term_id, [])
            for posting in postings:
                if posting["doc_id"] == doc_id:
                    raise ValueError("duplicate posting")
            postings.append(
                {
                    "doc_id": doc_id,
                    "title_tf": term["title_tf"],
                    "body_tf": term["body_tf"],
                    "tag_tf": term["tag_tf"],
                }
            )
            postings.sort(key=lambda posting: posting["doc_id"])

        seen_documents.add(doc_id)

    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--documents", type=int, default=500)
    parser.add_argument("--terms-per-document", type=int, default=16)
    args = parser.parse_args()
    if args.documents < 1 or args.terms_per_document < 1:
        parser.error("--documents and --terms-per-document must be positive")

    records = make_records(args.documents, args.terms_per_document)
    term_entry_count = args.documents * args.terms_per_document

    start = time.perf_counter()
    legacy = build_legacy(records)
    legacy_seconds = time.perf_counter() - start

    optimized_index = InvertedIndex()
    start = time.perf_counter()
    optimized_index.build_from_forward_records(records)
    optimized_seconds = time.perf_counter() - start

    if optimized_index.get_index() != legacy:
        raise ValueError("legacy and optimized construction results differ")

    print(f"Documents          : {args.documents:,}")
    print(f"Term entries       : {term_entry_count:,}")
    print(f"Legacy build       : {legacy_seconds:.6f}s")
    print(f"Optimized build    : {optimized_seconds:.6f}s")
    print("Timed work         : construction only")
    print("Validation included: no")
    print("Serialization      : not included")
    print("Indexes equivalent : True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
