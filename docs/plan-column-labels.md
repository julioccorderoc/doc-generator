# Plan — Feature: Column Label Overrides

**Status:** Draft — not yet started
**Complexity:** Low-Medium
**Touches:** 3 schemas, 3 builders, 3 templates, `_shared.py`, tests, 3 reference docs
**Breaking changes:** None — purely additive

---

## What / Why

Users need to customize what the column headers say in their documents.
Different companies use different terminology:

- "Qty" → "Quantity" or "Units"
- "Unit Price" → "Rate" or "Unit Rate"
- "Total" → "Amount" or "Line Total"
- "Description" → "Item" or "Product"
- "Buyer ID" → "Product Code" or "Part #"
- "Vendor ID" → "Supplier Code"
- "Specification" → "Parameter" (RFQ)

The headers are currently hardcoded in templates. This feature adds an optional
`column_labels` dict field to each schema that overrides specific column headers
without changing anything else.

---

## Design Decision

**Option A (chosen):** Optional dict field `column_labels: dict[str, str]`

- Keys are snake_case column identifiers; values are display strings
- Builder merges defaults with overrides; template uses `{{ labels.qty }}`
- Validator rejects unknown keys with a clear error

**Option B (rejected):** Individual fields (`label_qty`, `label_unit_price`, ...)

- Schema bloat, hard to discover, hard to document

---

## Schema Changes

### Per doc type — valid keys and defaults

**Purchase Order** (`schemas/purchase_order.py`):

```python
column_labels: Optional[dict[str, str]] = None
```

Valid keys and default display values:

```python
PO_DEFAULT_LABELS = {
    "description": "Description",
    "qty":         "Qty",
    "unit":        "Unit",
    "unit_price":  "Unit Price",
    "total":       "Total",
    "buyer_id":    "Buyer ID",
    "vendor_id":   "Vendor ID",
    "barcode":     "Barcode",
}
```

**Invoice** (`schemas/invoice.py`):

```python
column_labels: Optional[dict[str, str]] = None
```

Valid keys:

```python
INVOICE_DEFAULT_LABELS = {
    "description": "Description",
    "qty":         "Qty",
    "unit":        "Unit",
    "unit_price":  "Unit Price",
    "total":       "Total",
    "buyer_id":    "Buyer ID",
    "sku":         "SKU",
}
```

**RFQ** (`schemas/request_for_quotation.py`):

```python
column_labels: Optional[dict[str, str]] = None
```

Valid keys:

```python
RFQ_DEFAULT_LABELS = {
    "product":       "Product",       # product summary table, first column
    "specification": "Specification", # spec table, label column
    "details":       "Details",       # spec table, value column
}
```

Note: RFQ product attribute columns (dynamic) are already customizable via
`product_attributes[].header` — no change needed there.

### Validator (same pattern for all three)

```python
@field_validator("column_labels")
@classmethod
def validate_column_labels(cls, v):
    if v is None:
        return v
    valid_keys = set(DEFAULT_LABELS)
    invalid = set(v) - valid_keys
    if invalid:
        raise ValueError(
            f"Unknown column_labels keys: {sorted(invalid)}. "
            f"Valid keys: {sorted(valid_keys)}"
        )
    return v
```

---

## Builder Changes

### `builders/_shared.py` — new helper

```python
def resolve_column_labels(
    defaults: dict[str, str],
    overrides: dict[str, str] | None,
) -> dict[str, str]:
    """Merge user overrides into the default column label map."""
    if not overrides:
        return defaults
    return {**defaults, **overrides}
```

### Each builder — pass `labels` to context

```python
# In build_po_context(), build_invoice_context(), build_rfq_context():
labels = resolve_column_labels(DEFAULT_LABELS, doc.column_labels)
# Add to context dict:
context["labels"] = labels
```

The DEFAULT_LABELS constants can live in `_shared.py` or in each builder module.
Preference: each builder owns its own defaults (they're doc-type-specific), and
`_shared.py` provides only the `resolve_column_labels()` helper.

---

## Template Changes

Replace every hardcoded column header `<th>` text with a `labels` variable lookup.

**Example — purchase_order.html:**

```html
<!-- Before -->
<th>Description</th>
<th>Unit</th>
<th>Qty</th>
<th>Unit Price</th>
<th>Total</th>

<!-- After -->
<th>{{ labels.description }}</th>
<th>{{ labels.unit }}</th>
<th>{{ labels.qty }}</th>
<th>{{ labels.unit_price }}</th>
<th>{{ labels.total }}</th>
```

Conditional columns use the same pattern:

```html
{% if meta.has_buyer_id_column %}<th>{{ labels.buyer_id }}</th>{% endif %}
{% if meta.has_vendor_id_column %}<th>{{ labels.vendor_id }}</th>{% endif %}
{% if meta.has_barcode_column %}<th>{{ labels.barcode }}</th>{% endif %}
```

---

## Files to Change

| File | Change |
|---|---|
| `schemas/purchase_order.py` | Add `column_labels` field + validator |
| `schemas/invoice.py` | Add `column_labels` field + validator |
| `schemas/request_for_quotation.py` | Add `column_labels` field + validator |
| `builders/_shared.py` | Add `resolve_column_labels()` |
| `builders/purchase_order.py` | Call `resolve_column_labels()`, pass `labels` to context |
| `builders/invoice.py` | Same |
| `builders/request_for_quotation.py` | Same |
| `templates/purchase_order.html` | Replace hardcoded `<th>` text |
| `templates/invoice.html` | Replace hardcoded `<th>` text |
| `templates/request_for_quotation.html` | Replace hardcoded `<th>` text |
| `references/purchase_order.md` | Document `column_labels` field |
| `references/invoice.md` | Document `column_labels` field |
| `references/request_for_quotation.md` | Document `column_labels` field |
| `SKILL.md` | Mention label override capability |
| `tests/test_schemas.py` | Add tests: valid overrides, unknown key rejection |
| `tests/test_builders.py` | Add test: labels propagate to context correctly |

**Total: ~15 files.** All additive changes — no existing behaviour is modified.

---

## Test Cases to Add

```python
# test_schemas.py
def test_po_column_labels_valid():
    # column_labels with known keys → accepted
def test_po_column_labels_unknown_key():
    # column_labels with "foobar" → ValidationError with clear message
def test_po_column_labels_none():
    # omitting column_labels → defaults are used
def test_invoice_column_labels_valid():
def test_rfq_column_labels_valid():

# test_builders.py
def test_po_labels_override_propagates_to_context():
    # Build context with column_labels={"qty": "Quantity"}
    # Assert context["labels"]["qty"] == "Quantity"
    # Assert context["labels"]["description"] == "Description"  (untouched default)
```

---

## Example Payload Usage

```json
{
  "po_number": "PO-2026-001",
  "column_labels": {
    "qty": "Quantity",
    "unit_price": "Unit Rate",
    "total": "Amount",
    "buyer_id": "Part #"
  }
}
```

---

## Notes

- No changes to `style.css`, `base.html`, `generate.py`, or `builders/__init__.py`
- The `#` column (row number) is not customizable — it has no semantic name
- For RFQ, the dynamic `product_attributes[].header` values are already user-controlled;
  `column_labels` only covers the fixed columns (`product`, `specification`, `details`)
- Column body cells do NOT change (they still use the same Python keys for data access)
- Validation in the schema ensures only known keys are accepted — prevents typos silently
  falling back to the default header
