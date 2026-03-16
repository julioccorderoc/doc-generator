# Purchase Order — Field Reference

This is the source of truth for the `purchase_order` document type. The Pydantic schema, the Jinja2 template, and Claude's data collection behavior are all derived from this document.

---

## Document Overview

A Purchase Order (PO) is a commercial document issued by a **buyer** to a **vendor**, authorizing the purchase of specific goods or services at agreed prices and terms. It is legally binding once accepted by the vendor.

---

## Field Reference

### Top-Level Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `po_number` | string | ✅ | — | Unique identifier for this PO. Format is up to the buyer (e.g. `PO-2026-0042`). Claude should suggest a sequential format if not provided. |
| `issue_date` | date | ✅ | today | Date the PO is issued. Defaults to today if not specified. Format: `YYYY-MM-DD`. |
| `delivery_date` | date | ❌ | — | Expected delivery date. Optional but recommended. Format: `YYYY-MM-DD`. |
| `currency` | string | ❌ | `USD` | Currency code. Phase 1 supports USD only. Formatting: `$1,234.56`. |
| `payment_terms` | string | ❌ | — | e.g. `Net 30`, `Due on receipt`, `50% upfront`. Free text. |
| `shipping_method` | string | ❌ | — | e.g. `FedEx Ground`, `FOB Destination`, `Will Call`. Free text. |
| `shipping_cost` | number | ❌ | `0.00` | Flat shipping fee to be added to the total. In USD. |
| `tax_rate` | number | ❌ | `0.00` | Tax rate as a decimal (e.g. `0.08` for 8%). Applied to subtotal. |
| `notes` | string | ❌ | — | General notes, terms, or instructions. Renders at the bottom of the document. |

---

### `buyer` Object — The company issuing the PO

| Field | Type | Required | Description |
|---|---|---|---|
| `buyer.name` | string | ✅ | Legal company name of the buyer. |
| `buyer.address` | string | ✅ | Full mailing address. Can be multiline (use `\n`). |
| `buyer.email` | string | ❌ | Contact email. |
| `buyer.phone` | string | ❌ | Contact phone number. |
| `buyer.logo` | string | ❌ | File path (absolute or relative) or URL to the company logo image. Claude resolves this before passing to the renderer. Renders in the document header if provided. Supported formats: PNG, JPG, SVG. |

---

### `vendor` Object — The supplier receiving the PO

| Field | Type | Required | Description |
|---|---|---|---|
| `vendor.name` | string | ✅ | Legal company name of the vendor. |
| `vendor.address` | string | ✅ | Full mailing address. Can be multiline (use `\n`). |
| `vendor.email` | string | ❌ | Contact email. |
| `vendor.phone` | string | ❌ | Contact phone number. |
| `vendor.contact_name` | string | ❌ | Name of the specific contact at the vendor. |

---

### `line_items` Array — What is being purchased

Each entry in `line_items` is an object with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | string | ✅ | Name or description of the item or service. |
| `quantity` | number | ✅ | Quantity ordered. Can be decimal (e.g. `2.5` for 2.5 hours). |
| `unit_price` | number | ✅ | Price per unit in USD. |
| `unit` | string | ❌ | Unit label displayed next to quantity. e.g. `units`, `hrs`, `kg`, `boxes`. Defaults to `units`. |
| `sku` | string | ❌ | Vendor or buyer SKU/part number. Displayed in the line item row if provided. |

**Minimum:** 1 line item required.

---

## Computed Fields

These are calculated by the script from the input data. **Never ask the user for these — they are always derived.**

| Field | Formula | Example |
|---|---|---|
| `line_items[n].total` | `quantity × unit_price` | `5 × $12.00 = $60.00` |
| `subtotal` | `sum(line_items[n].total)` | `$60.00 + $40.00 = $100.00` |
| `tax_amount` | `subtotal × tax_rate` | `$100.00 × 0.08 = $8.00` |
| `grand_total` | `subtotal + tax_amount + shipping_cost` | `$100.00 + $8.00 + $5.00 = $113.00` |

All monetary values are rounded to 2 decimal places.

---

