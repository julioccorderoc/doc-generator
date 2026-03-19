"""
Pydantic v2 schema for the invoice document type.

Source of truth: references/invoice.md
Do not add or remove fields without updating that file first.

Computed fields (total, subtotal, tax_amount, grand_total, balance_due) are
derived automatically — they must never appear in the input payload.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import Field, computed_field, field_validator, model_validator

from schemas.base import DocModel, Money, round_money


class LineItem(DocModel):
    description: str = Field(..., description="Name or description of the item or service.")
    quantity: Money = Field(..., description="Quantity delivered or hours worked. Must be greater than zero. Can be decimal.")
    unit_price: Money = Field(..., description="Price per unit in USD. Must be greater than zero.")
    unit: str = Field(default="units", description="Unit label displayed next to quantity. e.g. units, hrs, kg, days.")
    buyer_id: Optional[str] = Field(default=None, description="Buyer's internal product code or reference identifier. Displayed as 'Buyer ID' column if provided.")
    count_units: bool = Field(default=True, description="Whether to include this item's quantity in total_units. Set to false for service lines that should not count toward the physical unit total.")

    @field_validator("quantity", "unit_price", mode="after")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity and unit price must be greater than zero.")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> Decimal:
        return round_money(self.quantity * self.unit_price)


class Issuer(DocModel):
    name: str = Field(..., description="Legal company name of the issuer.")
    address: str = Field(..., description="Full mailing address. Can be multiline (use \\n).")
    contact_name: Optional[str] = Field(default=None, description="Name of the billing contact at the issuer. Displayed below the address.")
    email: Optional[str] = Field(default=None, description="Contact or billing email.")
    phone: Optional[str] = Field(default=None, description="Contact phone number.")
    logo: Optional[str] = Field(default=None, description="Base64 data URI (data:image/png;base64,...). Claude reads the file and encodes it before building the payload — never pass a file path or URL.")

    @field_validator("name", "address", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required and cannot be blank.")
        return v

    @field_validator("logo", mode="after")
    @classmethod
    def logo_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^data:image/[a-zA-Z0-9\-\+]+;base64,[a-zA-Z0-9+/=]+$", v):
            raise ValueError("Logo must be a base64 data URI (data:image/...;base64,...)")
        return v


class BillTo(DocModel):
    name: str = Field(..., description="Legal company or individual name of the client.")
    address: str = Field(..., description="Full mailing address. Can be multiline (use \\n).")
    contact_name: Optional[str] = Field(default=None, description="Name of the accounts payable contact at the client. Displayed below the address.")
    email: Optional[str] = Field(default=None, description="Contact email at the client.")
    phone: Optional[str] = Field(default=None, description="Contact phone number at the client.")

    @field_validator("name", "address", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required and cannot be blank.")
        return v


class PaymentDetailItem(DocModel):
    label: str = Field(..., description="Display label for the field, e.g. Bank, Account Name, Routing Number, PayPal.")
    value: str = Field(..., description="The corresponding value, e.g. Chase Bank, billing@acme.com.")

    @field_validator("label", "value", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required and cannot be blank.")
        return v


class Invoice(DocModel):
    invoice_number: str = Field(..., description="Unique identifier for this invoice. Format is up to the issuer. Suggest sequential if not provided.")
    issue_date: date = Field(default_factory=date.today, description="Date the invoice is issued. Defaults to today. Format: YYYY-MM-DD.")
    due_date: Optional[date] = Field(default=None, description="Payment due date. Optional but strongly recommended. Format: YYYY-MM-DD.")
    currency: Literal["USD"] = Field(default="USD", description="Currency code. Phase 2 supports USD only.")
    payment_terms: Optional[str] = Field(default=None, description="e.g. Net 30, Due on receipt, 50% upfront. Free text.")
    tax_rate: Money = Field(default=Decimal("0.00"), description="Tax rate as a decimal (e.g. 0.08 for 8%). Applied to subtotal. Must be between 0.0 and 1.0.")
    shipping_cost: Money = Field(default=Decimal("0.00"), description="Flat shipping or delivery fee added to the total. In USD.")
    notes: Optional[str] = Field(default=None, description="General notes, additional terms, or instructions. Renders at the bottom of the document.")
    paid: bool = Field(default=False, description="Whether the invoice has already been paid. If true, amount_paid should also be provided.")
    amount_paid: Money = Field(default=Decimal("0.00"), description="Amount already received. Meaningful only when paid is true. In USD.")
    primary_color: Optional[str] = Field(default=None, description="Brand color override. Must be a hex color (#RRGGBB) or a single-word CSS color name.")
    issuer: Issuer = Field(..., description="The company sending the invoice.")
    bill_to: BillTo = Field(..., description="The client being billed.")
    line_items: list[LineItem] = Field(..., description="What is being invoiced. Minimum 1 item.")
    payment_details: list[PaymentDetailItem] = Field(default=[], description="How to pay. An optional ordered list of name/value pairs.")

    @field_validator("invoice_number", mode="after")
    @classmethod
    def invoice_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("The invoice number is required and cannot be blank.")
        return v

    @field_validator("primary_color", mode="after")
    @classmethod
    def primary_color_safe(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|[a-zA-Z]+)$", v):
            raise ValueError("primary_color must be a hex color (#RRGGBB or #RGB) or a CSS color name")
        return v

    @field_validator("line_items", mode="after")
    @classmethod
    def at_least_one_line_item(cls, v: list[LineItem]) -> list[LineItem]:
        if not v:
            raise ValueError("At least one line item is required.")
        return v

    @field_validator("tax_rate", mode="after")
    @classmethod
    def tax_rate_in_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.0") <= v <= Decimal("1.0")):
            raise ValueError("Tax rate must be a decimal between 0 and 1 (e.g. 0.08 for 8%).")
        return v

    @field_validator("shipping_cost", "amount_paid", mode="after")
    @classmethod
    def must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Shipping cost and amount paid must be zero or positive.")
        return v

    @model_validator(mode="after")
    def due_after_issue(self) -> Invoice:
        if self.due_date and self.due_date < self.issue_date:
            raise ValueError("The due date cannot be before the issue date.")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal(self) -> Decimal:
        return round_money(sum((item.total for item in self.line_items), Decimal("0")))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tax_amount(self) -> Decimal:
        return round_money(self.subtotal * self.tax_rate)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def grand_total(self) -> Decimal:
        return round_money(self.subtotal + self.tax_amount + self.shipping_cost)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_units(self) -> Decimal:
        return sum(
            (item.quantity for item in self.line_items if item.count_units),
            Decimal("0"),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance_due(self) -> Decimal:
        return round_money(self.grand_total - self.amount_paid)
