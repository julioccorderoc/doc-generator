# 001 — Use `Decimal` for All Monetary Fields

**Status:** Accepted
**Date:** 2026-03-16

## Context

JSON has no native decimal type. All numbers in a JSON payload are parsed as IEEE 754 floating-point, which introduces silent rounding errors for monetary values. For example, `0.1 + 0.2` evaluates to `0.30000000000000004` in Python float arithmetic. In a financial document where a computed grand total must match the sum of line items exactly, any rounding drift is a correctness bug.

Pydantic v2 will accept a `float` annotation and pass the raw float through. The error is invisible until a computed total is off by a cent.

## Decision

All monetary fields in every Pydantic schema use `Decimal` as the type, not `float` or `int`. The coercion from JSON's float representation to `Decimal` is performed via `Decimal(str(value))` — not `Decimal(value)` directly, which would preserve the float's binary imprecision.

This coercion is enforced by a shared annotated type `Money` defined in `schemas/base.py`:

```python
from decimal import Decimal
from typing import Annotated
from pydantic import BeforeValidator

def _coerce_decimal(v: object) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float, str)):
        return Decimal(str(v))
    raise ValueError(f"Cannot coerce {type(v).__name__} to Decimal")

Money = Annotated[Decimal, BeforeValidator(_coerce_decimal)]
```

Any field that holds a monetary value is annotated as `Money`, not `Decimal` or `float`. No schema author needs to remember to add the coercion — it is structural.

All computed monetary values are rounded to two decimal places using `ROUND_HALF_UP` via a shared `round_money()` helper.

## Consequences

- Monetary arithmetic is exact. Computed totals will always match a manual calculation.
- Payload JSON can use standard float notation (`24.00`, `18.5`) — the coercion is transparent.
- `Decimal` values cannot be directly serialized to JSON without a custom encoder. `generate.py` formats all monetary values to strings before passing them to the Jinja2 context, so serialization of `Decimal` objects never occurs at render time.
- Introducing a new schema field that holds money requires using `Money` as the annotation — `float` is wrong and will silently produce float precision errors.
