"""Parametrized smoke tests over `builders.REGISTRY`.

Guards the contract that every registered doc type:

  1. Has a fixture named `tests/fixtures/sample_<short_name>.json` that the
     registered Pydantic model accepts.
  2. Has a context builder that returns a dict containing the keys all
     base.html-derived templates require (`css_path`, `theme_css`).
  3. Has a Jinja2 template file that actually exists at
     `templates/<doc_type>.html`.
  4. Has a non-empty `file_prefix` used for output filenames.

Plus two structural checks on the REGISTRY itself: every config has the same
field set, and `file_prefix` values are unique (no two doc types collide on
output filenames).

These tests are deliberately fast — no PDF rendering, no WeasyPrint. The full
end-to-end render path is covered by `tests/test_integration.py`.
"""
from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from builders import REGISTRY, DocTypeConfig

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
TEMPLATES = ROOT / "templates"

# Map doc-type slug → canonical fixture filename. Kept explicit because the
# fixtures use short names (`sample_po.json`) but registry keys use the long
# slugs (`purchase_order`).
_FIXTURE_MAP: dict[str, str] = {
    "purchase_order": "sample_po.json",
    "invoice": "sample_invoice.json",
    "request_for_quotation": "sample_rfq.json",
}


def _load_fixture(doc_type: str) -> dict:
    """Load the canonical sample fixture for a doc type."""
    if doc_type not in _FIXTURE_MAP:
        pytest.fail(
            f"No fixture mapping for doc_type {doc_type!r}. "
            f"Add an entry to _FIXTURE_MAP in tests/test_registry.py."
        )
    path = FIXTURES / _FIXTURE_MAP[doc_type]
    return json.loads(path.read_text())


# Builder modules call resolve_logo() at render time. The sample fixtures omit
# the logo (or pass null) so resolve_logo returns None — but we patch every
# known builder module so the test stays robust if a fixture is later updated
# to include a data-URI logo without contributors knowing this test exists.
_BUILDER_LOGO_PATCHES = (
    "builders.purchase_order.resolve_logo",
    "builders.invoice.resolve_logo",
    "builders.request_for_quotation.resolve_logo",
)


def _build_with_patched_logo(config: DocTypeConfig, payload: dict) -> dict:
    """Validate the payload + run the builder with logo resolution mocked out."""
    doc = config.model(**payload)
    # Stack patches so any builder's resolve_logo import returns None. Patches
    # for modules that don't import resolve_logo are no-ops.
    from contextlib import ExitStack
    with ExitStack() as stack:
        for target in _BUILDER_LOGO_PATCHES:
            try:
                stack.enter_context(patch(target, return_value=None))
            except (AttributeError, ModuleNotFoundError):
                # Builder doesn't import resolve_logo — skip.
                continue
        return config.build_context(doc)


# ── Parametrized end-to-end smoke test ────────────────────────────────────────

@pytest.mark.parametrize("doc_type", list(REGISTRY.keys()))
def test_registry_entry_end_to_end(doc_type: str) -> None:
    """Validate fixture + run builder + check template/prefix for each doc type."""
    config = REGISTRY[doc_type]
    payload = _load_fixture(doc_type)

    # (a) Schema accepts the canonical fixture.
    context = _build_with_patched_logo(config, payload)

    # (b) Builder produces a context dict with the keys base.html consumes.
    assert isinstance(context, dict), (
        f"build_context for {doc_type!r} returned {type(context).__name__}, expected dict"
    )
    for required_key in ("css_path", "theme_css"):
        assert required_key in context, (
            f"{doc_type!r} context missing required key {required_key!r}"
        )

    # (c) Template file referenced by the registry actually exists.
    template_path = TEMPLATES / config.template
    assert template_path.is_file(), (
        f"{doc_type!r} template file not found: {template_path}"
    )
    assert config.template == f"{doc_type}.html", (
        f"{doc_type!r} template name {config.template!r} does not follow the "
        f"<doc_type>.html convention"
    )

    # (d) file_prefix is a non-empty string.
    assert isinstance(config.file_prefix, str) and config.file_prefix, (
        f"{doc_type!r} file_prefix must be a non-empty string, got {config.file_prefix!r}"
    )


# ── REGISTRY structural sanity checks ─────────────────────────────────────────

def test_registry_file_prefixes_are_unique() -> None:
    """No two doc types may share a `file_prefix` (output filename collision)."""
    prefixes = [config.file_prefix for config in REGISTRY.values()]
    duplicates = {p for p in prefixes if prefixes.count(p) > 1}
    assert not duplicates, f"Duplicate file_prefix values in REGISTRY: {duplicates}"


def test_registry_configs_have_consistent_fields() -> None:
    """Every REGISTRY entry must be a DocTypeConfig with the same field set."""
    expected_fields = {f.name for f in fields(DocTypeConfig)}
    for doc_type, config in REGISTRY.items():
        assert isinstance(config, DocTypeConfig), (
            f"REGISTRY[{doc_type!r}] is {type(config).__name__}, expected DocTypeConfig"
        )
        actual_fields = {f.name for f in fields(type(config))}
        assert actual_fields == expected_fields, (
            f"REGISTRY[{doc_type!r}] has fields {actual_fields}, "
            f"expected {expected_fields}"
        )
