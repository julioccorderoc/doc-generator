# EXTENDING.md — How to Add a New Document Type

This is the complete developer guide for adding a new document type to doc-generator.

**Four files. No existing files change.**

```text
1. references/<doc_type>.md      → Define all fields, rules, computed fields, layout notes
2. schemas/<doc_type>.py         → Pydantic v2 model derived from the reference
3. templates/<doc_type>.html     → Jinja2 template extending base.html
4. scripts/generate.py           → Two lines: one in REGISTRY, one in CONTEXT_BUILDERS
```

The core engine (`generate.py`), base layout (`base.html`), and stylesheet (`style.css`) are never modified when adding a document type.

---

## Step 1 — Write `references/<doc_type>.md`

The reference file is the **source of truth**. Write it first. The schema and template are derived from it. Never derive the reference from the code.

A reference file must contain exactly these sections, in this order:

### 1.1 Document Overview

One or two sentences describing what this document is, who creates it, and who receives it. Identify the two parties by their roles (e.g. issuer/client, buyer/vendor, shipper/consignee).

### 1.2 Field Reference

One table per top-level object (document-level fields, party A, party B, line items array). Use this column set:

```text
| Field | Type | Required | Default | Description |
```

For sub-objects where `Default` doesn't apply, omit that column.

**Rules:**

- Mark computed fields as `—` (do not include them here — they belong in §1.3 Computed Fields).
- Use `✅` for required, `❌` for optional.
- For dates: format `YYYY-MM-DD`, note if it defaults to today.
- For money: use `number` as the type; note the currency.
- For optional arrays (like `payment_details` on Invoice): document the array and its entry shape in its own sub-section.
- Document `count_units` on line items if the doc type has physical vs. service line distinction.

### 1.3 Computed Fields

Table with `Field | Formula | Example` columns. List every field that is derived from the payload and must never appear in the input JSON.

```text
| line_items[n].total | quantity × unit_price  | 5 × $12.00 = $60.00 |
| subtotal            | sum(line item totals)  | $60.00 + $40.00 = $100.00 |
| ...                 | ...                    | ... |
```

Include the note: *All monetary values are rounded to 2 decimal places.*

### 1.4 Validation Rules

Bulleted list of every constraint enforced by the schema. Be specific:

- Required string fields must be non-empty.
- Date ordering constraints (e.g. `due_date >= issue_date`).
- Numeric range constraints (e.g. `tax_rate` in `[0.0, 1.0]`).
- Array minimums (e.g. at least one line item required).
- Cross-field rules (e.g. `paid = true` requires `amount_paid >= 0`).

### 1.5 Claude Data Collection Protocol

A numbered list of instructions for Claude when collecting data to generate this document type. Follow the pattern established in `purchase_order.md` and `invoice.md`:

1. Identify what the user has already provided.
2. Ask for all missing required fields in one pass (not field by field).
3. List which defaults to apply silently (issue_date, currency, tax_rate, etc.).
4. State explicitly: never ask for computed fields.
5. Logo handling: ask only if the user mentions it.
6. `count_units` for service lines: ask if a line item is clearly a service.
7. Any doc-type-specific data (e.g. payment details for invoices, payment status).
8. Confirm before generating.

### 1.6 Example Payload

A complete, valid JSON example with all significant fields populated. Follow it with the expected computed output showing the math.

### 1.7 Document Layout Notes

Numbered list describing the visual structure of the document from top to bottom. Each item is one visual section. This is what the template author implements. Specify:

- Which party appears left vs. right in the address block.
- What columns the line items table has, and any that are conditionally rendered.
- Which totals rows are conditional (e.g. tax only if rate > 0).
- Any doc-type-specific visual components (status strip, payment details block, etc.).

---

## Step 2 — Write `schemas/<doc_type>.py`

### 2.1 File structure

```python
"""
Pydantic v2 schema for the <doc_type> document type.

Source of truth: references/<doc_type>.md
Do not add or remove fields without updating that file first.

Computed fields (...) are derived automatically — they must never
appear in the input payload.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field, computed_field, field_validator, model_validator

from schemas.base import DocModel, Money, round_money
```

### 2.2 Base class

All models (including nested ones) inherit from `DocModel`, not `BaseModel` directly:

