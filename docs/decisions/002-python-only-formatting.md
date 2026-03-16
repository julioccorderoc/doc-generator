# 002 — All Formatting Happens in Python; Templates Receive Strings

**Status:** Accepted
**Date:** 2026-03-16

## Context

Jinja2 templates can perform formatting inline via filters (`{{ value | round(2) }}`, `{{ date | strftime('%B %d') }}`). It is tempting to pass raw `Decimal` and `date` values to the template and format them there, keeping the context dict simple.

The problem is that this distributes formatting logic across templates. When a second document type is added, its template must independently implement the same formatting rules. If the USD formatting rule changes (e.g., from `$1,234.56` to `USD 1,234.56`), every template must be updated. Templates also have no type safety, no unit tests, and no debugger.

## Decision

The Jinja2 context passed to every template contains only display-ready strings for all monetary and date values. Raw `Decimal` and `date` objects are never passed to a template.

Formatting is centralised in `utils/formatting.py`:

- `format_currency(value)` → `"$1,234.56"` (USD/American standard)
- `format_date(value)` → `"March 16, 2026"` (American long format)
- `format_quantity(value)` → `"50"` or `"2.5"` (trailing zeros removed)

The context builder in `scripts/generate.py` calls these functions for every monetary and date field before constructing the template context dict. Templates only render pre-formatted values — they never contain arithmetic, rounding, or date logic.

## Consequences

- Formatting is defined once, tested once, and changed once.
- Templates are pure display logic. They can be reviewed visually without understanding Python types.
- Adding a new document type requires implementing a context builder that calls the shared formatting utilities — it cannot accidentally format a `Decimal` differently.
- Template authors must not pass `Decimal` or `date` values directly to a template. If a raw numeric or date value appears in a template context, it is a bug.
- The tradeoff is a slightly more verbose context builder. This is acceptable — context builders are the defined seam between schema and template.
