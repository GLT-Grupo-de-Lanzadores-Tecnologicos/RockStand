"""User interface language: Qt translators and the saved language choice.

Source strings in the code and in ``main_window.ui`` are in English. Other
languages come from Qt Linguist files in ``translations/`` (``.ts`` is the
editable source, ``.qm`` the compiled file loaded at runtime). See
``docs/translations.md`` for how to update them.

The language is chosen before the main window is built, so a change made
from the Language menu applies the next time the application starts.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QCoreApplication, QLibraryInfo, QLocale, QSettings, QTranslator

from resources import TRANSLATIONS_DIR, resource_path

DEFAULT_LANGUAGE = "en"
# Language code -> name shown in the menu (always in its own language).
LANGUAGES = {"en": "English", "es": "Español"}

SETTINGS_ORGANIZATION = "GLT UTN Haedo"
SETTINGS_APPLICATION = "RocktStand"
LANGUAGE_SETTING_KEY = "ui/language"

TRANSLATION_FILE_FORMAT = TRANSLATIONS_DIR + "/rocktstand_{code}.qm"

# Keeps the installed translators alive: Qt does not take ownership of them.
_installed: list[QTranslator] = []
_active_language = DEFAULT_LANGUAGE


def _settings() -> QSettings:
    return QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)


def system_language() -> str:
    """The system UI language if it is supported, otherwise English."""
    for name in QLocale.system().uiLanguages():
        code = name.split("-")[0].split("_")[0].lower()
        if code in LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def saved_language() -> Optional[str]:
    value = _settings().value(LANGUAGE_SETTING_KEY)
    return value if value in LANGUAGES else None


def save_language(code: str) -> None:
    if code not in LANGUAGES:
        raise ValueError(f"Unsupported language: {code}")
    _settings().setValue(LANGUAGE_SETTING_KEY, code)


def startup_language() -> str:
    """The language chosen in the menu, or the system language the first time."""
    return saved_language() or system_language()


def active_language() -> str:
    """The language whose translations are currently installed."""
    return _active_language


def install_translators(app: QCoreApplication, code: str) -> bool:
    """Load the application and Qt translations for ``code`` into ``app``.

    English needs no translator. Returns False if the application translation
    could not be loaded (the interface then stays in English).
    """
    global _active_language
    remove_translators(app)
    if code == DEFAULT_LANGUAGE or code not in LANGUAGES:
        return code == DEFAULT_LANGUAGE

    app_translator = QTranslator()
    if not app_translator.load(resource_path(TRANSLATION_FILE_FORMAT.format(code=code))):
        return False
    _install(app, app_translator)
    _active_language = code

    # Qt's own strings: standard buttons (OK, Cancel...) and file dialogs.
    qt_translator = QTranslator()
    if qt_translator.load(f"qtbase_{code}", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        _install(app, qt_translator)
    return True


def remove_translators(app: QCoreApplication) -> None:
    global _active_language
    _active_language = DEFAULT_LANGUAGE
    while _installed:
        app.removeTranslator(_installed.pop())


def _install(app: QCoreApplication, translator: QTranslator) -> None:
    app.installTranslator(translator)
    _installed.append(translator)
