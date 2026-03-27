"""Direct unit tests for the pure helper functions in builders/_shared.py."""
import pytest
from decimal import Decimal

from builders._shared import (
    primary_color_css,
    font_family_css,
    parse_terms_sections,
    build_footer_text,
)

def test_primary_color_css_returns_empty_when_none():
    assert primary_color_css(None) == ""
    assert primary_color_css("") == ""

def test_primary_color_css_injects_color():
    css = primary_color_css("#FF0000")
    assert "--color-primary: #FF0000;" in css
    assert "--color-bg-header: #FF0000;" in css

def test_font_family_css_rejects_injections():
    with pytest.raises(ValueError):
        font_family_css("Arial; background: red;")
    
    with pytest.raises(ValueError):
        font_family_css("url(http://evil.com)")

def test_font_family_css_accepts_clean_fonts():
    css = font_family_css("Inter, sans-serif")
    assert "--font-family: Inter, sans-serif;" in css

def test_parse_terms_sections_splits_headings():
    text = "## 1. Terms\nBody 1\n## 2. Conditions\nBody 2"
    sections = parse_terms_sections(text)
    assert len(sections) == 2
    assert sections[0]["title"] == "Terms"
    assert sections[0]["body"] == "Body 1"
    assert sections[1]["title"] == "Conditions"
    assert sections[1]["body"] == "Body 2"

def test_parse_terms_sections_handles_no_headings():
    text = "Just some text without any headings."
    sections = parse_terms_sections(text)
    assert len(sections) == 1
    assert sections[0]["title"] is None
    assert sections[0]["body"] == "Just some text without any headings."

class DummyParty:
    def __init__(self, name, address, phone=None, email=None):
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email

def test_build_footer_text():
    party = DummyParty("Acme Corp", "123 Main St\nSuite 100", "555-1234", "bot@acme.com")
    text = build_footer_text(party)
    assert text == "Acme Corp · 123 Main St, Suite 100 · 555-1234 · bot@acme.com"

def test_build_footer_text_omits_none():
    party = DummyParty("Acme Corp", "123 Main St")
    text = build_footer_text(party)
    assert text == "Acme Corp · 123 Main St"
