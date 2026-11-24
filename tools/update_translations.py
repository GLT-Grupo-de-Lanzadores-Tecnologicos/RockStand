"""Update the Qt Linguist translation files.

    python tools/update_translations.py

1. ``pylupdate5`` (installed with PyQt5) scans the sources and ``main_window.ui``
   and adds new or changed strings to ``src/translations/*.ts``. Existing
   translations are kept.
2. Translate the new entries with Qt Linguist (open the ``.ts`` file).
3. Run this script again: ``lrelease`` compiles every ``.ts`` into the ``.qm``
   loaded at runtime.

``lrelease`` comes with Qt, not with PyQt5. It is looked up in ``PATH``, then in
the ``LRELEASE`` environment variable, then in a default ``C:\\Qt`` installation.
Commit both the ``.ts`` and the ``.qm`` files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
TRANSLATIONS = SRC / "translations"
LANGUAGES = ["es"]


def source_files() -> list[Path]:
    files = sorted(SRC.rglob("*.py")) + sorted(SRC.rglob("*.ui"))
    return [path for path in files if "__pycache__" not in path.parts]


def find_lrelease() -> str | None:
    found = shutil.which("lrelease") or os.environ.get("LRELEASE")
    if found:
        return found
    candidates = sorted(Path("C:/Qt").glob("*/*/bin/lrelease.exe"), reverse=True)
    return str(candidates[0]) if candidates else None


def main() -> int:
    pylupdate = shutil.which("pylupdate5")
    if pylupdate is None:
        print("pylupdate5 not found: install PyQt5 (pip install -r requirements.txt).")
        return 1

    ts_files = [TRANSLATIONS / f"rocktstand_{code}.ts" for code in LANGUAGES]
    TRANSLATIONS.mkdir(exist_ok=True)
    sources = [str(path.relative_to(REPO_ROOT)) for path in source_files()]
    targets = [str(path.relative_to(REPO_ROOT)) for path in ts_files]
    subprocess.run(
        [pylupdate, "-noobsolete", *sources, "-ts", *targets], check=True, cwd=REPO_ROOT
    )

    lrelease = find_lrelease()
    if lrelease is None:
        print("lrelease not found: install Qt (Qt Linguist) or set LRELEASE to its path.")
        return 1
    for ts_file in ts_files:
        subprocess.run([lrelease, str(ts_file), "-qm", str(ts_file.with_suffix(".qm"))], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
