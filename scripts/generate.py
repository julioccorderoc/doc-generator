#!/usr/bin/env python3
"""doc-generator CLI entrypoint — thin wrapper around `core.generate`.

Usage:
    uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview]

See CLAUDE.md § CLI Contract for the full interface specification.
See docs/decisions/003-file-path-payload.md for why --payload is a file path.
See docs/decisions/004-argparse-only-cli.md for why we use argparse.

All generation logic lives in `core/generate.py`. This script only:
  - parses CLI args
  - loads the payload file
  - calls `core.generate.generate()`
  - writes the resulting PDF to disk
  - prints the absolute path, optionally saves payload, optionally previews
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve the project root so imports work regardless of the caller's cwd.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from builders import REGISTRY
from core.generate import GenerationError, generate
from utils.constants import DEFAULT_MAX_PAYLOAD_BYTES
from utils.file_naming import next_output_filename
from utils.preview import open_preview


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
    parser.add_argument("--doc_type", required=True,
                        help=f"Document type slug. Supported: {', '.join(REGISTRY)}")
    parser.add_argument("--payload", required=True,
                        help="Path to a JSON file containing the document data.")
    parser.add_argument("--preview", action="store_true",
                        help="Open the PDF in the system viewer after generation.")
    parser.add_argument("--output_name", default=None,
                        help="Custom filename stem (e.g. 'NS39' produces PO_NS39.pdf). "
                             "Defaults to auto-naming: <PREFIX>_YYYYMMDD_XXXX.pdf.")
    parser.add_argument("--output_dir", default=None,
                        help="Directory to save the generated PDF. Defaults to the "
                             "internal output/ folder. Pass $(pwd) to save in the "
                             "caller's working directory.")
    parser.add_argument("--save_payload", action="store_true",
                        help="Save the validated payload (with computed fields) as "
                             "a JSON file alongside the PDF, using the same stem.")
    args = parser.parse_args()

    # ── Resolve payload size limit (env override) ─────────────────────────
    _max_bytes_env = os.environ.get("DOCGEN_MAX_PAYLOAD_BYTES")
    try:
        max_payload_bytes = int(_max_bytes_env) if _max_bytes_env else DEFAULT_MAX_PAYLOAD_BYTES
    except ValueError:
        print(f"Invalid DOCGEN_MAX_PAYLOAD_BYTES: {_max_bytes_env!r}. Must be an integer.")
        return 1

    # ── Load payload file ─────────────────────────────────────────────────
    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Payload file not found: {args.payload}")
        return 1
    if payload_path.stat().st_size > max_payload_bytes:
        print(f"Payload file exceeds the {max_payload_bytes} byte limit.")
        return 1
    try:
        payload_dict = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in payload file: {exc}")
        return 1

    # ── Run core pipeline ─────────────────────────────────────────────────
    try:
        result = generate(args.doc_type, payload_dict, max_payload_bytes=max_payload_bytes)
    except GenerationError as exc:
        print(str(exc))
        return 1

    # ── Write PDF ─────────────────────────────────────────────────────────
    try:
        output_dir = Path(args.output_dir) if args.output_dir else None
        config = REGISTRY[args.doc_type]
        output_path = next_output_filename(config.file_prefix, args.output_name, output_dir)
    except ValueError as exc:
        print(str(exc))
        return 1
    output_path.write_bytes(result.pdf_bytes)
    print(str(output_path))

    # ── Optionally save validated payload ─────────────────────────────────
    if args.save_payload:
        json_path = output_path.with_suffix(".json")
        json_path.write_text(
            json.dumps(result.payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Optionally preview (best-effort) ──────────────────────────────────
    if args.preview:
        open_preview(output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
