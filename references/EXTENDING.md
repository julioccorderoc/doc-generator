# EXTENDING.md — How to Add a New Document Type

Complete developer guide for adding new document types.

> **Running as coding agent session?** Copy [`references/NEW_DOC_TYPE.md`](NEW_DOC_TYPE.md), fill in placeholders, paste as opening prompt. Handles orient, implementation, verification, and acceptance in one shot.

**4 new files + 1 registry edit.** Steps 1–4 create new files; step 5 appends a single entry to the existing `builders/__init__.py` registry.

```text
1. schemas/<doc_type>.py         → Pydantic v2 model (Single Source of Truth)        [NEW]
2. references/<doc_type>.md      → Tiny quirk list and minimal JSON shape            [NEW]
3. templates/<doc_type>.html     → Jinja2 template extending base.html               [NEW]
4. builders/<doc_type>.py        → Context builder function (build_<doc_type>_context) [NEW]
5. builders/__init__.py          → Add one DocTypeConfig entry to REGISTRY           [EDIT]
```

Core engine (`generate.py`), base layout (`base.html`), stylesheet (`style.css`), and density presets (`assets/density/*.css`) are never modified when adding doc types.

---

## Step 1 — Write `schemas/<doc_type>.py`

Pydantic schema = **Single Source of Truth**. Write first.
Model on `schemas/purchase_order.py` as reference. Key rules:

- **`DocModel` base class** — all classes (including nested) inherit from `DocModel`, not `BaseModel`. Sets `populate_by_name = True`.
- **Reuse mixins from `schemas/base.py`** — inherit instead of copy-pasting. `ThemeFieldsMixin` provides the standard `logo`, `primary_color`, `font_family`, `doc_style` fields and their validators. `MonetaryComputedMixin` provides the standard `subtotal`, `tax_amount`, `grand_total`, and `total_units` computed fields for any doc type with line items + tax. Compose them on the root model: `class MyDoc(DocModel, ThemeFieldsMixin, MonetaryComputedMixin): ...`. Reach for the shared `validate_non_empty_string`, `validate_tax_rate`, `validate_at_least_one_line_item`, and `validate_currency` helpers in `base.py` before writing new validators.
- **`Money` type** — every monetary field; never `float` or bare `Decimal`. Accepts `int`, `float`, `str`, or `Decimal` from JSON. See [001-decimal-for-money](../docs/decisions/001-decimal-for-money.md).
- **Descriptions as documentation** — every field needs `Field(..., description="...")`. Describe meaning, constraints, when to ask.
- **Friendly Validation Errors** — `ValueError` messages go directly to user via Claude. Make them conversational (e.g. `"The delivery date cannot be before the issue date."`).
- **`@field_validator(mode="after")`** — single-field constraints. Always `@classmethod`.
- **`@model_validator(mode="after")`** — cross-field constraints (e.g. `due_date >= issue_date`).
- **Defaults** — `Field(default_factory=date.today, ...)` for today; `Field(default=Decimal("0.00"), ...)` (not `0.0`) for monetary defaults.
- **Logo** — covered by `ThemeFieldsMixin`. If you don't inherit the mixin, add `logo: Optional[str] = Field(default=None, ...)` at **root level** (not nested in party sub-model) and a `@field_validator` enforcing `data:image/[type];base64,[chars]` (or `None`). See `schemas/purchase_order.py` `PurchaseOrder.logo_format` for reference. `utils/logo.py` also validates at render time as defense-in-depth, but schema is primary enforcement.

### Why computed fields (and how Pydantic handles them)

Derived monetary values (`subtotal`, `tax_amount`, `grand_total`, line item `total`) are **always computed from the raw inputs** — never accepted from the payload. This guarantees a single source of truth: a malformed or tampered `subtotal` in the JSON cannot reach the PDF. Pydantic v2 silently ignores any extra keys whose names match `@computed_field` properties when validating input, then recomputes them from the validated raw fields. Use `MonetaryComputedMixin` to inherit the standard set, or write your own:

```python
@computed_field  # type: ignore[prop-decorator]
@property
def subtotal(self) -> Money:
    return round_money(sum((item.total for item in self.line_items), Decimal("0")))
```

Always call `round_money()` on monetary results and add the `# type: ignore[prop-decorator]` comment.

---

## Step 2 — Write `references/<doc_type>.md`

Tiny supplementary reference for AI payload generator. Teaches document quirks and expected JSON shape.
Follow `references/purchase_order.md` pattern. Must contain exactly:

### Document Quirks

Behavioral quirks outside Pydantic descriptions. Examples: service vs physical lines, optional identifier columns, terms attachment defaults.

### Payload Construction

Two sub-sections:

1. **Minimal payload** — required fields only, `"..."` placeholders. Quick-reference shape for Claude.
2. **Field encoding notes** — address line breaks (`\n`), date format (`YYYY-MM-DD`), money as numbers not strings.

---

## Step 3 — Write `templates/<doc_type>.html`

### 3.0 Read Design System first

