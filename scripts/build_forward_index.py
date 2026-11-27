"""Build indexes/forward/forward_index.jsonl from the Phase 2 documents.

Run from the repository root:

    python scripts/build_forward_index.py
    python scripts/build_forward_index.py --root . --documents data/processed/documents.jsonl

Reads ``<root>/indexes/lexicon/lexicon.jsonl`` and writes
``<root>/indexes/forward/forward_index.jsonl`` (``--root`` is the repository
root, matching ``Lexicon.load/save``). Uses Rafay's ``Lexicon`` class when
``backend/search_engine/indexing/lexicon.py`` exists, otherwise a small read-only
adapter over ``lexicon.jsonl``. After building, it checks that every term's
document frequency matches the Lexicon's ``df``. Faraz's ``index_builder.py`` is
the real orchestrator; this script only builds the Forward Index.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.search_engine.indexing.forward_index import (  # noqa: E402
        ForwardIndex,
    iter_documents_jsonl,
)


class JsonlLexiconAdapter:
    """Minimal read-only Lexicon over lexicon.jsonl (fallback only)."""

    def __init__(self, path: Path) -> None:
        self._term_to_id: dict[str, int] = {}
        self._id_to_term: dict[int, str] = {}
        self.document_frequency: dict[int, int] = {}
        with open(path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                term, term_id = record["term"], record["term_id"]
                if term in self._term_to_id or term_id in self._id_to_term:
                    raise ValueError(f"{path}:{line_number}: duplicate term or term_id")
                self._term_to_id[term] = term_id
                self._id_to_term[term_id] = term
                self.document_frequency[term_id] = record["df"]

    def get_term_id(self, term: str):
        return self._term_to_id.get(term)

    def get_term(self, term_id: int):
        return self._id_to_term.get(term_id)

    def get_document_frequency(self, term_id: int):
        return self.document_frequency.get(term_id)

    def __len__(self) -> int:
        return len(self._term_to_id)


def load_lexicon(root: Path):
    try:
        from backend.search_engine.indexing.lexicon import Lexicon  # type: ignore
    except ImportError:
        print("lexicon.py not found; using JSONL adapter over lexicon.jsonl")
        return JsonlLexiconAdapter(root / "indexes" / "lexicon" / "lexicon.jsonl")
    print("Using Lexicon from backend/search_engine/indexing/lexicon.py")
    return Lexicon.load(root)


def peak_ram_mb() -> str:
    """Peak RSS if measurable on this platform, otherwise 'not measured'."""
    try:
        import resource  # Linux / macOS

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return f"{peak / (1024 if sys.platform != 'darwin' else 1024 * 1024):.0f} MB"
    except ImportError:
        pass
    try:
        import psutil  # optional

        info = psutil.Process().memory_info()
        return f"{getattr(info, 'peak_wset', info.rss) / 1024 / 1024:.0f} MB"
    except ImportError:
        return "not measured (pip install psutil to measure on Windows)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--documents", type=Path, default=None,
                        help="default: <root>/data/processed/documents.jsonl")
    parser.add_argument("--expected-docs", type=int, default=50083)
    args = parser.parse_args()
    documents_path = args.documents or args.root / "data/processed/documents.jsonl"

    start = time.perf_counter()
    lexicon = load_lexicon(args.root)
    print(f"Lexicon loaded in {time.perf_counter() - start:.1f}s")

    build_start = time.perf_counter()
    index = ForwardIndex.build(iter_documents_jsonl(documents_path), lexicon)
    index.validate(lexicon)
    index.verify_document_frequencies(lexicon)  # forward-index df must equal Lexicon df
    build_seconds = time.perf_counter() - build_start

    path = index.save(args.root)
    reloaded = ForwardIndex.load(args.root, lexicon)
    reload_ok = reloaded.doc_ids() == index.doc_ids() and all(
        reloaded.get_document_terms(d) == index.get_document_terms(d) for d in index.doc_ids()
    )

    entries = sum(len(index.get_document_terms(d)) for d in index.doc_ids())
    print(f"Documents indexed : {len(index):,} (expected {args.expected_docs:,})")
    print(f"Term entries      : {entries:,}")
    print("Lexicon df check  : passed (every term's df matches the Lexicon)")
    print(f"Build + validate  : {build_seconds:.1f}s")
    print(f"Output file       : {path} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Reload identical  : {reload_ok}")
    print(f"Peak RAM          : {peak_ram_mb()}")

    if len(index) != args.expected_docs:
        print("WARNING: document count differs from the expected Phase 2 count", file=sys.stderr)
        return 1
    return 0 if reload_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
