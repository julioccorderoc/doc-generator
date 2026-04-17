"""
Pydantic v2 schema for the purchase_order document type.

Source of truth: references/purchase_order.md
Do not add or remove fields without updating that file first.

Computed fields (total, subtotal, tax_amount, grand_total) are derived
automatically — they must never appear in the input payload.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, Union

from pydantic import Field, computed_field, field_validator, model_validator

from schemas.base import (
    DocModel,
    MonetaryComputedMixin,
    Money,
    ThemeFieldsMixin,
    round_money,
    validate_at_least_one_line_item,
    validate_currency,
    validate_non_empty_string,
    validate_tax_rate,
)


class LineItem(DocModel):
    description: str = Field(..., description="Name or description of the item or service.")
    quantity: Money = Field(..., description="Quantity ordered. Must be greater than zero. Can be decimal (e.g. 2.5 for 2.5 hours).")
    unit_price: Optional[Money] = Field(default=None, description="Price per unit in USD. Omit for blanket POs where price is not yet confirmed (renders as TBD).")
    unit: str = Field(default="units", description="Unit label displayed next to quantity. e.g. units, hrs, kg, boxes.")
    buyer_id: Optional[str] = Field(default=None, description="Buyer's internal part number or identifier. Displayed as 'Buyer ID' column if provided. Ask explicitly.")
    vendor_id: Optional[str] = Field(default=None, description="Supplier's part number or identifier. Displayed as 'Vendor ID' column if provided. Ask explicitly.")
    barcode: Optional[str] = Field(default=None, description="Product barcode (EAN, UPC, etc.). Displayed as 'Barcode' column. Ask explicitly.")
    count_units: bool = Field(default=True, description="Whether to include this item's quantity in total_units. Set to false for service lines (labour, prep, setup fees).")

    @field_validator("quantity", mode="after")
    @classmethod
    def quantity_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return v

    @field_validator("unit_price", mode="after")
    @classmethod
    def unit_price_must_be_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Unit price must be greater than zero.")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> Optional[Decimal]:
        if self.unit_price is None:
            return None
        return round_money(self.quantity * self.unit_price)


class Buyer(DocModel):
    name: str = Field(..., description="Legal company name of the buyer.")
    address: str = Field(..., description="Full mailing address. Can be multiline (use \\n).")
    contact_name: Optional[str] = Field(default=None, description="Name of the purchasing contact at the buyer company.")
    email: Optional[str] = Field(default=None, description="Contact email.")
    phone: Optional[str] = Field(default=None, description="Contact phone number.")

    _validate_required = field_validator("name", "address", mode="after")(validate_non_empty_string)


class Vendor(DocModel):
    name: str = Field(..., description="Legal company name of the vendor.")
    address: str = Field(..., description="Full mailing address. Can be multiline (use \\n).")
    email: Optional[str] = Field(default=None, description="Contact email.")
    phone: Optional[str] = Field(default=None, description="Contact phone number.")
    contact_name: Optional[str] = Field(default=None, description="Name of the specific contact at the vendor. Displayed without 'Attn:' prefix.")

    _validate_required = field_validator("name", "address", mode="after")(validate_non_empty_string)


class TableAnnex(DocModel):
    title: Optional[str] = Field(default=None, description="Heading for this annex. Defaults to 'Addendum' if omitted.")
    headers: list[str] = Field(..., description="Column header labels. Must have at least 1 entry.")
    rows: list[list[str]] = Field(default_factory=list, description="Table rows. Each row must have the same number of cells as headers.")
    new_page: bool = Field(default=False, description="Force this annex to start on a new page. Default false — annex flows after the preceding content.")

    @model_validator(mode="after")
    def rows_match_headers(self) -> TableAnnex:
        n = len(self.headers)
        for i, row in enumerate(self.rows):
            if len(row) != n:
                raise ValueError(
                    f"Row {i + 1} has {len(row)} cell(s) but headers defines {n} column(s)."
                )
        return self


class PurchaseOrder(ThemeFieldsMixin, MonetaryComputedMixin, DocModel):
    po_number: str = Field(..., description="Unique identifier for this PO. Format is up to the buyer (e.g. PO-2026-0042). Suggest sequential if not provided.")
    issue_date: date = Field(default_factory=date.today, description="Date the PO is issued. Defaults to today if not specified. Format: YYYY-MM-DD.")
    delivery_date: Optional[date] = Field(default=None, description="Expected delivery date. Optional but recommended. Format: YYYY-MM-DD.")
    currency: str = Field(default="USD", description="Currency code. Phase 1 supports USD only.")
    product: Optional[str] = Field(default=None, description="Product name for single-product POs. Displayed as the first item in the meta-band when provided.")
    payment_terms: Optional[str] = Field(default=None, description="e.g. Net 30, Due on receipt, 50% upfront. Free text.")
    shipping_method: Optional[str] = Field(default=None, description="e.g. FedEx Ground, FOB Destination, Will Call. Free text.")
    shipping_cost: Money = Field(default=Decimal("0.00"), description="Flat shipping fee to be added to the total. In USD.")
    tax_rate: Money = Field(default=Decimal("0.00"), description="Tax rate as a decimal (e.g. 0.08 for 8%). Applied to subtotal.")
    notes: Optional[str] = Field(default=None, description="General notes, terms, or instructions. Renders at the bottom of the document.")
    annex_terms: Optional[Union[bool, str]] = Field(default=None, description="true = standard T&C; string = custom T&C text; null = no T&C page.")
    annex_tables: list[TableAnnex] = Field(default_factory=list, description="List of tabular annexes. Each renders on its own page with a title and a flexible-column table.")
    buyer: Buyer = Field(..., description="The company issuing the PO.")
    vendor: Vendor = Field(..., description="The supplier receiving the PO.")
    line_items: list[LineItem] = Field(..., description="What is being purchased. Minimum 1 item.")

    @field_validator("po_number", mode="after")
    @classmethod
    def po_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("The PO number is required and cannot be blank.")
        return v

    @field_validator("annex_terms", mode="before")
    @classmethod
    def normalise_annex_terms(cls, v):
        if v is False:
            return None
        if isinstance(v, str) and len(v) > 50_000:
            raise ValueError("annex_terms must not exceed 50000 characters")
        return v

    _validate_line_items = field_validator("line_items", mode="after")(validate_at_least_one_line_item)
    _validate_tax_rate = field_validator("tax_rate", mode="after")(validate_tax_rate)
    _validate_currency = field_validator("currency", mode="after")(validate_currency)

    @field_validator("shipping_cost", mode="after")
    @classmethod
    def shipping_cost_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Shipping cost must be zero or positive.")
        return v

    @model_validator(mode="after")
    def delivery_after_issue(self) -> PurchaseOrder:
        if self.delivery_date and self.delivery_date < self.issue_date:
            raise ValueError("The delivery date cannot be before the issue date.")
        return self
