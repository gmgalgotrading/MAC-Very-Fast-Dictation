import sys
from PySide6.QtWidgets import QApplication, QLabel, QSystemTrayIcon, QMenu, QFileDialog
from PySide6.QtCore import Qt, QMetaObject, QTimer
from PySide6.QtGui import QIcon, QAction

class Notification:
    """Widget de notificación y menú de barra superior (System Tray)."""

    def __init__(self, shutdown_callback=None, file_selected_callback=None, text_file_selected_callback=None, clipboard_process_callback=None):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            
        # Evitamos que se cierre al desaparecer ventanas
        self.app.setQuitOnLastWindowClosed(False)

        icon_path = "images/icon.png"
        self.app.setWindowIcon(QIcon(icon_path))

        self.widget = QLabel("")
        self.widget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.ToolTip)
        
        # --- ESTADOS Y CALLBACKS ---
        self.current_mode = "consulta" 
        self.shutdown_callback = shutdown_callback
        self.file_selected_callback = file_selected_callback 
        self.text_file_selected_callback = text_file_selected_callback
        self.clipboard_process_callback = clipboard_process_callback

        # --- CREACIÓN DEL MENÚ SUPERIOR ---
        self._setup_tray_icon(icon_path)

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

        # Opción 2: Resumen de Historial (NUEVO)
        self.action_historial = QAction("Modo: Resumen de Historial", self.menu)
        self.action_historial.setCheckable(True)
        self.action_historial.setChecked(False)
        self.action_historial.triggered.connect(lambda: self.set_mode("historial"))
        self.menu.addAction(self.action_historial)

        # Opción 3: Conferencia Médica
        self.action_conferencia = QAction("Modo: Conferencia", self.menu)
        self.action_conferencia.setCheckable(True)
        self.action_conferencia.setChecked(False)
        self.action_conferencia.triggered.connect(lambda: self.set_mode("conferencia"))
        self.menu.addAction(self.action_conferencia)

        self.menu.addSeparator()

        # Información del micro (no clickeable)
        self.action_mic = QAction("🎙️ Grabar con micrófono (Doble Ctrl)", self.menu)
        self.action_mic.setEnabled(False) 
        self.menu.addAction(self.action_mic)

        # Subir archivo de audio
        self.action_upload = QAction("🎵 Subir y procesar archivo de AUDIO...", self.menu)
        self.action_upload.triggered.connect(self.open_file_dialog)
        self.menu.addAction(self.action_upload)
        
        self.menu.addSeparator()

        # Subir archivo de texto
        self.action_upload_text = QAction("📄 Subir y procesar archivo de TEXTO...", self.menu)
        self.action_upload_text.triggered.connect(self.open_text_file_dialog)
        self.menu.addAction(self.action_upload_text)

        # Procesar desde portapapeles
        self.action_clipboard = QAction("📋 Procesar PORTAPAPELES (Doble Option/Alt)", self.menu)
        self.action_clipboard.triggered.connect(self._trigger_clipboard)
        self.menu.addAction(self.action_clipboard)

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
            self.action_historial.setChecked(False)
            self.action_conferencia.setChecked(False)
        elif mode == "historial":
            self.action_consulta.setChecked(False)
            self.action_historial.setChecked(True)
            self.action_conferencia.setChecked(False)
        else:
            self.action_consulta.setChecked(False)
            self.action_historial.setChecked(False)
            self.action_conferencia.setChecked(True)
        print(f"\n⚙️ Modo cambiado a: {mode.upper()}")

    def open_file_dialog(self):
        """Abre el buscador de archivos para AUDIO."""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecciona una grabación médica",
            "",
            "Archivos de Audio (*.wav *.mp3 *.m4a)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        
        if file_path and self.file_selected_callback:
            print(f"\n🎵 Archivo de audio seleccionado: {file_path}")
            self.file_selected_callback(file_path)
            
    def open_text_file_dialog(self):
        """Abre el buscador de archivos para TEXTO."""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Selecciona un archivo de texto clínico",
            "",
            "Archivos de Texto (*.txt *.md *.rtf)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        
        if file_path and self.text_file_selected_callback:
            print(f"\n📄 Archivo de texto seleccionado: {file_path}")
            self.text_file_selected_callback(file_path)

    def _trigger_clipboard(self):
        """Dispara el procesamiento del portapapeles."""
        if self.clipboard_process_callback:
            print("\n📋 Intentando procesar desde el portapapeles (vía Menú o Atajo)...")
            self.clipboard_process_callback()

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
        self.widget.setText("🎙️ Grabando... (Pulsa Ctrl para parar)")
        self.widget.setStyleSheet(
            "background-color: #d32f2f; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def show_processing(self):
        self.widget.setText("⏳ Transcribiendo audio...")
        self.widget.setStyleSheet(
            "background-color: #f39c12; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def show_structuring(self):
        modos_nombres = {"consulta": "Consulta", "historial": "Historial", "conferencia": "Conferencia"}
        modo_texto = modos_nombres.get(self.current_mode, "Texto")
        self.widget.setText(f"🧠 Estructurando texto con IA ({modo_texto})...")
        self.widget.setStyleSheet(
            "background-color: #8e44ad; color: white; padding: 15px; border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.widget.adjustSize()
        self._position_top_right()
        QMetaObject.invokeMethod(self.widget, "show", Qt.QueuedConnection)

    def hide(self):
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