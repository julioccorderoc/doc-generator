"""builders — document type registry.

This is the single registration point for every supported document type.
Adding a new doc type requires exactly one new entry in REGISTRY (plus the
four files described in references/EXTENDING.md).

Usage in the pipeline (scripts/generate.py):

    from builders import REGISTRY

    config = REGISTRY["invoice"]
    doc     = config.model(**raw)          # validate payload
    context = config.build_context(doc)    # build display context
    html    = env.get_template(config.template).render(**context)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type

from schemas.purchase_order import PurchaseOrder
from schemas.invoice import Invoice
from builders.purchase_order import build_po_context
from builders.invoice import build_invoice_context


@dataclass(frozen=True)
class DocTypeConfig:
    """Immutable configuration record for a registered document type.

    Attributes:
        model:         Pydantic v2 model class used to validate the payload.
        template:      Filename of the Jinja2 template (relative to templates/).
        build_context: Callable that maps a validated model instance to a
                       display-ready context dict for the template.
    """
    model: Type
    template: str
    build_context: Callable


# ── Document type registry ─────────────────────────────────────────────────
# One entry per supported doc type.
# To add a new type: create builders/<doc_type>.py, then add one entry here.

REGISTRY: dict[str, DocTypeConfig] = {
    "purchase_order": DocTypeConfig(
        model=PurchaseOrder,
        template="purchase_order.html",
        build_context=build_po_context,
    ),
    "invoice": DocTypeConfig(
        model=Invoice,
        template="invoice.html",
        build_context=build_invoice_context,
    ),
}
