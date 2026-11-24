# Translations

The user interface is written in English and translated with Qt's standard
tools (Qt Linguist). Spanish is the only translation for now.

| File                                 | Purpose                                            |
| ------------------------------------ | -------------------------------------------------- |
| `src/translations/rocktstand_es.ts`  | Editable translation source (XML, Qt Linguist)     |
| `src/translations/rocktstand_es.qm`  | Compiled file loaded at runtime and bundled in the `.exe` |
| `tools/update_translations.py`       | Runs `pylupdate5` and `lrelease`                   |
| `src/i18n.py`                        | Installs the translators and saves the language choice |

Both the `.ts` and the `.qm` are committed, so running the application needs
no Qt tools.

## Writing translatable code

- Inside a `QObject` subclass (windows, dialogs, the serial worker) use
  `self.tr("Text")`. The context is the class name.
- Elsewhere use `QCoreApplication.translate("Context", "Text")`.
- For constants defined at module level, mark the text with
  `QT_TRANSLATE_NOOP("Context", "Text")` and translate it where it is shown.
  `services/calibration_service.py` defines its own no-op `QT_TRANSLATE_NOOP`
  so it stays free of Qt imports.
- Never use f-strings for translated text: `pylupdate5` cannot read them.
  Write `self.tr("Connected to {0}").format(port)`.
- Do not end a `tr` / `translate` / `QT_TRANSLATE_NOOP` call with a trailing
  comma: `pylupdate5` silently skips it.
- Strings in `main_window.ui` are translated automatically. Mark values that
  must not change (numbers, units) with `notr="true"` in Qt Designer.
- Units (`N`, `kgf`, `gf`) and the header of exported `.txt` files are not
  translated: the file format must stay the same.

## Updating the translations

1. Add or change strings in the code or the `.ui` file.
2. Run `python tools/update_translations.py`. New strings are added to the
   `.ts` file as *unfinished*; existing translations are kept.
3. Open `src/translations/rocktstand_es.ts` with Qt Linguist, translate the
   unfinished entries and mark them as done.
4. Run `python tools/update_translations.py` again to compile the `.qm`.
5. Run the tests: `tests/test_translations.py` fails if any entry is unfinished.

`lrelease` comes with a Qt installation (it is not part of PyQt5). The script
finds it in `PATH`, in the `LRELEASE` environment variable, or under `C:\Qt`.
A `.qm` built by Qt 6's `lrelease` loads fine in PyQt5.

## Adding a language

1. Add the code to `LANGUAGES` in `tools/update_translations.py` and in
   `src/i18n.py`, and add a menu action in `main_window.ui` (its text is the
   language name in that language, with `notr="true"`).
2. Register the action in `MainWindow._setup_language_menu`.
3. Run the update steps above, and add the new `.qm` to `DATA_FILES` in
   `build_exe.py`.
