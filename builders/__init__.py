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
from typing import Any, Protocol, Type

from schemas.purchase_order import PurchaseOrder
from schemas.invoice import Invoice
from schemas.request_for_quotation import RequestForQuotation
from builders.purchase_order import build_po_context
from builders.invoice import build_invoice_context
from builders.request_for_quotation import build_rfq_context


class ContextBuilder(Protocol):
    """Protocol for context builder callables.

    Any function with signature ``(doc: Any) -> dict`` satisfies this protocol.
    Provides better IDE support and static analysis than bare ``Callable``.
    """
    def __call__(self, doc: Any) -> dict: ...


@dataclass(frozen=True)
class DocTypeConfig:
    """Immutable configuration record for a registered document type.

    Attributes:
        model:         Pydantic v2 model class used to validate the payload.
        template:      Filename of the Jinja2 template (relative to templates/).
        build_context: Callable that maps a validated model instance to a
                       display-ready context dict for the template.
        file_prefix:   Short uppercase prefix used in output filenames
                       (e.g. "PO" → PO_20260316_0001.pdf).
        css_file:      Filename (relative to assets/) of the doc-type CSS.
                       Declarative source of truth for which stylesheet a
                       doc type uses. Today builders still load this file
                       at module top; future work may switch the pipeline
                       to inject the loaded CSS via the registry.
    """
    model: Type
    template: str
    build_context: ContextBuilder
    file_prefix: str
    css_file: str


# ── Document type registry ─────────────────────────────────────────────────
# One entry per supported doc type.
# To add a new type: create builders/<doc_type>.py, then add one entry here.

REGISTRY: dict[str, DocTypeConfig] = {
    "purchase_order": DocTypeConfig(
        model=PurchaseOrder,
        template="purchase_order.html",
        build_context=build_po_context,
        file_prefix="PO",
        css_file="purchase_order.css",
    ),
    "invoice": DocTypeConfig(
        model=Invoice,
        template="invoice.html",
        build_context=build_invoice_context,
        file_prefix="INV",
        css_file="invoice.css",
    ),
    "request_for_quotation": DocTypeConfig(
        model=RequestForQuotation,
        template="request_for_quotation.html",
        build_context=build_rfq_context,
        file_prefix="RFQ",
        css_file="request_for_quotation.css",
    ),
}
