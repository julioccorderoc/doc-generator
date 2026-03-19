# New Document Type — Coding Agent Session Prompt

Copy this file, fill in every `[PLACEHOLDER]`, and paste the result as the opening prompt for a coding agent session. The agent will implement the new doc type end-to-end in a single session with no follow-up needed.

---

## Task

Implement the `[doc_type_slug]` document type end-to-end in doc-generator.

**What this document is:** [One sentence — what it is, who creates it, who receives it. E.g. "A delivery receipt issued by a shipper to a recipient confirming goods were delivered."]

**Parties:** [Party A role] (left address block) · [Party B role] (right address block)

**Key fields:**

- Required: [list the non-obvious required fields beyond the standard number/date/parties/line-items]
- Optional: [list the optional fields specific to this doc type]
- Computed: [list any computed fields beyond subtotal/tax_amount/grand_total/total_units]

**Layout notes:** [Describe the document from top to bottom — any sections that differ from a standard PO/Invoice layout. E.g. "Includes a signature block at the bottom", "Has a delivery date band below the header", "No tax or shipping rows".]

---

## Step 0 — Orient before touching anything

Read these files in order before writing a single line of code:

1. `CLAUDE.md` — architecture, CLI contract, folder structure, design decisions
2. `references/EXTENDING.md` — the five-file pattern and all rules
3. `references/DESIGN_SYSTEM.md` — color palette, typography, CSS conventions
4. `schemas/purchase_order.py` — reference implementation for schema conventions
5. `builders/purchase_order.py` and `builders/invoice.py` — reference implementations for builder conventions
6. `tests/test_schemas.py` and `tests/test_builders.py` — reference for test conventions

Then run the existing verification suite to confirm the baseline is green before making any changes:

```bash
uv run pytest
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type invoice --payload tests/fixtures/sample_invoice.json
```

If any of these fail, stop and investigate before proceeding.

---

## Files to create (in this exact order)

### 1. `schemas/[doc_type_slug].py`

The Single Source of Truth for the payload structure. Write this first.
Pydantic v2 model. Follow `schemas/purchase_order.py` exactly for conventions:

- `DocModel` base class
- `Money` type on all monetary fields
- `@computed_field` + `@property` for derived values, `round_money()` on every monetary result
- `Field(default_factory=date.today)` for today's date
- Use `Field(description="...")` extensively to document exactly what Claude should ask the user for and how to format it.
- Use `@field_validator(mode="after")` to raise user-friendly `ValueError` strings that Claude will pass directly to the user.

### 2. `references/[doc_type_slug].md`

A tiny supplementary reference file for Claude. It should define:

- **Document Quirks:** edge cases that don't fit in Pydantic descriptions.
- **Payload Construction:** A minimal JSON payload shape example and any field encoding notes.
Look at `references/purchase_order.md` for the minimal template.

### 3. `assets/[doc_type_slug].css`

Doc-type-specific CSS loaded at module level in the builder. If this doc type needs no custom component styles beyond `style.css`, create an empty file (still required so the pattern is consistent). All values must use `var(--)` custom properties — no hardcoded colors, sizes, or fonts.

### 4. `templates/[doc_type_slug].html`

Jinja2 template extending `base.html`. No logic — only `{% if %}`, `{% for %}`, and `{{ value }}`. Read `references/DESIGN_SYSTEM.md` before writing any markup.

### 5. `builders/[doc_type_slug].py`

Context builder function `build_[doc_type_slug]_context(doc)`. Load CSS with:

```python
_[DOC_TYPE_UPPER]_CSS: str = (ASSETS_DIR / "[doc_type_slug].css").read_text(encoding="utf-8")
```

No raw `Decimal` or `date` objects in the returned dict. Use `build_line_items`, `build_line_items_meta`, `build_totals`, `get_css_path`, `primary_color_css` from `builders._shared`. Include `"footer_text": build_footer_text(doc.<issuing_party>)` — the footer renders automatically from `base.html`'s default block when this key is present and non-empty.

---

## Files to modify (exactly these, nothing else)

### 6. `builders/__init__.py`

Add one `DocTypeConfig` entry to `REGISTRY`. Add one import each for the new model and builder.

### 7. `tests/fixtures/sample_[doc_type_slug].json`

Valid, complete payload. Logo omitted or `null` for portability. Cover the important optional fields. At least one service line (`count_units: false`) if the doc type has physical vs. service line items.

### 8. `tests/fixtures/invalid_[doc_type_slug].json`

Payload that triggers multiple validation errors: a missing required field, an out-of-range value, and a cross-field violation (if the schema has model validators).

### 9. `tests/test_schemas.py`

Add tests for the new doc type following the existing pattern:

- Valid fixture loads without errors
- Computed fields are correct (at minimum: line item `total`, `subtotal`, `grand_total`)
- Invalid fixture raises `ValidationError` with expected field paths

### 10. `tests/test_builders.py`

Add tests for the new builder following the existing pattern:

- No raw `Decimal` or `date` objects in the context (use `_raw_typed_values`)
- Required keys present: `css_path`, `line_items`, `grand_total`, `subtotal`
- `show_tax` is `False` when `tax_rate == 0`; `True` when `tax_rate > 0`
- Any doc-type-specific boolean flags

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

- [ ] `schemas/[doc_type_slug].py` is heavily annotated with `Field(description=...)` and friendly validation errors.
- [ ] `references/[doc_type_slug].md` exists with quirks and payload rules.
- [ ] `assets/[doc_type_slug].css` exists (may be empty)
- [ ] Valid fixture generates a clean PDF with correct totals; opens with `--preview`
- [ ] Invalid fixture exits with code 1 and a readable error (no Python traceback)
- [ ] Zero changes to `base.html`, `style.css`, or `scripts/generate.py`'s core engine
- [ ] `uv run pytest` is all green (existing tests unaffected)
- [ ] No raw `Decimal` or `date` objects in the template context
- [ ] No arithmetic or formatting logic in the Jinja2 template
