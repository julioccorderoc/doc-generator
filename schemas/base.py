"""
Shared base types and helpers for all document schemas.

Key export: ``Money`` — an annotated Decimal type that coerces any
numeric JSON input (float, int, str) to Decimal via str() to avoid
float imprecision. See docs/decisions/001-decimal-for-money.md.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from pydantic import BaseModel, BeforeValidator


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


class DocModel(BaseModel):
    """Base model for all document schemas."""

    model_config = {"populate_by_name": True}
