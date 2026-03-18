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
    get_css_path,
    parse_terms_sections,
    primary_color_css,
)

_PO_CSS: str = (ASSETS_DIR / "purchase_order.css").read_text(encoding="utf-8")
_TERMS_PRESET: str = (ROOT / "references" / "po_terms_conditions.md").read_text(
    encoding="utf-8"
)


def build_po_context(doc: PurchaseOrder) -> dict:
    """Build the full Jinja2 template context for a Purchase Order."""
    logo_data = resolve_logo(doc.buyer.logo)

    return {
        # ── Header ────────────────────────────────────────────────────────
        "po_number": doc.po_number,
        "issue_date": format_date(doc.issue_date),
        "delivery_date": format_date(doc.delivery_date) if doc.delivery_date else None,

        # ── Parties ───────────────────────────────────────────────────────
        "buyer": {
            "name": doc.buyer.name,
            "address": doc.buyer.address,
            "contact_name": doc.buyer.contact_name,
            "email": doc.buyer.email,
            "phone": doc.buyer.phone,
            "logo": Markup(logo_data) if logo_data else None,
        },
        "vendor": {
            "name": doc.vendor.name,
            "address": doc.vendor.address,
            "contact_name": doc.vendor.contact_name,
            "email": doc.vendor.email,
            "phone": doc.vendor.phone,
        },

        # ── Meta band ─────────────────────────────────────────────────────
        "payment_terms": doc.payment_terms,
        "shipping_method": doc.shipping_method,

        # ── Line items ────────────────────────────────────────────────────
        "line_items": build_line_items(doc),
        **build_line_items_meta(doc),

        # ── Totals ────────────────────────────────────────────────────────
        **build_totals(doc),

        # ── Notes ─────────────────────────────────────────────────────────
        "notes": doc.notes,

        # ── Footer ────────────────────────────────────────────────────────
        # Derived from buyer info — no additional fields needed
        "footer_text": build_footer_text(doc.buyer),

        # ── T&C annex ─────────────────────────────────────────────────────
        "terms_sections": (
            parse_terms_sections(_TERMS_PRESET) if doc.annex_terms is True
            else parse_terms_sections(doc.annex_terms) if isinstance(doc.annex_terms, str) and doc.annex_terms.strip()
            else None
        ),

        # ── Template infrastructure ───────────────────────────────────────
        # css_path: absolute file:// URI for base stylesheet (required by base.html)
        # theme_css: optional :root override injected as inline <style> block
        "css_path": get_css_path(),
        "theme_css": Markup(_PO_CSS + (primary_color_css(doc.primary_color) or "")),
    }