```python
from schemas.base import DocModel

class LineItem(DocModel):
    ...

class MyDocType(DocModel):
    ...
```

`DocModel` sets `populate_by_name = True` and is the only place to change shared model config.

### 2.3 Money fields

Use the `Money` annotated type for **every monetary field** — never `float`, never bare `Decimal`:

```python
from schemas.base import Money

unit_price: Money
shipping_cost: Money = Decimal("0.00")
tax_rate: Money = Decimal("0.00")
```

`Money = Annotated[Decimal, BeforeValidator(_coerce_decimal)]` — it accepts `int`, `float`, `str`, or `Decimal` from JSON and coerces to `Decimal` via `str()` to avoid float imprecision (see `docs/decisions/001-decimal-for-money.md`).

### 2.4 Computed fields

Use Pydantic v2's `@computed_field` + `@property` pattern. Always call `round_money()` on monetary results. Add the `# type: ignore[prop-decorator]` comment:

```python
from schemas.base import round_money

@computed_field  # type: ignore[prop-decorator]
@property
def total(self) -> Decimal:
    return round_money(self.quantity * self.unit_price)

@computed_field  # type: ignore[prop-decorator]
@property
def grand_total(self) -> Decimal:
    return round_money(self.subtotal + self.tax_amount + self.shipping_cost)
```

**Computed fields must never be accepted from the payload.** Pydantic v2 silently ignores extra fields by default when using `model_config = {"populate_by_name": True}` — the payload cannot inject computed values.

### 2.5 Field validators

Use `@field_validator` with `mode="after"` for single-field constraints. Use `@classmethod`:

```python
@field_validator("quantity", "unit_price", mode="after")
@classmethod
def must_be_positive(cls, v: Decimal) -> Decimal:
    if v <= 0:
        raise ValueError("must be greater than zero")
    return v

@field_validator("tax_rate", mode="after")
@classmethod
def tax_rate_in_range(cls, v: Decimal) -> Decimal:
    if not (Decimal("0.0") <= v <= Decimal("1.0")):
        raise ValueError("must be between 0.0 and 1.0")
    return v

@field_validator("name", "address", mode="after")
@classmethod
def must_be_non_empty(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("must not be empty")
    return v
```

### 2.6 Cross-field validation

Use `@model_validator(mode="after")` for constraints that span multiple fields:

```python
@model_validator(mode="after")
def due_after_issue(self) -> MyDocType:
    if self.due_date and self.due_date < self.issue_date:
        raise ValueError("due_date must be on or after issue_date")
    return self
```

### 2.7 Optional fields with defaults

Use `Field(default_factory=date.today)` for fields that default to today. Use `Decimal("0.00")` (not `0.0`) for monetary defaults:

```python
issue_date: date = Field(default_factory=date.today)
tax_rate: Money = Decimal("0.00")
notes: Optional[str] = None
```

### 2.8 Logo field

If your doc type has a party with a logo, follow the existing pattern — accept any string (file path or URL), validate format at a coarse level in the schema, delegate existence checking to `utils/logo.py` at render time:

```python
@field_validator("logo", mode="after")
@classmethod
def logo_format(cls, v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if v.startswith("http://") or v.startswith("https://"):
        return v
    # Treat as a file path — existence validated at render time by utils/logo.py
    return v
```

---

## Step 3 — Write `templates/<doc_type>.html`

### 3.0 Read the Design System first

