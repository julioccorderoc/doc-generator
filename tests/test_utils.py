"""Tests for utility functions: formatting, logo resolution, and file naming."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import utils.file_naming as fn_module
from utils.formatting import format_currency, format_quantity, format_tax_rate
from utils.logo import resolve_logo


# ── format_currency ───────────────────────────────────────────────────────────

def test_format_currency_typical():
    assert format_currency(Decimal("1234.56")) == "$1,234.56"


def test_format_currency_zero():
    assert format_currency(Decimal("0")) == "$0.00"


# ── format_quantity ───────────────────────────────────────────────────────────

def test_format_quantity_integer_like():
    assert format_quantity(Decimal("75")) == "75"


def test_format_quantity_non_integer():
    assert format_quantity(Decimal("1.5")) == "1.5"


# ── format_tax_rate ───────────────────────────────────────────────────────────

def test_format_tax_rate_whole_percent():
    assert format_tax_rate(Decimal("0.08")) == "8%"


# ── resolve_logo ──────────────────────────────────────────────────────────────

def test_resolve_logo_none():
    assert resolve_logo(None) is None


def test_resolve_logo_data_uri_returned_as_is():
    uri = "data:image/png;base64,abc123"
    assert resolve_logo(uri) == uri


def test_resolve_logo_file_path_raises():
    with pytest.raises(ValueError):
        resolve_logo("/some/path/logo.png")


def test_resolve_logo_url_raises():
    with pytest.raises(ValueError):
        resolve_logo("https://example.com/logo.png")


# ── next_output_filename ──────────────────────────────────────────────────────

def test_next_output_filename_auto_naming(tmp_path, monkeypatch):
    monkeypatch.setattr(fn_module, "OUTPUT_DIR", tmp_path)
    result = fn_module.next_output_filename("invoice")
    today = date.today().strftime("%Y%m%d")
    assert result.name == f"invoice_{today}_0001.pdf"


def test_next_output_filename_increments(tmp_path, monkeypatch):
    monkeypatch.setattr(fn_module, "OUTPUT_DIR", tmp_path)
    result1 = fn_module.next_output_filename("invoice")
    result1.touch()  # simulate the file being written
    result2 = fn_module.next_output_filename("invoice")
    today = date.today().strftime("%Y%m%d")
    assert result1.name == f"invoice_{today}_0001.pdf"
    assert result2.name == f"invoice_{today}_0002.pdf"


def test_next_output_filename_custom_name(tmp_path, monkeypatch):
    monkeypatch.setattr(fn_module, "OUTPUT_DIR", tmp_path)
    result = fn_module.next_output_filename("invoice", name="INV-2026-0001")
    assert result.name == "invoice_INV-2026-0001.pdf"


def test_next_output_filename_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(fn_module, "OUTPUT_DIR", tmp_path)
    with pytest.raises(ValueError):
        fn_module.next_output_filename("invoice", name="../evil")
