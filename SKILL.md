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

## Reference Files

Before collecting data for any doc type, read the corresponding reference file from the project root:

| Doc type | Reference file |
| --- | --- |
| `purchase_order` | `references/purchase_order.md` |
| `invoice` | `references/invoice.md` |

Each reference file is the source of truth for: all fields (required/optional) with when-to-ask guidance, service line handling, payment status rules (invoice), validation rules, and payload construction notes including a minimal shape and field encoding.

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

## Invocation

### 1. Write the payload to a temp file

Construct the complete JSON payload from the collected data. Write it to a temporary file. Do not include any computed fields in the JSON.

Example payload path: `/tmp/doc_payload_<timestamp>.json`

### 2. Run the CLI

```bash
cd ~/doc-generator && DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type <doc_type_slug> \
  --payload <path_to_payload_file>
```

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
