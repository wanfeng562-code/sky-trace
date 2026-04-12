import sys

from PySide6.QtWidgets import QApplication

from app.backend_manager import BackendManager
from app.window import MainWindow


def main() -> int:
    """Desktop entrypoint.

    TODO: Add splash screen and startup checks (ports, config, dependencies).
    """

    backend = BackendManager()
    backend.start()

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    exit_code = app.exec()
    backend.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
