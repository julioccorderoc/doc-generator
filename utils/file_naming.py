"""
Auto-naming logic for generated PDF files.

Output format: <doc_type>_YYYYMMDD_XXXX.pdf
Example:       purchase_order_20260316_0001.pdf

Sequence resets per day per doc_type.
"""
import re
from datetime import date
from pathlib import Path

# output/ lives at the project root, two levels above this file
_OUTPUT_DIR = Path(__file__).parent.parent / "output"


def next_output_filename(doc_type: str) -> Path:
    """Return the next sequential output path for the given doc_type.

    Creates output/ if it does not exist.
    """
    _OUTPUT_DIR.mkdir(exist_ok=True)

    today = date.today().strftime("%Y%m%d")
    prefix = f"{doc_type}_{today}_"
    pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}})\.pdf$")

    existing_numbers = []
    for f in _OUTPUT_DIR.iterdir():
        m = pattern.match(f.name)
        if m:
            existing_numbers.append(int(m.group(1)))

    next_num = max(existing_numbers) + 1 if existing_numbers else 1
    return _OUTPUT_DIR / f"{prefix}{next_num:04d}.pdf"
