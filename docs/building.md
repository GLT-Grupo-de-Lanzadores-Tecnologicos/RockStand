# Testing and building

## Environment

```bash
pip install -r requirements-dev.txt
```

`requirements.txt` holds the runtime dependencies; `requirements-dev.txt` adds
`pytest` and `PyInstaller`.

## Tests

```bash
python -m pytest
```

Run it from the repository root. The suite needs no hardware and no display:

- `tests/test_serial_worker.py` runs the real worker thread against a fake
  serial port that answers like the firmware.
- `tests/test_ui_smoke.py` builds the real windows with Qt's `offscreen`
  platform and drives the main flows (measurements, units, tare, recording,
  range export, calibration).
- The remaining files are plain unit tests of `services/`.

## Windows executable

```bash
python build_exe.py
```

This runs PyInstaller in one-file, windowed mode and produces
`dist/RocktStand.exe` (about 50 MB). The script bundles:

| Source file              | Path inside the bundle |
| ------------------------ | ---------------------- |
| `src/ui/main_window.ui`  | `ui/main_window.ui`    |
| `src/assets/logo.png`    | `assets/logo.png`      |

and uses `src/assets/logo.ico` as the executable icon. At runtime
`src/resources.py` finds these files through `sys._MEIPASS`.

`build/`, `dist/` and `*.spec` are ignored by git: publish the executable as a
GitHub release asset instead of committing it.

If a new data file is added to the application, add it to `DATA_FILES` in
`build_exe.py` and to `src/resources.py`; a file missing from the bundle only
fails when the executable is started.

## Updating the logo

`src/assets/logo.png` must be an opaque RGB PNG (no alpha channel). To
regenerate both assets from a new source image with Pillow:

```python
from PIL import Image

image = Image.open("new_logo.jpeg").convert("RGB")
image.save("src/assets/logo.png", optimize=True)
image.save("src/assets/logo.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
```

## Releasing

1. Update `APP_VERSION` in `src/app_info.py`.
2. Add an entry to `CHANGELOG.md`.
3. Run the tests and build the executable.
4. Tag the commit (`vX.Y.Z`) and attach `dist/RocktStand.exe` to the release.
