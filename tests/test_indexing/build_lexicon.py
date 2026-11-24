import json
from backend.search_engine.indexing.lexicon import Lexicon

docs = []
with open("data/processed/documents.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            docs.append(json.loads(line))

lex = Lexicon.build(docs)
lex.save("data/lexicon")
print("Done! Terms:", len(lex.term_to_id))