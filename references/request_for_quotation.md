# Request for Quotation (RFQ) — Reference

This is a supplementary reference for the `request_for_quotation` document type.
The **Single Source of Truth** for the payload schema is `schemas/request_for_quotation.py`.
The universal data collection workflow and field encoding rules are in `SKILL.md`.

---

## Document Quirks

- **No Monetary Values & No Computed Fields**: The RFQ is purely descriptive.
- **`valid_until`**: Do **not** ask for this by default. Only include it when the user explicitly mentions a submission deadline or quote expiry date.
- **`product_description`**: Do **not** ask for this. Only include it if the user volunteers a subtitle or short description.
- **Spec sections guidance**: Encourage the user to group specifications under section headings (e.g. "Formula", "Packaging"). If the user provides a flat list of specs, group them under a single unnamed section.
- **Vendor**: Ask if the RFQ is addressed to a specific vendor, or if it's a broadcast (no vendor block).
- **Font (`font_family`)**: Do **not** ask for this. Only set it when the user explicitly requests a different font (e.g. "use Georgia"). Accepts any valid CSS font stack (e.g. `"Georgia, serif"`). Leave `null` otherwise.
- **Page density (`doc_style`)**: Do **not** ask for this unprompted. Set it only if the user says something like "make it more compact", "fit everything on one page", or "more spacious/formal". Values: `"compact"` (tighter spacing, smaller fonts), `"normal"` (default — no change), `"comfortable"` (more whitespace, larger fonts). Leave `null`/omit for the default.

---

## Payload Construction

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

- **Address line breaks:** use `\n` within the string.
- **Multiline spec values:** use `\n` within the value string for multi-line cells.
- **`product_attributes`:** omit or `[]` if no summary table columns are needed.
- **`vendor`:** omit entirely for broadcast RFQs.
- **`spec_sections[*].title`:** omit or set to `null` for an unnamed section — the builder defaults to "Specifications" so every section has a visible heading in the PDF.

---

## Layout Notes

- Each spec section renders as its own visual block: a **section heading** (`.section-group__heading` from `style.css`) followed by a separate **table** with its own `<thead>`.
- The `.section-group` / `.section-group__heading` classes are defined in the base `style.css` and are reusable across doc types.
- If a section starts on a new page, the column headers ("Specification | Details") repeat — readers always know what columns they're looking at.
