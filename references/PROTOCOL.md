# Claude Data Collection Protocol

When a user asks to generate a business document (Purchase Order, Invoice, RFQ, etc.), Claude MUST follow this exact protocol to collect the necessary data before building the payload.

1. **Identify what's already provided** — the user may have given partial information inline (e.g. "Create a PO for Acme for 5 laptops").
2. **Ask for required fields in one pass** — do not ask field by field. Group all missing required fields into a single, structured conversational request.
3. **Use smart defaults silently** — check the Pydantic schema for `default` or `default_factory` values (e.g., `issue_date` defaults to today). Do not ask the user for these unless they need to be overridden. Suggest logical formats for ID numbers (like `PO-2026-001`) if omitted.
4. **Never ask for computed fields** — any field marked with `@computed_field` in the Pydantic schema (like `subtotal`, `grand_total`, `tax_amount`, etc.) is fully calculated by the Python tool. Never ask the user to provide them.
5. **Handle logo gracefully** — if the user mentions a logo or branding, ask for the file path. Run `scripts/encode_logo.py --image <path> --payload <payload_file>` to encode it and inject it at the root `logo` key before generating. If they don't mention a logo, do not ask. Never use the Read tool to base64-encode images — that loads the entire string into context.
6. **Pass validation errors to the user** — if the tool returns a validation error, do not attempt to guess what it means. The validation errors are written cleanly. Just output the error string to the user and ask them to fix the input.
7. **Confirm before generating** — once all required data is collected, show a brief summary of the document and ask for confirmation before invoking the script.
