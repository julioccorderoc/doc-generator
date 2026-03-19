# Future Features & Roadmap

This document outlines the planned future capabilities for the `doc-generator` project. These additions will extend the system's utility while adhering to the deterministic, schema-driven, CLI-first design principles.

## 1. Additional Document Types

Adding more documents to complete the business lifecycle:

- **Delivery Notes & Packing Slips:** For tracking physical shipments, including box counts, weights, and dimensional data.
- **Order Confirmations / Quotes:** For formalizing agreements before an invoice or purchase order is generated.

*(Development note: Add these using the exact same 5-file architecture documented in `references/EXTENDING.md`.)*

## 2. Advanced Financials & Discounts

- **Item-Level Discounts:** Allow a `discount` field on line items (either flat USD or a percentage off the `unit_price`).
- **Global Discounts:** Support a document-level total discount applied before tax calculations.

## 3. Multi-Currency Support & Number Formatting

Currently, doc-generator strictly forces `USD` and American formatting (`$1,234.56` and `YYYY-MM-DD`).

- **Currency Expansion:** Support `EUR`, `GBP`, `CAD`, `AUD`, etc., ensuring the symbol matches the currency code.
- **Regional Number Formats:** Support using a comma as a decimal separator (e.g. `1.234,56 €` for European users).

## 4. Complex Tax Handling

- **Compound/Multiple Taxes:** Instead of a single `tax_rate`, support an array of taxes applied sequentially or concurrently (e.g., Canadian GST + PST, or VAT + state taxes).
- **Tax Exempt Items:** Allow marking specific `line_items` as tax-exempt so they are excluded from the `tax_amount` calculation.

## 5. Better PDF Renderer Performance / Asynchrony

- The project will continue replacing blocking CLI preview calls (`subprocess.run`) with asynchronous background calls (`subprocess.Popen`), preventing agent and user blockage after PDF generation.
- Further enhancements might bypass manual viewer launching if integrating strictly as an API service.
