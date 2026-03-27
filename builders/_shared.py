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

    Every monetary value is a pre-formatted string. `buyer_id` and `sku` are
    included unconditionally; templates gate their columns with the
    `has_buyer_id_column` / `has_sku_column` flags from build_line_items_meta.
    `sku` uses getattr so PO/RFQ line items (which lack the field) return None.
    """
    return [
        {
            "description": item.description,
            "quantity": format_quantity(item.quantity),
            "unit": item.unit,
            "unit_price": format_currency(item.unit_price),
            "total": format_currency(item.total),
            "buyer_id": item.buyer_id,
            "sku": getattr(item, "sku", None),
        }
        for item in doc.line_items
    ]


def build_line_items_meta(doc) -> dict[str, bool | str]:
    """Return boolean/summary flags derived from the line items array.

    Intended to be unpacked into the context: `**build_line_items_meta(doc)`.
    """
    return {
        # Show the Buyer ID column only when at least one item has a buyer_id
        "has_buyer_id_column": any(item.buyer_id for item in doc.line_items),
        # Show the SKU column only when at least one item has a sku (invoice-only field)
        "has_sku_column": any(getattr(item, "sku", None) for item in doc.line_items),
        # Show total units row only when at least one item has count_units=True
        "show_total_units": any(item.count_units for item in doc.line_items),
        "total_units": format_quantity(doc.total_units),
    }


# ── Totals ─────────────────────────────────────────────────────────────────

def build_totals(doc) -> dict[str, bool | str]:
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


# ── Footer ─────────────────────────────────────────────────────────────────

def build_footer_text(party) -> str:
    """Build the one-line footer text from a party object (buyer or issuer).

    Collapses multiline addresses to a single line. Phone and email are
    included only when present. Returns a '·'-separated string for use
    in the doc-footer bar.
    """
    addr_oneline = ", ".join(
        line.strip() for line in party.address.split("\n") if line.strip()
    )
    parts = [party.name, addr_oneline]
    if party.phone:
        parts.append(party.phone)
    if party.email:
        parts.append(party.email)
    return " · ".join(parts)


# ── Template infrastructure ────────────────────────────────────────────────

def get_css_path() -> Markup:
    """Return the file:// URI for the base stylesheet, marked safe."""
    return Markup((ASSETS_DIR / "style.css").as_uri())  # nosec B704


def parse_terms_sections(text: str) -> list[dict]:
    """Parse markdown T&C text into [{title, body}] for the template.

    Recognises ## N. Title headings. If no headings are found, the whole
    text is returned as a single untitled section.
    """
    import re
    pattern = re.compile(
        r"##\s+(?:\d+\.\s+)?(.+?)\n+(.*?)(?=\n##\s|\Z)", re.DOTALL
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return [{"title": None, "body": text.strip()}]
    sections = []
    for m in matches:
        title = m.group(1).strip()
        body_lines = [l.strip() for l in m.group(2).strip().splitlines() if l.strip()]
        body = " ".join(body_lines)
        sections.append({"title": title, "body": body})
    return sections


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


def font_family_css(font_family: str | None) -> str:
    """Return a CSS :root block overriding the font-family variable.

    Rejects values containing CSS injection vectors (semicolons, braces,
    url(), @-rules). Returns an empty string when no font is provided.
    """
    import re
    if not font_family:
        return ""
    if re.search(r'[;{}@]|url\s*\(', font_family, re.IGNORECASE):
        raise ValueError(
            "font_family contains invalid characters. "
            "Provide a plain font stack, e.g. 'Georgia, serif'."
        )
    return f":root {{\n  --font-family: {font_family};\n}}\n"


# ── Document density presets ──────────────────────────────────────────────────

_COMPACT_CSS = """:root {
  --font-size-base:             9pt;
  --font-size-sm:               7.5pt;
  --font-size-xs:               6.5pt;
  --font-size-lg:               12pt;
  --font-size-xl:               19pt;
  --font-size-grand:            10pt;
  --font-size-balance:          11pt;
  --spacing-xs:                 3pt;
  --spacing-sm:                 6pt;
  --spacing-md:                 11pt;
  --spacing-lg:                 17pt;
  --spacing-xl:                 25pt;
  --table-cell-padding:         4pt 6pt;
  --header-padding:             12pt 15pt;
  --header-logo-height:         38pt;
  --table-cell-padding-compact: 3pt 4pt;
  --table-cell-padding-dense:   2pt 3pt;
  --font-size-dense:            6pt;
}
"""

_COMFORTABLE_CSS = """:root {
  --font-size-base:             11pt;
  --font-size-sm:               9.5pt;
  --font-size-xs:               8.5pt;
  --font-size-lg:               16pt;
  --font-size-xl:               25pt;
  --font-size-grand:            12pt;
  --font-size-balance:          15pt;
  --spacing-xs:                 5pt;
  --spacing-sm:                 10pt;
  --spacing-md:                 17pt;
  --spacing-lg:                 27pt;
  --spacing-xl:                 40pt;
  --table-cell-padding:         8pt 11pt;
  --header-padding:             20pt 24pt;
  --header-logo-height:         58pt;
  --table-cell-padding-compact: 6pt 8pt;
  --table-cell-padding-dense:   4pt 6pt;
  --font-size-dense:            8pt;
}
"""


def density_css(style: str | None) -> str:
    """Return a CSS :root block for the requested density preset.

    Returns an empty string for 'normal' (the default) so callers can
    safely concatenate without extra conditionals.
    """
    if not style or style == "normal":
        return ""
    if style == "compact":
        return _COMPACT_CSS
    if style == "comfortable":
        return _COMFORTABLE_CSS
    return ""
