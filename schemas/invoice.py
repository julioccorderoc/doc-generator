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
    description: str
    quantity: Money
    unit_price: Money
    unit: str = "units"
    buyer_id: Optional[str] = None
    count_units: bool = True

    @field_validator("quantity", "unit_price", mode="after")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("must be greater than zero")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> Decimal:
        return round_money(self.quantity * self.unit_price)


class Issuer(DocModel):
    name: str
    address: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    logo: Optional[str] = None

    @field_validator("name", "address", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v

    @field_validator("logo", mode="after")
    @classmethod
    def logo_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^data:image/[a-zA-Z0-9\-\+]+;base64,[a-zA-Z0-9+/=]+$", v):
            raise ValueError("logo must be a data URI (data:image/...;base64,...)")
        return v


class BillTo(DocModel):
    name: str
    address: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("name", "address", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class PaymentDetailItem(DocModel):
    label: str
    value: str

    @field_validator("label", "value", mode="after")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class Invoice(DocModel):
    invoice_number: str
    issue_date: date = Field(default_factory=date.today)
    due_date: Optional[date] = None
    currency: Literal["USD"] = "USD"
    payment_terms: Optional[str] = None
    tax_rate: Money = Decimal("0.00")
    shipping_cost: Money = Decimal("0.00")
    notes: Optional[str] = None
    paid: bool = False
    amount_paid: Money = Decimal("0.00")
    primary_color: Optional[str] = None
    issuer: Issuer
    bill_to: BillTo
    line_items: list[LineItem]
    payment_details: list[PaymentDetailItem] = []

    @field_validator("invoice_number", mode="after")
    @classmethod
    def invoice_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
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
            raise ValueError("must contain at least one line item")
        return v

    @field_validator("tax_rate", mode="after")
    @classmethod
    def tax_rate_in_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.0") <= v <= Decimal("1.0")):
            raise ValueError("must be between 0.0 and 1.0")
        return v

    @field_validator("shipping_cost", "amount_paid", mode="after")
    @classmethod
    def must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be zero or positive")
        return v

    @model_validator(mode="after")
    def due_after_issue(self) -> Invoice:
        if self.due_date and self.due_date < self.issue_date:
            raise ValueError("due_date must be on or after issue_date")
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
