#!/usr/bin/env python3
"""
doc-generator CLI entrypoint.

Usage:
    uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview]

See CLAUDE.md § CLI Contract for the full interface specification.
See docs/decisions/003-file-path-payload.md for why --payload is a file path.
See docs/decisions/004-argparse-only-cli.md for why we use argparse.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Resolve the project root relative to this file so imports and path
# lookups work regardless of the caller's working directory.
ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"

sys.path.insert(0, str(ROOT))

from markupsafe import Markup
from pydantic import ValidationError
from jinja2 import Environment, FileSystemLoader
import weasyprint

from schemas.purchase_order import PurchaseOrder
from utils.file_naming import next_output_filename
from utils.formatting import format_currency, format_date, format_quantity, format_tax_rate
from utils.logo import resolve_logo
from utils.preview import open_preview


# ── Registry ──────────────────────────────────────────────────────────────
# Maps doc_type slug → (PydanticModel, template_filename)
# Adding a new document type = one line here. Nothing else changes.

REGISTRY: dict[str, tuple[type, str]] = {
    "purchase_order": (PurchaseOrder, "purchase_order.html"),
}


# ── Context builders ───────────────────────────────────────────────────────
# One builder per doc type. Receives a validated model instance; returns
# a dict of display-ready strings for the Jinja2 template.
# Raw Decimal/date objects must never reach the template.
# See docs/decisions/002-python-only-formatting.md.

def _build_po_context(doc: PurchaseOrder) -> dict:
    logo_data = resolve_logo(doc.buyer.logo)

    return {
        # Header
        "po_number": doc.po_number,
        "issue_date": format_date(doc.issue_date),
        "delivery_date": format_date(doc.delivery_date) if doc.delivery_date else None,
        # Parties
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
        # Meta band
        "payment_terms": doc.payment_terms,
        "shipping_method": doc.shipping_method,
        # Line items — all monetary values pre-formatted
        "line_items": [
            {
                "description": item.description,
                "quantity": format_quantity(item.quantity),
                "unit": item.unit,
                "unit_price": format_currency(item.unit_price),
                "total": format_currency(item.total),
                "sku": item.sku,
            }
            for item in doc.line_items
        ],
        "has_sku_column": any(item.sku for item in doc.line_items),
        # Unit total (only shown when at least one item has count_units=True)
        "show_total_units": any(item.count_units for item in doc.line_items),
        "total_units": format_quantity(doc.total_units),
        # Totals
        "subtotal": format_currency(doc.subtotal),
        "tax_rate_pct": format_tax_rate(doc.tax_rate),
        "tax_amount": format_currency(doc.tax_amount),
        "shipping_cost": format_currency(doc.shipping_cost),
        "grand_total": format_currency(doc.grand_total),
        "show_tax": doc.tax_rate > 0,
        "show_shipping": doc.shipping_cost > 0,
        # Notes
        "notes": doc.notes,
        # Template infrastructure — mark as safe (trusted paths we generate)
        "css_path": Markup((ASSETS_DIR / "style.css").as_uri()),
    }


CONTEXT_BUILDERS: dict[str, callable] = {
    "purchase_order": _build_po_context,
}


# ── Jinja2 environment ─────────────────────────────────────────────────────

def _make_jinja_env() -> Environment:
    from markupsafe import Markup, escape

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    def nl2br(value: str) -> Markup:
        """Replace newlines with <br> tags, safely escaping user content."""
        return Markup(escape(value).replace("\n", Markup("<br>\n")))

    env.filters["nl2br"] = nl2br
    return env


# ── Error formatting ───────────────────────────────────────────────────────

def _format_validation_errors(exc: ValidationError) -> str:
    lines = ["Validation failed:"]
    for error in exc.errors():
        loc = " → ".join(str(p) for p in error["loc"])
        msg = error["msg"].removeprefix("Value error, ")
        lines.append(f"  {loc}: {msg}")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Generate a PDF document from a JSON payload.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported doc types: " + ", ".join(REGISTRY) + "\n"
            "Exit code 0 on success; 1 on any error. Output path printed to stdout."
        ),
    )
    parser.add_argument(
        "--doc_type",
        required=True,
        help=f"Document type slug. Supported: {', '.join(REGISTRY)}",
    )
    parser.add_argument(
        "--payload",
        required=True,
        help="Path to a JSON file containing the document data.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the PDF in the system viewer after generation.",
    )
    args = parser.parse_args()

    # ── 1. Validate doc_type ───────────────────────────────────────────────
    if args.doc_type not in REGISTRY:
        print(
            f"Unknown doc_type '{args.doc_type}'. "
            f"Supported types: {', '.join(REGISTRY)}"
        )
        sys.exit(1)

    # ── 2. Load payload JSON ───────────────────────────────────────────────
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Payload file not found: {payload_path}")
        sys.exit(1)

    try:
        raw = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in payload file: {exc}")
        sys.exit(1)

    # ── 3. Validate against schema ─────────────────────────────────────────
    model_class, template_name = REGISTRY[args.doc_type]
    try:
        doc = model_class(**raw)
    except ValidationError as exc:
        print(_format_validation_errors(exc))
        sys.exit(1)

    # ── 4. Build template context ──────────────────────────────────────────
    context_builder = CONTEXT_BUILDERS[args.doc_type]
    try:
        context = context_builder(doc)
    except ValueError as exc:
        print(f"Error preparing document: {exc}")
        sys.exit(1)

    # ── 5. Render HTML ─────────────────────────────────────────────────────
    env = _make_jinja_env()
    template = env.get_template(template_name)
    html = template.render(**context)

    # ── 6. Write PDF ───────────────────────────────────────────────────────
    output_path = next_output_filename(args.doc_type)
    weasyprint.HTML(string=html).write_pdf(str(output_path))

    print(str(output_path))

    # ── 7. Preview (best-effort) ───────────────────────────────────────────
    if args.preview:
        open_preview(output_path)


if __name__ == "__main__":
    main()
