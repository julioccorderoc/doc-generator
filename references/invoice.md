# Invoice — Reference

This is a supplementary reference for the `invoice` document type.
The **Single Source of Truth** for the payload schema is `schemas/invoice.py`.
The global data collection workflow is `references/PROTOCOL.md`.

---

## Document Quirks

- **Service lines (`count_units`)**: If a line item is clearly a service (consulting, setup, labour), ask if it should be excluded from the unit total. Default is `true` (counted); set to `false` to exclude.
- **SKU (`sku` on line items)**: Do **not** ask for this proactively. Only include it when the user provides seller part numbers, product codes, or SKUs. A SKU column only appears if at least one line item has a value.
- **Payment details**: Extract any provided bank details or payment links to the `payment_details` array. If not mentioned, do not force the issue.
- **Payment status**: If the user indicates partial or full payment has already been received, collect `paid` and `amount_paid` values. Otherwise, leave alone.
- **Font (`font_family`)**: Do **not** ask for this. Only set it when the user explicitly requests a different font (e.g. "use Georgia"). Accepts any valid CSS font stack (e.g. `"Georgia, serif"`). Leave `null` otherwise.

---

## Payload Construction

### Minimal payload (required fields only)

```json
{
  "invoice_number": "INV-2026-0001",
  "issuer": {
    "name": "...",
    "address": "..."
  },
  "bill_to": {
    "name": "...",
    "address": "..."
  },
  "line_items": [
    {
      "description": "...",
      "quantity": 1,
      "unit_price": 10.00
    }
  ]
}
```

### Field encoding notes

- **Addresses:** Use `\n` for line breaks (e.g. `"123 Main St\nSuite 4\nNew York, NY"`).
- **Dates:** Always `"YYYY-MM-DD"` string format.
- **Money:** Numbers, not strings. `10.00`, not `"$10.00"`.
