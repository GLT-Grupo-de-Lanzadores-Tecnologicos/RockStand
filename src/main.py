"""RocktStand entry point."""

import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from resources import LOGO_PNG, resource_path
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path(LOGO_PNG)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
