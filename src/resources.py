"""Locate bundled data files both from source and from the PyInstaller build."""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent

MAIN_WINDOW_UI = "ui/main_window.ui"
LOGO_PNG = "assets/logo.png"


def resource_path(relative_path: str) -> str:
    """Return the absolute path of a data file.

    PyInstaller unpacks data files into ``sys._MEIPASS``; when running from
    source the same relative layout lives next to this module.
    """
    base_path = Path(getattr(sys, "_MEIPASS", SOURCE_ROOT))
    return str(base_path / relative_path)
