# 002 — All Formatting Happens in Python; Templates Receive Strings

**Status:** Accepted
**Date:** 2026-03-16

## Context

Jinja2 templates can format inline via filters (`{{ value | round(2) }}`, `{{ date | strftime('%B %d') }}`). Tempting to pass raw `Decimal` and `date` values to templates.

Problem: distributes formatting logic across templates. Second doc type must independently implement same formatting rules. If USD formatting changes (e.g. `$1,234.56` to `USD 1,234.56`), every template needs updating. Templates have no type safety, no unit tests, no debugger.

## Decision

Jinja2 context contains only display-ready strings for all monetary and date values. Raw `Decimal` and `date` objects never passed to templates.

Formatting centralised in `utils/formatting.py`:

- `format_currency(value)` -> `"$1,234.56"` (USD/American standard)
- `format_date(value)` -> `"March 16, 2026"` (American long format)
- `format_quantity(value)` -> `"50"` or `"2.5"` (trailing zeros removed)

Context builder calls these for every monetary and date field before constructing template context dict. Templates only render pre-formatted values — never contain arithmetic, rounding, or date logic.

## Consequences

- Formatting defined once, tested once, changed once.
- Templates are pure display logic. Reviewable visually without understanding Python types.
- New doc type context builder calls shared formatting utilities — cannot accidentally format differently.
- Template authors must not pass `Decimal` or `date` values to templates. Raw numeric/date value in template context is a bug.
- Tradeoff: slightly more verbose context builder. Acceptable — context builders are the defined seam between schema and template.
