# Purchase Order — Reference

This is a supplementary reference for the `purchase_order` document type.
The **Single Source of Truth** for the payload schema is `schemas/purchase_order.py`.
The global data collection workflow is `references/PROTOCOL.md`.

---

## Document Quirks

- **PO optional identifier columns** (`buyer_id`, `vendor_id`, `barcode`) on line items: Do not include them unless the user provides the values or explicitly asks for them. A column only appears in the document if at least one line item has a value.
- **Service lines (`count_units`)**: If a line item is clearly a service (consulting, setup, labour), ask if it should be excluded from the unit total. Default is `true` (counted); set to `false` to exclude.
- **Annex Terms (`annex_terms`)**: By default, no T&C page is attached (`null`). Ask the user if they want to attach the standard Terms & Conditions page (`true`) or standard custom text (`string`).

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
