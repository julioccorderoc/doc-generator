"""
Pydantic v2 schema for the invoice document type.

Source of truth: references/invoice.md
Do not add or remove fields without updating that file first.

Computed fields (total, subtotal, tax_amount, grand_total, balance_due) are
derived automatically — they must never appear in the input payload.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

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
    quantity: Money = Field(..., description="Quantity delivered or hours worked. Must be greater than zero. Can be decimal.")
    unit_price: Money = Field(..., description="Price per unit in USD. Must be greater than zero.")
    unit: str = Field(default="units", description="Unit label displayed next to quantity. e.g. units, hrs, kg, days.")
    sku: Optional[str] = Field(default=None, description="Seller's product or part number (SKU). Displayed as 'SKU' column when provided on any line item. Ask explicitly if not mentioned.")
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

    _validate_required = field_validator("name", "address", mode="after")(validate_non_empty_string)


class BillTo(DocModel):
    name: str = Field(..., description="Legal company or individual name of the client.")
    address: str = Field(..., description="Full mailing address. Can be multiline (use \\n).")
    contact_name: Optional[str] = Field(default=None, description="Name of the accounts payable contact at the client. Displayed below the address.")
    email: Optional[str] = Field(default=None, description="Contact email at the client.")
    phone: Optional[str] = Field(default=None, description="Contact phone number at the client.")

    _validate_required = field_validator("name", "address", mode="after")(validate_non_empty_string)


class PaymentDetailItem(DocModel):
    label: str = Field(..., description="Display label for the field, e.g. Bank, Account Name, Routing Number, PayPal.")
    value: str = Field(..., description="The corresponding value, e.g. Chase Bank, billing@acme.com.")

    @field_validator("label", "value", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required and cannot be blank.")
        return v


class Invoice(ThemeFieldsMixin, MonetaryComputedMixin, DocModel):
    invoice_number: str = Field(..., description="Unique identifier for this invoice. Format is up to the issuer. Suggest sequential if not provided.")
    issue_date: date = Field(default_factory=date.today, description="Date the invoice is issued. Defaults to today. Format: YYYY-MM-DD.")
    due_date: Optional[date] = Field(default=None, description="Payment due date. Optional but strongly recommended. Format: YYYY-MM-DD.")
    currency: str = Field(default="USD", description="Currency code. Phase 2 supports USD only.")
    payment_terms: Optional[str] = Field(default=None, description="e.g. Net 30, Due on receipt, 50% upfront. Free text.")
    tax_rate: Money = Field(default=Decimal("0.00"), description="Tax rate as a decimal (e.g. 0.08 for 8%). Applied to subtotal. Must be between 0.0 and 1.0.")
    shipping_cost: Money = Field(default=Decimal("0.00"), description="Flat shipping or delivery fee added to the total. In USD.")
    notes: Optional[str] = Field(default=None, description="General notes, additional terms, or instructions. Renders at the bottom of the document.")
    paid: bool = Field(default=False, description="Whether the invoice has already been paid. If true, amount_paid should also be provided.")
    amount_paid: Money = Field(default=Decimal("0.00"), description="Amount already received. Meaningful only when paid is true. In USD.")
    issuer: Issuer = Field(..., description="The company sending the invoice.")
    bill_to: BillTo = Field(..., description="The client being billed.")
    line_items: list[LineItem] = Field(..., description="What is being invoiced. Minimum 1 item.")
    payment_details: list[PaymentDetailItem] = Field(default_factory=list, description="How to pay. An optional ordered list of name/value pairs.")

    @field_validator("invoice_number", mode="after")
    @classmethod
    def invoice_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("The invoice number is required and cannot be blank.")
        return v

    _validate_line_items = field_validator("line_items", mode="after")(validate_at_least_one_line_item)
    _validate_tax_rate = field_validator("tax_rate", mode="after")(validate_tax_rate)
    _validate_currency = field_validator("currency", mode="after")(validate_currency)

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
    def balance_due(self) -> Decimal:
        return round_money(self.grand_total - self.amount_paid)
