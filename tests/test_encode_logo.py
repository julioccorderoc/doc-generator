"""Tests for scripts/encode_logo.py

Runs the script as a subprocess to test the full CLI contract.
No system dependencies beyond stdlib.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "encode_logo.py"
FIXTURES = Path(__file__).parent / "fixtures"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_encode_png_without_payload(tmp_path):
    img = tmp_path / "logo.png"
    # minimal valid PNG (1×1 transparent pixel)
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    out_path = tmp_path / "logo_with_logo.json"

    result = run("--image", str(img), "--out", str(out_path))

    assert result.returncode == 0, result.stdout
    assert result.stdout.strip() == str(out_path.resolve())

    payload = json.loads(out_path.read_text())
    assert "logo" in payload
    assert payload["logo"].startswith("data:image/png;base64,")


def test_encode_injects_into_existing_payload(tmp_path):
    img = tmp_path / "brand.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)

    payload_path = FIXTURES / "sample_po.json"
    out_path = tmp_path / "po_with_logo.json"

    result = run("--image", str(img), "--payload", str(payload_path), "--out", str(out_path))

    assert result.returncode == 0, result.stdout
    payload = json.loads(out_path.read_text())
    assert payload["logo"].startswith("data:image/png;base64,")
    assert payload["po_number"] == "PO-2026-0001"


def test_encode_overwrites_existing_logo_field(tmp_path):
    img = tmp_path / "new.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)

    existing = {"logo": "data:image/png;base64,OLD", "po_number": "PO-X"}
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(existing))
    out_path = tmp_path / "out.json"

    result = run("--image", str(img), "--payload", str(payload_path), "--out", str(out_path))

    assert result.returncode == 0
    payload = json.loads(out_path.read_text())
    assert payload["logo"] != "data:image/png;base64,OLD"
    assert payload["logo"].startswith("data:image/png;base64,")


def test_missing_image_exits_1(tmp_path):
    out_path = tmp_path / "out.json"
    result = run("--image", "/nonexistent/logo.png", "--out", str(out_path))
    assert result.returncode == 1
    assert "not found" in result.stdout.lower()


def test_unsupported_format_exits_1(tmp_path):
    img = tmp_path / "logo.bmp"
    img.write_bytes(b"BM" + b"\x00" * 20)
    out_path = tmp_path / "out.json"

    result = run("--image", str(img), "--out", str(out_path))

    assert result.returncode == 1
    assert "unsupported" in result.stdout.lower()


def test_jpeg_produces_correct_mime(tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)
    out_path = tmp_path / "out.json"

    result = run("--image", str(img), "--out", str(out_path))

    assert result.returncode == 0
    payload = json.loads(out_path.read_text())
    assert payload["logo"].startswith("data:image/jpeg;base64,")


def test_data_uri_decodes_to_original_bytes(tmp_path):
    original_bytes = b"\x89PNG\r\n\x1a\n" + bytes(range(32))
    img = tmp_path / "test.png"
    img.write_bytes(original_bytes)
    out_path = tmp_path / "out.json"

    run("--image", str(img), "--out", str(out_path))

    payload = json.loads(out_path.read_text())
    prefix = "data:image/png;base64,"
    encoded_part = payload["logo"][len(prefix):]
    decoded = base64.b64decode(encoded_part)
    assert decoded == original_bytes
