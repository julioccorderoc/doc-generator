"""Shared context-building helpers used across all document types.

Each helper accepts a validated Pydantic model instance and returns a
fragment of the Jinja2 template context. Builder modules compose these
fragments with dict-unpacking (`**build_totals(doc)`) to avoid repeating
the same field projections in every doc type.

All monetary values are returned as pre-formatted strings. No raw
Decimal or date objects ever reach a template (ADR-002).
"""
from __future__ import annotations

from markupsafe import Markup

from utils.formatting import format_currency, format_quantity, format_tax_rate
from utils.paths import ASSETS_DIR


# ── Line items ─────────────────────────────────────────────────────────────

def build_line_items(doc) -> list[dict]:
    """Return a display-ready list of line item dicts for any doc type.

    Every monetary value is a pre-formatted string. `sku` is included
    unconditionally; templates gate the column with `has_sku_column`.
    """
    return [
        {
            "description": item.description,
            "quantity": format_quantity(item.quantity),
            "unit": item.unit,
            "unit_price": format_currency(item.unit_price),
            "total": format_currency(item.total),
            "sku": item.sku,
        }
        for item in doc.line_items
    ]


def build_line_items_meta(doc) -> dict:
    """Return boolean/summary flags derived from the line items array.

    Intended to be unpacked into the context: `**build_line_items_meta(doc)`.
    """
    return {
        # Show the SKU column only when at least one item has a SKU
        "has_sku_column": any(item.sku for item in doc.line_items),
        # Show total units row only when at least one item has count_units=True
        "show_total_units": any(item.count_units for item in doc.line_items),
        "total_units": format_quantity(doc.total_units),
    }


# ── Totals ─────────────────────────────────────────────────────────────────

def build_totals(doc) -> dict:
    """Return all standard totals-table values as formatted strings.

    Intended to be unpacked into the context: `**build_totals(doc)`.
    Includes the `show_tax` / `show_shipping` booleans so templates
    never contain arithmetic or comparison logic.
    """
    return {
        "subtotal": format_currency(doc.subtotal),
        "tax_rate_pct": format_tax_rate(doc.tax_rate),
        "tax_amount": format_currency(doc.tax_amount),
        "shipping_cost": format_currency(doc.shipping_cost),
        "grand_total": format_currency(doc.grand_total),
        "show_tax": doc.tax_rate > 0,
        "show_shipping": doc.shipping_cost > 0,
    }


# ── Template infrastructure ────────────────────────────────────────────────

def get_css_path() -> Markup:
    """Return the file:// URI for the base stylesheet, marked safe."""
    return Markup((ASSETS_DIR / "style.css").as_uri())


def primary_color_css(color: str | None) -> str:
    """Return a CSS :root block overriding the primary colour variables.

    Returns an empty string when no colour is provided so callers can
    safely concatenate without extra conditionals.
    """
    if not color:
        return ""
    return (
        f":root {{\n"
        f"  --color-primary: {color};\n"
        f"  --color-bg-header: {color};\n"
        f"}}\n"
    )
