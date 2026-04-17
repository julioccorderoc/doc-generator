# Plan: Multi-Currency Support (Top 5 Currencies)

**Status:** Ready to implement — not yet started.
**Project root:** `/Users/juliocordero/Documents/NCL/doc-generator`
**Run tests:** `uv run pytest` (no system deps needed for unit tests)
**Run generate:** `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py ...`

---

## Context & Background

`doc-generator` is a schema-driven PDF generation CLI (no LLM in render path). Supports `purchase_order`, `invoice`, and `request_for_quotation`. RFQ has no monetary fields — unaffected by this change.

**Current state (Phase 8):**

- `format_currency()` in `utils/formatting.py:11` hardcoded to `$X,XXX.XX` (USD only).
- Both `PurchaseOrder` and `Invoice` have `currency: str = "USD"`, but it's accepted by schema then hard-blocked in `scripts/generate.py` (step 3a) before reaching builder.
- No tests for non-USD formatting.

**Goal:** Allow top 5 currencies. USD stays default. Invalid codes produce clean Pydantic validation error. No template changes needed — formatted string (symbol included) already fully produced in Python.

---

## Supported Currencies

| Code | Name          | Symbol | Decimals | Example      |
|------|---------------|--------|----------|--------------|
| USD  | US Dollar     | $      | 2        | $1,234.56    |
| EUR  | Euro          | €      | 2        | €1,234.56    |
| GBP  | British Pound | £      | 2        | £1,234.56    |
| JPY  | Japanese Yen  | ¥      | 0        | ¥1,235       |
| CNY  | Chinese Yuan  | CN¥    | 2        | CN¥1,234.56  |

**Number format:** American style for all (comma thousands, period decimal). Consistent with existing `format_quantity`.

**JPY:** No subunit (sen). Displayed as whole number. Internal `round_money()` (always 2dp) unchanged — JPY amounts in practice are whole numbers; display layer formats with 0 decimal places.

**CNY:** Uses `CN¥` prefix to distinguish from JPY (both use `¥` in isolation).

---

## Architecture Reference

All formatting in Python builders, never in Jinja2 templates (ADR-002). Templates receive fully-formatted strings. **Zero template changes** for this feature.

### Call-site map for `format_currency`

| File | Function | Call | Argument |
|------|----------|------|----------|
| `builders/_shared.py` | `build_line_items(doc)` | 2x per item | `item.unit_price`, `item.total` |
| `builders/_shared.py` | `build_totals(doc)` | 4x | `doc.subtotal`, `doc.tax_amount`, `doc.shipping_cost`, `doc.grand_total` |
| `builders/invoice.py` | `build_invoice_context(doc)` | 2x | `doc.amount_paid`, `doc.balance_due` |

**Total call sites to update: 8** (all pass `Decimal`, all need `currency` arg added).

### How currency flows today (payload -> PDF)

```text
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

```text
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

Add `_CURRENCY_CONFIG` lookup and update `format_currency` to accept `currency` parameter (default `"USD"` — existing callers unaffected).

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

### Step 2 — `utils/constants.py` _(partially done)_

`SUPPORTED_CURRENCIES` already lives in `utils/constants.py` as `("USD",)`. Expand the tuple to include the new codes:

```python
SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP", "JPY", "CNY")
```

---

### Step 3 — `schemas/purchase_order.py` _(done)_

The `validate_currency` helper in `schemas/base.py` and its wiring on `PurchaseOrder` (`_validate_currency = field_validator("currency", mode="after")(validate_currency)`) are already in place. Nothing to do here — expanding the tuple in Step 2 is picked up automatically.

---

### Step 4 — `schemas/invoice.py` _(done)_

Same as Step 3: `Invoice._validate_currency` is already wired.

---

### Step 5 — `builders/_shared.py`

Both `build_line_items(doc)` and `build_totals(doc)` already receive full `doc` object. Read `currency` and pass to `format_currency`:

```python
# At top of each function:
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

No signature change — callers unaffected. `getattr(doc, "currency", "USD")` safely returns `"USD"` for RFQ (no currency field, no monetary fields — `build_totals` never called for RFQ).

---

### Step 6 — `builders/invoice.py`

Two direct `format_currency()` calls in `build_invoice_context()` need currency arg:

```python
currency = doc.currency  # "USD", "EUR", etc.

# Two changed lines:
"amount_paid": format_currency(doc.amount_paid, currency),
"balance_due": format_currency(doc.balance_due, currency),
```

---

### Step 7 — `scripts/generate.py`

Remove step-3a block entirely (lines labelled "3a. Reject unsupported currencies"):

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

Currency validation now handled by Pydantic schema validators (Steps 3-4). Invalid codes produce structured `ValidationError` with clear field-level message, printed cleanly by `_format_validation_errors()`.

---

### Step 8 — Tests

**Files:** `tests/test_utils.py`, `tests/test_schemas.py`

In `tests/test_utils.py`, replace existing `format_currency` single-case tests with parametrised set:

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

- `templates/*.html` — receive pre-formatted strings; no change needed
- `assets/*.css` — no currency-specific styles
- `builders/purchase_order.py` — uses `build_totals()` and `build_line_items()` from `_shared.py`; Step 5 handles transparently
- `builders/request_for_quotation.py` — no monetary fields; `getattr` fallback covers it
- `tests/fixtures/*.json` — existing fixtures omit `currency`, defaults to `"USD"`; no changes needed
- `SKILL.md` / `CLAUDE.md` / `references/*.md` — update after implementation to note 5 supported currencies

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
- `round_money()` in `schemas/base.py` NOT changed (always 2dp internally)
- No logic in templates (ADR-002) — all symbol/format decisions stay in Python
- RFQ still works with no currency field (safe via `getattr(..., "USD")` fallback)
- All tests pass: `uv run pytest`
