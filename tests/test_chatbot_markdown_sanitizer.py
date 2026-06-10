from pathlib import Path


MARKDOWN_JS = Path(__file__).resolve().parents[1] / "web" / "static" / "js" / "markdown.js"
CHATBOT_JS = Path(__file__).resolve().parents[1] / "web" / "static" / "js" / "chatbot.js"


def test_chatbot_markdown_uses_sanitized_render_path():
    # After the ES6 refactor, sanitizer logic lives in markdown.js
    source = MARKDOWN_JS.read_text(encoding="utf-8")

    assert "function renderSafeMarkdown" in source
    assert "sanitizeMarkdownFragment(template.content)" in source
    assert "innerHTML = marked.parse" not in source


def test_chatbot_markdown_sanitizer_blocks_common_xss_vectors():
    # After the ES6 refactor, sanitizer logic lives in markdown.js
    source = MARKDOWN_JS.read_text(encoding="utf-8")

    assert 'name.startsWith("on")' in source
    assert 'name === "srcdoc"' in source
    assert "URL_ATTRIBUTES.has(name)" in source
    assert '"javascript:"' not in source
    assert '["http:", "https:", "mailto:", "tel:"]' in source


def test_chatbot_js_imports_markdown_module():
    # Verify chatbot.js no longer contains inline sanitizer logic
    # and instead delegates to the markdown module via ES6 imports
    source = CHATBOT_JS.read_text(encoding="utf-8")

    assert "innerHTML = marked.parse" not in source
    assert "function renderSafeMarkdown" not in source
