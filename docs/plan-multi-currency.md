# Plan: Multi-Currency Support (Top 5 Currencies)

**Status:** Ready to implement — not yet started.
**Project root:** `/Users/juliocordero/Documents/NCL/doc-generator`
**Run tests:** `uv run pytest` (no system deps needed for unit tests)
**Run generate:** `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py ...`

---

## Context & Background

`doc-generator` is a schema-driven PDF generation CLI (no LLM in the render path). It
supports Purchase Orders (`purchase_order`), Invoices (`invoice`), and Requests for
Quotation (`request_for_quotation`). RFQ has no monetary fields and is unaffected by
this change.

**Current state (as of Phase 8):**
- `format_currency()` in `utils/formatting.py:11` is hardcoded to `$X,XXX.XX` (USD only).
- Both `PurchaseOrder` (`schemas/purchase_order.py:87`) and `Invoice` (`schemas/invoice.py`)
  have a `currency: str = "USD"` field, but it is accepted by the schema and immediately
  hard-blocked in `scripts/generate.py` (step 3a) before it ever reaches the builder.
- No tests exist for non-USD formatting.

**Goal:** Allow the top 5 currencies. USD stays the default. Invalid codes produce a clean
Pydantic validation error (consistent with all other field errors). No template changes
needed — the formatted string (symbol included) is already fully produced in Python.

---

## Supported Currencies

| Code | Name          | Symbol | Decimals | Example      |
|------|---------------|--------|----------|--------------|
| USD  | US Dollar     | $      | 2        | $1,234.56    |
| EUR  | Euro          | €      | 2        | €1,234.56    |
| GBP  | British Pound | £      | 2        | £1,234.56    |
| JPY  | Japanese Yen  | ¥      | 0        | ¥1,235       |
| CNY  | Chinese Yuan  | CN¥    | 2        | CN¥1,234.56  |

**Number format:** American style for all (comma thousands separator, period decimal).
Consistent with existing `format_quantity` convention.

**JPY note:** No subunit (sen). Displayed as whole number. Internal `round_money()`
(always 2 dp) is unchanged — JPY amounts in practice are whole numbers, so the display
layer simply formats with 0 decimal places.

**CNY note:** Uses `CN¥` prefix to distinguish from JPY (both use `¥` in isolation).

---

## Architecture Reference

All formatting decisions happen in Python builders, never in Jinja2 templates
(see `docs/decisions/002-python-only-formatting.md`). Templates receive fully-formatted
strings. This means **zero template changes** for this feature.

### Call-site map for `format_currency`

| File | Function | Call | Argument |
|------|----------|------|----------|
| `builders/_shared.py` | `build_line_items(doc)` | 2× per item | `item.unit_price`, `item.total` |
| `builders/_shared.py` | `build_totals(doc)` | 4× | `doc.subtotal`, `doc.tax_amount`, `doc.shipping_cost`, `doc.grand_total` |
| `builders/invoice.py` | `build_invoice_context(doc)` | 2× | `doc.amount_paid`, `doc.balance_due` |

**Total call sites to update: 8** (all pass a `Decimal`, all need a `currency` arg added).

### How currency flows today (payload → PDF)

```
JSON payload
  └─ "currency": "EUR"  ← accepted by schema, defaults to "USD"
        │
  Pydantic model
  └─ doc.currency = "EUR"  ← stored but never used
        │
  scripts/generate.py step 3a   ← HARD BLOCKER (to be removed)
  └─ if currency != "USD": sys.exit(1)
        │
  builder (never reached for EUR today)
  └─ format_currency(doc.subtotal)  ← no currency arg, always "$"
        │
  template context
  └─ "subtotal": "$1,234.56"  ← USD-formatted string
```

**After this plan:**

```
  Pydantic model
  └─ doc.currency = "EUR"  ← validated against SUPPORTED_CURRENCIES
        │
  generate.py step 3a removed entirely
        │
  builder
  └─ format_currency(doc.subtotal, doc.currency)  ← "€1,234.56"
        │
  template context
  └─ "subtotal": "€1,234.56"
```

---

## Implementation Steps (in order)

### Step 1 — `utils/formatting.py`

**File:** `utils/formatting.py`

Add a `_CURRENCY_CONFIG` lookup table and update `format_currency` to accept a `currency`
parameter (default `"USD"` so all existing callers with no second argument are unaffected).

```python
_CURRENCY_CONFIG: dict[str, tuple[str, int]] = {
    # code → (symbol, decimal_places)
    "USD": ("$",   2),
    "EUR": ("€",   2),
    "GBP": ("£",   2),
    "JPY": ("¥",   0),
    "CNY": ("CN¥", 2),
}

def format_currency(value: Decimal | float, currency: str = "USD") -> str:
    """Format a monetary value with the appropriate symbol and decimal places.

    Uses American number formatting (comma thousands, period decimal) for all
    currencies. The currency must be one of the keys in _CURRENCY_CONFIG.
    """
    symbol, decimals = _CURRENCY_CONFIG[currency]
    return f"{symbol}{float(value):,.{decimals}f}"
```

No other functions in `formatting.py` change.

---

### Step 2 — `schemas/base.py`

**File:** `schemas/base.py`

Add a shared constant (single source of truth used by all schemas and the guard removal).
Place it after the `round_money` function, before `DocModel`:

```python
SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"USD", "EUR", "GBP", "JPY", "CNY"})
```

---

### Step 3 — `schemas/purchase_order.py`

**File:** `schemas/purchase_order.py`

Import `SUPPORTED_CURRENCIES` from `schemas.base` and add a field validator to the
`PurchaseOrder` class:

