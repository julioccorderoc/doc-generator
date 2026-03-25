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
    header: str = Field(..., description="Column header (e.g. 'Capsules per bottle').")
    value: str = Field(..., description="Cell value for this product (e.g. '120').")


class SpecRow(DocModel):
    """A single row in a specification section."""
    label: str = Field(..., description="Row label in left column (e.g. 'Formula (per serving)').")
    value: str = Field(..., description="Row value in right column; supports \\n for multiline content.")


class SpecSection(DocModel):
    """A group of spec rows, optionally preceded by a section title row."""
    title: Optional[str] = Field(default=None, description="Section heading rendered as a full-width row. Omit or null for no heading.")
    rows: list[SpecRow] = Field(..., description="One or more label/value pairs.")

    @field_validator("rows", mode="after")
    @classmethod
    def at_least_one_row(cls, v: list[SpecRow]) -> list[SpecRow]:
        if not v:
            raise ValueError("At least one row is required in each specification section.")
        return v


class Annex(DocModel):
    """A named reference or attachment."""
    title: str = Field(..., description="Name of the attachment or reference (e.g. 'Two pack polybag specs').")
    url: Optional[str] = Field(default=None, description="URL rendered as plain text in the PDF.")


class RFQContact(DocModel):
    """Contact person for vendor questions."""
    name: Optional[str] = Field(default=None, description="Contact person's name")
    email: Optional[str] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, description="Contact phone")
    website: Optional[str] = Field(default=None, description="Website URL")


class RFQParty(DocModel):
    """A party (issuer or vendor) on the RFQ."""
    name: str = Field(..., description="Company or individual name.")
    address: Optional[str] = Field(default=None, description="Mailing address; use \\n for line breaks.")
    phone: Optional[str] = Field(default=None, description="Phone number.")
    email: Optional[str] = Field(default=None, description="Email address.")
    website: Optional[str] = Field(default=None, description="Website URL.")

    @field_validator("name", mode="after")
    @classmethod
    def name_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field is required and cannot be blank.")
        return v


class RequestForQuotation(DocModel):
    rfq_number: str = Field(..., description="Unique RFQ identifier (e.g. 'RFQ-2026-001').")
    issue_date: date = Field(default_factory=date.today, description="Date the RFQ is issued.")
    valid_until: Optional[date] = Field(default=None, description="Deadline for vendor to submit a quote; must be after issue_date. Only include when the user explicitly requests a submission deadline.")

    issuer: RFQParty = Field(..., description="Party issuing the RFQ.")
    vendor: Optional[RFQParty] = Field(default=None, description="Recipient vendor. Omit for broadcast RFQs.")

    product_name: str = Field(..., description="Name of the product or service being quoted.")
    product_description: Optional[str] = Field(default=None, description="Short description or subtitle for the product. Only include when the user explicitly asks for one.")
    product_attributes: list[RFQAttribute] = Field(default=[], description="Dynamic columns for the product summary table.")

    spec_sections: list[SpecSection] = Field(..., description="One or more specification sections. At least one required.")

    notes: Optional[str] = Field(default=None, description="Free-form notes printed below the spec table.")
    annexes: Optional[list[Annex]] = Field(default=None, description="Named references/attachments.")
    contact: Optional[RFQContact] = Field(default=None, description="Contact person for questions.")

    logo: Optional[str] = Field(default=None, description="Base64 data URI (data:image/png;base64,...). Claude reads the file and encodes it. Never pass a file path/URL.")
    primary_color: Optional[str] = Field(default=None, description="Color to override the document header. Hex color or CSS name.")
    font_family: Optional[str] = Field(default=None, description="Font stack override, e.g. 'Georgia, serif'. Only set when the user explicitly requests a different font. Leave null otherwise.")

    @field_validator("rfq_number", mode="after")
    @classmethod
    def rfq_number_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("The RFQ number is required and cannot be blank.")
        return v

    @field_validator("logo", mode="after")
    @classmethod
    def logo_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^data:image/[a-zA-Z0-9\-\+]+;base64,[a-zA-Z0-9+/=]+$", v):
            raise ValueError("Logo must be a base64 data URI (data:image/...;base64,...)")
        return v

    @field_validator("primary_color", mode="after")
    @classmethod
    def primary_color_safe(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|[a-zA-Z]+)$", v):
            raise ValueError("primary_color must be a hex color (#RRGGBB or #RGB) or a CSS color name")
        return v

    @field_validator("font_family", mode="after")
    @classmethod
    def font_family_safe(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if re.search(r'[;{}@]|url\s*\(', v, re.IGNORECASE):
            raise ValueError("font_family contains invalid characters. Provide a plain font stack, e.g. 'Georgia, serif'.")
        return v

    @field_validator("product_name", mode="after")
    @classmethod
    def product_name_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("The product name is required and cannot be blank.")
        return v

    @field_validator("spec_sections", mode="after")
    @classmethod
    def at_least_one_section(cls, v: list[SpecSection]) -> list[SpecSection]:
        if not v:
            raise ValueError("At least one specification section with at least one row is required.")
        return v

    @model_validator(mode="after")
    def valid_until_after_date(self) -> RequestForQuotation:
        if self.valid_until and self.valid_until <= self.issue_date:
            raise ValueError("The quote-by date must be after the issue date.")
        return self