## Validation Rules

- `po_number` must be a non-empty string.
- `issue_date` and `delivery_date` (if provided) must be valid dates. `delivery_date`, if provided, must be on or after `issue_date`.
- `line_items` must contain at least one item.
- `quantity` and `unit_price` must be positive numbers greater than zero.
- `shipping_cost` and `tax_rate` must be zero or positive. `tax_rate` must be between `0.0` and `1.0`.
- `buyer.name`, `buyer.address`, `vendor.name`, `vendor.address` are all required and must be non-empty strings.
- `buyer.logo`, if provided, must be either a valid absolute file path to an existing file, or a valid URL starting with `http://` or `https://`.

---

## Claude Data Collection Protocol

When a user asks to generate a Purchase Order, Claude should:

1. **Identify what's already provided** — the user may have given some fields inline (e.g. "PO for Acme, 100 units of X at $5").
2. **Ask for required fields in one pass** — do not ask field by field. Group all missing required fields into a single request.
3. **Use smart defaults** — apply `issue_date = today` and `currency = USD` silently without asking. Suggest `po_number` format if missing.
4. **Never ask for computed fields** — do not ask for subtotal, tax_amount, grand_total, or line item totals.
5. **Handle logo gracefully** — if the user mentions a logo, ask for the file path or URL. If they don't mention it, do not ask.
6. **Confirm before generating** — once all required data is collected, show a brief summary and ask for confirmation before invoking the script.

---

## Example Payload

```json
{
  "po_number": "PO-2026-0001",
  "issue_date": "2026-03-16",
  "delivery_date": "2026-04-01",
  "payment_terms": "Net 30",
  "shipping_method": "FedEx Ground",
  "shipping_cost": 15.00,
  "tax_rate": 0.08,
  "notes": "Please include packing slip with each box.",
  "buyer": {
    "name": "Natural Cure Labs",
    "address": "123 Wellness Ave\nLos Angeles, CA 90001",
    "email": "purchasing@naturalcurelabs.com",
    "phone": "+1 (310) 555-0100",
    "logo": "/Users/julio/assets/ncl_logo.png"
  },
  "vendor": {
    "name": "Acme Ingredients Co.",
    "address": "456 Supply St\nChicago, IL 60601",
    "email": "orders@acmeingredients.com",
    "phone": "+1 (312) 555-0199",
    "contact_name": "Sarah Mitchell"
  },
  "line_items": [
    {
      "description": "Organic Ashwagandha Extract (KSM-66)",
      "quantity": 50,
      "unit_price": 24.00,
      "unit": "kg",
      "sku": "ACM-ASH-001"
    },
    {
      "description": "Magnesium Glycinate Powder",
      "quantity": 25,
      "unit_price": 18.50,
      "unit": "kg",
      "sku": "ACM-MAG-007"
    },
    {
      "description": "Capsule Filling Service",
      "quantity": 10,
      "unit_price": 85.00,
      "unit": "hrs"
    }
  ]
}
```

**Expected computed output:**

```text
line_items[0].total  = $1,200.00
line_items[1].total  = $462.50
line_items[2].total  = $850.00
subtotal             = $2,512.50
tax_amount           = $201.00   (8%)
shipping_cost        = $15.00
grand_total          = $2,728.50
```

---

## Document Layout Notes (for template authors)

The PO template should follow this visual structure, top to bottom:

1. **Header row** — buyer logo (if provided) on the left, document title "PURCHASE ORDER" + PO number + issue date on the right
2. **Address block** — two columns: "Bill From" (buyer) on the left, "Bill To" (vendor) on the right
3. **Meta row** — delivery date, payment terms, shipping method in a compact horizontal band
4. **Line items table** — columns: `#` | `SKU` (if any item has one) | `Description` | `Unit` | `Qty` | `Unit Price` | `Total`
5. **Totals block** — right-aligned: Subtotal / Tax (rate%) / Shipping / **Grand Total**
6. **Notes** — full-width text block at the bottom, preceded by a divider, only rendered if `notes` is present
7. **Footer** — page number, subtle "Generated by doc-generator" if desired
