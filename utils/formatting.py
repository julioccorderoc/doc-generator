"""
Formatting utilities for display values passed to Jinja2 templates.

All functions return strings. Raw Decimal/date objects are never passed
to templates — see docs/decisions/002-python-only-formatting.md.
"""
from decimal import Decimal
from datetime import date as date_type


def format_currency(value: Decimal | float) -> str:
    """Format a monetary value as USD American standard: $1,234.56"""
    return f"${float(value):,.2f}"


def format_date(value: date_type | str) -> str:
    """Format a date as American long format: March 16, 2026"""
    if isinstance(value, str):
        from datetime import datetime
        value = datetime.strptime(value, "%Y-%m-%d").date()
    # strftime's %d includes a leading zero; use .day to avoid it
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def format_quantity(value: Decimal | float) -> str:
    """Format a quantity, removing unnecessary trailing zeros.

    50   → "50"
    2.5  → "2.5"
    2.50 → "2.5"
    """
    d = Decimal(str(value))
    normalized = d.normalize()
    # If the exponent is negative (has decimal places), keep them; else show as int
    if normalized == normalized.to_integral_value():
        return str(int(normalized))
    return str(normalized)


def format_tax_rate(value: Decimal | float) -> str:
    """Format a tax rate decimal as a percentage string: 0.08 → '8%'"""
    pct = float(value) * 100
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct:g}%"
