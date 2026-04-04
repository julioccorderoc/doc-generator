"""
Encode a logo image as a base64 data URI and inject it into a JSON payload.

Usage:
    uv run python scripts/encode_logo.py --image <path> [--payload <path>] [--out <path>]

On success: writes the enriched JSON to the output file and prints the absolute
output path to stdout (one line). Exit code 0.

On failure: prints a plain error message to stdout. Exit code 1.

The logo is always injected at the root "logo" key — consistent across all
doc types (purchase_order, invoice, request_for_quotation).

This script exists so that Claude never needs to hold a base64 string in its
context window. It reads the image, encodes it, injects it into the payload,
and writes to a new file — all off-context.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

_MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Encode a logo image and inject it into a JSON payload at root 'logo'."
    )
    parser.add_argument("--image", required=True, help="Path to the image file.")
    parser.add_argument("--payload", default=None, help="Path to an existing JSON payload. If omitted, a minimal payload with only 'logo' is written.")
    parser.add_argument("--out", default=None, help="Output path. Defaults to /tmp/<payload_stem>_with_logo.json.")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: image file not found: {image_path}")
        return 1

    suffix = image_path.suffix.lower()
    mime = _MIME_TYPES.get(suffix)
    if mime is None:
        supported = ", ".join(sorted(_MIME_TYPES))
        print(f"Error: unsupported image format '{suffix}'. Supported: {supported}")
        return 1

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime};base64,{encoded}"

    if args.payload:
        payload_path = Path(args.payload)
        if not payload_path.exists():
            print(f"Error: payload file not found: {payload_path}")
            return 1
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        stem = payload_path.stem
    else:
        payload = {}
        stem = image_path.stem

    payload["logo"] = data_uri

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("/tmp") / f"{stem}_with_logo.json"

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(out_path.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
