"""Build indexes/inverted/inverted_index.jsonl from the Forward Index.

Run from the repository root:

    python scripts/build_inverted_index.py
    python scripts/build_inverted_index.py --root . --forward-index indexes/forward/forward_index.jsonl
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.search_engine.indexing.inverted_index import (  # noqa: E402
    INVERTED_INDEX_REL_PATH,
    InvertedIndex,
)
from backend.search_engine.indexing.lexicon import Lexicon  # noqa: E402


def iter_forward_records(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Forward Index file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: malformed JSON ({exc})"
                ) from exc
            yield record


def iter_forward_records_with_progress(
    path: Path,
    progress: dict[str, int],
    report_every: int,
):
    for record in iter_forward_records(path):
        yield record
        progress["documents"] += 1
        progress["term_entries"] += len(record["terms"])
        if progress["documents"] % report_every == 0:
            print(
                f"Processed {progress['documents']:,} documents; "
                f"{progress['term_entries']:,} term entries",
                flush=True,
            )


def assert_jsonl_matches(index: InvertedIndex, path: Path, label: str) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, expected in enumerate(index.iter_jsonl_lines(), start=1):
            actual = handle.readline()
            if actual != expected:
                raise ValueError(
                    f"{label} JSONL differs from the index at line {line_number}"
                )
        if handle.readline():
            raise ValueError(f"{label} JSONL contains additional records")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--forward-index",
        type=Path,
        default=None,
        help="default: <root>/indexes/forward/forward_index.jsonl",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="report progress every N accepted Forward records",
    )
    args = parser.parse_args()
    if args.progress_every < 1:
        parser.error("--progress-every must be positive")

    root = args.root.resolve()
    forward_path = (
        args.forward_index.resolve()
        if args.forward_index is not None
        else root / "indexes" / "forward" / "forward_index.jsonl"
    )
    lexicon_path = root / "indexes" / "lexicon" / "lexicon.jsonl"
    output_path = root / INVERTED_INDEX_REL_PATH
    if not lexicon_path.is_file():
        print(
            f"Inverted Index build failed: Lexicon not found at {lexicon_path}",
            file=sys.stderr,
        )
        print("Run: python scripts/build_lexicon.py", file=sys.stderr)
        return 1
    if not forward_path.is_file():
        print(
            f"Inverted Index build failed: Forward Index not found at {forward_path}",
            file=sys.stderr,
        )
        print("Run: python scripts/build_forward_index.py", file=sys.stderr)
        return 1

    started = time.perf_counter()
    try:
        lexicon = Lexicon.load(root)
        print(
            f"Loaded Lexicon: {len(lexicon.term_to_id):,} terms",
            flush=True,
        )
        progress = {"documents": 0, "term_entries": 0}
        build_started = time.perf_counter()
        index = InvertedIndex()
        index.build_from_forward_records(
            iter_forward_records_with_progress(
                forward_path, progress, args.progress_every
            )
        )
        build_seconds = time.perf_counter() - build_started
        print(
            f"Bulk construction complete: {progress['documents']:,} documents, "
            f"{progress['term_entries']:,} term entries in {build_seconds:.1f}s",
            flush=True,
        )

        validation_started = time.perf_counter()
        print("Validating structure and cross-index consistency...", flush=True)
        index.validate()
        index.validate_against_lexicon(lexicon)
        index.validate_against_forward_records(
            iter_forward_records(forward_path)
        )
        built_df = index.df
        built_term_count = len(index)
        built_posting_count = sum(built_df.values())

        if built_term_count != len(lexicon.term_to_id):
            raise ValueError(
                f"term count mismatch: Forward-derived Inverted Index has "
                f"{built_term_count}, Lexicon has {len(lexicon.term_to_id)}"
            )
        if built_posting_count != progress["term_entries"]:
            raise ValueError(
                f"posting count mismatch: Inverted Index has "
                f"{built_posting_count}, Forward Index has "
                f"{progress['term_entries']} term entries"
            )
        validation_seconds = time.perf_counter() - validation_started
        print(
            f"Full validation complete in {validation_seconds:.1f}s",
            flush=True,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".inverted-index-stage-", dir=str(root)
        ) as staging_dir:
            staged_root = Path(staging_dir)
            print("Saving staged JSONL...", flush=True)
            staged_path = index.save(staged_root)
            assert_jsonl_matches(index, staged_path, "saved")
            print("Staged JSONL matches the built index.", flush=True)

            del index
            gc.collect()

            print("Reloading staged JSONL into a fresh InvertedIndex...", flush=True)
            reloaded = InvertedIndex.load(staged_root, lexicon)
            reloaded_df = reloaded.df
            reloaded_posting_count = sum(reloaded_df.values())
            if (
                len(reloaded) != built_term_count
                or reloaded_posting_count != built_posting_count
                or reloaded_df != built_df
            ):
                raise ValueError("Inverted Index round-trip summary mismatch")
            assert_jsonl_matches(reloaded, staged_path, "reloaded")
            print("Reloaded index matches the staged JSONL.", flush=True)

            os.replace(staged_path, output_path)
    except KeyboardInterrupt:
        print(
            "Inverted Index build interrupted; existing output was preserved.",
            file=sys.stderr,
            flush=True,
        )
        return 130
    except (FileNotFoundError, OSError, ValueError, MemoryError) as exc:
        print(f"Inverted Index build failed: {exc}", file=sys.stderr)
        return 1

    total_seconds = time.perf_counter() - started
    print(f"Vocabulary terms  : {len(lexicon.term_to_id):,}")
    print(f"Documents processed: {progress['documents']:,}")
    print(f"Forward term entries: {progress['term_entries']:,}")
    print(f"Inverted postings : {built_posting_count:,}")
    print(f"Bulk build        : {build_seconds:.1f}s")
    print(f"Full validation   : {validation_seconds:.1f}s")
    print(f"Total elapsed     : {total_seconds:.1f}s")
    print(f"Output file       : {output_path}")
    print(f"Output size       : {output_path.stat().st_size:,} bytes")
    print("Validation        : passed (structure, Lexicon, exact Forward postings)")
    print("Reload comparison : passed (summary and exact JSONL contents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
