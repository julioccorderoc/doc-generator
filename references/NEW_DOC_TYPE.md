# New Document Type — Coding Agent Session Prompt

Copy this file, fill in every `[PLACEHOLDER]`, paste as opening prompt. Agent implements new doc type end-to-end in single session.

---

## Task

Implement `[doc_type_slug]` document type end-to-end in doc-generator.

**What this document is:** [One sentence — what it is, who creates it, who receives it.]

**Parties:** [Party A role] (left address block) · [Party B role] (right address block)

**Key fields:**

- Required: [non-obvious required fields beyond standard number/date/parties/line-items]
- Optional: [optional fields specific to this doc type]
- Computed: [computed fields beyond subtotal/tax_amount/grand_total/total_units]

**Layout notes:** [Top-to-bottom description of sections differing from standard PO/Invoice. E.g. "signature block at bottom", "delivery date band below header", "no tax or shipping rows".]

---

## Step 0 — Orient before touching anything

Read these files in order before writing code:

1. `CLAUDE.md` — architecture, CLI contract, folder structure, design decisions
2. `references/EXTENDING.md` — five-file pattern and all rules
3. `references/DESIGN_SYSTEM.md` — color palette, typography, CSS conventions
4. `schemas/purchase_order.py` — reference schema conventions
5. `builders/purchase_order.py` and `builders/invoice.py` — reference builder conventions
6. `tests/test_schemas.py` and `tests/test_builders.py` — reference test conventions

Then run verification suite to confirm green baseline:

```bash
uv run pytest
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type invoice --payload tests/fixtures/sample_invoice.json
```

If any fail, stop and investigate.

---

## Files to create (in this exact order)

### 1. `schemas/[doc_type_slug].py`

Single Source of Truth for payload structure. Write first.
Pydantic v2 model. Follow `schemas/purchase_order.py` conventions:

- `DocModel` base class
- `Money` type on all monetary fields
- `@computed_field` + `@property` for derived values, `round_money()` on every monetary result
- `Field(default_factory=date.today)` for today's date
- `Field(description="...")` extensively — documents what Claude should ask and how to format
- `@field_validator(mode="after")` for user-friendly `ValueError` strings passed directly to user

### 2. `references/[doc_type_slug].md`

Tiny supplementary reference for Claude:

- **Document Quirks:** edge cases outside Pydantic descriptions
- **Payload Construction:** minimal JSON payload shape + field encoding notes

Follow `references/purchase_order.md` pattern.

### 3. `assets/[doc_type_slug].css`

Doc-type-specific CSS loaded at module level in builder. If no custom styles needed beyond `style.css`, create empty file (pattern consistency). All values use `var(--)` custom properties — no hardcoded colors/sizes/fonts.

### 4. `templates/[doc_type_slug].html`

Jinja2 template extending `base.html`. No logic — only `{% if %}`, `{% for %}`, `{{ value }}`. Read `references/DESIGN_SYSTEM.md` before writing markup.

### 5. `builders/[doc_type_slug].py`

Context builder `build_[doc_type_slug]_context(doc)`. Load CSS:

```python
_[DOC_TYPE_UPPER]_CSS: str = (ASSETS_DIR / "[doc_type_slug].css").read_text(encoding="utf-8")
```

No raw `Decimal` or `date` in returned dict. Use `build_line_items`, `build_line_items_meta`, `build_totals`, `get_css_path`, `primary_color_css`, `font_family_css`, `density_css` from `builders._shared`. Include `"footer_text": build_footer_text(doc.<issuing_party>)` — footer renders automatically from `base.html` when present and non-empty.

---

## Files to modify (exactly these, nothing else)

### 6. `builders/__init__.py`

Add one `DocTypeConfig` entry to `REGISTRY`. One import each for new model and builder.

### 7. `tests/fixtures/sample_[doc_type_slug].json`

Valid, complete payload. Logo omitted or `null` for portability. Cover important optional fields. At least one service line (`count_units: false`) if doc type supports it.

### 8. `tests/fixtures/invalid_[doc_type_slug].json`

Triggers multiple validation errors: missing required field, out-of-range value, cross-field violation (if schema has model validators).

### 9. `tests/test_schemas.py`

Add tests following existing pattern:

- Valid fixture loads without errors
- Computed fields correct (minimum: line item `total`, `subtotal`, `grand_total`)
- Invalid fixture raises `ValidationError` with expected field paths

### 10. `tests/test_builders.py`

Add tests following existing pattern:

- No raw `Decimal` or `date` in context (use `_raw_typed_values`)
- Required keys present: `css_path`, `line_items`, `grand_total`, `subtotal`
- `show_tax` is `False` when `tax_rate == 0`; `True` when `tax_rate > 0`
- Doc-type-specific boolean flags

---

## Verification

Run in this exact order after all changes:

```bash
# Unit tests — must be all green, no system deps
uv run pytest

# End-to-end — valid fixture
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type [doc_type_slug] --payload tests/fixtures/sample_[doc_type_slug].json --preview
# → exit 0, PDF opens

# End-to-end — invalid fixture
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type [doc_type_slug] --payload tests/fixtures/invalid_[doc_type_slug].json
# → exit 1, structured validation error, no PDF

# Existing doc types still work
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type invoice --payload tests/fixtures/sample_invoice.json
```

---

## Acceptance checklist

- [ ] `schemas/[doc_type_slug].py` heavily annotated with `Field(description=...)` and friendly validation errors
- [ ] `references/[doc_type_slug].md` exists with quirks and payload rules
- [ ] `assets/[doc_type_slug].css` exists (may be empty)
- [ ] Valid fixture generates clean PDF with correct totals; opens with `--preview`
- [ ] Invalid fixture exits code 1 with readable error (no Python traceback)
- [ ] Zero changes to `base.html`, `style.css`, or `scripts/generate.py`'s core engine
- [ ] `uv run pytest` all green (existing tests unaffected)
- [ ] No raw `Decimal` or `date` in template context
- [ ] No arithmetic or formatting logic in Jinja2 template
