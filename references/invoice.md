# Invoice — Field Reference

This is the source of truth for the `invoice` document type. The Pydantic schema, the Jinja2 template, and Claude's data collection behavior are all derived from this document.

---

## Field Reference

### Top-Level Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `invoice_number` | string | ✅ | — | Unique identifier for this invoice. Format is up to the issuer (e.g. `INV-2026-0001`). Claude should suggest a sequential format if not provided. |
| `issue_date` | date | ✅ | today | Date the invoice is issued. Defaults to today if not specified. Format: `YYYY-MM-DD`. |
| `due_date` | date | ❌ | — | Payment due date. Optional but strongly recommended. Format: `YYYY-MM-DD`. Must be on or after `issue_date` if provided. |
| `currency` | string | ❌ | `USD` | Currency code. Phase 2 supports USD only. Formatting: `$1,234.56`. |
| `payment_terms` | string | ❌ | — | e.g. `Net 30`, `Due on receipt`, `50% upfront`. Free text. |
| `tax_rate` | number | ❌ | `0.00` | Tax rate as a decimal (e.g. `0.08` for 8%). Applied to subtotal. Must be between `0.0` and `1.0`. |
| `shipping_cost` | number | ❌ | `0.00` | Flat shipping or delivery fee added to the total. In USD. Must be zero or positive. |
| `notes` | string | ❌ | — | General notes, additional terms, or instructions. Renders at the bottom of the document. |
| `paid` | boolean | ❌ | `false` | Whether the invoice has already been paid. If `true`, `amount_paid` should also be provided. |
| `amount_paid` | number | ❌ | `0.00` | Amount already received. Meaningful only when `paid` is `true`. In USD. Must be zero or positive. |
| `primary_color` | string | ❌ | — | Brand color override. Must be a hex color in `#RRGGBB` or `#RGB` format, or a single-word CSS color name (e.g. `"#7c3aed"`, `"#fff"`, `"purple"`). Overrides the header background and primary accent color. |

---

### `issuer` Object — The company sending the invoice

| Field | Type | Required | Description |
|---|---|---|---|
| `issuer.name` | string | ✅ | Legal company name of the issuer. |
| `issuer.address` | string | ✅ | Full mailing address. Can be multiline (use `\n`). |
| `issuer.contact_name` | string | ❌ | Name of the billing contact at the issuer. Displayed below the address. |
| `issuer.email` | string | ❌ | Contact or billing email. |
| `issuer.phone` | string | ❌ | Contact phone number. |
| `issuer.logo` | string | ❌ | Base64 data URI (`data:image/png;base64,...`). Claude reads the file and encodes it before building the payload — never pass a file path or URL. Renders in the document header if provided. Supported formats: PNG, JPG, SVG. |

---

### `bill_to` Object — The client being billed

| Field | Type | Required | Description |
|---|---|---|---|
| `bill_to.name` | string | ✅ | Legal company or individual name of the client. |
| `bill_to.address` | string | ✅ | Full mailing address. Can be multiline (use `\n`). |
| `bill_to.contact_name` | string | ❌ | Name of the accounts payable contact at the client. Displayed below the address. |
| `bill_to.email` | string | ❌ | Contact email at the client. |
| `bill_to.phone` | string | ❌ | Contact phone number at the client. |

---

### `line_items` Array — What is being invoiced

Each entry in `line_items` is an object with the following fields:

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `description` | string | ✅ | — | Name or description of the item or service. |
| `quantity` | number | ✅ | — | Quantity delivered or hours worked. Must be greater than zero. Can be decimal (e.g. `2.5` for 2.5 hours). |
| `unit_price` | number | ✅ | — | Price per unit in USD. Must be greater than zero. |
| `unit` | string | ❌ | `units` | Unit label displayed next to quantity. e.g. `units`, `hrs`, `kg`, `days`. |
| `buyer_id` | string | ❌ | — | Buyer's internal product code or reference identifier. Displayed as "Buyer ID" column if provided on any item. |
| `count_units` | boolean | ❌ | `true` | Whether to include this item's quantity in `total_units`. Set to `false` for service lines (labour, consulting, setup fees) that should not count toward the physical unit total. |

**Minimum:** 1 line item required.

---

### `payment_details` Array — How to pay (optional)

An optional ordered list of name/value pairs describing how the client should remit payment. Accepts any payment method without hardcoding specific fields. Renders as a labeled block near the bottom of the document.

Each entry:

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | ✅ | Display label for the field, e.g. `Bank`, `Account Name`, `BSB / Routing`, `Account Number`, `Reference`, `PayPal`. |
| `value` | string | ✅ | The corresponding value, e.g. `Commonwealth Bank of Australia`, `Natural Cure Labs LLC`. |

Examples of complete `payment_details` arrays:

```json
[
  { "label": "Bank", "value": "Chase Bank" },
  { "label": "Account Name", "value": "Natural Cure Labs LLC" },
  { "label": "Routing Number", "value": "021000021" },
  { "label": "Account Number", "value": "123456789" },
  { "label": "Reference", "value": "INV-2026-0001" }
]
```

```json
[
  { "label": "PayPal", "value": "billing@naturalcurelabs.com" }
]
```

If omitted or an empty list, the payment details block is not rendered.

---

## Computed Fields

These are calculated by the script from the input data. **Never ask the user for these — they are always derived.**

