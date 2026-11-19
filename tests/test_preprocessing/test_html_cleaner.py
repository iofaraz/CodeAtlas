from search_engine.preprocessing.html_cleaner import clean_html


def test_removes_tags_and_decodes_entities():
    assert clean_html("<p>Use <b>Python</b> &amp; SQL</p>") == "Use Python & SQL"


def test_preserves_code_text():
    assert "std::vector<int>" in clean_html("<pre><code>std::vector&lt;int&gt;</code></pre>")


def test_empty_and_malformed_html_are_safe():
    assert clean_html("") == ""
    assert clean_html(None) == ""
    assert clean_html("<p>Malformed") == "Malformed"


def test_nested_tags_and_paragraph_boundaries():
    html_text = "<div><p>First <b>nested</b> text</p><p>Second text</p></div>"
    assert clean_html(html_text) == "First nested text Second text"


def test_lists_and_headings_have_separation():
    html_text = "<h2>Title</h2><ul><li>Python</li><li>C++</li></ul>"
    assert clean_html(html_text) == "Title Python C++"


def test_entities_and_special_attributes():
    html_text = '<p title="1 > 0 &amp; 2">Rock &amp; Roll &lt; Python &gt; Java</p>'
    assert clean_html(html_text) == "Rock & Roll < Python > Java"


def test_inline_and_preformatted_code_are_preserved():
    html_text = "<p>Use <code>std::vector</code> and <code>!=</code>.</p><pre><code>int x = 1;\nC++ C#</code></pre>"
    result = clean_html(html_text)
    assert "std::vector" in result
    assert "!=" in result
    assert "int x = 1;" in result
    assert "C++ C#" in result


def test_programming_symbols_are_not_removed():
    assert clean_html("C++ C# &lt;vector&gt;") == "C++ C# <vector>"
    assert clean_html("Use <vector> in C++") == "Use <vector> in C++"


def test_br_preserves_following_text():
    assert clean_html("A<br>B") == "A B"
    assert clean_html("A<br/>B") == "A B"
    assert clean_html("A<br>B<br>C") == "A B C"
