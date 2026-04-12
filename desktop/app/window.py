from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from app.bridge import AppBridge


class MainWindow(QMainWindow):
    """Main desktop window hosting the frontend web app."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sky-Trace")
        self.resize(1366, 820)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        # TODO: Extend bridge APIs after frontend-side WebChannel handshake is in place.
        channel = QWebChannel(self.view.page())
        channel.registerObject("AppBridge", AppBridge())
        self.view.page().setWebChannel(channel)

        self._load_frontend()

    def _load_frontend(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        dist_index = project_root / "client" / "dist" / "index.html"

        if dist_index.exists():
            self.view.load(QUrl.fromLocalFile(str(dist_index)))
            return

        # TODO: Read dev URL from env/config instead of hard-coded fallback.
        self.view.load(QUrl("http://localhost:5173"))
