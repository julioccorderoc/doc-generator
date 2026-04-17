"""core.generate — pure pipeline: JSON payload → PDF bytes.

No I/O beyond reading CSS/templates from disk. No stdout. No file writes.
The CLI layer (`scripts/generate.py`) is responsible for all side effects.

Typical usage:

    from core.generate import generate, GenerationError

    try:
        result = generate("purchase_order", payload_dict)
    except GenerationError as exc:
        # handle
        ...
    else:
        Path("out.pdf").write_bytes(result.pdf_bytes)
        saved_payload = result.payload  # validated, with computed fields
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from pydantic import ValidationError
import weasyprint

from builders import REGISTRY
from utils.constants import DEFAULT_MAX_PAYLOAD_BYTES, SUPPORTED_CURRENCIES
from utils.paths import ROOT, TEMPLATES_DIR


# ── Public API ────────────────────────────────────────────────────────────

class GenerationError(Exception):
    """Raised on any failure in the generation pipeline.

    Covers: unknown doc_type, oversize payload, unsupported currency,
    schema validation error, and context-build failures. The CLI layer
    catches this and formats it for stdout.
    """
    pass


@dataclass(frozen=True)
class GenerationResult:
    """Return value of `generate()`.

    Attributes:
        pdf_bytes: Rendered PDF as raw bytes. Caller writes to disk.
        context:   The fully-resolved template context dict used to render.
        payload:   The validated payload (`doc.model_dump(mode="json")`),
                   including any Pydantic `@computed_field` values.
        doc_type:  The doc_type slug that was generated.
    """
    pdf_bytes: bytes
    context: dict
    payload: dict
    doc_type: str


def generate(
    doc_type: str,
    payload_dict: dict,
    *,
    max_payload_bytes: int | None = None,
) -> GenerationResult:
    """Validate payload, build context, render PDF. Returns bytes; writes nothing.

    Args:
        doc_type:          Slug matching a key in `builders.REGISTRY`.
        payload_dict:      Raw payload as a dict (typically parsed from JSON).
        max_payload_bytes: Serialized-size cap for `payload_dict`. When `None`,
                           uses `utils.constants.DEFAULT_MAX_PAYLOAD_BYTES`.
                           When non-positive, treated as unlimited (emits a
                           `warnings.warn`).

    Raises:
        GenerationError: For any failure in the pipeline. The message is
                         formatted to be suitable for the CLI to print directly.
    """
    # ── 1. doc_type lookup ────────────────────────────────────────────────
    config = REGISTRY.get(doc_type)
    if config is None:
        raise GenerationError(
            f"Unknown doc_type '{doc_type}'. "
            f"Supported types: {', '.join(REGISTRY)}"
        )

    # ── 2. Payload-size guard ─────────────────────────────────────────────
    effective_max = DEFAULT_MAX_PAYLOAD_BYTES if max_payload_bytes is None else max_payload_bytes
    if effective_max is not None and effective_max <= 0:
        warnings.warn(
            "max_payload_bytes is non-positive; payload size check disabled.",
            stacklevel=2,
        )
    else:
        serialized_size = len(json.dumps(payload_dict).encode("utf-8"))
        if serialized_size > effective_max:
            raise GenerationError(
                f"Payload exceeds the {effective_max} byte limit."
            )

    # ── 3. Currency guard ─────────────────────────────────────────────────
    # Defensive: schemas that declare a `currency` field also constrain it
    # via Literal/validators, so most mismatches are caught in step 4. This
    # check protects programmatic callers who might bypass schema coercion.
    raw_currency = payload_dict.get("currency") if isinstance(payload_dict, dict) else None
    if raw_currency is not None and raw_currency not in SUPPORTED_CURRENCIES:
        raise GenerationError(
            f"Currency '{raw_currency}' is not supported. "
            f"Supported currencies: {', '.join(SUPPORTED_CURRENCIES)}"
        )

    # ── 4. Pydantic validation ────────────────────────────────────────────
    try:
        doc = config.model.model_validate(payload_dict)
    except ValidationError as exc:
        raise GenerationError(_format_validation_errors(exc)) from exc

    # ── 5. Build template context ─────────────────────────────────────────
    try:
        context = config.build_context(doc)
    except ValueError as exc:
        raise GenerationError(f"Error preparing document: {exc}") from exc

    # ── 6. Render HTML via Jinja2 ─────────────────────────────────────────
    env = _make_jinja_env()
    html = env.get_template(config.template).render(**context)

    # ── 7. Render PDF via WeasyPrint ──────────────────────────────────────
    pdf_bytes = weasyprint.HTML(string=html, base_url=str(ROOT)).write_pdf()

    return GenerationResult(
        pdf_bytes=pdf_bytes,
        context=context,
        payload=doc.model_dump(mode="json"),
        doc_type=doc_type,
    )


# ── Internals ─────────────────────────────────────────────────────────────

def _make_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    def nl2br(value: str) -> Markup:
        """Replace newlines with <br> tags, safely escaping user content."""
        return Markup(escape(value).replace("\n", Markup("<br>\n")))  # nosec B704

    env.filters["nl2br"] = nl2br
    return env


def _format_validation_errors(exc: ValidationError) -> str:
    """Render a Pydantic ValidationError as a multi-line `Validation failed:` block.

    Format is part of the CLI contract (see CLAUDE.md § CLI Contract and
    references/ERRORS.md). Do not change without updating both documents.
    """
    lines = ["Validation failed:"]
    for error in exc.errors():
        loc = " → ".join(str(p) for p in error["loc"])
        msg = error["msg"].removeprefix("Value error, ")
        lines.append(f"  {loc}: {msg}")
    return "\n".join(lines)
