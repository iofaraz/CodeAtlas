import json
from collections import Counter
from pathlib import Path

TOKEN_FIELDS = ("title_tokens", "body_tokens", "tag_tokens")
LEXICON_FILENAME = "lexicon.json"


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
    def __init__(self, term_to_id=None, id_to_term=None, term_to_df=None):
        self.term_to_id = dict(term_to_id) if term_to_id is not None else {}
        self.id_to_term = dict(id_to_term) if id_to_term is not None else {}
        self.term_to_df = dict(term_to_df) if term_to_df is not None else {}
        if self.term_to_id or self.id_to_term or self.term_to_df:
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
        term_to_df = {}

        for idx, term in enumerate(sorted_terms, start=1):
            term_to_id[term] = idx
            id_to_term[idx] = term
            term_to_df[term] = doc_freq_counter[term]

        return cls(
            term_to_id=term_to_id,
            id_to_term=id_to_term,
            term_to_df=term_to_df,
        )

    def validate(self):
        n_terms = len(self.term_to_id)

        if len(self.id_to_term) != n_terms:
            raise ValueError(
                f"Inconsistent mapping sizes: term_to_id has {n_terms} entries, "
                f"id_to_term has {len(self.id_to_term)} entries."
            )

        if len(self.term_to_df) != n_terms:
            raise ValueError(
                f"Inconsistent statistics size: term_to_id has {n_terms} entries, "
                f"term_to_df has {len(self.term_to_df)} entries."
            )

        seen_ids = set()
        for term, term_id in self.term_to_id.items():
            if not term or not isinstance(term, str):
                raise ValueError(f"Invalid term in lexicon: {term!r}")

            if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
                raise ValueError(f"Invalid term_id {term_id!r} for term {term!r}; must be a positive int.")

            if term_id in seen_ids:
                raise ValueError(f"Duplicate term_id {term_id} detected.")
            seen_ids.add(term_id)

            if term_id not in self.id_to_term:
                raise ValueError(f"term_id {term_id} for term {term!r} missing from id_to_term.")

            if self.id_to_term[term_id] != term:
                raise ValueError(
                    f"Duplicate or conflicting mapping for term_id {term_id}: "
                    f"term_to_id has {term!r}, id_to_term has {self.id_to_term[term_id]!r}."
                )

            if term not in self.term_to_df:
                raise ValueError(f"Term {term!r} missing from term_to_df.")

            df = self.term_to_df[term]
            if isinstance(df, bool) or not isinstance(df, int) or df < 1:
                raise ValueError(f"Invalid document frequency {df!r} for term {term!r}; must be >= 1.")

    def get_term_id(self, term):
        normalized = _normalize_term(term)
        if not normalized:
            return None
        return self.term_to_id.get(normalized)

    def get_term(self, term_id):
        if isinstance(term_id, bool) or not isinstance(term_id, int):
            return None
        return self.id_to_term.get(term_id)

    def get_document_frequency(self, term_id):
        term = self.get_term(term_id)
        if term is None:
            return None
        return self.term_to_df.get(term)

    def save(self, output_dir):
        self.validate()
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        target_file = out_path / LEXICON_FILENAME

        entries = []
        for term in sorted(self.term_to_id.keys(), key=lambda t: self.term_to_id[t]):
            entries.append({
                "term_id": self.term_to_id[term],
                "term": term,
                "df": self.term_to_df[term],
            })

        payload = {"entries": entries}

        with target_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")

        return target_file

    @classmethod
    def load(cls, input_dir):
        in_path = Path(input_dir) / LEXICON_FILENAME
        if not in_path.is_file():
            raise FileNotFoundError(f"Lexicon file not found at: {in_path}")

        with in_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "entries" not in data or not isinstance(data["entries"], list):
            raise ValueError(f"Malformed lexicon file at {in_path}: expected top-level 'entries' list.")

        term_to_id = {}
        id_to_term = {}
        term_to_df = {}

        for entry in data["entries"]:
            if not isinstance(entry, dict):
                raise ValueError(f"Malformed lexicon entry: {entry!r}")

            if "term" not in entry or "term_id" not in entry or "df" not in entry:
                raise ValueError(f"Lexicon entry missing required keys ('term', 'term_id', 'df'): {entry!r}")

            term = _normalize_term(entry["term"])
            term_id = entry["term_id"]
            df = entry["df"]

            if not term:
                raise ValueError("Lexicon entry contains an empty term.")
            if term in term_to_id:
                raise ValueError(f"Duplicate term in lexicon file: {term!r}")
            if isinstance(term_id, bool) or not isinstance(term_id, int) or term_id < 1:
                raise ValueError(f"Invalid term_id {term_id!r} for term {term!r}")
            if term_id in id_to_term:
                raise ValueError(f"Duplicate term_id {term_id} in lexicon file.")
            if isinstance(df, bool) or not isinstance(df, int) or df < 1:
                raise ValueError(f"Invalid df {df!r} for term {term!r}")

            term_to_id[term] = term_id
            id_to_term[term_id] = term
            term_to_df[term] = df

        return cls(
            term_to_id=term_to_id,
            id_to_term=id_to_term,
            term_to_df=term_to_df,
        )