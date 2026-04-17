"""core — library-importable generation pipeline.

Public API:

    from core.generate import generate, GenerationError, GenerationResult

`generate()` is pure (no I/O beyond reading CSS/templates, no stdout, no
file writes). All side effects — writing PDFs, printing paths, opening
viewers — are the responsibility of the CLI layer in `scripts/generate.py`.
"""
from __future__ import annotations

from core.generate import GenerationError, GenerationResult, generate

__all__ = ["generate", "GenerationError", "GenerationResult"]
