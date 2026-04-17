"""Project-wide constants — keep this list short.

Extracted from literal values scattered across the codebase. Add a constant
here only when it was duplicated in 2+ places or when it represents a
business/deployment boundary (limits, supported values, defaults).
"""
from __future__ import annotations

# ── Currency ──────────────────────────────────────────────────────────────
# Phase 1 is USD-only. Multi-currency is backlogged (docs/future_features.md).
# Adding a new currency = one-line change here + any locale-aware formatting
# in utils/formatting.py.
SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD",)
DEFAULT_CURRENCY: str = "USD"

# ── Payload limits ────────────────────────────────────────────────────────
# CLI payload size guard. Overridable at runtime via the
# DOCGEN_MAX_PAYLOAD_BYTES environment variable (see scripts/generate.py).
DEFAULT_MAX_PAYLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB
