"""Build the Windows executable: ``python build_exe.py`` -> ``dist/RocktStand.exe``."""

from __future__ import annotations

import os
from pathlib import Path

import PyInstaller.__main__

REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"
EXE_NAME = "RocktStand"

# (source file, folder inside the bundle) - must match src/resources.py
DATA_FILES = [
    (SRC / "ui" / "main_window.ui", "ui"),
    (SRC / "assets" / "logo.png", "assets"),
]

# Optional pyqtgraph extras and build tools that the application never uses.
# Leaving them out roughly halves the size of the executable.
EXCLUDED_MODULES = [
    "IPython",
    "matplotlib",
    "PIL",
    "pygments",
    "pytest",
    "scipy",
    "setuptools",
    "tkinter",
]


def main() -> None:
    args = [
        str(SRC / "main.py"),
        "--name", EXE_NAME,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(SRC),
        "--icon", str(SRC / "assets" / "logo.ico"),
        "--distpath", str(REPO_ROOT / "dist"),
        "--workpath", str(REPO_ROOT / "build"),
        "--specpath", str(REPO_ROOT / "build"),
    ]
    for source, target_dir in DATA_FILES:
        args += ["--add-data", f"{source}{os.pathsep}{target_dir}"]
    for module in EXCLUDED_MODULES:
        args += ["--exclude-module", module]

    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
