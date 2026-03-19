"""
OS-aware PDF opener. Opens the generated PDF in the system default viewer.

Silently no-ops in headless environments (no DISPLAY, CI, SSH sessions)
and on any unexpected error. Never raises — preview is best-effort only.
"""
import os
import subprocess
import sys
from pathlib import Path


def open_preview(path: Path) -> None:
    """Open *path* in the OS default PDF viewer.

    Platforms:
        macOS   — ``open <path>``
        Linux   — ``xdg-open <path>`` (skipped if no DISPLAY/WAYLAND_DISPLAY)
        Windows — ``os.startfile(<path>)``

    Any exception is silently swallowed. This function must never cause
    the main script to exit with an error.
    """
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform.startswith("linux"):
            if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                return  # headless — no-op
            subprocess.Popen(["xdg-open", str(path)])
        elif sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        # Unknown platform: no-op
    except Exception:
        pass
