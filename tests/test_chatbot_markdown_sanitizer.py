from pathlib import Path


CHATBOT_JS = Path(__file__).resolve().parents[1] / "web" / "static" / "js" / "chatbot.js"


def test_chatbot_markdown_uses_sanitized_render_path():
    source = CHATBOT_JS.read_text(encoding="utf-8")

    assert "function renderSafeMarkdown" in source
    assert "sanitizeMarkdownFragment(template.content)" in source
    assert "innerHTML = marked.parse" not in source


def test_chatbot_markdown_sanitizer_blocks_common_xss_vectors():
    source = CHATBOT_JS.read_text(encoding="utf-8")

    assert 'name.startsWith("on")' in source
    assert 'name === "srcdoc"' in source
    assert "URL_ATTRIBUTES.has(name)" in source
    assert '"javascript:"' not in source
    assert '["http:", "https:", "mailto:", "tel:"]' in source
