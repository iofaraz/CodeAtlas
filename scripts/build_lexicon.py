"""Build indexes/lexicon/lexicon.jsonl from the Phase 2 documents.

Run from the repository root:

    python scripts/build_lexicon.py
    python scripts/build_lexicon.py --root . --documents data/processed/documents.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.search_engine.indexing.lexicon import Lexicon  # noqa: E402


def iter_documents(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Preprocessed documents file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: malformed JSON ({exc})"
                ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--documents",
        type=Path,
        default=None,
        help="default: <root>/data/processed/documents.jsonl",
    )
    args = parser.parse_args()

    documents_path = args.documents or args.root / "data/processed/documents.jsonl"
    try:
        start = time.perf_counter()
        lexicon = Lexicon.build(iter_documents(documents_path))
        lexicon.validate()
        path = lexicon.save(args.root)
        reloaded = Lexicon.load(args.root)
        if reloaded.term_to_id != lexicon.term_to_id:
            raise ValueError("Lexicon round-trip changed term-ID mappings")
        if reloaded.document_frequency != lexicon.document_frequency:
            raise ValueError("Lexicon round-trip changed document frequencies")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"Lexicon build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Vocabulary size   : {len(lexicon.term_to_id):,}")
    print(f"Build + validate  : {time.perf_counter() - start:.1f}s")
    print(f"Output file       : {path}")
    print("Reload identical  : True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())