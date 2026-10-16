from __future__ import annotations

import os

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
        # Browser keys need an authorized HTTP origin; file:// has no domain.
        # Start Vite (or a local production preview) before opening the wrapper.
        frontend_url = os.environ.get("SKYTRACE_FRONTEND_URL", "").strip() or "http://127.0.0.1:5173"
        self.view.load(QUrl(frontend_url))
