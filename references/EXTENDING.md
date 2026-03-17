# EXTENDING.md — How to Add a New Document Type

This is the complete developer guide for adding a new document type to doc-generator.

**Five files. No other existing files change.**

```text
1. references/<doc_type>.md      → Define all fields, rules, computed fields, layout notes
2. schemas/<doc_type>.py         → Pydantic v2 model derived from the reference
3. templates/<doc_type>.html     → Jinja2 template extending base.html
4. builders/<doc_type>.py        → Context builder function (build_<doc_type>_context)
5. builders/__init__.py          → One DocTypeConfig entry added to REGISTRY
```

The core engine (`generate.py`), base layout (`base.html`), and stylesheet (`style.css`) are never modified when adding a document type.

---

## Step 1 — Write `references/<doc_type>.md`

The reference file is the **source of truth**. Write it first. The schema and template are derived from it. Never derive the reference from the code.

A reference file must contain exactly these sections, in this order:

### 1.1 Document Overview

One or two sentences describing what this document is, who creates it, and who receives it. Identify the two parties by their roles (e.g. issuer/client, buyer/vendor, shipper/consignee).

### 1.2 Field Reference

One table per top-level object (document-level fields, party A, party B, line items array). Column set: `| Field | Type | Required | Default | Description |`. Omit `Default` for sub-object tables where it doesn't apply.

- Mark computed fields as `—` (they belong in §1.3).
- Use `✅` / `❌` for required/optional.
- For dates: note `YYYY-MM-DD` format and whether the field defaults to today.
- For money: type `number`, note the currency.
- For optional arrays: document the array and its entry shape in their own sub-section.
- Document `count_units` on line items if the doc type has a physical vs. service line distinction.

### 1.3 Computed Fields

Table: `| Field | Formula | Example |`. List every field derived from the payload that must never appear in the input JSON. Include: *All monetary values are rounded to 2 decimal places.*

### 1.4 Validation Rules

Bulleted list of every constraint: required strings non-empty, date ordering, numeric ranges, array minimums, cross-field rules.

### 1.5 Claude Data Collection Protocol

Numbered instructions for Claude. Follow the pattern in `purchase_order.md` and `invoice.md`:

1. Identify what the user has already provided.
2. Ask for all missing required fields in one pass (not field by field).
3. List which defaults to apply silently.
4. State explicitly: never ask for computed fields.
5. Logo: ask only if the user mentions it.
6. `count_units` for service lines: ask if a line item is clearly a service.
7. Any doc-type-specific data collection rules (e.g. payment status, payment details).
8. Confirm before generating.

### 1.6 Example Payload

Complete valid JSON with all significant fields populated, followed by the expected computed output showing the math.

### 1.7 Payload Construction

Two sub-sections:

1. **Minimal payload** — required fields only, with `"..."` placeholders. Quick-reference shape for Claude when building a payload.
2. **Field encoding notes** — address line breaks (`\n`), date format (`YYYY-MM-DD`), money as numbers not strings, computed fields excluded, logo path/URL rules.

Follow the pattern in `references/purchase_order.md` and `references/invoice.md`.

### 1.8 Document Layout Notes

Numbered list of the visual structure from top to bottom. Specify party positions (left/right), table columns (and which are conditional), conditional totals rows, and any doc-type-specific components.

---

## Step 2 — Write `schemas/<doc_type>.py`

Model your file on `schemas/purchase_order.py` as the reference implementation. Key rules:

- **`DocModel` base class** — all classes (including nested) inherit from `DocModel`, not `BaseModel`. `DocModel` sets `populate_by_name = True`.
- **`Money` type** — use for every monetary field; never `float` or bare `Decimal`. Accepts `int`, `float`, `str`, or `Decimal` from JSON. See [001-decimal-for-money](../docs/decisions/001-decimal-for-money.md).
- **`@computed_field` + `@property`** — always call `round_money()` on monetary results; add `# type: ignore[prop-decorator]`. Computed fields are silently ignored when present in the payload — they can never be injected.
- **`@field_validator(mode="after")`** — for single-field constraints. Always `@classmethod`.
- **`@model_validator(mode="after")`** — for cross-field constraints (e.g. `due_date >= issue_date`).
- **Defaults** — `Field(default_factory=date.today)` for today; `Decimal("0.00")` (not `0.0`) for monetary defaults.
- **Logo** — accept any string; validate only for `http(s)://` prefix or treat as file path; delegate existence checking to `utils/logo.py` at render time.

---

## Step 3 — Write `templates/<doc_type>.html`

### 3.0 Read the Design System first

