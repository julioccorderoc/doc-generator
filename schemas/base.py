"""
Shared base types, helpers, and mixins for all document schemas.

Key exports:
    - ``Money`` — annotated Decimal type that coerces any numeric JSON
      input (float, int, str) to Decimal via str() to avoid float
      imprecision. See docs/decisions/001-decimal-for-money.md.
    - ``round_money`` — quantize a Decimal to 2 places (HALF_UP).
    - Reusable validators: ``validate_logo_format``,
      ``validate_primary_color``, ``validate_font_family``,
      ``validate_non_empty_string``, ``validate_tax_rate``,
      ``validate_at_least_one_line_item``.
    - Mixins: ``ThemeFieldsMixin`` (logo / primary_color / font_family /
      doc_style + their validators) and ``MonetaryComputedMixin``
      (subtotal / tax_amount / grand_total / total_units).
"""
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, computed_field, field_validator


def _coerce_decimal(v: object) -> Decimal:
    """Coerce numeric input to Decimal via string to preserve precision.

    JSON floats like 24.0 become Decimal("24.0"), not the binary float
    0.23999999999999... that Decimal(24.0) would produce.
    """
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        return Decimal(str(v))
    raise ValueError(f"Cannot coerce {type(v).__name__!r} to Decimal")


# Use this annotation on every monetary field in every schema.
Money = Annotated[Decimal, BeforeValidator(_coerce_decimal)]


def round_money(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Reusable validator functions ──────────────────────────────────────────────

def validate_logo_format(v: str | None) -> str | None:
    if v is None:
        return v
    if not re.match(r"^data:image/[a-zA-Z0-9\-\+]+;base64,[a-zA-Z0-9+/=]+$", v):
        raise ValueError("Logo must be a base64 data URI (data:image/...;base64,...)")
    return v


def validate_primary_color(v: str | None) -> str | None:
    if v is None:
        return v
    if not re.match(r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|[a-zA-Z]+)$", v):
        raise ValueError("primary_color must be a hex color (#RRGGBB or #RGB) or a CSS color name")
    return v


def validate_font_family(v: str | None) -> str | None:
    if v is None:
        return v
    if re.search(r'[;{}@]|url\s*\(', v, re.IGNORECASE):
        raise ValueError("font_family contains invalid characters. Provide a plain font stack, e.g. 'Georgia, serif'.")
    return v


def validate_non_empty_string(v: str) -> str:
    """Ensure a required string field is not blank after stripping whitespace."""
    if not v.strip():
        raise ValueError("This field is required and cannot be blank.")
    return v


def validate_tax_rate(v: Decimal) -> Decimal:
    """Tax rate must be expressed as a fraction in [0, 1]."""
    if not (Decimal("0.0") <= v <= Decimal("1.0")):
        raise ValueError("Tax rate must be a decimal between 0 and 1 (e.g. 0.08 for 8%).")
    return v


def validate_at_least_one_line_item(v: list) -> list:
    """Reject empty line-item lists."""
    if not v:
        raise ValueError("At least one line item is required.")
    return v


class DocModel(BaseModel):
    """Base model for all document schemas."""

    model_config = {"populate_by_name": True}


# ── Reusable mixins ───────────────────────────────────────────────────────────

class ThemeFieldsMixin(BaseModel):
    """Theme/branding fields shared by every doc-type root schema.

    Includes the four user-tunable presentation knobs and the validators
    that protect them. Compose by listing this mixin before ``DocModel``
    (or another ``BaseModel``) in the doc-type schema's bases.
    """

    logo: Optional[str] = Field(
        default=None,
        description="Base64 data URI (data:image/png;base64,...). Use scripts/encode_logo.py to encode — never pass a file path or URL.",
    )
    primary_color: Optional[str] = Field(
        default=None,
        description="Brand color override. Must be a hex color (#RRGGBB) or a single-word CSS color name.",
    )
    font_family: Optional[str] = Field(
        default=None,
        description="Font stack override, e.g. 'Georgia, serif'. Only set when the user explicitly requests a different font. Leave null otherwise.",
    )
    doc_style: Literal["compact", "normal", "comfortable"] = Field(
        default="normal",
        description="Page density preset. 'compact' fits more content per page; 'comfortable' adds more whitespace for readability. Default: 'normal'.",
    )

    @field_validator("logo", mode="after")
    @classmethod
    def _logo_format(cls, v: Optional[str]) -> Optional[str]:
        return validate_logo_format(v)

    @field_validator("primary_color", mode="after")
    @classmethod
    def _primary_color_safe(cls, v: Optional[str]) -> Optional[str]:
        return validate_primary_color(v)

    @field_validator("font_family", mode="after")
    @classmethod
    def _font_family_safe(cls, v: Optional[str]) -> Optional[str]:
        return validate_font_family(v)


class MonetaryComputedMixin(BaseModel):
    """Computed monetary fields shared by PO and Invoice.

    Assumes the inheriting model exposes:
        - ``line_items``: an iterable of items each with a ``total``
          (Decimal or None) and a ``quantity`` (Decimal). Items may
          optionally expose ``count_units: bool`` (defaults to True
          when missing) controlling inclusion in ``total_units``.
        - ``tax_rate``: Decimal in [0, 1].
        - ``shipping_cost``: Decimal.

    A ``None`` line-item ``total`` (e.g. PO blanket lines without a
    confirmed price) is skipped from ``subtotal``.
    """

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal(self) -> Decimal:
        return round_money(sum(
            (item.total for item in self.line_items if item.total is not None),
            Decimal("0"),
        ))

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
            (item.quantity for item in self.line_items if getattr(item, "count_units", True)),
            Decimal("0"),
        )
