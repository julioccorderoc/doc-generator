# Design System — doc-generator

This is the visual source of truth for all document types in doc-generator. It is the equivalent of what `references/purchase_order.md` is for a document type: the spec everything else is derived from.

Before writing or modifying any template or stylesheet, read this document first.

---

## Overview

The design language is clean, typography-driven, and professional — suited to B2B business documents. It relies entirely on CSS custom properties defined in `assets/style.css`. No hardcoded color, size, or font values appear in rule bodies. Theming is achieved by overriding `:root` variables, either via the `themes/` folder or via a `primary_color` payload field.

---

## Color Palette

Two user-chosen primaries; all others derived or fixed.

### Core Variables

| Variable | Value | Used for |
|---|---|---|
| `--color-primary` | `#1A4021` | Header background, company names in address block, Grand Total / Balance Due text |
| `--color-accent` | `#65C08E` | Accent stripe on top of header, table header row tint, 2pt rule above Balance Due |
| `--color-text` | `#111827` | All body text, meta band values, line item cells |
| `--color-text-muted` | `#6b7280` | Section labels (FROM, BILL TO, VENDOR, BUYER), totals row labels, contact info, SKU / unit columns |
| `--color-text-inverse` | `#ffffff` | White text on dark header background |
| `--color-border` | `#d1d5db` | Totals divider lines, table bottom borders |
| `--color-border-light` | `#e5e7eb` | Meta band borders, row separators in line items table, bottom-section top border |
| `--color-bg-page` | `#ffffff` | Document body background |
| `--color-bg-header` | `#1A4021` | Document header bar (matches `--color-primary` by default; overridden independently when `primary_color` is set) |
| `--color-bg-table-head` | `#f0faf4` | Line items table header row — light tint of accent |
| `--color-bg-table-alt` | `#f8fdfb` | Alternating even rows in line items table — very subtle |

> **Removed:** `--color-total-row` no longer exists. The previous dark-filled total row has been replaced with a typography-driven hierarchy (see Totals Block Design below).

### Semantic Colors (doc-type-specific, not in style.css)

These values live in `assets/invoice.css`. They are fixed and not overridable via `primary_color`.

| Usage | Value |
|---|---|
| Amount Paid text | `#16a34a` (green) |
| Status strip — Paid background | `#f0fdf4` |
| Status strip — Paid text | `#15803d` |
| Status strip — Paid border | `#16a34a` |
| Status strip — Partial background | `#fffbeb` |
| Status strip — Partial text | `#b45309` |
| Status strip — Partial border | `#f59e0b` |

---

## Typography Hierarchy

All type is set in `"Helvetica Neue", Helvetica, Arial, sans-serif`. No external font imports. The following table maps visual roles to their CSS values.

| Element | Size | Weight | Color | Notes |
|---|---|---|---|---|
| Document type label (INVOICE, PURCHASE ORDER) | `--font-size-xl` (22pt) | Bold | `--color-text-inverse` | Uppercase, tracking 0.04em |
| Document number | `--font-size-lg` (14pt) | Medium (500) | `--color-text-inverse` | Reduced opacity 0.85 |
| Issue date | `--font-size-sm` (8.5pt) | Normal | `--color-text-inverse` | Reduced opacity 0.70 |
| Company name (address block) | `--font-size-base` (10pt) | Bold | `--color-primary` | `.address-block__name` |
| Section labels (FROM, BILL TO, VENDOR, BUYER) | `--font-size-xs` (7.5pt) | Bold | `--color-text-muted` | Uppercase, tracking 0.08em |
| Address detail | `--font-size-sm` (8.5pt) | Normal | `--color-text` | Line height 1.5 |
| Contact line | `--font-size-sm` (8.5pt) | Normal | `--color-text-muted` | Below address |
| Meta band label | `--font-size-xs` (7.5pt) | Bold | `--color-text-muted` | Uppercase, tracking 0.07em |
| Meta band value | `--font-size-sm` (8.5pt) | Medium (500) | `--color-text` | |
| Table headers | `--font-size-xs` (7.5pt) | Bold | `--color-text` | Uppercase, tracking 0.06em |
| Line item body | `--font-size-sm` (8.5pt) | Normal | `--color-text` | |
| Line item total column | `--font-size-sm` (8.5pt) | Medium (500) | `--color-text` | |
| Totals labels (Subtotal, Tax, Shipping) | `--font-size-sm` (8.5pt) | Normal | `--color-text-muted` | Right-aligned label column |
| Totals values | `--font-size-sm` (8.5pt) | Medium (500) | `--color-text` | Right-aligned value column |
| Grand Total label + value | `--font-size-grand` (11pt) | Bold | `--color-primary` | No background fill |
| Amount Paid (invoice only) | `--font-size-sm` (8.5pt) | Normal | `#16a34a` | Green text, both columns |
| Balance Due (invoice only) | `--font-size-balance` (13pt) | Bold | `--color-primary` | Largest financial figure; 2pt accent rule above |

---

## Header Design

The document header is a full-width dark bar.

- **Background:** `var(--color-bg-header)` — dark forest green
- **Accent stripe:** `3pt solid var(--color-accent)` on the top edge — a visible medium-green stripe
- **Logo:** left-aligned, max 48pt tall, max 140pt wide, `object-fit: contain`
- **Title block:** right-aligned; stacked document type → document number → issue date
- **Border radius:** `2pt` on the container

