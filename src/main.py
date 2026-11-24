"""RocktStand entry point."""

import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

import i18n
from resources import LOGO_PNG, resource_path
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path(LOGO_PNG)))
    # Before the window is built: the .ui strings are translated while loading.
    i18n.install_translators(app, i18n.startup_language())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
