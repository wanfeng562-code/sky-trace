from PySide6.QtCore import QObject, Signal, Slot


class AppBridge(QObject):
    """Qt WebChannel bridge exposed to the Vue frontend.

    TODO: Implement settings IO, export features and diagnostics bridge methods.
    """

    backendStatusChanged = Signal(str)

    @Slot(result=str)
    def getAppVersion(self) -> str:
        return "0.1.0"
