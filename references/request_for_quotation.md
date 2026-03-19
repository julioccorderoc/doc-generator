# Request for Quotation (RFQ) — Reference

## §1.1 Field Reference

### Document-level fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `rfq_number` | string | ✅ | — | Unique RFQ identifier (e.g. "RFQ-2026-001") |
| `issue_date` | string (YYYY-MM-DD) | ❌ | today | Date the RFQ is issued |
| `valid_until` | string (YYYY-MM-DD) | ❌ | — | Deadline for vendor to submit a quote; must be after `issue_date`. Only include when the user explicitly requests a submission deadline — do not ask for it by default. |
| `issuer` | object | ✅ | — | Party issuing the RFQ — see Issuer table below |
| `vendor` | object | ❌ | — | Recipient vendor — see Vendor table below; omit for broadcast RFQs |
| `product_name` | string | ✅ | — | Name of the product or service being quoted |
| `product_description` | string | ❌ | — | Short description or subtitle for the product, appears below the name in the summary table. Optional — product name alone is sufficient. Only include when the user provides a description or explicitly asks for one. |
| `product_attributes` | array | ❌ | `[]` | Dynamic columns for the product summary table — see below |
| `spec_sections` | array | ✅ | — | One or more specification sections — see below; at least one required |
| `notes` | string | ❌ | — | Free-form notes printed below the spec table |
| `annexes` | array | ❌ | — | Named references/attachments — see below |
| `contact` | object | ❌ | — | Contact person for questions — see Contact table below |
| `logo` | string | ❌ | — | Base64 data URI (`data:image/png;base64,...`) for the issuer logo. Claude reads and encodes the file — never pass a file path or URL. |
| `primary_color` | string | ❌ | — | Color to override the document header. Must be a hex color in `#RRGGBB` or `#RGB` format, or a single-word CSS color name (e.g. `"#1A4021"`, `"#fff"`, `"green"`). |

### Issuer (object)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Issuer company or individual name |
| `address` | string | ❌ | Mailing address; use `\n` for line breaks |
| `phone` | string | ❌ | Phone number |
| `email` | string | ❌ | Email address |
| `website` | string | ❌ | Website URL |

### Vendor (object, optional)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Vendor company or individual name |
| `address` | string | ❌ | Mailing address; use `\n` for line breaks |
| `phone` | string | ❌ | Phone number |
| `email` | string | ❌ | Email address |
| `website` | string | ❌ | Website URL |

### Product attributes array (entries in `product_attributes`)

Each entry adds one column to the product summary table.

| Field | Type | Required | Description |
|---|---|---|---|
| `header` | string | ✅ | Column header (e.g. "Capsules per bottle") |
| `value` | string | ✅ | Cell value for this product (e.g. "120") |

### Spec sections array (entries in `spec_sections`)

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ❌ | Section heading rendered as a full-width row. Omit or `null` for no heading |
| `rows` | array | ✅ | One or more `{label, value}` pairs — see below |

### Spec row (entries in `spec_sections[*].rows`)

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | ✅ | Row label in left column (e.g. "Formula (per serving)") |
| `value` | string | ✅ | Row value in right column; supports `\n` for multiline content |

### Annexes array (entries in `annexes`)

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | ✅ | Name of the attachment or reference (e.g. "Two pack polybag specs") |
| `url` | string | ❌ | URL rendered as plain text in the PDF |

### Contact (object, optional)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ❌ | Contact person's name |
| `email` | string | ❌ | Contact email |
| `phone` | string | ❌ | Contact phone |
| `website` | string | ❌ | Website URL |

---

## §1.2 Validation Rules

- `rfq_number` must be a non-empty string (after stripping whitespace)
- `product_name` must be a non-empty string
- `spec_sections` must contain at least one entry
- `valid_until`, if provided, must be strictly after `date`
- `issuer.name` must be a non-empty string
- `vendor.name`, if vendor is provided, must be non-empty

---

## §1.3 Claude Data Collection Protocol

1. **Identify what the user has already provided.** The user may have supplied a product name, some specs, or a partial JSON blob.

2. **Ask for all missing required fields in a single pass:**
   - `rfq_number` — the RFQ identifier
   - `issuer.name` — issuer company name
   - `product_name` — name of the product being quoted
   - `spec_sections` — at least one section with at least one row; this is the main body of the RFQ

3. **Apply these defaults silently (never ask):**
   - `issue_date` → today
   - `product_attributes` → `[]` if not provided
   - `issuer.address`, `issuer.phone`, `issuer.email` → omit if not provided

4. **Never ask for computed fields** — there are none for this doc type.

5. **`valid_until`:** Do **not** ask for this by default. Only include it when the user explicitly mentions a submission deadline or quote expiry date. It exists as an option but is not standard for all RFQs.

