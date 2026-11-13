# Changelog

## v0.3.0 - 2026-11-13

Repository clean-up for publication by GLT UTN Haedo.

- Project renamed to **RocktStand - Rocket Stand Test Software**.
- User interface, documentation, comments and messages translated to English.
  The exported `.txt` format is unchanged.
- GLT logo added to the side panel, the window icon and the executable icon.
- The window title shows the version.
- Recordings are flushed to disk after every sample.
- Code reorganised for readability: unit conversion, session recording and the
  plot axis moved out of the main window; dead code removed (`ConfigDialog`,
  `ForceConversionService`, the unused root `ui/` stub).
- Fixed: the **Calibrate** button crashed after closing the wizard
  (`QDialog` was not imported).
- Fixed: Y-axis labels that were multiples of ten lost their trailing zeros
  (`100` was shown as `1`).
- The X range and Delta t read-outs are now shown while a range is selected.
- The side panel scrolls when the window is shorter than its content.
- Closing the window now waits for the serial thread to stop.
- Tests run from the repository root and cover the serial worker and the UI.
- Sample measurement logs removed from the repository; log file patterns added
  to `.gitignore`.
- Documentation rewritten from the code; the outdated v2 protocol proposals
  were removed.
- Added `build_exe.py` to build the Windows executable.

## v0.2.0 - 2026-04-29

Functional improvements on top of `v0.1.0`:

- Button to pause and resume the reading of measurements.
- Units and plot settings embedded in the right-hand panel.
- Load cell type setting (tension / compression).

## v0.1.0 - 2026-04-28

First release:

- PyQt5 desktop application for force measurement over a serial port.
- Real-time plot with pyqtgraph.
- Software tare, calibration, and full-session or range export to TXT.
- Service layer covered by unit tests in `tests/`.
