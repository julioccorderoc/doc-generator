# Purchase Order — Reference

This is a supplementary reference for the `purchase_order` document type.
The **Single Source of Truth** for the payload schema is `schemas/purchase_order.py`.
The global data collection workflow is `references/PROTOCOL.md`.

---

## Document Quirks

- **PO optional identifier columns** (`buyer_id`, `vendor_id`, `barcode`) on line items: Do not include them unless the user provides the values or explicitly asks for them. A column only appears in the document if at least one line item has a value.
- **Service lines (`count_units`)**: If a line item is clearly a service (consulting, setup, labour), ask if it should be excluded from the unit total. Default is `true` (counted); set to `false` to exclude.
- **Optional `unit_price`**: Omit `unit_price` from a line item when the price is not yet confirmed (blanket POs). The document renders "TBD" in the Unit Price and Total columns for those rows. Three pricing states exist:
  - **All priced** — normal rendering.
  - **Partially priced** — totals shown as "Est. Subtotal *" / "Est. Grand Total *" (priced items only); an auto-generated disclaimer note is appended.
  - **Fully unpriced** — Unit Price and Total columns hidden; financials block hidden; Total Units still shown.
- **`product` field**: Optional. For single-product POs, set this to the product name and it will appear as the first item in the meta-band (the row with Delivery Date, Payment Terms, etc.). Do not ask for it unless the PO is clearly for a single product type.
- **Annex Terms (`annex_terms`)**: By default, no T&C page is attached (`null`). Ask the user if they want to attach the standard Terms & Conditions page (`true`) or custom T&C text (`string`).
- **Tabular annexes (`annex_tables`)**: A list of structured table annexes. By default each annex flows after the preceding content (no forced page break). Set `new_page: true` on an individual annex to force it onto a fresh page. The T&C annex (`annex_terms`) always starts on a new page — that behavior is fixed. See structure below.
- **Logo (`logo`)**: Root-level field on the document (not inside `buyer`). Optional. Must be a base64 data URI (`data:image/png;base64,...`). Use `scripts/encode_logo.py` to encode from a file path — never pass a file path or URL directly. Do not ask for it proactively; only include if the user provides a logo.
- **Font (`font_family`)**: Do **not** ask for this. Only set it when the user explicitly requests a different font (e.g. "use Georgia"). Accepts any valid CSS font stack (e.g. `"Georgia, serif"`). Leave `null` otherwise.
- **Page density (`doc_style`)**: Do **not** ask for this unprompted. Set it only if the user says something like "make it more compact", "fit everything on one page", or "more spacious/formal". Values: `"compact"` (tighter spacing, smaller fonts), `"normal"` (default — no change), `"comfortable"` (more whitespace, larger fonts). Leave `null`/omit for the default.

---

## Payload Construction

### Minimal payload (required fields only)

```json
{
  "po_number": "PO-2026-0042",
  "buyer": {
    "name": "..."
  },
  "vendor": {
    "name": "...",
    "address": "..."
  },
  "line_items": [
    {
      "description": "...",
      "quantity": 1
    }
  ]
}
```

> `unit_price` is now optional. Omit it for blanket POs or lines awaiting price confirmation.

### Field encoding notes

- **Addresses:** Use `\n` for line breaks (e.g. `"123 Main St\nSuite 4\nNew York, NY"`).
- **Dates:** Always `"YYYY-MM-DD"` string format.
- **Money:** Numbers, not strings. `10.00`, not `"$10.00"`.

---

## `annex_tables` Structure

Each entry in `annex_tables` is a `TableAnnex` object:

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | No | Heading for the annex. Defaults to `"Addendum"` if omitted. |
| `headers` | list[string] | **Yes** | Column header labels. Minimum 1. |
| `rows` | list[list[string]] | No | Table rows. Each row must have the same number of cells as `headers`. Defaults to `[]`. |
| `new_page` | boolean | No | Force this annex to start on a new page. Default `false` — the annex flows after the preceding content. Set to `true` when the annex should always open on a fresh page (e.g. a long logistics table). |

### Example — logistics addendum

```json
"annex_tables": [
  {
    "title": "Logistics Addendum — Shipment Distribution",
    "headers": ["Recipient", "Address", "SKU", "Qty", "Notes"],
    "rows": [
      ["Factory A", "123 Industrial Blvd, Monterrey", "ECO-250-CLR", "10,000", "Arrive before June 10"],
      ["Factory B", "456 Park Ave, Guadalajara",      "ECO-250-CLR", "5,000",  "Fragile — double-wrap pallets"]
    ]
  }
]
```

> **Column count note:** Wide tables (8+ columns) may overflow the page width. This is the user's responsibility — no validation is enforced.

Both `annex_terms` and `annex_tables` can coexist on the same PO. Rendering order: T&C (`annex_terms`) first, then each `TableAnnex` in list order.
