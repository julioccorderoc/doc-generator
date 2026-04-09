#!/usr/bin/env python3
"""doc-generator CLI entrypoint.

Usage:
    uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview]

See CLAUDE.md § CLI Contract for the full interface specification.
See docs/decisions/003-file-path-payload.md for why --payload is a file path.
See docs/decisions/004-argparse-only-cli.md for why we use argparse.

Document types and their context builders are registered in builders/__init__.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Resolve the project root so imports work regardless of the caller's cwd.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from markupsafe import Markup, escape
from pydantic import ValidationError
from jinja2 import Environment, FileSystemLoader
import weasyprint

from builders import REGISTRY
from utils.paths import TEMPLATES_DIR
from utils.file_naming import next_output_filename
from utils.preview import open_preview


# ── Jinja2 environment ─────────────────────────────────────────────────────

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


# ── Error formatting ───────────────────────────────────────────────────────

def _format_validation_errors(exc: ValidationError) -> str:
    lines = ["Validation failed:"]
    for error in exc.errors():
        loc = " → ".join(str(p) for p in error["loc"])
        msg = error["msg"].removeprefix("Value error, ")
        lines.append(f"  {loc}: {msg}")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Generate a PDF document from a JSON payload.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported doc types: " + ", ".join(REGISTRY) + "\n"
            "Exit code 0 on success; 1 on any error. Output path printed to stdout."
        ),
    )
    parser.add_argument(
        "--doc_type",
        required=True,
        help=f"Document type slug. Supported: {', '.join(REGISTRY)}",
    )
    parser.add_argument(
        "--payload",
        required=True,
        help="Path to a JSON file containing the document data.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the PDF in the system viewer after generation.",
    )
    parser.add_argument(
        "--output_name",
        default=None,
        help=(
            "Custom filename stem (e.g. 'NS39' produces PO_NS39.pdf). "
            "Defaults to auto-naming: <PREFIX>_YYYYMMDD_XXXX.pdf."
        ),
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help=(
            "Directory to save the generated PDF. "
            "Defaults to the internal output/ folder. "
            "Pass $(pwd) to save in the caller's working directory."
        ),
    )
    parser.add_argument(
        "--save_payload",
        action="store_true",
        help=(
            "Save the validated payload (with computed fields) as a JSON file "
            "alongside the PDF, using the same filename stem."
        ),
    )
    args = parser.parse_args()

    # ── 1. Validate doc_type ───────────────────────────────────────────────
    config = REGISTRY.get(args.doc_type)
    if config is None:
        print(
            f"Unknown doc_type '{args.doc_type}'. "
            f"Supported types: {', '.join(REGISTRY)}"
        )
        return 1

    # ── 2. Load payload JSON ───────────────────────────────────────────────
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Payload file not found: {args.payload}")
        return 1

    _MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    if payload_path.stat().st_size > _MAX_PAYLOAD_BYTES:
        print("Payload file exceeds the 10 MB limit.")
        return 1

    try:
        raw = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in payload file: {exc}")
        return 1

    # ── 3. Validate against schema ─────────────────────────────────────────
    try:
        doc = config.model(**raw)
    except ValidationError as exc:
        print(_format_validation_errors(exc))
        return 1


    # ── 4. Build template context ──────────────────────────────────────────
    try:
        context = config.build_context(doc)
    except ValueError as exc:
        print(f"Error preparing document: {exc}")
        return 1

    # ── 5. Render HTML ─────────────────────────────────────────────────────
    env = _make_jinja_env()
    html = env.get_template(config.template).render(**context)

    # ── 6. Write PDF ───────────────────────────────────────────────────────
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = next_output_filename(config.file_prefix, args.output_name, output_dir)
    weasyprint.HTML(string=html).write_pdf(str(output_path))

    print(str(output_path))

    # ── 7. Save validated payload ──────────────────────────────────────────
    if args.save_payload:
        json_path = output_path.with_suffix(".json")
        json_path.write_text(
            json.dumps(doc.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── 8. Preview (best-effort) ───────────────────────────────────────────
    if args.preview:
        open_preview(output_path)

    return 0

if __name__ == "__main__":
    sys.exit(main())
