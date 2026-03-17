---
name: doc-generator
description: "Generates professional PDF business documents (like purchase orders and invoices) from user-provided data. Handles data collection, validation, and PDF generation via a schema-driven CLI tool. Use this skill whenever the user mentions creating, generating, or sending any of: purchase order, PO, invoice, bill, or any formal commercial document for goods or services, even if phrased casually ('make a PO for Acme', 'need to invoice a client', 'bill someone for work done', 'write up a purchase order'). This skill manages the full workflow: collecting required fields, applying smart defaults, building the JSON payload, running the CLI, and presenting the PDF path and key figures"
---

# doc-generator

Claude's operating instructions for generating business documents using the doc-generator CLI. Covers trigger conditions, data collection per document type, CLI invocation, and result presentation

## Trigger Conditions

Invoke this skill when the user asks to **create, generate, or produce** any of the supported document types. Trigger on any of:

- "generate a purchase order / PO"
- "create an invoice / bill"
- "make a PO for [vendor]"
- "send an invoice to [client] for [work]"
- "I need a purchase order for [items]"
- Any phrasing that implies creating a formal commercial document for goods or services

### Do NOT trigger when

- The user is asking about a document they have received (they want to parse or read it, not generate it).
- The user wants to edit an existing PDF that was already generated.
- The user is asking a general question about POs or invoices without wanting to create one.

## Supported Document Types

| `doc_type` slug | Human name | Required fields (minimum) |
| --- | --- | --- |
| `purchase_order` | Purchase Order | `po_number`, `buyer.name`, `buyer.address`, `vendor.name`, `vendor.address`, at least 1 line item with `description`, `quantity`, `unit_price` |
| `invoice` | Invoice | `invoice_number`, `issuer.name`, `issuer.address`, `bill_to.name`, `bill_to.address`, at least 1 line item with `description`, `quantity`, `unit_price` |

If the user requests a document type not in this table, inform them it is not yet supported and list what is available.

## Universal Rules

### Computed fields — never ask

The following fields are **always calculated by the tool**. Never ask the user for them. Never include them in the payload.

| Computed field | Available on |
| --- | --- |
| `line_items[n].total` | all doc types |
| `subtotal` | all doc types |
| `tax_amount` | all doc types |
| `grand_total` | all doc types |
| `total_units` | all doc types |
| `balance_due` | invoice only |

### Smart defaults — apply silently

Apply these without asking the user:

| Field | Default | Notes |
| --- | --- | --- |
| `issue_date` | today (`YYYY-MM-DD`) | All doc types |
| `currency` | `USD` | All doc types |
| `tax_rate` | `0.00` | All doc types |
| `shipping_cost` | `0.00` | All doc types |
| `paid` | `false` | Invoice only |
| `amount_paid` | `0.00` | Invoice only |

### Document numbering

If the user has not provided a document number, **suggest one** based on the current date:

- PO: `PO-YYYY-NNNN` (e.g. `PO-2026-0001`)
- Invoice: `INV-YYYY-NNNN` (e.g. `INV-2026-0001`)

Ask the user to confirm the suggested number before generating.

### Ask for required fields in one pass

Identify all missing required fields and ask for them together. Do not ask field by field in separate turns.

### Confirm before generating

Once all required data is collected, show a brief summary (document type, number, parties, number of line items, grand total if calculable) and ask for confirmation before running the CLI.

## Data Collection Protocol — Purchase Order

### Required fields to collect

1. **PO number** — suggest format `PO-YYYY-NNNN` if not provided.
2. **Buyer** — the company issuing the PO.
   - `buyer.name` — legal company name.
   - `buyer.address` — full mailing address (multiline OK, use `\n`).
3. **Vendor** — the supplier receiving the PO.
   - `vendor.name` — legal company name.
   - `vendor.address` — full mailing address.
4. **Line items** — at least one item:
   - `description` — what is being ordered.
   - `quantity` — number ordered (can be decimal; service lines allowed).
   - `unit_price` — price per unit in USD.

### Optional fields — ask when relevant

| Field | When to ask |
| --- | --- |
| `buyer.contact_name`, `buyer.email`, `buyer.phone` | Ask once: "Any contact details for the buyer?" |
| `vendor.contact_name`, `vendor.email`, `vendor.phone` | Ask once: "Any contact details for the vendor?" |
| `delivery_date` | Ask if not mentioned. Strongly recommended. |
| `payment_terms` | Ask if not mentioned (e.g. "Net 30", "Due on receipt"). |
| `shipping_method` | Ask if the order involves physical goods. |
| `shipping_cost` | Ask if shipping is at a flat rate. Default: `0.00`. |
| `tax_rate` | Ask if applicable. Provide as a decimal (e.g. `0.08` for 8%). |
| `notes` | Ask: "Any notes, instructions, or terms to include?" |
| `line_item.unit` | Ask per line item if not implied (e.g. `kg`, `hrs`, `boxes`). Default: `units`. |
| `line_item.sku` | Ask if the buyer or vendor uses SKU/part numbers. |
| `buyer.logo` | Ask only if the user mentions a logo. Ask for file path or URL. |

### Service lines (`count_units`)

If a line item is clearly a service (labour, consulting, preparation, setup fee, etc.), ask:
> "Should this line be excluded from the total unit count? (It's a service, not a physical item.)"

If yes: set `count_units: false`. Default is `true` (counted).

## Data Collection Protocol — Invoice

### Required invoice fields

