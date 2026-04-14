# Design System — doc-generator

Visual source of truth for all document types. Equivalent of `references/purchase_order.md` for a doc type: spec everything else derives from.

Read before writing or modifying any template or stylesheet.

---

## Overview

Clean, typography-driven, professional design for B2B documents. Built entirely on CSS custom properties in `assets/style.css`. No hardcoded color, size, or font values in rule bodies. Theming via `:root` variable overrides — `themes/` folder or `primary_color` payload field.

---

## Color Palette

Two user-chosen primaries; all others derived or fixed.

### Core Variables

| Variable | Value | Used for |
|---|---|---|
| `--color-primary` | `#1A4021` | Header background, company names in address block, Grand Total / Balance Due text |
| `--color-accent` | `#65C08E` | Accent stripe on header, table header row tint, 2pt rule above Balance Due |
| `--color-text` | `#111827` | All body text, meta band values, line item cells |
| `--color-text-muted` | `#6b7280` | Section labels (FROM, BILL TO, VENDOR, BUYER), totals row labels, contact info, SKU / unit columns |
| `--color-text-inverse` | `#ffffff` | White text on dark header |
| `--color-border` | `#d1d5db` | Totals divider lines, table bottom borders |
| `--color-border-light` | `#e5e7eb` | Meta band borders, row separators, bottom-section top border |
| `--color-bg-page` | `#ffffff` | Document body background |
| `--color-bg-header` | `#1A4021` | Header bar (matches `--color-primary` by default; overridden independently when `primary_color` set) |
| `--color-bg-table-head` | `#f0faf4` | Line items header row — light tint of accent |
| `--color-bg-table-alt` | `#f8fdfb` | Alternating even rows — very subtle |

> **Removed:** `--color-total-row` no longer exists. Dark-filled total row replaced with typography-driven hierarchy (see Totals Block Design).

### Semantic Colors (doc-type-specific, not in style.css)

In `assets/invoice.css`. Fixed, not overridable via `primary_color`.

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

All type set in `"Helvetica Neue", Helvetica, Arial, sans-serif`. No external font imports.

| Element | Size | Weight | Color | Notes |
|---|---|---|---|---|
| Document type label (INVOICE, PURCHASE ORDER) | `--font-size-xl` (22pt) | Bold | `--color-text-inverse` | Uppercase, tracking 0.04em |
| Document number | `--font-size-lg` (14pt) | Medium (500) | `--color-text-inverse` | Opacity 0.85 |
| Issue date | `--font-size-sm` (8.5pt) | Normal | `--color-text-inverse` | Opacity 0.70 |
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

Full-width dark bar.

- **Background:** `var(--color-bg-header)` — dark forest green
- **Accent stripe:** `3pt solid var(--color-accent)` on top edge — medium-green stripe
- **Logo:** left-aligned, max 48pt tall, max 140pt wide, `object-fit: contain`
- **Title block:** right-aligned; stacked document type → number → issue date
- **Border radius:** `2pt`

---

## Totals Block Design

**No dark-background filled rows.** Hierarchy is entirely typographic.

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

General rule `.totals__table td:first-child` (0,1,2) sets `color: var(--color-text-muted)` on first-column cells. To override for specific rows, qualify with table parent:

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

Subtle full-width bar pinned to bottom of every page via `position: fixed; bottom: 0`.

- **Background:** `var(--color-bg-page)` (white) — no fill, light separator line
- **Border:** `1pt solid var(--color-border-light)` on top edge
- **Text:** `var(--color-text-muted)` at `var(--font-size-xs)`, centred
- **Content:** `footer_text` — single `·`-separated line from issuing party data: `name · address (single line) · phone · email`. Phone/email included only when present.
- **Body padding:** `padding-bottom: 28pt` on `body` reserves space so content never flows behind footer.

