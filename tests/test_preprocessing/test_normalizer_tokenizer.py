from search_engine.preprocessing.normalizer import normalize_text
from search_engine.preprocessing.tokenizer import tokenize


def test_lowercase_and_whitespace_normalization():
    assert normalize_text("  API   For   C++ \n") == "api for c++"


def test_empty_input():
    assert normalize_text("") == ""
    assert tokenize("") == []


def test_technical_terms_are_preserved_as_possible():
    tokens = tokenize("C++ C# Node.js std::vector O(n) x != y")
    assert "c++" in tokens
    assert "c#" in tokens
    assert "node.js" in tokens
    assert "std::vector" in tokens
    assert "o(n)" in tokens
    assert "!=" in tokens


def test_tokenization_is_consistent():
    text = "Python API python"
    assert tokenize(text) == tokenize(text)


def test_multiple_whitespace_newlines_and_tabs():
    assert normalize_text("  Alpha\tBeta\n\nGamma   Delta  ") == "alpha beta gamma delta"
    assert tokenize("Alpha\tBeta\nGamma") == ["alpha", "beta", "gamma"]


def test_unicode_normalization():
    decomposed = "Cafe\u0301"
    assert normalize_text(decomposed) == "café"
    assert tokenize(decomposed) == ["café"]


def test_none_input():
    assert normalize_text(None) == ""
    assert tokenize(None) == []


def test_mixed_case_and_technical_punctuation():
    assert tokenize("API api Html HTML") == ["api", "api", "html", "html"]
    assert tokenize("a==b x!=y n<=m q>=p") == ["a", "==", "b", "x", "!=", "y", "n", "<=", "m", "q", ">=", "p"]


def test_repeated_words_and_deterministic_output():
    assert tokenize("Python python PYTHON") == ["python", "python", "python"]
