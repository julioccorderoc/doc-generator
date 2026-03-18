"""
Logo resolver: validates that a logo value is a pre-resolved base64 data URI.

Accepted format: data:image/<subtype>;base64,<data>
Returns None if source is None.
Raises ValueError for file paths, URLs, or any other format.
"""


def resolve_logo(source: str | None) -> str | None:
    """Validate and return a logo data URI.

    Args:
        source: A ``data:image/...;base64,...`` string, or None to omit the logo.

    Returns:
        The data URI string as-is, or None.

    Raises:
        ValueError: If source is not a data URI.
    """
    if source is None:
        return None

    if source.startswith("data:image/"):
        return source

    raise ValueError(
        "Logo must be a data URI (data:image/...;base64,...). "
        "File paths and URLs are not accepted."
    )