Before writing any markup or CSS, read [`references/DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md). It defines:

- The full color palette and what each variable is used for
- The typography hierarchy (font sizes and weights per element)
- The header accent stripe
- The totals block layout and the CSS specificity rules required to override row styles
- How `primary_color` theming works end-to-end

Do not hardcode any color, size, or font value in templates. Everything must reference a `var(--*)` from the design system.

### 3.1 Extend base.html

Every template must start with:

```html
{% extends "base.html" %}
```

`base.html` provides:

- `<html>`, `<head>`, `<body>` structure
- The `style.css` link via `{{ css_path }}`
- An optional `<style>{{ theme_css }}</style>` block (only rendered if `theme_css` is defined in context)
- Two override blocks: `{% block header %}` and `{% block content %}`

### 3.2 Available CSS classes from `style.css`

These classes are available in all templates. Do not redefine their core styles:

| Class | Purpose |
|---|---|
| `.doc-header` | Flex row: logo left, title block right |
| `.doc-header__logo` | Left column of the header (logo or placeholder) |
| `.doc-header__logo--placeholder` | Empty spacer when no logo |
| `.doc-header__title` | Right column of the header |
| `.doc-header__type` | Document type label (e.g. "Purchase Order") |
| `.doc-header__number` | Document identifier (PO number, invoice number) |
| `.doc-header__date` | Issue date |
| `.address-block` | Flex row: two party columns |
| `.address-block__party` | One party column |
| `.address-block__label` | Small uppercase party label (e.g. "Vendor", "From") |
| `.address-block__name` | Bold party name |
| `.address-block__detail` | Address lines |
| `.address-block__contact` | Contact name / email / phone line |
| `.meta-band` | Compact horizontal band for dates and terms |
| `.meta-band__item` | One item in the meta band |
| `.meta-band__label` | Small label above the value |
| `.meta-band__value` | The value |
| `.line-items` | The line items table |
| `.num` | Row number column |
| `.sku` | SKU column (conditionally rendered) |
| `.description` | Item description column (grows) |
| `.unit` | Unit label column |
| `.qty` | Quantity column |
| `.price` | Unit price column |
| `.total` | Line total column |
| `.bottom-section` | Flex row: notes (left, grows) · totals (right, fixed) |
| `.bottom-section__notes` | Notes column |
| `.bottom-section__totals` | Totals column |
| `.notes__label` | "Notes" label |
| `.notes__text` | Notes body |
| `.totals__table` | The totals table |
| `.totals__units` | Total units row (visually separated) |
| `.totals__divider` | Row with a top border separator |
| `.totals__grand` | Grand total row — bold, `--color-primary` text, hairline rule above via `.totals__divider`, no background fill |

### 3.3 Adding doc-type-specific styles

Do **not** add new CSS rules to `style.css`. Instead, define a `_MY_THEME_CSS` string constant in `generate.py` and pass it as `"theme_css": Markup(...)` in the context builder. The base template injects it as an inline `<style>` block when the variable is defined.

```python
# In generate.py:
_MY_THEME_CSS = """
.my-component {
    border-top: 2pt solid var(--color-accent);
    padding: var(--spacing-md);
    color: var(--color-primary);
}
"""
```

All values must use CSS custom properties from the design system — never hardcode colors, sizes, or fonts. See [`references/DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) for the full variable reference.

**Specificity note:** The base rule `.totals__table td:first-child` (specificity 0,1,2) sets muted color on all first-column cells. When your doc type adds rows to the totals table that need different styling, always qualify selectors with `.totals__table` to get specificity 0,2,1 and override it. See the Specificity Rules section in `DESIGN_SYSTEM.md`.

### 3.4 Template rules

**No logic in templates.** All computation, formatting, and conditional logic happens in Python (in the context builder). Templates only display values. Permitted Jinja2 constructs:

- `{% if variable %}` — show/hide sections based on pre-computed booleans from the context
- `{% for item in list %}` — iterate over pre-built lists
- `{{ value }}` — output a pre-formatted string
- `{{ address | nl2br }}` — apply the `nl2br` filter to render `\n` as `<br>` in addresses

Not permitted in templates:

- Arithmetic (`+`, `-`, `*`, `/`)
- String formatting (`format()`, `|int`, custom Jinja2 filters beyond `nl2br`)
- Complex conditionals that compute display values

### 3.5 Conditional columns

The SKU column pattern — omit the column entirely when no line item has a SKU — is the established pattern for conditional table columns:

```html
{% if has_sku_column %}<th class="sku">SKU</th>{% endif %}
...
{% if has_sku_column %}<td class="sku">{{ item.sku or "" }}</td>{% endif %}
```

The `has_sku_column` boolean is computed in the context builder:

```python
"has_sku_column": any(item.sku for item in doc.line_items),
```

---

## Step 4 — Register in `scripts/generate.py`

Two lines. Nothing else changes.

### 4.1 Add to REGISTRY

