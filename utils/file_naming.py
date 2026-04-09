"""
Auto-naming logic for generated PDF files.

Output format: <PREFIX>_YYYYMMDD_XXXX.pdf
Example:       PO_20260316_0001.pdf

PREFIX comes from DocTypeConfig.file_prefix (PO, INV, RFQ).
Sequence resets per day per prefix.
"""
import re
from datetime import date
from pathlib import Path

from utils.paths import OUTPUT_DIR


def next_output_filename(
    doc_type: str,
    name: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Return the output path for the given doc_type.

    If `output_dir` is provided, files are saved there instead of OUTPUT_DIR.
    If `name` is provided, returns <prefix>_<name>.pdf (no sequence counter).
    Otherwise uses auto-naming: <prefix>_YYYYMMDD_XXXX.pdf.

    Creates the target directory if it does not exist.

    Raises ValueError if `name` contains path separators or traversal sequences.
    """
    base_dir = output_dir if output_dir is not None else OUTPUT_DIR
    base_dir.mkdir(exist_ok=True)

    if name:
        if "/" in name or "\\" in name or ".." in name:
            raise ValueError(
                "output_name must be a plain filename stem with no path separators."
            )
        sanitized = name.strip()
        if not sanitized:
            raise ValueError(
                "output_name must be a plain filename stem with no path separators."
            )
        return base_dir / f"{doc_type}_{sanitized}.pdf"

    today = date.today().strftime("%Y%m%d")
    prefix = f"{doc_type}_{today}_"
    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}})\.pdf$")

    existing_numbers = []
    for f in base_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            existing_numbers.append(int(m.group(1)))

    next_num = max(existing_numbers) + 1 if existing_numbers else 1
    return base_dir / f"{prefix}{next_num:04d}.pdf"
