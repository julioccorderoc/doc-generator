"""Project root and standard directory paths.

Single source of truth for all path constants.
Every module that needs ROOT / TEMPLATES_DIR / ASSETS_DIR imports from here
rather than recomputing `Path(__file__).parent.parent` independently.
"""
from pathlib import Path

ROOT: Path = Path(__file__).parent.parent
TEMPLATES_DIR: Path = ROOT / "templates"
ASSETS_DIR: Path = ROOT / "assets"
OUTPUT_DIR: Path = ROOT / "output"
