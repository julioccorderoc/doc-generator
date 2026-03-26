# EXTENDING.md — How to Add a New Document Type

This is the complete developer guide for adding a new document type to doc-generator.

> **Running this as a coding agent session?** Copy [`references/NEW_DOC_TYPE.md`](NEW_DOC_TYPE.md), fill in the placeholders, and paste it as your opening prompt. It handles orient, implementation order, verification, and the acceptance checklist in one shot.

**Five files. No other existing files change.**

```text
1. schemas/<doc_type>.py         → Pydantic v2 model (The Single Source of Truth)
2. references/<doc_type>.md      → Tiny quirk list and minimal JSON shape
3. templates/<doc_type>.html     → Jinja2 template extending base.html
4. builders/<doc_type>.py        → Context builder function (build_<doc_type>_context)
5. builders/__init__.py          → One DocTypeConfig entry added to REGISTRY
```

The core engine (`generate.py`), base layout (`base.html`), and stylesheet (`style.css`) are never modified when adding a document type.

---

## Step 1 — Write `schemas/<doc_type>.py`

The Pydantic schema is the **Single Source of Truth**. Write it first.
Model your file on `schemas/purchase_order.py` as the reference implementation. Key rules:

- **`DocModel` base class** — all classes (including nested) inherit from `DocModel`, not `BaseModel`. `DocModel` sets `populate_by_name = True`.
- **`Money` type** — use for every monetary field; never `float` or bare `Decimal`. Accepts `int`, `float`, `str`, or `Decimal` from JSON. See [001-decimal-for-money](../docs/decisions/001-decimal-for-money.md).
- **Descriptions as documentation** — Every field must have a `Field(..., description="...")`. Describe what the field means, its constraints, and when the payload generator should ask for it.
- **Friendly Validation Errors** — `ValueError` messages raised by your validators will be fed directly to the user by Claude. Make them conversational (e.g. `"The delivery date cannot be before the issue date."`).
- **`@computed_field` + `@property`** — always call `round_money()` on monetary results; add `# type: ignore[prop-decorator]`. Computed fields are silently ignored when present in the payload — they can never be injected.
- **`@field_validator(mode="after")`** — for single-field constraints. Always `@classmethod`.
- **`@model_validator(mode="after")`** — for cross-field constraints (e.g. `due_date >= issue_date`).
- **Defaults** — `Field(default_factory=date.today, ...)` for today; `Field(default=Decimal("0.00"), ...)` (not `0.0`) for monetary defaults.
- **Logo** — accept `Optional[str]`; add a `@field_validator` that enforces the value starts with `data:image/` (or is `None`). See `schemas/purchase_order.py` `Buyer.logo_format` for the reference implementation. `utils/logo.py` also validates at render time as defense-in-depth, but the schema is the primary enforcement point.

---

## Step 2 — Write `references/<doc_type>.md`

A tiny, supplementary reference file to teach the AI payload generator about document quirks and the expected JSON shape.
Follow the pattern in `references/purchase_order.md`. It must contain exactly these sections:

### Document Quirks

List any behavioral quirks that don't fit into Pydantic field descriptions. Examples: How to handle service lines vs physical lines, rules around optional identifier columns appearing, or whether a terms attachment is included by default.

### Payload Construction

Two sub-sections:

1. **Minimal payload** — required fields only, with `"..."` placeholders. Quick-reference shape for Claude when building a payload.
2. **Field encoding notes** — address line breaks (`\n`), date format (`YYYY-MM-DD`), money as numbers not strings.

---

## Step 3 — Write `templates/<doc_type>.html`

### 3.0 Read the Design System first