```python
from schemas.base import DocModel, Money, round_money, SUPPORTED_CURRENCIES

# Inside PurchaseOrder class:
@field_validator("currency", mode="after")
@classmethod
def currency_supported(cls, v: str) -> str:
    if v not in SUPPORTED_CURRENCIES:
        raise ValueError(f"must be one of {sorted(SUPPORTED_CURRENCIES)}")
    return v
```

---

### Step 4 — `schemas/invoice.py`

**File:** `schemas/invoice.py`

Identical change to Step 3: import `SUPPORTED_CURRENCIES`, add the same
`currency_supported` field validator to the `Invoice` class.

---

### Step 5 — `builders/_shared.py`

**File:** `builders/_shared.py`

Both `build_line_items(doc)` and `build_totals(doc)` already receive the full `doc`
object. Read `currency` from it and pass to `format_currency`:

```python
# At the top of each function:
currency = getattr(doc, "currency", "USD")  # safe fallback for RFQ (no currency field)

# build_line_items: 2 changed lines
"unit_price": format_currency(item.unit_price, currency),
"total":      format_currency(item.total,      currency),

# build_totals: 4 changed lines
"subtotal":      format_currency(doc.subtotal,      currency),
"tax_amount":    format_currency(doc.tax_amount,    currency),
"shipping_cost": format_currency(doc.shipping_cost, currency),
"grand_total":   format_currency(doc.grand_total,   currency),
```

No signature change → callers (`build_po_context`, `build_rfq_context`) are unaffected.
`getattr(doc, "currency", "USD")` safely returns `"USD"` for RFQ (which has no currency
field and no monetary fields — `build_totals` is never called for RFQ).

---

### Step 6 — `builders/invoice.py`

**File:** `builders/invoice.py`

Two direct `format_currency()` calls in `build_invoice_context()` need the currency arg:

```python
currency = doc.currency  # "USD", "EUR", etc.

# Two changed lines:
"amount_paid": format_currency(doc.amount_paid, currency),
"balance_due": format_currency(doc.balance_due, currency),
```

---

### Step 7 — `scripts/generate.py`

**File:** `scripts/generate.py`

Remove the step-3a block entirely (lines labelled "3a. Reject unsupported currencies"):

```python
# DELETE THIS ENTIRE BLOCK:
# ── 3a. Reject unsupported currencies ─────────────────────────────────────
currency = getattr(doc, "currency", None)
if currency is not None and currency != "USD":
    print(
        f"Currency '{currency}' is not yet supported. "
        "Only USD is currently supported."
    )
    sys.exit(1)
```

Currency validation is now handled by the Pydantic schema validators added in Steps 3–4.
Invalid codes produce a structured `ValidationError` with a clear field-level message,
printed cleanly by `_format_validation_errors()`.

---

### Step 8 — Tests

**Files:** `tests/test_utils.py`, `tests/test_schemas.py`

In `tests/test_utils.py`, replace the two existing `format_currency` single-case tests
with a parametrised set:

```python
@pytest.mark.parametrize("value,currency,expected", [
    (Decimal("1234.56"), "USD", "$1,234.56"),
    (Decimal("0"),       "USD", "$0.00"),
    (Decimal("1234.56"), "EUR", "€1,234.56"),
    (Decimal("1234.56"), "GBP", "£1,234.56"),
    (Decimal("1234.00"), "JPY", "¥1,234"),    # no decimal places
    (Decimal("1234.56"), "CNY", "CN¥1,234.56"),
])
def test_format_currency(value, currency, expected):
    assert format_currency(value, currency) == expected
```

In `tests/test_schemas.py`, add schema validation tests:

```python
def test_po_valid_currency_eur():
    raw = load("sample_po.json")
    raw["currency"] = "EUR"
    doc = PurchaseOrder(**raw)
    assert doc.currency == "EUR"

def test_po_invalid_currency_raises():
    raw = load("sample_po.json")
    raw["currency"] = "CHF"
    with pytest.raises(ValidationError):
        PurchaseOrder(**raw)

def test_invoice_valid_currency_jpy():
    raw = load("sample_invoice.json")
    raw["currency"] = "JPY"
    doc = Invoice(**raw)
    assert doc.currency == "JPY"
```

---

## Files NOT Changed

- `templates/*.html` — templates receive pre-formatted strings; no change needed
- `assets/*.css` — no currency-specific styles
- `builders/purchase_order.py` — uses `build_totals()` and `build_line_items()` from
  `_shared.py`; Step 5 handles it transparently
- `builders/request_for_quotation.py` — no monetary fields; `getattr` fallback covers it
- `tests/fixtures/*.json` — existing fixtures omit `currency`, which defaults to `"USD"`;
  no changes needed
- `SKILL.md` / `CLAUDE.md` / `references/*.md` — update after implementation to note
  the 5 supported currencies

---

## Verification

```bash
# Full test suite (must stay green)
uv run pytest

# Smoke test: EUR purchase order (add "currency": "EUR" to sample_po.json)
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview
# Expected: PDF opens with € symbol and correct formatting

# Invalid currency produces clean validation error (set "currency": "CHF" in payload)
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json
# Expected: "Validation failed:\n  currency: must be one of ['CNY', 'EUR', 'GBP', 'JPY', 'USD']"
# Exit code: 1
```

---

## Key Invariants to Preserve

- `format_currency(value)` with no second argument still returns `"$X,XXX.XX"` (USD default)
- `round_money()` in `schemas/base.py` is NOT changed (always 2 dp internally)
- No logic in templates (decision 002) — all symbol/format decisions stay in Python
- RFQ still works with no currency field (safe via `getattr(..., "USD")` fallback)
- All tests pass: `uv run pytest`