Footer renders automatically — `base.html`'s default `{% block footer %}` outputs bar when `footer_text` is defined and non-empty. Needs no user-provided fields — `build_footer_text(party)` in `builders._shared` derives everything from party object. Override `{% block footer %}` only to suppress or customise.

---

## Per-Document Style Override Fields

Three optional payload fields shared by all doc types. Never ask proactively — set only when user explicitly requests.

| Field | Type | Default | Description |
|---|---|---|---|
| `primary_color` | `string` | `null` | Hex or CSS color name. Overrides header background and primary text accents. |
| `font_family` | `string` | `null` | CSS font stack (e.g. `"Georgia, serif"`). Only set when explicitly requested. |
| `doc_style` | `"compact"`, `"normal"`, `"comfortable"` | `"normal"` | Page density preset. `"compact"` tightens spacing; `"comfortable"` adds whitespace. |

### How they work in context builder

Each field has corresponding helper in `builders/_shared.py` returning CSS `:root` block or empty string when absent/default:

```python
"theme_css": Markup(
    _MY_CSS
    + primary_color_css(doc.primary_color)   # overrides --color-primary, --color-bg-header
    + font_family_css(doc.font_family)        # overrides --font-family
    + density_css(doc.doc_style)              # overrides all spacing/font-size variables
)
```

All three return `""` when `None` or `"normal"` — concatenation always safe. **Density goes last** — must override doc-type CSS variables (e.g. `purchase_order.css` defines PO-specific density variables that `density_css()` overrides).

`:root` block injected after `style.css` via `<style>` tag in `base.html`, taking precedence over base stylesheet.

### `primary_color`

- Overrides: `--color-primary` (company names, total text) and `--color-bg-header` (header bar)
- Does **not** override: `--color-accent`, status strip colors, semantic fixed colors
- Format: hex (`#RRGGBB`, `#RGB`) or single-word CSS color name — validated by schema

### `doc_style`

- `"compact"`: ~15% smaller fonts, ~20% tighter spacing. More content per page.
- `"normal"` (default): current `style.css` values. No CSS injected.
- `"comfortable"`: ~15% larger fonts, ~20% more whitespace. More readable, more formal.
- PO auto-density classes (`.line-items--compact`, `.line-items--dense`) use CSS variables (`--table-cell-padding-compact`, `--table-cell-padding-dense`, `--font-size-dense`) also overridden by `density_css()`, so auto-density scales consistently with `doc_style`.

### Payload usage

```json
{
  "primary_color": "#7c3aed",
  "font_family": "Georgia, serif",
  "doc_style": "comfortable"
}
```

All three combine freely — override different CSS variables, no conflicts.

---

## Doc-Type-Specific Styles

New CSS rules for doc type must **never** go in `style.css`. Place in `assets/<doc_type>.css`, load at module level in `builders/<doc_type>.py`:

```python
_MY_CSS: str = (ASSETS_DIR / "<doc_type>.css").read_text(encoding="utf-8")
```

Pass as first element in `theme_css`. All values reference CSS custom properties — no hardcoded colors/sizes/fonts.

If doc type has auto-density classes (like PO compact/dense table), define padding/font-size as CSS variables in `assets/<doc_type>.css` `:root` block so `density_css()` can override them.

See `assets/invoice.css` + `builders/invoice.py` and `assets/purchase_order.css` + `builders/purchase_order.py` as references.

---

## File Ownership

| File | Owns |
|---|---|
| `assets/style.css` | All base layout, palette variables, shared component styles |
| `assets/<doc_type>.css` (e.g. `invoice.css`) | Doc-type-specific component styles — loaded at module level in `builders/<doc_type>.py` |
| `assets/themes/` | Named theme override files (future) |
| `builders/_shared.py` helpers | `primary_color_css()`, `font_family_css()`, `density_css()` — per-document `:root` overrides |
| Payload `primary_color` / `font_family` / `doc_style` fields | Per-document visual overrides injected at render time |