---

## Totals Block Design

**No dark-background filled rows.** The hierarchy is entirely typographic.

### Row anatomy (top to bottom)

```text
Total Units            [n]          ← 10pt bold primary; bottom border separates from financials
──────────────────────────────────  ← (units border)
Subtotal             $xxx.xx        ← 8.5pt, muted label / medium value
Tax (x%)             $xxx.xx        ← only if tax_rate > 0
Shipping             $xxx.xx        ← only if shipping_cost > 0
──────────────────────────────────  ← 1pt hairline (--color-border) via .totals__divider
Grand Total          $x,xxx.xx      ← 11pt bold --color-primary, both columns
                                    (invoice only below this line)
Amount Paid         ($xxx.xx)       ← 8.5pt, #16a34a green, both columns
══════════════════════════════════  ← 2pt solid --color-accent above Balance Due
Balance Due          $x,xxx.xx      ← 13pt bold --color-primary — biggest number on page
```

### CSS responsibility split

- **`style.css`** owns: `.totals__units`, `.totals__divider`, `.totals__grand`
- **`assets/invoice.css`** owns: `.totals__amount-paid`, `.totals__balance`

### Specificity rules

The general rule `.totals__table td:first-child` (specificity 0,1,2) sets `color: var(--color-text-muted)` on all first-column cells. To override for specific rows, always qualify with the table parent:

```css
/* Wrong — specificity 0,1,1; loses to td:first-child (0,1,2) */
.totals__balance td { color: var(--color-primary); }

/* Correct — specificity 0,2,1; wins */
.totals__table .totals__balance td { color: var(--color-primary); }

/* Also needed to override first-child muted color */
.totals__table .totals__balance td:first-child { color: var(--color-primary); }
```

---

## Spacing Scale

| Variable | Value | Typical use |
|---|---|---|
| `--spacing-xs` | 4pt | Tight margins, small gaps within rows |
| `--spacing-sm` | 8pt | Meta band padding, table cell padding |
| `--spacing-md` | 14pt | Address block margin-bottom, section padding |
| `--spacing-lg` | 22pt | Between major sections (header, address block, line items) |
| `--spacing-xl` | 32pt | Bottom section gap, address party column gap |

---

## Footer Design

The document footer is a subtle, full-width bar pinned to the bottom of every page via `position: fixed; bottom: 0`.

- **Background:** `var(--color-bg-page)` (white) — no fill block, just a light separator line
- **Border:** `1pt solid var(--color-border-light)` on the top edge
- **Text:** `var(--color-text-muted)` at `var(--font-size-xs)`, centred
- **Content:** `footer_text` — a single `·`-separated line derived from the issuing party's data: `name · address (single line) · phone · email`. Phone and email are included only when present.
- **Body padding:** `padding-bottom: 28pt` on `body` reserves space so document content never flows behind the footer.

The footer renders automatically — `base.html`'s default `{% block footer %}` outputs the bar whenever `footer_text` is defined and non-empty in the context. It requires no user-provided fields — `build_footer_text(party)` in `builders._shared` derives everything from the party object already in the context. Override `{% block footer %}` only to suppress or customise the footer.

---

## `primary_color` Theming Field

Any document type can accept an optional `primary_color: string` field in the payload.

**What it overrides:**

- `--color-primary` — affects: company names in address block, Grand Total / Balance Due text
- `--color-bg-header` — header bar background

**What it does not override:**

- `--color-accent` — stays `#65C08E`
- Status strip colors, Amount Paid green, and any other semantic fixed colors

**How it works in the context builder:**

```python
color_override = ""
if doc.primary_color:
    color_override = (
        f":root {{ --color-primary: {doc.primary_color}; "
        f"--color-bg-header: {doc.primary_color}; }}\n"
    )
# For PO (no other theme CSS):
"theme_css": Markup(color_override) if color_override else None

# For Invoice (combined with invoice-specific CSS from assets/invoice.css):
"theme_css": Markup(color_override + _INVOICE_CSS)
```

The `:root` block is injected after `style.css` loads, so it takes precedence.

**Payload usage:**

```json
{
  "primary_color": "#7c3aed",
  ...
}
```

Format: any valid CSS color string (hex recommended). No format validation is performed — the value is inserted verbatim into a CSS `:root` block.

---

## Doc-Type-Specific Styles

New CSS rules for a doc type must **never** be added to `style.css`. Place them in `assets/<doc_type>.css` and load the file at module level in `builders/<doc_type>.py`:

```python
_MY_CSS: str = (ASSETS_DIR / "<doc_type>.css").read_text(encoding="utf-8")
```

Then pass it as `"theme_css": Markup(...)` in the context builder. All values must reference CSS custom properties — no hardcoded colors, sizes, or fonts.

See `assets/invoice.css` + `builders/invoice.py` as the reference implementation.

---

## File Ownership

| File | Owns |
|---|---|
| `assets/style.css` | All base layout, palette variables, shared component styles |
| `assets/<doc_type>.css` (e.g. `invoice.css`) | Doc-type-specific component styles — loaded at module level in `builders/<doc_type>.py` |
| `assets/themes/` | Named theme override files (future) |
| Payload `primary_color` field | Per-document brand color override injected at render time |