Before writing any markup or CSS, read [`references/DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md). It defines the full color palette, typography, all available CSS classes, specificity rules, and how `primary_color` theming works end-to-end. Never hardcode any color, size, or font value — everything uses `var(--)`.

### 3.1 Extend base.html

Every template starts with `{% extends "base.html" %}`. `base.html` provides the `<html>/<head>/<body>` structure, `style.css` link, optional inline `<style>{{ theme_css }}</style>` block, and three override blocks: `{% block header %}`, `{% block content %}`, and `{% block footer %}`.

The footer renders automatically: `base.html` outputs `<div class="doc-footer">{{ footer_text }}</div>` whenever `footer_text` is defined and non-empty in the context. Add `"footer_text": build_footer_text(doc.<issuing_party>)` to the context builder — `build_footer_text` is in `builders._shared`. No `{% block footer %}` override is needed in the child template. Override only to suppress (`{% block footer %}{% endblock %}`) or customise the footer.

### 3.2 Doc-type-specific styles

Never add to `style.css`. Place doc-type-specific CSS in `assets/<doc_type>.css` and load it at module level in `builders/<doc_type>.py`:

```python
_MY_CSS: str = (ASSETS_DIR / "<doc_type>.css").read_text(encoding="utf-8")
```

Pass it as `"theme_css": Markup(_MY_CSS + primary_color_css(doc.primary_color) + font_family_css(doc.font_family) + density_css(doc.doc_style))` in the context builder. All three helpers are in `builders._shared` and return `""` when the field is `None` or `"normal"`, so concatenation is always safe. Density goes last — it must override any variables set by the doc-type CSS. All CSS values must use `var(--)` from DESIGN_SYSTEM.md. See `assets/invoice.css` as the reference implementation.

**Specificity note:** The base rule `.totals__table td:first-child` (specificity 0,1,2) sets muted color on first-column cells. Override by qualifying selectors with `.totals__table` (specificity 0,2,1). See the Specificity Rules section in DESIGN_SYSTEM.md.

**Page breaks:** `style.css` provides the following global rules for free — never repeat them in doc-type CSS:

- `tr { break-inside: avoid }` — rows never split across pages
- `thead { break-after: avoid }` — header row is never stranded at the bottom of a page without at least one body row
- `.meta-band { break-inside: avoid }` — the meta band stays together
- `.bottom-section__totals { break-inside: avoid }` — the totals block stays together

If your doc type has other elements that must stay together (e.g. a section-title row followed by content rows), add `break-after: avoid` or `break-inside: avoid` to the doc-type CSS file. See `rfq-spec-section-header` in `assets/request_for_quotation.css` as the reference pattern.

### 3.3 Template rules

**No logic in templates.** All computation, formatting, and conditionals happen in Python. Permitted Jinja2 constructs:

- `{% if variable %}` — show/hide sections based on pre-computed booleans
- `{% for item in list %}` — iterate over pre-built lists
- `{{ value }}` — output a pre-formatted string
- `{{ address | nl2br }}` — render `\n` as `<br>` in addresses

Not permitted: arithmetic, string formatting, custom filters beyond `nl2br`.

### 3.4 Conditional columns

Omit a column entirely when no row needs it. Compute the gate boolean in the context builder (e.g. `"has_buyer_id_column": any(item.buyer_id for item in doc.line_items)`) and guard both `<th>` and each `<td>` with `{% if has_buyer_id_column %}`. See the `buyer_id` / `vendor_id` / `barcode` columns in `templates/purchase_order.html` for the reference pattern.

---

## Step 4 — Write `builders/<doc_type>.py`

Model your file on `builders/purchase_order.py` as the reference implementation. Context builder conventions:

- **No raw `Decimal`** — all monetary values must be strings: `format_currency(doc.amount)`.
- **No raw `date`** — all dates must be strings: `format_date(doc.issue_date)` or `None`.
- **Logos** — `Markup(resolve_logo(doc.party.logo))` or `None`.
- **`css_path`** — always required: `get_css_path()` from `builders._shared`.
- **Boolean flags** — compute `show_tax`, `show_shipping`, `has_buyer_id_column`, etc. here so templates contain no logic.
- **Shared helpers** — use `build_line_items`, `build_line_items_meta`, `build_totals` from `builders._shared` to avoid duplication.
- **`theme_css`** — `Markup(_MY_CSS + primary_color_css(doc.primary_color) + font_family_css(doc.font_family) + density_css(doc.doc_style))`. Import all three helpers from `builders._shared`. They return `""` when the field is `None` or `"normal"`. Density goes last.

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
        file_prefix="MDT",                  # ← short uppercase prefix for output filenames
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

- [ ] `schemas/<doc_type>.py` is heavily documented with `Field(description=...)` and friendly error strings.
- [ ] `references/<doc_type>.md` exists with document quirks and minimal payload shape.
- [ ] Valid fixture generates a clean, single-page PDF with correct totals.
- [ ] Invalid fixture exits with code 1 and a readable error (no Python traceback).
- [ ] Adding the new doc type required zero changes to `base.html`, `style.css`, or `scripts/generate.py`'s core engine.
- [ ] No raw `Decimal` or `date` objects in the template context.
- [ ] No arithmetic or formatting logic in the Jinja2 template.