Read [`references/DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) before writing markup/CSS. Defines full color palette, typography, CSS classes, specificity rules, and `primary_color` theming. Never hardcode any color, size, or font — everything uses `var(--)`.

### 3.1 Extend base.html

Every template starts with `{% extends "base.html" %}`. `base.html` provides `<html>/<head>/<body>`, `style.css` link, optional inline `<style>{{ theme_css }}</style>`, and three override blocks: `{% block header %}`, `{% block content %}`, `{% block footer %}`.

Footer renders automatically: `base.html` outputs `<div class="doc-footer">{{ footer_text }}</div>` when `footer_text` is defined and non-empty. Add `"footer_text": build_footer_text(doc.<issuing_party>)` to context builder — `build_footer_text` is in `builders._shared`. No `{% block footer %}` override needed. Override only to suppress (`{% block footer %}{% endblock %}`) or customise.

### 3.2 Doc-type-specific styles

Never add to `style.css`. Place doc-type CSS in `assets/<doc_type>.css`, load at module level in `builders/<doc_type>.py`:

```python
_MY_CSS: str = (ASSETS_DIR / "<doc_type>.css").read_text(encoding="utf-8")
```

Pass as `"theme_css": build_theme_css(_MY_CSS, doc)`. The single `build_theme_css()` helper in `builders._shared` composes the doc-type CSS with `primary_color_css`, `font_family_css`, and `density_css` in the correct order (density goes last so it overrides doc-type variables). Each underlying helper returns `""` when its field is `None` or `"normal"` so concatenation stays safe. `density_css()` reads its presets from `assets/density/<style>.css` — new doc types automatically inherit `compact` / `normal` / `comfortable` support with no extra code. All CSS values use `var(--)` from DESIGN_SYSTEM.md. See `assets/invoice.css` as reference.

**Specificity note:** Base rule `.totals__table td:first-child` (0,1,2) sets muted color on first-column cells. Override by qualifying with `.totals__table` (0,2,1). See Specificity Rules in DESIGN_SYSTEM.md.

**Page breaks:** `style.css` provides these global rules for free — never repeat in doc-type CSS:

- `tr { break-inside: avoid }` — rows never split
- `thead { break-after: avoid }` — no orphaned headers
- `.meta-band { break-inside: avoid }` — meta band stays together
- `.bottom-section__totals { break-inside: avoid }` — totals block stays together

For grouped tables with section headings, use reusable `.section-group` / `.section-group__heading` classes from `style.css` — includes `break-after: avoid` on heading. For other stay-together elements, add `break-after: avoid` or `break-inside: avoid` to doc-type CSS. See `.po-terms__section` in `assets/purchase_order.css`.

### 3.3 Template rules

**No logic in templates.** All computation, formatting, conditionals in Python. Permitted Jinja2:

- `{% if variable %}` — show/hide sections via pre-computed booleans
- `{% for item in list %}` — iterate pre-built lists
- `{{ value }}` — output pre-formatted string
- `{{ address | nl2br }}` — render `\n` as `<br>` in addresses

Not permitted: arithmetic, string formatting, custom filters beyond `nl2br`.

### 3.4 Conditional columns

Omit column entirely when no row needs it. Compute gate boolean in context builder (e.g. `"has_buyer_id_column": any(item.buyer_id for item in doc.line_items)`) and guard both `<th>` and each `<td>` with `{% if has_buyer_id_column %}`. See `buyer_id` / `vendor_id` / `barcode` columns in `templates/purchase_order.html`.

---

## Step 4 — Write `builders/<doc_type>.py`

Model on `builders/purchase_order.py`. Context builder conventions:

- **No raw `Decimal`** — all monetary values as strings: `format_currency(doc.amount)`.
- **No raw `date`** — all dates as strings: `format_date(doc.issue_date)` or `None`.
- **Logo** — `resolve_logo(doc.logo)` (root-level field). Pass as `"logo": logo_data` at top level, not nested in party dict.
- **`css_path`** — always required: `get_css_path()` from `builders._shared`.
- **Boolean flags** — compute `show_tax`, `show_shipping`, `has_buyer_id_column`, etc. here so templates have no logic.
- **Shared helpers** — use `build_line_items`, `build_line_items_meta`, `build_totals` from `builders._shared`.
- **`theme_css`** — one call: `"theme_css": build_theme_css(_MY_CSS, doc)`. `build_theme_css` (from `builders._shared`) handles primary colour, font family, and density preset composition for you. The lower-level `primary_color_css` / `font_family_css` / `density_css` helpers stay available if you need bespoke composition.

---

## Step 5 — Register in `builders/__init__.py`

The single edit. Append one `DocTypeConfig` entry to `REGISTRY` plus the matching imports — nothing else in the file changes.

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

Complete valid payload exercising key features:

- All required fields populated
- At least one optional field per category (dates, numeric modifiers, notes)
- Multiple line items, at least one service line (`count_units: false`) if supported
- Logo omitted or `null` for CI portability

Base on example in `references/<doc_type>.md`.

### 6.2 `tests/fixtures/invalid_<doc_type>.json`

Payload triggering multiple validation errors:

- Missing required field (e.g. omit `doc_number`)
- Format/range violation (e.g. `tax_rate: 1.5`)
- Cross-field violation if schema has model validators (e.g. `due_date` before `issue_date`)

Expected: `exit code 1`, structured error to stdout, no PDF.

### 6.3 Additional scenario fixtures (optional)

Second valid fixture for meaningfully different scenarios:

- Contractor vs company (Invoice has `sample_invoice_contractor.json`)
- Fully/partially/unpaid (Invoice)
- With/without optional blocks (annex, payment details)

---

## Acceptance Checklist

- [ ] `schemas/<doc_type>.py` heavily documented with `Field(description=...)` and friendly error strings
- [ ] `references/<doc_type>.md` exists with document quirks and minimal payload shape
- [ ] Valid fixture generates clean, single-page PDF with correct totals
- [ ] Invalid fixture exits code 1 with readable error (no Python traceback)
- [ ] New doc type required zero changes to `base.html`, `style.css`, or `scripts/generate.py`'s core engine
- [ ] No raw `Decimal` or `date` objects in template context
- [ ] No arithmetic or formatting logic in Jinja2 template
