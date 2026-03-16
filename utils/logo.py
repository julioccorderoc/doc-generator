"""
Logo resolver: converts a file path or URL into a base64 data URI
suitable for embedding directly in an HTML <img src="..."> attribute.

Supported formats: PNG, JPG/JPEG, SVG.
Returns None if source is None.
Raises ValueError on missing file or failed URL fetch.
"""
import base64
import urllib.request
from pathlib import Path

_MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


def resolve_logo(source: str | None) -> str | None:
    """Resolve a logo source to a base64 data URI.

    Args:
        source: Absolute or relative file path, or http(s):// URL.
                Pass None to skip logo entirely.

    Returns:
        A data URI string like ``data:image/png;base64,...``,
        or None if source is None.

    Raises:
        ValueError: If the file does not exist, the URL fetch fails,
                    or the format is not supported.
    """
    if source is None:
        return None

    if source.startswith("http://") or source.startswith("https://"):
        return _resolve_url(source)

    return _resolve_file(source)


def _resolve_file(source: str) -> str:
    path = Path(source)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise ValueError(f"Logo file not found: {path}")

    ext = path.suffix.lower()
    mime = _MIME_TYPES.get(ext)
    if mime is None:
        supported = ", ".join(_MIME_TYPES)
        raise ValueError(
            f"Unsupported logo format '{ext}'. Supported: {supported}"
        )

    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _resolve_url(source: str) -> str:
    try:
        req = urllib.request.Request(source, headers={"User-Agent": "doc-generator/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
    except Exception as exc:
        raise ValueError(f"Failed to fetch logo from URL '{source}': {exc}") from exc

    # Guess MIME from URL extension; fall back to image/png
    ext = Path(source.split("?")[0]).suffix.lower()
    mime = _MIME_TYPES.get(ext, "image/png")
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
