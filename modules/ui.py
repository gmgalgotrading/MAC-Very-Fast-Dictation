import sys
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QMetaObject, QTimer
from PySide6.QtGui import QIcon

class Notification:
    """Widget de notificación con soporte para múltiples estados."""

    def __init__(self, shutdown_callback=None):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

        icon_path = "images/icon.png"
        self.app.setWindowIcon(QIcon(icon_path))

        self.widget = QLabel("")
        self.widget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.ToolTip)
        
        self.shutdown_callback = shutdown_callback
        if shutdown_callback:
            self.timer = QTimer()
            self.timer.timeout.connect(self._check_shutdown)
            self.timer.start(200)

    def _position_top_right(self):
        """Posiciona el cartel en la esquina superior derecha, respetando la barra de menú."""
        screen = self.app.primaryScreen()
        if screen:
            geom = screen.availableGeometry() 
            margin_x = 20
            margin_y = 20
            self.widget.move(
                geom.x() + geom.width() - self.widget.width() - margin_x,
                geom.y() + margin_y
            )

    def show_recording(self):
        """Muestra el aviso rojo de grabación."""
        self.widget.setText("🎙️ Grabando... (Pulsa Ctrl para parar)")
        self.widget.setStyleSheet(
            "background-color: #d32f2f; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def show_processing(self):
        """Muestra el aviso naranja de procesamiento."""
        self.widget.setText("⏳ Generando transcripción. Espera...")
        self.widget.setStyleSheet(
            "background-color: #f39c12; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def hide(self):
        """Oculta el widget."""
        QMetaObject.invokeMethod(self.widget, "hide", Qt.QueuedConnection)

    def run(self):
        return self.app.exec()

    def _check_shutdown(self):
        if self.shutdown_callback and self.shutdown_callback():
            self.quit()

    def quit(self):
        if hasattr(self, "timer"):
            self.timer.stop()
        if self.app:
            self.app.quit()