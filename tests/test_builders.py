"""Tests for context builder output shape and type-safety.

No system dependencies — no WeasyPrint, no Pango, no display.
Calls builder functions directly with validated model instances and asserts
on the shape, types, and computed values of the returned context dict.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from schemas.purchase_order import PurchaseOrder
from schemas.invoice import Invoice
from builders.purchase_order import build_po_context
from builders.invoice import build_invoice_context

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _raw_typed_values(obj, path: str = "") -> list[tuple[str, object]]:
    """Recursively collect (path, value) for any raw Decimal or date in obj."""
    found = []
    if isinstance(obj, (Decimal, date)):
        found.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(_raw_typed_values(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_raw_typed_values(v, f"{path}[{i}]"))
    return found


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def po_context():
    doc = PurchaseOrder(**load("sample_po.json"))
    with patch("builders.purchase_order.resolve_logo", return_value=None):
        return build_po_context(doc)


@pytest.fixture
def invoice_context():
    doc = Invoice(**load("sample_invoice.json"))
    with patch("builders.invoice.resolve_logo", return_value=None):
        return build_invoice_context(doc)


@pytest.fixture
def contractor_context():
    doc = Invoice(**load("sample_invoice_contractor.json"))
    with patch("builders.invoice.resolve_logo", return_value=None):
        return build_invoice_context(doc)


# ── PO builder: type safety ───────────────────────────────────────────────────

def test_po_no_raw_decimals_or_dates(po_context):
    raw = _raw_typed_values(po_context)
    assert raw == [], f"Raw Decimal/date objects found in PO context: {raw}"


def test_po_required_keys_present(po_context):
    for key in ("css_path", "line_items", "grand_total", "subtotal"):
        assert key in po_context, f"Missing required context key: {key!r}"


# ── PO builder: show_tax ──────────────────────────────────────────────────────

def test_po_show_tax_true_when_nonzero(po_context):
    # sample_po has tax_rate=0.08
    assert po_context["show_tax"] is True


def test_po_show_tax_false_when_zero():
    raw = load("sample_po.json")
    raw["tax_rate"] = 0.0
    doc = PurchaseOrder(**raw)
    with patch("builders.purchase_order.resolve_logo", return_value=None):
        ctx = build_po_context(doc)
    assert ctx["show_tax"] is False


# ── PO builder: line items ────────────────────────────────────────────────────

def test_po_line_items_count(po_context):
    assert len(po_context["line_items"]) == 3


def test_po_line_item_values(po_context):
    first = po_context["line_items"][0]
    assert first["description"] == "Organic Ashwagandha Extract (KSM-66)"
    # total should be a formatted currency string, not a raw number
    assert isinstance(first["total"], str)
    assert "$" in first["total"]


def test_po_show_total_units(po_context):
    # sample_po has two count_units=True items
    assert po_context["show_total_units"] is True


# ── Invoice builder: type safety ──────────────────────────────────────────────

def test_invoice_no_raw_decimals_or_dates(invoice_context):
    raw = _raw_typed_values(invoice_context)
    assert raw == [], f"Raw Decimal/date objects found in Invoice context: {raw}"


def test_invoice_required_keys_present(invoice_context):
    for key in ("css_path", "line_items", "grand_total", "subtotal"):
        assert key in invoice_context, f"Missing required context key: {key!r}"


# ── Invoice builder: show_tax ─────────────────────────────────────────────────

def test_invoice_show_tax_true_when_nonzero(invoice_context):
    # sample_invoice has tax_rate=0.10
    assert invoice_context["show_tax"] is True


def test_invoice_show_tax_false_for_contractor(contractor_context):
    # contractor has tax_rate=0.00
    assert contractor_context["show_tax"] is False


# ── Invoice builder: show_amount_paid ────────────────────────────────────────

def test_invoice_show_amount_paid_true(invoice_context):
    # sample_invoice has amount_paid=825.00
    assert invoice_context["show_amount_paid"] is True


def test_invoice_show_amount_paid_false_for_contractor(contractor_context):
    # contractor has no amount_paid (defaults to 0)
    assert contractor_context["show_amount_paid"] is False


# ── Invoice builder: document_status derivation ───────────────────────────────

def test_invoice_document_status_paid(invoice_context):
    # sample_invoice has paid=true
    assert invoice_context["document_status"] == "paid"
    assert invoice_context["status_label"] == "Paid"


def test_invoice_document_status_none_when_unpaid(contractor_context):
    # contractor has paid=False, amount_paid=0
    assert contractor_context["document_status"] is None
    assert contractor_context["status_label"] is None


def test_invoice_document_status_partial():
    raw = load("sample_invoice.json")
    raw["paid"] = False
    raw["amount_paid"] = 100.00
    doc = Invoice(**raw)
    with patch("builders.invoice.resolve_logo", return_value=None):
        ctx = build_invoice_context(doc)
    assert ctx["document_status"] == "partial"
    assert ctx["status_label"] == "Partially Paid"
