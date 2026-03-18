"""
Pydantic v2 schema for the request_for_quotation document type.

Source of truth: references/request_for_quotation.md
Do not add or remove fields without updating that file first.

Unlike PO/Invoice, this document type has no monetary fields and no
computed fields — it is purely descriptive.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import Field, field_validator, model_validator

from schemas.base import DocModel


class RFQAttribute(DocModel):
    """A single column entry in the product summary table."""
    header: str
    value: str


class SpecRow(DocModel):
    """A single row in a specification section."""
    label: str
    value: str


class SpecSection(DocModel):
    """A group of spec rows, optionally preceded by a section title row."""
    title: Optional[str] = None
    rows: list[SpecRow]

    @field_validator("rows", mode="after")
    @classmethod
    def at_least_one_row(cls, v: list[SpecRow]) -> list[SpecRow]:
        if not v:
            raise ValueError("spec section must contain at least one row")
        return v


class Annex(DocModel):
    """A named reference or attachment."""
    title: str
    url: Optional[str] = None


class RFQContact(DocModel):
    """Contact person for vendor questions."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class RFQParty(DocModel):
    """A party (issuer or vendor) on the RFQ."""
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    @field_validator("name", mode="after")
    @classmethod
    def name_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class RequestForQuotation(DocModel):
    rfq_number: str
    issue_date: date = Field(default_factory=date.today)
    valid_until: Optional[date] = None

    issuer: RFQParty
    vendor: Optional[RFQParty] = None

    product_name: str
    product_description: Optional[str] = None
    product_attributes: list[RFQAttribute] = []

    spec_sections: list[SpecSection]

    notes: Optional[str] = None
    annexes: Optional[list[Annex]] = None
    contact: Optional[RFQContact] = None

    logo: Optional[str] = None
    primary_color: Optional[str] = None

    @field_validator("rfq_number", mode="after")
    @classmethod
    def rfq_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v

    @field_validator("logo", mode="after")
    @classmethod
    def logo_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith("data:image/"):
            raise ValueError("logo must be a data URI (data:image/...;base64,...)")
        return v

    @field_validator("primary_color", mode="after")
    @classmethod
    def primary_color_safe(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|[a-zA-Z]+)$", v):
            raise ValueError("primary_color must be a hex color (#RRGGBB or #RGB) or a CSS color name")
        return v

    @field_validator("product_name", mode="after")
    @classmethod
    def product_name_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v

    @field_validator("spec_sections", mode="after")
    @classmethod
    def at_least_one_section(cls, v: list[SpecSection]) -> list[SpecSection]:
        if not v:
            raise ValueError("must contain at least one spec section")
        return v

    @model_validator(mode="after")
    def valid_until_after_date(self) -> RequestForQuotation:
        if self.valid_until and self.valid_until <= self.issue_date:
            raise ValueError("valid_until must be after date")
        return self