```python
REGISTRY: dict[str, tuple[type, str]] = {
    "purchase_order": (PurchaseOrder, "purchase_order.html"),
    "invoice": (Invoice, "invoice.html"),
    "my_doc_type": (MyDocType, "my_doc_type.html"),   # ← add this line
}
```

### 4.2 Add to CONTEXT_BUILDERS

```python
CONTEXT_BUILDERS: dict[str, callable] = {
    "purchase_order": _build_po_context,
    "invoice": _build_invoice_context,
    "my_doc_type": _build_my_doc_type_context,   # ← add this line
}
```

### 4.3 Context builder conventions

The context builder receives the validated model instance and returns a `dict` of display-ready values. Rules:

- **No raw `Decimal` in the return dict.** All monetary values must be strings: `format_currency(doc.amount)`.
- **No raw `date` objects.** All dates must be strings: `format_date(doc.issue_date)` or `None`.
- **Logos must be `Markup` or `None`.** Call `resolve_logo(doc.party.logo)` then wrap: `Markup(logo_data) if logo_data else None`.
- **`css_path` is always required** (used by `base.html`): `"css_path": Markup((ASSETS_DIR / "style.css").as_uri())`.
- **Boolean flags for optional sections** (e.g. `show_tax`, `show_shipping`, `has_sku_column`) are computed here so templates don't contain logic.
- **`theme_css`** (optional): `"theme_css": Markup(_MY_THEME_CSS)` if the doc type needs component styles beyond `style.css`.

Minimal context builder skeleton:

```python
def _build_my_doc_type_context(doc: MyDocType) -> dict:
    logo_data = resolve_logo(doc.issuer.logo)

    return {
        # Header
        "doc_number": doc.doc_number,
        "issue_date": format_date(doc.issue_date),
        # Parties
        "issuer": {
            "name": doc.issuer.name,
            "address": doc.issuer.address,
            "logo": Markup(logo_data) if logo_data else None,
        },
        # Line items
        "line_items": [
            {
                "description": item.description,
                "quantity": format_quantity(item.quantity),
                "unit_price": format_currency(item.unit_price),
                "total": format_currency(item.total),
            }
            for item in doc.line_items
        ],
        # Totals
        "grand_total": format_currency(doc.grand_total),
        # Template infrastructure
        "css_path": Markup((ASSETS_DIR / "style.css").as_uri()),
    }
```

---

## Step 5 — Write Test Fixtures

### 5.1 `tests/fixtures/sample_<doc_type>.json`

A complete, valid payload that exercises the key features of the doc type:

- All required fields populated.
- At least one optional field of each category populated (dates, numeric modifiers, notes).
- Multiple line items, with at least one service line (`count_units: false`) if the doc type supports it.
- Logo omitted or set to `null` for portability (so the fixture works in CI without a local file path).

Base the payload on the example in `references/<doc_type>.md`.

### 5.2 `tests/fixtures/invalid_<doc_type>.json`

A payload that triggers multiple validation errors. Cover:

- At least one missing required field (e.g. omit `doc_number`).
- At least one format/range violation (e.g. `tax_rate: 1.5`).
- At least one cross-field violation if the schema has model validators (e.g. `due_date` before `issue_date`).

Expected behavior: `exit code 1`, structured error printed to stdout, no PDF written.

### 5.3 Additional scenario fixtures (optional)

Add a second valid fixture for meaningfully different scenarios:

- Contractor vs. company (Invoice has `sample_invoice_contractor.json`).
- Fully paid vs. partially paid vs. unpaid (Invoice).
- With and without optional blocks (annex, payment details).

---

## Acceptance Checklist

Before declaring a new doc type complete:

- [ ] `references/<doc_type>.md` exists with all required sections.
- [ ] `schemas/<doc_type>.py` derived from the reference. All computed fields use `round_money()`.
- [ ] Valid fixture generates a clean, single-page PDF with correct totals.
- [ ] Invalid fixture exits with code 1 and a readable error (no Python traceback).
- [ ] Adding the new doc type required zero changes to `base.html`, `style.css`, or `generate.py`'s core engine.
- [ ] No raw `Decimal` or `date` objects in the template context.
- [ ] No arithmetic or formatting logic in the Jinja2 template.
