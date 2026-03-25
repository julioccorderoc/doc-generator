"""Context builder for Request for Quotation documents.

Source of truth: references/request_for_quotation.md
Do not add or remove context keys without updating that file first.

Receives a validated RequestForQuotation model instance; returns a dict of
display-ready strings consumed by templates/request_for_quotation.html.
No raw Decimal or date objects are allowed in the return value (ADR-002).
"""
from __future__ import annotations

from markupsafe import Markup

from schemas.request_for_quotation import RequestForQuotation, RFQParty
from utils.formatting import format_date
from utils.logo import resolve_logo
from utils.paths import ASSETS_DIR
from builders._shared import font_family_css, get_css_path, primary_color_css


_RFQ_CSS: str = (ASSETS_DIR / "request_for_quotation.css").read_text(encoding="utf-8")


def _build_party(party: RFQParty) -> dict:
    """Convert an RFQParty model to a display-ready dict."""
    return {
        "name": party.name,
        "address": party.address,
        "phone": party.phone,
        "email": party.email,
        "website": party.website,
    }


def _build_footer_text(issuer: RFQParty) -> str:
    """Build the one-line footer text from the issuer."""
    parts = [issuer.name]
    if issuer.address:
        addr_oneline = ", ".join(
            line.strip() for line in issuer.address.split("\n") if line.strip()
        )
        parts.append(addr_oneline)
    if issuer.phone:
        parts.append(issuer.phone)
    if issuer.email:
        parts.append(issuer.email)
    return " · ".join(parts)


def build_rfq_context(doc: RequestForQuotation) -> dict:
    """Build the full Jinja2 template context for a Request for Quotation."""
    logo_data = resolve_logo(doc.logo)

    # Build spec sections as plain dicts (no Pydantic objects in context)
    spec_sections = [
        {
            "title": section.title,
            "rows": [{"label": row.label, "value": row.value} for row in section.rows],
        }
        for section in doc.spec_sections
    ]

    # Build annexes list; also compute whether any annex has a URL
    annexes = None
    has_any_annex_url = False
    if doc.annexes:
        annexes = [{"title": a.title, "url": a.url} for a in doc.annexes]
        has_any_annex_url = any(a.url for a in doc.annexes)

    # Build contact dict
    contact = None
    if doc.contact:
        contact = {
            "name": doc.contact.name,
            "email": doc.contact.email,
            "phone": doc.contact.phone,
            "website": doc.contact.website,
        }

    # Theme CSS: RFQ-specific styles + optional primary colour override
    theme_css = _RFQ_CSS + primary_color_css(doc.primary_color) + font_family_css(doc.font_family)

    return {
        # ── Header ────────────────────────────────────────────────────────
        "rfq_number": doc.rfq_number,
        "issue_date": format_date(doc.issue_date),
        "valid_until": format_date(doc.valid_until) if doc.valid_until else None,

        # ── Parties ───────────────────────────────────────────────────────
        "issuer": _build_party(doc.issuer),
        "vendor": _build_party(doc.vendor) if doc.vendor else None,

        # ── Product summary ───────────────────────────────────────────────
        "product_name": doc.product_name,
        "product_description": doc.product_description,
        "product_attributes": [
            {"header": a.header, "value": a.value} for a in doc.product_attributes
        ],

        # ── Spec table ────────────────────────────────────────────────────
        "spec_sections": spec_sections,

        # ── Notes ─────────────────────────────────────────────────────────
        "notes": doc.notes,

        # ── Annexes ───────────────────────────────────────────────────────
        "annexes": annexes,
        "has_any_annex_url": has_any_annex_url,

        # ── Contact ───────────────────────────────────────────────────────
        "contact": contact,

        # ── Footer ────────────────────────────────────────────────────────
        "footer_text": _build_footer_text(doc.issuer),

        # ── Logo ──────────────────────────────────────────────────────────
        "logo": logo_data,

        # ── Template infrastructure ───────────────────────────────────────
        "css_path": get_css_path(),
        "theme_css": Markup(theme_css),
    }