1. **Invoice number** — suggest format `INV-YYYY-NNNN` if not provided.
2. **Issuer** — the party sending the invoice (the one being paid).
   - `issuer.name` — **ask: "What is your name or business name?"** — do not assume company; this field accepts both a person's name (contractor) and a company name.
   - `issuer.address` — full mailing address.
3. **Bill To** — the client being billed.
   - `bill_to.name` — legal name of the client (company or individual).
   - `bill_to.address` — full mailing address.
4. **Line items** — at least one item:
   - `description` — what is being invoiced.
   - `quantity` — hours worked, items delivered, etc. (can be decimal).
   - `unit_price` — price per unit in USD.

### Optional invoice fields

| Field | When to ask |
| --- | --- |
| `issuer.contact_name`, `issuer.email`, `issuer.phone` | Ask once: "Any contact details to show on the invoice?" |
| `bill_to.contact_name`, `bill_to.email`, `bill_to.phone` | Ask once: "Any contact details for the recipient?" |
| `due_date` | Ask: "When is payment due?" Strongly recommended. Must be on or after `issue_date`. |
| `payment_terms` | Ask if not implied by due_date (e.g. "Net 30"). |
| `tax_rate` | Ask if applicable. Provide as a decimal (e.g. `0.10` for 10%). |
| `shipping_cost` | Ask if the invoice includes a shipping or delivery fee. |
| `notes` | Ask: "Any notes or additional terms to include?" |
| `line_item.unit` | Ask per line item if not implied (e.g. `hrs`, `days`, `units`). |
| `line_item.sku` | Ask if relevant (product codes, service reference numbers). |
| `issuer.logo` | Ask only if the user mentions a logo. Ask for file path or URL. |
| `payment_details` | Ask: "Do you want to include payment instructions (bank details, PayPal, etc.)?" If yes, collect as many `{label, value}` pairs as needed. |

### Payment status

- If the user mentions the invoice has already been paid (fully): set `paid: true`, ask for `amount_paid`.
- If the user mentions partial payment received: set `paid: false`, set `amount_paid` to the amount received.
- If no payment mentioned: apply defaults (`paid: false`, `amount_paid: 0.00`) silently.

### Invoice service lines

Same rule as Purchase Order: if a line item is a service, ask whether to exclude it from total units. Set `count_units: false` if yes.

## Invocation

### 1. Write the payload to a temp file

Construct the complete JSON payload from the collected data. Write it to a temporary file. Do not include any computed fields in the JSON.

Example payload path: `/tmp/doc_payload_<timestamp>.json`

### 2. Run the CLI

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type <doc_type_slug> \
  --payload <path_to_payload_file>
```

Run from the project root: `{{PROJECT_ROOT}}`

**Do not pass `--preview`** when running as a skill (the user will open the file themselves).

### 3. Capture stdout and exit code

- **Exit code 0:** stdout contains the output file path (e.g. `output/purchase_order_20260316_0001.pdf`). Generation succeeded.
- **Exit code 1:** stdout contains an error message. Generation failed.

## Output Presentation

### On success

Tell the user:

1. The document was generated successfully.
2. The output path (make it clickable or easy to copy).
3. A one-line summary of the key figures (e.g. "Grand total: $2,728.50" or "Balance due: $825.00").

Example response:
> Purchase Order **PO-2026-0001** generated successfully.
> Output: `output/purchase_order_20260316_0001.pdf`
> Grand total: $2,728.50 (75 units · Net 30 · FedEx Ground)

### On success with partial payment (invoice)

Highlight both grand total and balance due:
> Invoice **INV-2026-0001** generated.
> Output: `output/invoice_20260316_0001.pdf`
> Grand total: $3,410.00 · Amount paid: $825.00 · **Balance due: $2,585.00**

### On unknown doc_type

> That document type is not currently supported. Supported types: `purchase_order`, `invoice`.

## Validation Error Relay

If the CLI exits with code 1, stdout contains a structured error from Pydantic in this format:

```text
Validation failed:
  field_name: error message
  nested.field: error message
```

**Do not show the raw error output directly.** Translate it into plain language for the user:

| Raw error pattern | User-facing message |
| --- | --- |
| `field → must not be empty` | "The [field label] is required and cannot be blank." |
| `must be greater than zero` | "Quantity and unit price must be greater than zero." |
| `tax_rate → must be between 0.0 and 1.0` | "Tax rate must be a decimal between 0 and 1 (e.g. `0.08` for 8%)." |
| `delivery_date must be on or after issue_date` | "The delivery date cannot be before the issue date." |
| `due_date must be on or after issue_date` | "The due date cannot be before the issue date." |
| `must contain at least one line item` | "At least one line item is required." |

After presenting the error, ask the user to correct the problematic values and offer to regenerate.

## Payload Construction Reference

### `purchase_order` minimal payload shape

```json
{
  "po_number": "PO-2026-0001",
  "issue_date": "2026-03-16",
  "buyer": {
    "name": "...",
    "address": "..."
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

### `invoice` minimal payload shape

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

- **Addresses:** Use `\n` for line breaks within the string (e.g. `"123 Main St\nSuite 4\nNew York, NY"`).
- **Dates:** Always `"YYYY-MM-DD"` string format.
- **Money:** Numbers (not strings). `10.00`, not `"$10.00"`. The tool accepts `int`, `float`, or numeric strings.
- **Computed fields:** Never included. Omit `subtotal`, `tax_amount`, `grand_total`, `balance_due`, and per-line `total` entirely.
- **Logo:** File path (absolute or relative to project root) or `http(s)://` URL. Omit or set to `null` if not provided.