6. **`product_description`:** Do **not** ask for this. Only include it if the user volunteers a subtitle or short description for the product. The product name alone is sufficient.

7. **Logo:** Ask only if the user explicitly mentions a logo or branding.

8. **Spec sections guidance:** Encourage the user to group specifications under section headings (e.g. "Formula", "Packaging", "Quality"). If the user provides a flat list of specs, group them under a single unnamed section.

9. **Annexes:** Ask if the user has any reference documents, links, or attachments to include.

10. **Contact block:** Ask if there is a specific contact person for vendor questions (name, email, phone). This is separate from the issuer.

11. **Vendor:** Ask if the RFQ is addressed to a specific vendor, or if it's a broadcast (no vendor block).

12. **Confirm before generating:** Show a summary of the document structure (product, number of spec sections, number of spec rows) and ask the user to confirm before writing the payload.

---

## §1.4 Example Payload

### Broadcast RFQ (no specific vendor, no submission deadline)

This is the typical case — sent to multiple vendors or shared openly. Use `tests/fixtures/sample_rfq_broadcast.json` as the working example.

```json
{
  "rfq_number": "RFQ-2026-002",
  "issuer": {
    "name": "Natural Cure Labs",
    "address": "P.O. Box 13945\nSt. Petersburg, FL 33733",
    "phone": "+1 (800) 303-6214",
    "email": "info@naturalcurelabs.com"
  },
  "product_name": "Level Off",
  "product_attributes": [
    { "header": "Capsules per bottle", "value": "120" },
    { "header": "Serving size", "value": "2 capsules" },
    { "header": "Volume (bottles)", "value": "4,000" }
  ],
  "spec_sections": [
    {
      "rows": [
        {
          "label": "Formula (per serving)",
          "value": "> 250mg Mulberry Leaf Extract 5% 1-Deoxynojirimycin\n> 250mg Lemon Peel Extract 50% Bioflavonoids\n> 85mg Ceylon Cinnamon 12:1 Extract Bark (Cinnamomum Verum)"
        },
        { "label": "Excipient", "value": "Ascorbyl palmitate" },
        { "label": "Capsule type", "value": "0 veggie" }
      ]
    },
    {
      "title": "Packaging",
      "rows": [
        { "label": "Bottle", "value": "250cc white PET bottle" },
        { "label": "Cap", "value": "45mm White Ribbed HS, with special liner (includes foil)" }
      ]
    }
  ],
  "notes": "Please include lead time, minimum order quantity, and payment terms in your quote.",
  "contact": {
    "name": "Julio Cordero",
    "email": "julio@naturalcurelabs.com",
    "phone": "+1 (727) 390-3461"
  }
}
```

### Addressed RFQ (specific vendor + submission deadline)

Use this form when the RFQ is directed at one vendor and a quote-by date is required. See `tests/fixtures/sample_rfq.json` for the full working example.

```json
{
  "rfq_number": "RFQ-2026-001",
  "issue_date": "2026-01-15",
  "valid_until": "2026-02-15",
  "issuer": { "name": "Natural Cure Labs", "..." : "..." },
  "vendor": {
    "name": "Precision Nutraceuticals Inc.",
    "address": "1200 Industrial Blvd\nTampa, FL 33601"
  },
  "product_name": "Level Off",
  "spec_sections": [ { "rows": [ { "label": "...", "value": "..." } ] } ],
  "annexes": [
    { "title": "Two pack polybag specs", "url": "https://example.com/polybag-specs.pdf" }
  ],
  "contact": { "name": "Julio Cordero", "email": "julio@naturalcurelabs.com" }
}
```

---

## §1.5 Payload Construction

### Minimal payload

```json
{
  "rfq_number": "...",
  "issuer": { "name": "..." },
  "product_name": "...",
  "spec_sections": [
    {
      "rows": [
        { "label": "...", "value": "..." }
      ]
    }
  ]
}
```

### Field encoding notes

- **Address line breaks:** use `\n` within the string, e.g. `"123 Main St\nCity, ST 12345"`
- **Dates:** `YYYY-MM-DD` format; `issue_date` defaults to today if omitted
- **Multiline spec values:** use `\n` within the value string for multi-line cells (e.g. ingredient lists)
- **`product_attributes`:** omit or `[]` if no summary table columns are needed
- **`vendor`:** omit entirely for broadcast RFQs
- **`spec_sections[*].title`:** omit or set to `null` for an unnamed section (no section header row rendered)
- **`annexes[*].url`:** omit if no URL; title still renders without a URL column
- **Logo:** `data:image/...;base64,...` data URI; Claude reads and encodes the file before building the payload. Omit for no logo.
- **`primary_color`:** hex color (`#RRGGBB` or `#RGB`) or single-word CSS color name (e.g. `"#1A4021"`, `"green"`); omit to use the default

---
