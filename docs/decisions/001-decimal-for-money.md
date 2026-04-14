# 001 — Use `Decimal` for All Monetary Fields

**Status:** Accepted
**Date:** 2026-03-16

## Context

JSON has no native decimal type. Numbers parsed as IEEE 754 float, introducing silent rounding errors for monetary values. E.g. `0.1 + 0.2` = `0.30000000000000004` in Python. In financial documents where computed totals must match line item sums exactly, any rounding drift is a correctness bug.

Pydantic v2 accepts `float` annotation and passes raw float through. Error is invisible until a computed total is off by a cent.

## Decision

All monetary fields use `Decimal`, not `float` or `int`. Coercion from JSON float to `Decimal` via `Decimal(str(value))` — not `Decimal(value)` directly (would preserve binary imprecision).

Enforced by shared annotated type `Money` in `schemas/base.py`:

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

Any monetary field annotated as `Money`, not `Decimal` or `float`. No schema author needs to remember coercion — it is structural.

All computed monetary values rounded to 2dp using `ROUND_HALF_UP` via shared `round_money()` helper.

## Consequences

- Monetary arithmetic is exact. Computed totals always match manual calculation.
- Payload JSON can use standard float notation (`24.00`, `18.5`) — coercion is transparent.
- `Decimal` values cannot serialize to JSON without custom encoder. `generate.py` formats all monetary values to strings before passing to Jinja2 context, so `Decimal` serialization never occurs at render time.
- New schema fields holding money must use `Money` annotation — `float` silently produces precision errors.
