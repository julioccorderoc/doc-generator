"""Integration tests for the generation pipeline.

Covers both the library entrypoint (`core.generate.generate`) and the
end-to-end CLI (`scripts/generate.py` as a subprocess).

Skipped automatically when weasyprint cannot import (CI without Pango).
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

try:
    importlib.import_module("weasyprint")
except (ImportError, OSError):
    pytest.skip("weasyprint not available (Pango missing)", allow_module_level=True)

from core.generate import GenerationError, GenerationResult, generate

ROOT = Path(__file__).parent.parent
GENERATE = ROOT / "scripts" / "generate.py"
FIXTURES = Path(__file__).parent / "fixtures"


# ── Library surface: core.generate.generate() ────────────────────────────

def _load(fixture: str) -> dict:
    return json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))


@pytest.mark.parametrize("doc_type,fixture", [
    ("purchase_order", "sample_po.json"),
    ("invoice", "sample_invoice.json"),
    ("request_for_quotation", "sample_rfq.json"),
])
def test_generate_returns_pdf_bytes(doc_type: str, fixture: str) -> None:
    """Happy path: each registered doc type produces a non-empty PDF."""
    result = generate(doc_type, _load(fixture))

    assert isinstance(result, GenerationResult)
    assert result.doc_type == doc_type
    assert isinstance(result.pdf_bytes, bytes)
    assert result.pdf_bytes.startswith(b"%PDF-"), "missing PDF magic bytes"
    assert len(result.pdf_bytes) > 1000, "PDF suspiciously small"
    assert isinstance(result.context, dict)
    assert isinstance(result.payload, dict)


def test_generate_unknown_doc_type_raises() -> None:
    with pytest.raises(GenerationError) as excinfo:
        generate("nonexistent_doc_type", _load("sample_po.json"))
    msg = str(excinfo.value)
    assert "Unknown doc_type 'nonexistent_doc_type'" in msg
    assert "purchase_order" in msg  # lists registered types


def test_generate_validation_error_wrapped() -> None:
    """Pydantic ValidationError is re-raised as GenerationError with the
    exact `Validation failed:` format the CLI depends on."""
    with pytest.raises(GenerationError) as excinfo:
        generate("purchase_order", _load("invalid_po.json"))
    msg = str(excinfo.value)
    assert msg.startswith("Validation failed:")
    assert "tax_rate" in msg


def test_generate_rejects_unsupported_currency() -> None:
    payload = _load("sample_po.json")
    payload["currency"] = "EUR"
    with pytest.raises(GenerationError) as excinfo:
        generate("purchase_order", payload)
    assert "EUR" in str(excinfo.value)


def test_generate_payload_size_guard_trips() -> None:
    payload = _load("sample_po.json")
    with pytest.raises(GenerationError) as excinfo:
        generate("purchase_order", payload, max_payload_bytes=10)
    assert "byte limit" in str(excinfo.value)


def test_generate_payload_size_unlimited_warns() -> None:
    payload = _load("sample_po.json")
    with pytest.warns(UserWarning, match="non-positive"):
        result = generate("purchase_order", payload, max_payload_bytes=0)
    assert result.pdf_bytes.startswith(b"%PDF-")


def test_generate_payload_dict_is_serialized_output() -> None:
    """`result.payload` is the validated payload with computed fields."""
    result = generate("purchase_order", _load("sample_po.json"))
    # Computed fields must appear in the dumped payload.
    for key in ("subtotal", "tax_amount", "grand_total"):
        assert key in result.payload, f"computed field '{key}' missing"


# ── End-to-end CLI surface: subprocess ───────────────────────────────────

def test_cli_generates_pdf_end_to_end(tmp_path) -> None:
    """End-to-end: CLI process writes a PDF, prints absolute path, exits 0."""
    payload = _load("sample_po.json")
    payload["logo"] = None
    payload_file = tmp_path / "po_no_logo.json"
    payload_file.write_text(json.dumps(payload))

    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "purchase_order",
         "--payload", str(payload_file),
         "--output_dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"generate.py failed:\n{result.stdout}\n{result.stderr}"
    )

    output_path = Path(result.stdout.strip())
    assert output_path.is_absolute(), "CLI must print absolute path"
    assert output_path.suffix == ".pdf"
    assert output_path.exists()


def test_cli_unknown_doc_type_exit_1(tmp_path) -> None:
    """CLI prints registered types and exits 1 on unknown doc_type."""
    payload_file = tmp_path / "p.json"
    payload_file.write_text(json.dumps(_load("sample_po.json")))

    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "not_real",
         "--payload", str(payload_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Unknown doc_type 'not_real'" in result.stdout
    assert "purchase_order" in result.stdout


def test_cli_validation_error_exit_1() -> None:
    """CLI emits the `Validation failed:` block verbatim on invalid payload."""
    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "purchase_order",
         "--payload", str(FIXTURES / "invalid_po.json")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout.startswith("Validation failed:")


def test_cli_missing_payload_file_exit_1(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "purchase_order",
         "--payload", str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Payload file not found" in result.stdout


def test_cli_invalid_json_exit_1(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "purchase_order",
         "--payload", str(bad)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Invalid JSON in payload file" in result.stdout