| Field | Formula | Example |
|---|---|---|
| `line_items[n].total` | `quantity × unit_price` | `5 × $200.00 = $1,000.00` |
| `subtotal` | `sum(line_items[n].total)` | `$1,000.00 + $500.00 = $1,500.00` |
| `tax_amount` | `subtotal × tax_rate` | `$1,500.00 × 0.10 = $150.00` |
| `grand_total` | `subtotal + tax_amount + shipping_cost` | `$1,500.00 + $150.00 + $0.00 = $1,650.00` |
| `balance_due` | `grand_total - amount_paid` | `$1,650.00 - $825.00 = $825.00` |
| `total_units` | `sum(quantity for items where count_units = true)` | `50 + 25 = 75` |

All monetary values are rounded to 2 decimal places.

`total_units` is displayed only when at least one line item has `count_units = true`.

`balance_due` equals `grand_total` when `paid = false` (i.e., `amount_paid` is `0.00`).

---

## Validation Rules

- `invoice_number` must be a non-empty string.
- `issue_date` and `due_date` (if provided) must be valid dates. `due_date`, if provided, must be on or after `issue_date`.
- `line_items` must contain at least one item.
- `quantity` and `unit_price` must be positive numbers greater than zero.
- `shipping_cost` must be zero or positive.
- `tax_rate` must be between `0.0` and `1.0`.
- `amount_paid` must be zero or positive. If `paid = true` and `amount_paid` is not provided, it defaults to `0.00` (valid, but Claude should ask).
- `issuer.name`, `issuer.address`, `bill_to.name`, `bill_to.address` are all required and must be non-empty strings.
- `issuer.logo`, if provided, must be a `data:image/...;base64,...` string. File paths and URLs are rejected — Claude must read and encode the file before building the payload.
- `payment_details` entries must each have a non-empty `label` and `value`.

---

## Claude Data Collection Protocol

When a user asks to generate an Invoice, Claude should:

1. **Identify what's already provided** — the user may have given partial information inline (e.g. "invoice for Acme for last month's consulting").
2. **Ask for required fields in one pass** — do not ask field by field. Group all missing required fields into a single request.
3. **Use smart defaults** — apply `issue_date = today`, `currency = USD`, `paid = false`, `amount_paid = 0.00`, `tax_rate = 0.00`, `shipping_cost = 0.00` silently without asking. Suggest `invoice_number` format if missing.
4. **Never ask for computed fields** — do not ask for `subtotal`, `tax_amount`, `grand_total`, `balance_due`, `total_units`, or per-line `total`.
5. **Handle logo gracefully** — if the user mentions a logo, ask for the file path. Use the Read tool to read the file and encode it as a base64 data URI (`data:image/...;base64,...`) before including it in the payload. If they don't mention a logo, do not ask.
6. **Ask about `count_units` for service lines** — if a line item is clearly a service (consulting, setup, labour), ask if it should be excluded from the unit total. Default is `true` (counted); set to `false` to exclude.
7. **Ask about payment details** — prompt the user to provide bank details or other payment instructions if they want them included. If not mentioned, do not force the issue.
8. **Ask about payment status** — if the user indicates partial or full payment has already been received, collect `paid` and `amount_paid` values.
9. **Confirm before generating** — once all required data is collected, show a brief summary and ask for confirmation before invoking the script.

---

## Example Payload

```json
{
  "invoice_number": "INV-2026-0001",
  "issue_date": "2026-03-16",
  "due_date": "2026-04-15",
  "payment_terms": "Net 30",
  "tax_rate": 0.10,
  "shipping_cost": 0.00,
  "notes": "Thank you for your business. Please include the invoice number in your payment reference.",
  "paid": true,
  "amount_paid": 825.00,
  "issuer": {
    "name": "Natural Cure Labs LLC",
    "address": "123 Wellness Ave\nLos Angeles, CA 90001",
    "contact_name": "Julio Cordero",
    "email": "billing@naturalcurelabs.com",
    "phone": "+1 (310) 555-0100",
    "logo": "data:image/png;base64,..."
  },
  "bill_to": {
    "name": "Acme Retail Group",
    "address": "789 Commerce Blvd\nNew York, NY 10001",
    "contact_name": "Michael Torres",
    "email": "ap@acmeretailgroup.com",
    "phone": "+1 (212) 555-0177"
  },
  "line_items": [
    {
      "description": "Product Formulation Consulting",
      "quantity": 8,
      "unit_price": 200.00,
      "unit": "hrs",
      "count_units": false
    },
    {
      "description": "Regulatory Compliance Review",
      "quantity": 3,
      "unit_price": 250.00,
      "unit": "hrs",
      "count_units": false
    },
    {
      "description": "Label Design & Copy (per SKU)",
      "quantity": 2,
      "unit_price": 375.00,
      "unit": "SKUs",
      "count_units": true
    }
  ],
  "payment_details": [
    { "label": "Bank", "value": "Chase Bank" },
    { "label": "Account Name", "value": "Natural Cure Labs LLC" },
    { "label": "Routing Number", "value": "021000021" },
    { "label": "Account Number", "value": "0987654321" },
    { "label": "Reference", "value": "INV-2026-0001" }
  ]
}
```

---

## Payload Construction

### Minimal payload (required fields only)

```json
{
  "invoice_number": "INV-2026-0001",
  "issue_date": "2026-03-16",
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
- **Computed fields:** Never included in the payload. Omit `subtotal`, `tax_amount`, `grand_total`, `balance_due`, `total_units`, and per-line `total`.
- **Logo:** Must be a base64 data URI (`data:image/...;base64,...`). Claude reads the image file and encodes it before writing the payload — never include a file path or URL. Omit or set to `null` if not provided.
