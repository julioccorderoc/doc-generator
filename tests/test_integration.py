"""End-to-end integration test: runs generate.py as a subprocess.

Skipped automatically when weasyprint cannot import (CI without Pango).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import importlib

import pytest

try:
    importlib.import_module("weasyprint")
except (ImportError, OSError):
    pytest.skip("weasyprint not available (Pango missing)", allow_module_level=True)

ROOT = Path(__file__).parent.parent
GENERATE = ROOT / "scripts" / "generate.py"
FIXTURES = Path(__file__).parent / "fixtures"


def test_generate_purchase_order_end_to_end(tmp_path):
    # Load the standard fixture; logo is already null at root level.
    payload = json.loads((FIXTURES / "sample_po.json").read_text())
    payload["logo"] = None
    payload_file = tmp_path / "po_no_logo.json"
    payload_file.write_text(json.dumps(payload))

    result = subprocess.run(
        [sys.executable, str(GENERATE), "--doc_type", "purchase_order",
         "--payload", str(payload_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"generate.py failed:\n{result.stdout}\n{result.stderr}"
    )

    output_path = Path(result.stdout.strip())
    assert output_path.suffix == ".pdf", f"Expected .pdf output, got: {output_path}"
    assert output_path.exists(), f"Output file not found: {output_path}"

    output_path.unlink()
