from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

class StreamOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # Banderas para ventana flotante invulnerable
        self.setWindowFlags(
            Qt.ToolTip | 
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.WindowTransparentForInput | 
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Tamaño total máximo de la ventana invisible
        self.setFixedSize(450, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5) 
        
        # CLAVE DE DISEÑO: Forzamos a que los elementos nazcan pegados arriba
        layout.setAlignment(Qt.AlignTop) 
        
        # --- CABECERA NARANJA DEL SPINNER ---
        self.spinner_label = QLabel("")
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 210);
                color: #f39c12; 
                font-family: 'Courier New';
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border: 1px solid rgba(100, 100, 100, 80);
                border-radius: 12px;
            }
        """)
        self.spinner_label.hide()
        layout.addWidget(self.spinner_label)
        
        # --- CAJA NEGRA DEL TEXTO VERDE ---
        self.text_edit = QTextEdit()
        self.text_edit.setFixedSize(450, 540) # Le damos tamaño fijo para que al aparecer ocupe todo
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 20, 20, 210);
                color: #00FF41; 
                font-family: 'Courier New';
                font-size: 13px;
                border: 1px solid rgba(100, 100, 100, 80);
                border-radius: 12px;
                padding: 15px;
            }
        """)
        self.text_edit.hide() # ¡MAGIA! La caja negra empieza invisible
        layout.addWidget(self.text_edit)
        
    def _colocar_en_esquina(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = 170  # Posición rebajada para que no se solape con el cartel morado
        self.move(x, y)
        
    def append_text(self, text):
        """Filtra con seguridad máxima si es un comando de carga o texto real de la IA."""
        
        # 1. Si termina, borramos el cartel naranja
        if "__SPINNER_CLEAR__" in text:
            self.spinner_label.hide()
            return
            
        # 2. Si es una animación, actualizamos el cartel naranja
        if "__SPINNER__" in text:
            texto_limpio = text.replace("__SPINNER__", "").strip()
            self.spinner_label.setText(texto_limpio)
            if self.spinner_label.isHidden():
                self.spinner_label.show()
            return
            
        # 3. ¡LA IA EMPIEZA A ESCRIBIR! Si la caja estaba oculta, la hacemos aparecer de golpe
        if self.text_edit.isHidden():
            self.text_edit.show()
            
        # Insertamos el texto verde matrix
        self.text_edit.insertPlainText(text)
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())
        
    def clear_and_show(self):
        self._colocar_en_esquina()
        self.text_edit.clear()
        self.text_edit.hide() # Nos aseguramos de ocultar la caja negra al iniciar una nueva tarea
        self.spinner_label.hide()
        QTimer.singleShot(300, self.show)