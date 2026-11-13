# Architecture

RocktStand is a PyQt5 application split into three layers. Dependencies only
point downwards.

```text
ui/         widgets and user interaction        (PyQt5, pyqtgraph)
services/   logic without widgets               (unit-tested)
domain_models.py   enums and dataclasses        (standard library only)
```

`src/` is the import root: modules are imported as `services.x` and `ui.x`,
both when running `python src/main.py` and in the tests (`pytest.ini` adds
`src` to the path).

## Data flow of one measurement

```text
Arduino --"1.2345\n"--> SerialWorker (worker thread)
                          parse_line()            services/simple_protocol.py
                          measurement_received(t_s, weight_kg, sequence)
                                  |  Qt signal, delivered on the GUI thread
                                  v
MainWindow.on_measurement
    kgf -> N, sign inversion for compression cells
    MeasurementService.append()   relative time, tare, peak, bounded buffer
    labels updated
    TxtRecorder.write()           only while recording
                                  
QTimer (50 ms) -> MainWindow.refresh_plot -> curve.setData
```

Forces are kept in **newtons** everywhere inside the application. Conversion to
the display unit happens only when a value is shown or written to a file
(`services/unit_conversion.py`).

## Threads

There are two threads:

- **GUI thread**: all widgets, `MeasurementService`, `TxtRecorder`.
- **Serial worker thread**: `SerialWorker.run()`, which owns the serial port.

They communicate only through Qt signals (worker -> GUI) and through a small
command queue (GUI -> worker, `SerialWorker._pending_writes`).
`SerialThreadController` creates and tears down the worker thread and re-emits
its signals, so `MainWindow` never touches the thread directly.

## Modules

### `services/`

| Module                   | Responsibility                                                       |
| ------------------------ | -------------------------------------------------------------------- |
| `serial_worker.py`       | Polling loop, command queue, scale-factor confirmation, thread lifecycle |
| `simple_protocol.py`     | Turn one reply line into `MeasurementLine`, `OkLine` or `ErrorLine`  |
| `serial_port_service.py` | List available ports; never raises, returns an error message instead |
| `measurement_service.py` | Sample buffer (4000 points), relative time, tare offset, peak force  |
| `calibration_service.py` | New scale factor from a known load, with sanity limits               |
| `unit_conversion.py`     | `N` / `kgf` / `gf` conversion; parsing of values such as `"333 gf"`  |
| `txt_export_service.py`  | TXT file format, range export, `TxtRecorder` for live recording      |

### `ui/`

| Module                 | Responsibility                                                    |
| ---------------------- | ----------------------------------------------------------------- |
| `main_window.py`       | Connects the widgets of `main_window.ui` to the services          |
| `main_window.ui`       | Layout, edited with Qt Designer and loaded at runtime with `uic`  |
| `calibrate_dialog.py`  | Five-step calibration wizard                                      |
| `x_range_selection.py` | Draggable band used to choose the time range to export            |
| `plot_axis.py`         | Y axis that prints plain decimals instead of scientific notation  |

### Other

| Module         | Responsibility                                                         |
| -------------- | ---------------------------------------------------------------------- |
| `main.py`      | Creates the `QApplication`, sets the icon, shows the window            |
| `app_info.py`  | Application name, version and organisation (single source of truth)    |
| `resources.py` | Resolves data file paths from source and inside the PyInstaller bundle |

## Design notes

- **Tare is done in software.** The firmware tares once at power-up; the
  **Tare** button stores an offset in `MeasurementService` and does not send
  anything to the Arduino. Clearing the plot keeps the tare.
- **Settings are locked while recording**, so a file never mixes units or signs.
- **Peak force** is the maximum corrected force since the last clear, starting
  from zero (a run with only negative forces reports a peak of `0`).
- **The sample buffer is bounded** to keep plotting fast. Long runs should be
  recorded to a file, which is not affected by the limit.
- **The scale factor is not persisted** by either side; see the README.
