# Future Features & Roadmap

Planned future capabilities for `doc-generator`. All additions adhere to deterministic, schema-driven, CLI-first design principles.

> **Already shipped:** Request for Quotation (Phase 6), per-document font customization via `font_family` (Phase 9), file prefix naming — PO/INV/RFQ (Phase 9), page density presets via `doc_style` (Phase 10), PO Terms & Conditions annex (Phase 7), tabular annexes `annex_tables` (Phase 8).

## 1. Additional Document Types

More documents to complete business lifecycle:

- **Delivery Notes & Packing Slips:** Track physical shipments — box counts, weights, dimensional data.
- **Order Confirmations / Quotes:** Formalize agreements before invoice or PO is generated.

*(Add using same 5-file architecture in `references/EXTENDING.md`.)*

## 2. Advanced Financials & Discounts

- **Item-Level Discounts:** `discount` field on line items (flat USD or percentage off `unit_price`).
- **Global Discounts:** Document-level total discount applied before tax calculations.

## 3. Multi-Currency Support & Number Formatting

Currently forces `USD` and American formatting (`$1,234.56` and `YYYY-MM-DD`).

- **Currency Expansion:** Support `EUR`, `GBP`, `CAD`, `AUD`, etc., with matching symbols.
- **Regional Number Formats:** Comma as decimal separator (e.g. `1.234,56 €` for European users).

## 4. Complex Tax Handling

- **Compound/Multiple Taxes:** Instead of single `tax_rate`, support array of taxes applied sequentially or concurrently (e.g. Canadian GST + PST, or VAT + state taxes).
- **Tax Exempt Items:** Mark specific `line_items` as tax-exempt, excluded from `tax_amount` calculation.

## 5. Better PDF Renderer Performance / Asynchrony

- Continue replacing blocking CLI preview calls (`subprocess.run`) with async background calls (`subprocess.Popen`), preventing agent/user blockage after PDF generation.
- Further enhancements might bypass manual viewer launching if integrating strictly as API service.
