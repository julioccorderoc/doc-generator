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
    build_line_items,
    build_line_items_meta,
    build_totals,
    get_css_path,
    primary_color_css,
)


# Invoice-specific component styles.
#
# Injected as an inline <style> block via the `theme_css` context variable.
# Lives here (not in assets/style.css) because these classes are only
# relevant to this document type. All values reference CSS custom properties
# from the design system — no hardcoded colours, sizes, or fonts.
#
# See references/DESIGN_SYSTEM.md for the full variable reference.
_INVOICE_CSS = """
/* ── Invoice-specific component styles ─────────────────── */

/* Status strip — rendered between header and address block */
.status-strip {
    padding: 6pt 20pt;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-bold);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: var(--spacing-lg);
    border-radius: var(--radius-sm);
}

.status-strip--paid {
    background: #f0fdf4;
    color: #15803d;
    border-left: 3pt solid #16a34a;
}

.status-strip--partial {
    background: #fffbeb;
    color: #b45309;
    border-left: 3pt solid #f59e0b;
}

/* Amount Paid row — green text both columns */
.totals__table .totals__amount-paid td:first-child { color: #16a34a; }
.totals__table .totals__amount-paid td:last-child  { color: #16a34a; font-weight: var(--font-weight-medium); }

/* Balance Due — 2pt accent rule above, bold primary, no background fill.
   Qualified with .totals__table (specificity 0,2,1) to beat the base
   .totals__table td:first-child rule (specificity 0,1,2). */
.totals__table .totals__balance td {
    border-top: 2pt solid var(--color-accent);
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-balance);
    padding-top: var(--spacing-xs);
    padding-bottom: var(--spacing-sm);
}

.totals__table .totals__balance td:first-child {
    color: var(--color-primary);
}

.totals__table .totals__balance td:last-child {
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
}

.payment-details {
    margin-top: var(--spacing-md);
    border-top: 1pt solid var(--color-border-light);
    padding-top: var(--spacing-md);
}

.payment-details__title {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted);
    margin-bottom: var(--spacing-sm);
}

.payment-details__table { border-collapse: collapse; }

.payment-details__label {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    padding: 3pt var(--spacing-md) 3pt 0;
    white-space: nowrap;
}

.payment-details__value {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    padding: 3pt 0;
}
"""


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

        # ── Template infrastructure ───────────────────────────────────────
        # theme_css: primary colour override (if any) + invoice component styles
        "css_path": get_css_path(),
        "theme_css": Markup(primary_color_css(doc.primary_color) + _INVOICE_CSS),
    }
