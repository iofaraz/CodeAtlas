import json
from collections import Counter
from pathlib import Path

TOKEN_FIELDS = ("title_tokens", "body_tokens", "tag_tokens")
LEXICON_REL_PATH = Path("indexes/lexicon/lexicon.jsonl")


def _extract_field_tokens(doc, field_name):
    if isinstance(doc, dict):
        raw = doc.get(field_name)
    else:
        raw = getattr(doc, field_name, None)

    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return raw


def _normalize_term(term):
    if not isinstance(term, str):
        raise ValueError(f"Term must be a string, got {type(term).__name__}: {term!r}")
    return term.strip().lower()


class Lexicon:
    def __init__(self, term_to_id=None, id_to_term=None, document_frequency=None):
        self.term_to_id = dict(term_to_id) if term_to_id is not None else {}
        self.id_to_term = dict(id_to_term) if id_to_term is not None else {}
        self.document_frequency = dict(document_frequency) if document_frequency is not None else {}
        if self.term_to_id or self.id_to_term or self.document_frequency:
            self.validate()

    @classmethod
    def build(cls, documents):
        doc_freq_counter = Counter()

        for doc in documents:
            doc_unique_terms = set()
            for field in TOKEN_FIELDS:
                for raw_token in _extract_field_tokens(doc, field):
                    term = _normalize_term(raw_token)
                    if term:
                        doc_unique_terms.add(term)

            for term in doc_unique_terms:
                doc_freq_counter[term] += 1

        sorted_terms = sorted(doc_freq_counter.keys())
        term_to_id = {}
        id_to_term = {}
        document_frequency = {}

        for term_id, term in enumerate(sorted_terms, start=1):
            term_to_id[term] = term_id
            id_to_term[term_id] = term
            document_frequency[term_id] = doc_freq_counter[term]

        return cls(
            term_to_id=term_to_id,
            id_to_term=id_to_term,
            document_frequency=document_frequency,
        )

    def validate(self):
        n_terms = len(self.term_to_id)

        if len(self.id_to_term) != n_terms:
            raise ValueError(
                f"Inconsistent mapping sizes: term_to_id has {n_terms} entries, "
                f"id_to_term has {len(self.id_to_term)} entries."
            )

        if len(self.document_frequency) != n_terms:
            raise ValueError(
                f"Inconsistent statistics size: term_to_id has {n_terms} entries, "
                f"document_frequency has {len(self.document_frequency)} entries."
            )

        seen_ids = set()
        for term, term_id in self.term_to_id.items():
            if not term or not isinstance(term, str):
                raise ValueError(f"Invalid term in lexicon: {term!r}")

            # 0 is reserved as invalid/unassigned, so valid IDs must be >= 1
            if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
                raise ValueError(f"Invalid term_id {term_id!r} for term {term!r}; must be >= 1.")

            if term_id in seen_ids:
                raise ValueError(f"Duplicate term_id {term_id} detected.")
            seen_ids.add(term_id)

            if term_id not in self.id_to_term:
                raise ValueError(f"term_id {term_id} for term {term!r} missing from id_to_term.")

            if self.id_to_term[term_id] != term:
                raise ValueError(
                    f"Conflicting mapping for term_id {term_id}: "
                    f"term_to_id has {term!r}, id_to_term has {self.id_to_term[term_id]!r}."
                )

            if term_id not in self.document_frequency:
                raise ValueError(f"term_id {term_id} missing from document_frequency.")

            df = self.document_frequency[term_id]
            if isinstance(df, bool) or not isinstance(df, int) or df < 1:
                raise ValueError(f"Invalid df {df!r} for term_id {term_id}; must be >= 1.")

    def get_term_id(self, term):
        normalized = _normalize_term(term)
        if not normalized:
            return None
        return self.term_to_id.get(normalized)

    def get_term(self, term_id):
        if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
            return None
        return self.id_to_term.get(term_id)

    def get_document_frequency(self, term_id):
        if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
            return None
        return self.document_frequency.get(term_id)

    def save(self, output_dir):
        self.validate()
        target_file = Path(output_dir) / LEXICON_REL_PATH
        target_file.parent.mkdir(parents=True, exist_ok=True)

        with target_file.open("w", encoding="utf-8") as f:
            for term_id in sorted(self.id_to_term.keys()):
                row = {
                    "term_id": term_id,
                    "term": self.id_to_term[term_id],
                    "df": self.document_frequency[term_id],
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        return target_file

    @classmethod
    def load(cls, input_dir):
        in_path = Path(input_dir) / LEXICON_REL_PATH
        if not in_path.is_file():
            raise FileNotFoundError(f"Lexicon file not found at: {in_path}")

        term_to_id = {}
        id_to_term = {}
        document_frequency = {}

        with in_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                entry = json.loads(stripped)
                if not isinstance(entry, dict):
                    raise ValueError(f"Malformed entry on line {line_num}: {entry!r}")

                for key in ("term_id", "term", "df"):
                    if key not in entry:
                        raise ValueError(f"Missing '{key}' on line {line_num}: {entry!r}")

                term = _normalize_term(entry["term"])
                term_id = entry["term_id"]
                df = entry["df"]

                if not term:
                    raise ValueError(f"Empty term on line {line_num}")
                if term in term_to_id:
                    raise ValueError(f"Duplicate term {term!r} on line {line_num}")
                if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
                    raise ValueError(f"Invalid term_id {term_id!r} on line {line_num}")
                if term_id in id_to_term:
                    raise ValueError(f"Duplicate term_id {term_id} on line {line_num}")
                if isinstance(df, bool) or not isinstance(df, int) or df < 1:
                    raise ValueError(f"Invalid df {df!r} on line {line_num}")

                term_to_id[term] = term_id
                id_to_term[term_id] = term
                document_frequency[term_id] = df

        return cls(
            term_to_id=term_to_id,
            id_to_term=id_to_term,
            document_frequency=document_frequency,
        )