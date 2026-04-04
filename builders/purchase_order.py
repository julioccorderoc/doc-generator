"""Context builder for Purchase Order documents.

Source of truth: references/purchase_order.md
Do not add or remove context keys without updating that file first.

Receives a validated PurchaseOrder model instance; returns a dict of
display-ready strings consumed by templates/purchase_order.html.
No raw Decimal or date objects are allowed in the return value (ADR-002).
"""
from __future__ import annotations

from markupsafe import Markup

from schemas.purchase_order import PurchaseOrder
from utils.formatting import format_date
from utils.logo import resolve_logo
from utils.paths import ASSETS_DIR, ROOT
from builders._shared import (
    build_footer_text,
    build_line_items,
    build_line_items_meta,
    build_totals,
    density_css,
    font_family_css,
    get_css_path,
    parse_terms_sections,
    primary_color_css,
)

_PO_CSS: str = (ASSETS_DIR / "purchase_order.css").read_text(encoding="utf-8")


def _build_po_line_items(doc: PurchaseOrder) -> list[dict]:
    """Extend the shared line items with PO-only identifier columns."""
    items = build_line_items(doc)
    for item_dict, item in zip(items, doc.line_items):
        item_dict["vendor_id"] = item.vendor_id
        item_dict["barcode"] = item.barcode
    return items


def _build_po_line_items_meta(doc: PurchaseOrder) -> dict:
    """Extend the shared meta flags with PO-only column visibility and pricing-state flags."""
    shared = build_line_items_meta(doc)
    has_vendor_id = any(item.vendor_id for item in doc.line_items)
    has_barcode = any(item.barcode for item in doc.line_items)
    active_id_cols = sum([shared["has_buyer_id_column"], has_vendor_id, has_barcode])

    has_unit_price_column = any(item.unit_price is not None for item in doc.line_items)
    is_partial_pricing = has_unit_price_column and any(item.unit_price is None for item in doc.line_items)
    is_fully_unpriced = not has_unit_price_column

    return {
        **shared,
        "has_vendor_id_column": has_vendor_id,
        "has_barcode_column": has_barcode,
        "active_id_cols": active_id_cols,
        "has_unit_price_column": has_unit_price_column,
        "is_partial_pricing": is_partial_pricing,
        "is_fully_unpriced": is_fully_unpriced,
    }
_TERMS_PRESET: str = (ROOT / "references" / "po_terms_conditions.md").read_text(
    encoding="utf-8"
)


_PARTIAL_PRICING_NOTE = (
    "* Prices marked TBD are not included in totals. "
    "Final amount subject to confirmation."
)


def build_po_context(doc: PurchaseOrder) -> dict:
    """Build the full Jinja2 template context for a Purchase Order."""
    logo_data = resolve_logo(doc.logo)
    line_items_meta = _build_po_line_items_meta(doc)
    is_partial_pricing = line_items_meta["is_partial_pricing"]

    # Auto-append estimation disclaimer when some lines lack a unit price
    if is_partial_pricing:
        notes = (doc.notes + "\n\n" + _PARTIAL_PRICING_NOTE) if doc.notes else _PARTIAL_PRICING_NOTE
    else:
        notes = doc.notes

    subtotal_label = "Est. Subtotal *" if is_partial_pricing else "Subtotal"
    grand_total_label = "Est. Grand Total *" if is_partial_pricing else "Grand Total"

    return {
        # ── Header ────────────────────────────────────────────────────────
        "po_number": doc.po_number,
        "issue_date": format_date(doc.issue_date),
        "delivery_date": format_date(doc.delivery_date) if doc.delivery_date else None,

        # ── Header logo ───────────────────────────────────────────────────
        "logo": logo_data,

        # ── Parties ───────────────────────────────────────────────────────
        "buyer": {
            "name": doc.buyer.name,
            "address": doc.buyer.address,
            "contact_name": doc.buyer.contact_name,
            "email": doc.buyer.email,
            "phone": doc.buyer.phone,
        },
        "vendor": {
            "name": doc.vendor.name,
            "address": doc.vendor.address,
            "contact_name": doc.vendor.contact_name,
            "email": doc.vendor.email,
            "phone": doc.vendor.phone,
        },

        # ── Meta band ─────────────────────────────────────────────────────
        "product": doc.product,
        "payment_terms": doc.payment_terms,
        "shipping_method": doc.shipping_method,

        # ── Line items ────────────────────────────────────────────────────
        "line_items": _build_po_line_items(doc),
        **line_items_meta,

        # ── Totals ────────────────────────────────────────────────────────
        **build_totals(doc),
        "subtotal_label": subtotal_label,
        "grand_total_label": grand_total_label,

        # ── Notes ─────────────────────────────────────────────────────────
        "notes": notes,

        # ── Footer ────────────────────────────────────────────────────────
        "footer_text": build_footer_text(doc.buyer),

        # ── T&C annex ─────────────────────────────────────────────────────
        "terms_sections": (
            parse_terms_sections(_TERMS_PRESET) if doc.annex_terms is True
            else parse_terms_sections(doc.annex_terms) if isinstance(doc.annex_terms, str) and doc.annex_terms.strip()
            else None
        ),

        # ── Tabular annexes ───────────────────────────────────────────────
        "annex_tables": [
            {
                "title": t.title,
                "headers": t.headers,
                "rows": t.rows,
            }
            for t in doc.annex_tables
        ],

        # ── Template infrastructure ───────────────────────────────────────
        "css_path": get_css_path(),
        "theme_css": Markup(  # nosec B704
            _PO_CSS
            + primary_color_css(doc.primary_color)
            + font_family_css(doc.font_family)
            + density_css(doc.doc_style)
        ),
    }
