"""Context builder for Invoice documents.

Source of truth: references/invoice.md
Do not add or remove context keys without updating that file first.

Receives a validated Invoice model instance; returns a dict of
display-ready strings consumed by templates/invoice.html.
No raw Decimal or date objects are allowed in the return value (ADR-002).
"""
from __future__ import annotations

from markupsafe import Markup

from schemas.invoice import Invoice
from utils.formatting import format_currency, format_date
from utils.logo import resolve_logo
from builders._shared import (
    build_footer_text,
    build_line_items,
    build_line_items_meta,
    build_totals,
    get_css_path,
    primary_color_css,
)
from utils.paths import ASSETS_DIR


# Invoice-specific component styles loaded from assets/invoice.css.
# Injected as an inline <style> block via the `theme_css` context variable.
# All values reference CSS custom properties from the design system —
# no hardcoded colours, sizes, or fonts.
# See references/DESIGN_SYSTEM.md for the full variable reference.
_INVOICE_CSS: str = (ASSETS_DIR / "invoice.css").read_text(encoding="utf-8")


def build_invoice_context(doc: Invoice) -> dict:
    """Build the full Jinja2 template context for an Invoice."""
    logo_data = resolve_logo(doc.issuer.logo)

    # Derive payment status for the status strip.
    # This is a display-only computed value — never accepted from user input.
    if doc.paid:
        document_status, status_label = "paid", "Paid"
    elif doc.amount_paid > 0:
        document_status, status_label = "partial", "Partially Paid"
    else:
        document_status, status_label = None, None

    return {
        # ── Header ────────────────────────────────────────────────────────
        "invoice_number": doc.invoice_number,
        "issue_date": format_date(doc.issue_date),
        "due_date": format_date(doc.due_date) if doc.due_date else None,
        "document_status": document_status,
        "status_label": status_label,

        # ── Parties ───────────────────────────────────────────────────────
        "issuer": {
            "name": doc.issuer.name,
            "address": doc.issuer.address,
            "contact_name": doc.issuer.contact_name,
            "email": doc.issuer.email,
            "phone": doc.issuer.phone,
            "logo": Markup(logo_data) if logo_data else None,
        },
        "bill_to": {
            "name": doc.bill_to.name,
            "address": doc.bill_to.address,
            "contact_name": doc.bill_to.contact_name,
            "email": doc.bill_to.email,
            "phone": doc.bill_to.phone,
        },

        # ── Meta band ─────────────────────────────────────────────────────
        "payment_terms": doc.payment_terms,

        # ── Line items ────────────────────────────────────────────────────
        "line_items": build_line_items(doc),
        **build_line_items_meta(doc),

        # ── Totals ────────────────────────────────────────────────────────
        **build_totals(doc),
        "amount_paid": format_currency(doc.amount_paid),
        "balance_due": format_currency(doc.balance_due),
        "show_amount_paid": doc.amount_paid > 0,

        # ── Payment details ───────────────────────────────────────────────
        "payment_details": [
            {"label": item.label, "value": item.value}
            for item in doc.payment_details
        ],

        # ── Notes ─────────────────────────────────────────────────────────
        "notes": doc.notes,

        # ── Footer ────────────────────────────────────────────────────────
        # Derived from issuer info — no additional fields needed
        "footer_text": build_footer_text(doc.issuer),

        # ── Template infrastructure ───────────────────────────────────────
        # theme_css: primary colour override (if any) + invoice component styles
        "css_path": get_css_path(),
        "theme_css": Markup(primary_color_css(doc.primary_color) + _INVOICE_CSS),
    }
