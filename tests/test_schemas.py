"""Tests for Pydantic schema validation and computed fields.

No system dependencies — no WeasyPrint, no Pango, no display.
Loads fixtures from tests/fixtures/ and validates against the schemas.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.purchase_order import PurchaseOrder
from schemas.invoice import Invoice
from schemas.request_for_quotation import RequestForQuotation

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Valid fixtures load without errors ────────────────────────────────────────

def test_sample_po_loads():
    doc = PurchaseOrder(**load("sample_po.json"))
    assert doc.po_number == "PO-2026-0001"


def test_sample_invoice_loads():
    doc = Invoice(**load("sample_invoice.json"))
    assert doc.invoice_number == "INV-2026-0001"


def test_sample_invoice_contractor_loads():
    doc = Invoice(**load("sample_invoice_contractor.json"))
    assert doc.invoice_number == "INV-2026-C001"


# ── Computed fields: Purchase Order ───────────────────────────────────────────

def test_po_line_item_totals():
    doc = PurchaseOrder(**load("sample_po.json"))
    # Organic Ashwagandha: 50 × 24.00 = 1200.00
    assert doc.line_items[0].total == Decimal("1200.00")
    # Magnesium Glycinate: 25 × 18.50 = 462.50
    assert doc.line_items[1].total == Decimal("462.50")
    # Capsule Filling: 10 × 85.00 = 850.00
    assert doc.line_items[2].total == Decimal("850.00")


def test_po_subtotal():
    doc = PurchaseOrder(**load("sample_po.json"))
    # 1200.00 + 462.50 + 850.00 = 2512.50
    assert doc.subtotal == Decimal("2512.50")


def test_po_tax_amount():
    doc = PurchaseOrder(**load("sample_po.json"))
    # 2512.50 × 0.08 = 201.00
    assert doc.tax_amount == Decimal("201.00")


def test_po_grand_total():
    doc = PurchaseOrder(**load("sample_po.json"))
    # 2512.50 + 201.00 + 15.00 = 2728.50
    assert doc.grand_total == Decimal("2728.50")


def test_po_total_units_excludes_service_lines():
    doc = PurchaseOrder(**load("sample_po.json"))
    # items[0]=50 + items[1]=25; items[2] has count_units=False
    assert doc.total_units == Decimal("75")


# ── Computed fields: Invoice ──────────────────────────────────────────────────

def test_invoice_line_item_totals():
    doc = Invoice(**load("sample_invoice.json"))
    # Product Formulation: 8 × 200.00 = 1600.00
    assert doc.line_items[0].total == Decimal("1600.00")
    # Regulatory Compliance: 3 × 250.00 = 750.00
    assert doc.line_items[1].total == Decimal("750.00")
    # Label Design: 2 × 375.00 = 750.00
    assert doc.line_items[2].total == Decimal("750.00")


def test_invoice_subtotal():
    doc = Invoice(**load("sample_invoice.json"))
    # 1600.00 + 750.00 + 750.00 = 3100.00
    assert doc.subtotal == Decimal("3100.00")


def test_invoice_tax_amount():
    doc = Invoice(**load("sample_invoice.json"))
    # 3100.00 × 0.10 = 310.00
    assert doc.tax_amount == Decimal("310.00")


def test_invoice_grand_total():
    doc = Invoice(**load("sample_invoice.json"))
    # 3100.00 + 310.00 + 0.00 = 3410.00
    assert doc.grand_total == Decimal("3410.00")


def test_invoice_balance_due():
    doc = Invoice(**load("sample_invoice.json"))
    # 3410.00 - 825.00 = 2585.00
    assert doc.balance_due == Decimal("2585.00")


def test_invoice_contractor_no_tax():
    doc = Invoice(**load("sample_invoice_contractor.json"))
    assert doc.tax_rate == Decimal("0.00")
    assert doc.tax_amount == Decimal("0.00")


def test_invoice_contractor_grand_total():
    doc = Invoice(**load("sample_invoice_contractor.json"))
    # 3040.00 + 1140.00 + 260.00 = 4440.00
    assert doc.grand_total == Decimal("4440.00")


def test_invoice_contractor_balance_due_equals_grand_total():
    doc = Invoice(**load("sample_invoice_contractor.json"))
    # amount_paid defaults to 0
    assert doc.balance_due == doc.grand_total


# ── Invalid fixtures raise ValidationError ───────────────────────────────────

# ── annex_terms field: Purchase Order ────────────────────────────────────────

def test_po_annex_terms_true_valid():
    doc = PurchaseOrder(**load("sample_po_with_annex.json"))
    assert doc.annex_terms is True


def test_po_annex_terms_false_normalised():
    raw = load("sample_po.json")
    raw["annex_terms"] = False
    doc = PurchaseOrder(**raw)
    assert doc.annex_terms is None


def test_po_annex_terms_custom_string():
    raw = load("sample_po.json")
    raw["annex_terms"] = "1. Payment\nAll invoices are due net 30."
    doc = PurchaseOrder(**raw)
    assert doc.annex_terms == "1. Payment\nAll invoices are due net 30."


# ── Invalid fixtures raise ValidationError ───────────────────────────────────

def test_invalid_po_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        PurchaseOrder(**load("invalid_po.json"))
    errors = exc_info.value.errors()
    field_paths = [" → ".join(str(p) for p in e["loc"]) for e in errors]
    assert any("tax_rate" in p for p in field_paths)
    assert any("name" in p for p in field_paths)
    assert any("address" in p for p in field_paths)
    assert any("quantity" in p for p in field_paths)


def test_invalid_invoice_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        Invoice(**load("invalid_invoice.json"))
    errors = exc_info.value.errors()
    # missing invoice_number + tax_rate out of range + bill_to.address missing
    assert exc_info.value.error_count() >= 2
    field_paths = [" → ".join(str(p) for p in e["loc"]) for e in errors]
    assert any("invoice_number" in p for p in field_paths)
    assert any("tax_rate" in p for p in field_paths)


# ── Valid fixture: RFQ ────────────────────────────────────────────────────────

def test_sample_rfq_loads():
    doc = RequestForQuotation(**load("sample_rfq.json"))
    assert doc.rfq_number == "RFQ-2026-001"


def test_rfq_spec_sections_loaded():
    doc = RequestForQuotation(**load("sample_rfq.json"))
    assert len(doc.spec_sections) == 2
    # first section has no title
    assert doc.spec_sections[0].title is None
    assert len(doc.spec_sections[0].rows) == 6
    # second section is "Packaging"
    assert doc.spec_sections[1].title == "Packaging"
    assert len(doc.spec_sections[1].rows) == 7


def test_rfq_product_attributes():
    doc = RequestForQuotation(**load("sample_rfq.json"))
    assert len(doc.product_attributes) == 3
    assert doc.product_attributes[0].header == "Capsules per bottle"
    assert doc.product_attributes[0].value == "120"


def test_rfq_valid_until_after_date():
    doc = RequestForQuotation(**load("sample_rfq.json"))
    assert doc.valid_until > doc.issue_date


# ── Invalid fixture: RFQ ──────────────────────────────────────────────────────

def test_invalid_rfq_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        RequestForQuotation(**load("invalid_rfq.json"))
    errors = exc_info.value.errors()
    field_paths = [" → ".join(str(p) for p in e["loc"]) for e in errors]
    # empty rfq_number
    assert any("rfq_number" in p for p in field_paths)
    # spec_sections is empty
    assert any("spec_sections" in p for p in field_paths)
    # rfq_number + spec_sections = at least 2 field errors
    assert exc_info.value.error_count() >= 2


# ── doc_style field: all doc types ────────────────────────────────────────────

def test_po_doc_style_default():
    doc = PurchaseOrder(**load("sample_po.json"))
    assert doc.doc_style == "normal"


def test_po_doc_style_valid_values():
    base = load("sample_po.json")
    for style in ("compact", "normal", "comfortable"):
        doc = PurchaseOrder(**{**base, "doc_style": style})
        assert doc.doc_style == style


def test_po_doc_style_invalid():
    base = load("sample_po.json")
    for bad in ("big", "small", "large", "dense", ""):
        with pytest.raises(ValidationError):
            PurchaseOrder(**{**base, "doc_style": bad})


def test_invoice_doc_style_valid():
    base = load("sample_invoice.json")
    doc = Invoice(**{**base, "doc_style": "compact"})
    assert doc.doc_style == "compact"
    doc2 = Invoice(**{**base, "doc_style": "comfortable"})
    assert doc2.doc_style == "comfortable"


def test_rfq_doc_style_valid():
    base = load("sample_rfq.json")
    doc = RequestForQuotation(**{**base, "doc_style": "comfortable"})
    assert doc.doc_style == "comfortable"


# ── unit_price optional: Purchase Order ───────────────────────────────────────

def test_po_unit_price_optional_line_item_total_is_none():
    raw = load("sample_po.json")
    raw["line_items"][0].pop("unit_price", None)
    raw["line_items"][0]["unit_price"] = None
    doc = PurchaseOrder(**raw)
    assert doc.line_items[0].unit_price is None
    assert doc.line_items[0].total is None


def test_po_subtotal_skips_none_totals():
    doc = PurchaseOrder(**load("sample_po_partial.json"))
    # only the two priced items count: 50*24 + 25*18.5 = 1200 + 462.5 = 1662.50
    assert doc.subtotal == Decimal("1662.50")


def test_po_blanket_subtotal_is_zero():
    doc = PurchaseOrder(**load("sample_po_blanket.json"))
    assert doc.subtotal == Decimal("0.00")
    assert doc.grand_total == Decimal("0.00")


def test_po_unit_price_zero_raises():
    raw = load("sample_po.json")
    raw["line_items"][0]["unit_price"] = 0
    with pytest.raises(ValidationError):
        PurchaseOrder(**raw)


# ── product field: Purchase Order ─────────────────────────────────────────────

def test_po_product_field_optional():
    doc = PurchaseOrder(**load("sample_po.json"))
    assert doc.product is None


def test_po_product_field_set():
    doc = PurchaseOrder(**load("sample_po_blanket.json"))
    assert doc.product == "Eco-Pack 250mL Bottle"


# ── logo field: root-level on PO and Invoice ─────────────────────────────────

def test_po_logo_valid_data_uri():
    raw = load("sample_po.json")
    raw["logo"] = "data:image/png;base64,abc123="
    doc = PurchaseOrder(**raw)
    assert doc.logo == "data:image/png;base64,abc123="


def test_po_logo_rejects_file_path():
    raw = load("sample_po.json")
    raw["logo"] = "/path/to/logo.png"
    with pytest.raises(ValidationError):
        PurchaseOrder(**raw)


def test_invoice_logo_valid_data_uri():
    raw = load("sample_invoice.json")
    raw["logo"] = "data:image/jpeg;base64,abc123="
    doc = Invoice(**raw)
    assert doc.logo == "data:image/jpeg;base64,abc123="


def test_invoice_logo_rejects_url():
    raw = load("sample_invoice.json")
    raw["logo"] = "https://example.com/logo.png"
    with pytest.raises(ValidationError):
        Invoice(**raw)


# ── annex_tables: Purchase Order ──────────────────────────────────────────────

def test_po_annex_tables_default_empty():
    doc = PurchaseOrder(**load("sample_po.json"))
    assert doc.annex_tables == []


def test_po_annex_table_valid():
    doc = PurchaseOrder(**load("sample_po_logistics.json"))
    assert len(doc.annex_tables) == 1
    annex = doc.annex_tables[0]
    assert annex.title == "Logistics Addendum — Shipment Distribution"
    assert len(annex.headers) == 5
    assert len(annex.rows) == 5
    assert len(annex.rows[0]) == 5


def test_po_annex_table_row_mismatch_raises():
    from schemas.purchase_order import TableAnnex
    with pytest.raises(Exception):
        TableAnnex(
            title="Bad Annex",
            headers=["A", "B", "C"],
            rows=[["only", "two"]],
        )


def test_po_annex_table_new_page_default():
    from schemas.purchase_order import TableAnnex
    annex = TableAnnex(headers=["Col"], rows=[["val"]])
    assert annex.new_page is False


def test_po_annex_table_new_page_true():
    from schemas.purchase_order import TableAnnex
    annex = TableAnnex(headers=["Col"], rows=[["val"]], new_page=True)
    assert annex.new_page is True
