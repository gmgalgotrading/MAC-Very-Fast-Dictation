import sys
from PySide6.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QMetaObject, QTimer
from PySide6.QtGui import QIcon, QAction

class Notification:
    """Widget de notificación y menú de barra superior (System Tray)."""

    def __init__(self, shutdown_callback=None):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

        icon_path = "images/icon.png"
        self.app.setWindowIcon(QIcon(icon_path))

        self.widget = QLabel("")
        self.widget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.ToolTip)
        
        # --- ESTADO INICIAL DEL MODO ---
        self.current_mode = "consulta" 

        # --- CREACIÓN DEL MENÚ SUPERIOR ---
        self._setup_tray_icon(icon_path)

        self.shutdown_callback = shutdown_callback
        if shutdown_callback:
            self.timer = QTimer()
            self.timer.timeout.connect(self._check_shutdown)
            self.timer.start(200)

    def _setup_tray_icon(self, icon_path):
        """Configura el icono y el menú desplegable en la barra de menú de macOS."""
        self.tray_icon = QSystemTrayIcon(self.app)
        self.tray_icon.setIcon(QIcon(icon_path))

        self.menu = QMenu()

        # Opción 1: Consulta Clínica
        self.action_consulta = QAction("Modo: Consulta Clínica", self.menu)
        self.action_consulta.setCheckable(True)
        self.action_consulta.setChecked(True)
        self.action_consulta.triggered.connect(lambda: self.set_mode("consulta"))
        self.menu.addAction(self.action_consulta)

        # Opción 2: Conferencia Médica
        self.action_conferencia = QAction("Modo: Conferencia", self.menu)
        self.action_conferencia.setCheckable(True)
        self.action_conferencia.setChecked(False)
        self.action_conferencia.triggered.connect(lambda: self.set_mode("conferencia"))
        self.menu.addAction(self.action_conferencia)

        self.menu.addSeparator()

        # Opción: Salir
        self.action_quit = QAction("Salir de Very Fast Dictation", self.menu)
        self.action_quit.triggered.connect(self.quit)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def set_mode(self, mode):
        """Actualiza el modo interno y cambia el 'tick' visual en el menú."""
        self.current_mode = mode
        if mode == "consulta":
            self.action_consulta.setChecked(True)
            self.action_conferencia.setChecked(False)
        else:
            self.action_consulta.setChecked(False)
            self.action_conferencia.setChecked(True)
        print(f"\n⚙️ Modo cambiado a: {mode.upper()}")

    def _position_top_right(self):
        """Posiciona el cartel en la esquina superior derecha."""
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
        """Muestra el aviso naranja para la fase de transcripción con Whisper."""
        self.widget.setText("⏳ Transcribiendo audio...")
        self.widget.setStyleSheet(
            "background-color: #f39c12; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def show_structuring(self):
        """Muestra el aviso morado indicando la fase de IA estructurando el texto."""
        modo_texto = "Consulta" if self.current_mode == "consulta" else "Conferencia"
        self.widget.setText(f"🧠 Estructurando la transcripción con IA ({modo_texto})...")
        self.widget.setStyleSheet(
            "background-color: #8e44ad; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
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