Before writing any markup or CSS, read [`references/DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md). It defines the full color palette, typography, all available CSS classes, specificity rules, and how `primary_color` theming works end-to-end. Never hardcode any color, size, or font value — everything uses `var(--)`.

### 3.1 Extend base.html

Every template starts with `{% extends "base.html" %}`. `base.html` provides the `<html>/<head>/<body>` structure, `style.css` link, optional inline `<style>{{ theme_css }}</style>` block, and two override blocks: `{% block header %}` and `{% block content %}`.

### 3.2 Doc-type-specific styles

Never add to `style.css`. Place doc-type-specific CSS in `assets/<doc_type>.css` and load it at module level in `builders/<doc_type>.py`:

```python
_MY_CSS: str = (ASSETS_DIR / "<doc_type>.css").read_text(encoding="utf-8")
```

Pass it as `"theme_css": Markup(_MY_CSS)` (combined with any `primary_color_css` override) in the context builder. All values must use `var(--)` from DESIGN_SYSTEM.md. See `assets/invoice.css` as the reference implementation.

**Specificity note:** The base rule `.totals__table td:first-child` (specificity 0,1,2) sets muted color on first-column cells. Override by qualifying selectors with `.totals__table` (specificity 0,2,1). See the Specificity Rules section in DESIGN_SYSTEM.md.

### 3.3 Template rules

**No logic in templates.** All computation, formatting, and conditionals happen in Python. Permitted Jinja2 constructs:

- `{% if variable %}` — show/hide sections based on pre-computed booleans
- `{% for item in list %}` — iterate over pre-built lists
- `{{ value }}` — output a pre-formatted string
- `{{ address | nl2br }}` — render `\n` as `<br>` in addresses

Not permitted: arithmetic, string formatting, custom filters beyond `nl2br`.

### 3.4 Conditional columns

Omit a column entirely when no row needs it. Compute the gate boolean in the context builder (e.g. `"has_sku_column": any(item.sku for item in doc.line_items)`) and guard both `<th>` and each `<td>` with `{% if has_sku_column %}`. See the SKU column in `templates/purchase_order.html` for the reference pattern.

---

## Step 4 — Write `builders/<doc_type>.py`

Model your file on `builders/purchase_order.py` as the reference implementation. Context builder conventions:

- **No raw `Decimal`** — all monetary values must be strings: `format_currency(doc.amount)`.
- **No raw `date`** — all dates must be strings: `format_date(doc.issue_date)` or `None`.
- **Logos** — `Markup(resolve_logo(doc.party.logo))` or `None`.
- **`css_path`** — always required: `get_css_path()` from `builders._shared`.
- **Boolean flags** — compute `show_tax`, `show_shipping`, `has_sku_column`, etc. here so templates contain no logic.
- **Shared helpers** — use `build_line_items`, `build_line_items_meta`, `build_totals` from `builders._shared` to avoid duplication.
- **`theme_css`** — `Markup(_MY_CSS)` if the doc type needs custom styles beyond `style.css`.

---

## Step 5 — Register in `builders/__init__.py`

One entry. Nothing else changes.

```python
# builders/__init__.py
from schemas.my_doc_type import MyDocType
from builders.my_doc_type import build_my_doc_type_context

REGISTRY: dict[str, DocTypeConfig] = {
    "purchase_order": DocTypeConfig(...),
    "invoice":        DocTypeConfig(...),
    "my_doc_type": DocTypeConfig(           # ← add this entry
        model=MyDocType,
        template="my_doc_type.html",
        build_context=build_my_doc_type_context,
    ),
}
```

---

## Step 6 — Write Test Fixtures

### 6.1 `tests/fixtures/sample_<doc_type>.json`

A complete, valid payload that exercises the key features of the doc type:

- All required fields populated.
- At least one optional field of each category populated (dates, numeric modifiers, notes).
- Multiple line items, with at least one service line (`count_units: false`) if the doc type supports it.
- Logo omitted or set to `null` for portability (so the fixture works in CI without a local file path).

Base the payload on the example in `references/<doc_type>.md`.

### 6.2 `tests/fixtures/invalid_<doc_type>.json`

A payload that triggers multiple validation errors. Cover:

- At least one missing required field (e.g. omit `doc_number`).
- At least one format/range violation (e.g. `tax_rate: 1.5`).
- At least one cross-field violation if the schema has model validators (e.g. `due_date` before `issue_date`).

Expected behavior: `exit code 1`, structured error printed to stdout, no PDF written.

### 6.3 Additional scenario fixtures (optional)

Add a second valid fixture for meaningfully different scenarios:

- Contractor vs. company (Invoice has `sample_invoice_contractor.json`).
- Fully paid vs. partially paid vs. unpaid (Invoice).
- With and without optional blocks (annex, payment details).

---

## Acceptance Checklist

Before declaring a new doc type complete:

- [ ] `references/<doc_type>.md` exists with all required sections (§1.1–1.8), including Payload Construction (minimal shape + encoding notes).
- [ ] `schemas/<doc_type>.py` derived from the reference. All computed fields use `round_money()`.
- [ ] Valid fixture generates a clean, single-page PDF with correct totals.
- [ ] Invalid fixture exits with code 1 and a readable error (no Python traceback).
- [ ] Adding the new doc type required zero changes to `base.html`, `style.css`, or `scripts/generate.py`'s core engine.
- [ ] No raw `Decimal` or `date` objects in the template context.
- [ ] No arithmetic or formatting logic in the Jinja2 template.
