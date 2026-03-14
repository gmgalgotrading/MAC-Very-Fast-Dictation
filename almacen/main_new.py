import os
os.environ["QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM"] = "1"

import time
from datetime import datetime
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
import numpy as np
import threading
import re
import subprocess  
from modules.stt import transcribe
from modules.ui import Notification
from modules.mac_paster import paste_text_natively, copiar_al_portapapeles, leer_del_portapapeles
from modules.llm import estructurar_texto_con_ia
from modules.vad import aislar_voz_humana 
from modules.stream_overlay import StreamOverlay  # NUEVO: Importamos la ventana fantasma
import sys
import signal
from PySide6.QtCore import QObject, Signal, Qt

# --- Configuration ---
DOUBLE_PRESS_INTERVAL = 0.3  
SAMPLE_RATE = 16000  
CHANNELS = 1  
OUTPUT_FILENAME_TEMPLATE = "recording.wav"
FRAMES_PER_BUFFER = 1024

# --- State ---
last_key_press_time = 0
last_alt_press_time = 0  
is_recording = False
audio_frames = []
listener_thread = None
notification = None
keyboard_listener = None
shutdown_requested = False
shutdown_in_progress = False
target_app_name = None  

class UICommunicator(QObject):
    show_recording_signal = Signal()
    show_processing_signal = Signal()
    show_structuring_signal = Signal()  
    hide_signal = Signal()
    quit_signal = Signal()
    
    # Señales para controlar la ventana fantasma
    show_stream_signal = Signal()
    hide_stream_signal = Signal()
    update_stream_signal = Signal(str)

ui_comm = None

# --- Función de CAJA NEGRA (Logs Clínicos) ---
def guardar_log(texto_bruto, texto_estructurado, modo):
    try:
        if not os.path.exists("logs"):
            os.makedirs("logs")
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H:%M:%S")
        with open(f"logs/log_{fecha_hoy}.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\nFECHA/HORA: {fecha_hoy} {hora_actual}\nMODO: {modo.upper()}\n{'-'*60}\nTEXTO ORIGINAL:\n{texto_bruto}\n{'-'*60}\nRESULTADO IA:\n{texto_estructurado}\n{'='*60}\n")
    except Exception as e:
        print(f"⚠️ Error al guardar el log clínico: {e}")

# --- Funciones de SO (macOS) ---
def get_active_app_name():
    if sys.platform == "darwin":
        try:
            result = subprocess.run(['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            pass
    return None

def activate_app(app_name):
    if sys.platform == "darwin" and app_name:
        try:
            subprocess.run(['osascript', '-e', f'tell application "{app_name}" to activate'], check=True)
            time.sleep(0.3)  
        except Exception:
            pass

def notify_mac(message, title="Very Fast Dictation"):
    subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}" sound name "Glass"'])

def signal_handler(sig, frame):
    global shutdown_requested, is_recording, keyboard_listener, shutdown_in_progress, ui_comm
    if shutdown_in_progress: return
    shutdown_in_progress = True
    print("\nCerrando aplicación...")
    shutdown_requested = True
    if is_recording: stop_recording()
    if keyboard_listener: keyboard_listener.stop()
    if ui_comm: ui_comm.quit_signal.emit()
    sys.exit(0)

def on_press(key):
    global last_key_press_time, last_alt_press_time, is_recording
    try:
        current_time = time.time()
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            if is_recording:
                stop_recording()
            elif current_time - last_key_press_time < DOUBLE_PRESS_INTERVAL:
                start_recording()
            last_key_press_time = current_time
                
        elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            if current_time - last_alt_press_time < DOUBLE_PRESS_INTERVAL and not is_recording:
                handle_clipboard_process(auto_paste=True)
            last_alt_press_time = current_time
    except Exception:
        pass

def record_audio():
    global audio_frames
    audio_frames = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32") as stream:
        while is_recording:
            frames, _ = stream.read(FRAMES_PER_BUFFER)
            audio_frames.append(frames)

def start_recording():
    global is_recording, listener_thread, ui_comm, target_app_name
    if is_recording: return
    target_app_name = get_active_app_name()
    modo_actual = notification.current_mode if notification else "consulta"
    print(f"\n▶ Grabando para [{target_app_name}] en modo [{modo_actual.upper()}]")
    if ui_comm: ui_comm.show_recording_signal.emit()
    is_recording = True
    listener_thread = threading.Thread(target=record_audio)
    listener_thread.start()

def process_text_direct(texto_bruto, auto_paste=False):
    global ui_comm, notification, target_app_name
    if not texto_bruto or len(texto_bruto.strip()) < 10: return

    modo_seleccionado = notification.current_mode if notification else "consulta"
    if ui_comm: ui_comm.show_structuring_signal.emit()
    
    # Callback que envía los datos a la ventana flotante
    def callback_stream(chunk):
        if ui_comm: ui_comm.update_stream_signal.emit(chunk)

    if ui_comm: ui_comm.show_stream_signal.emit() # Mostramos la ventana
    
    texto_final = estructurar_texto_con_ia(texto_bruto, modo=modo_seleccionado, stream_callback=callback_stream)
    
    if ui_comm: ui_comm.hide_stream_signal.emit() # Ocultamos la ventana al terminar
    
    guardar_log(texto_bruto, texto_final, modo_seleccionado)
    
    if auto_paste:
        if target_app_name: activate_app(target_app_name)
        try: paste_text_natively(texto_final + "\n")
        except Exception as e: print(e)
    else:
        try:
            copiar_al_portapapeles(texto_final + "\n")
            notify_mac("✅ IA completada. ¡Lista para pegar (Cmd+V)!")
        except Exception as e: print(e)

    if ui_comm: ui_comm.hide_signal.emit()


def process_audio_file(file_path, is_external=False):
    global ui_comm, target_app_name, notification
    if ui_comm: ui_comm.show_processing_signal.emit()

    transcript = transcribe(file_path)
    if transcript:
        texto_limpio = re.sub(r'[\u4e00-\u9fff]+', '', transcript).strip()
        texto_limpio = re.sub(r'(.)\1{10,}', '', texto_limpio)
        
        if len(texto_limpio) > 1:
            modo_seleccionado = notification.current_mode if notification else "consulta"
            if ui_comm: ui_comm.show_structuring_signal.emit()
            
            # Callback que envía los datos a la ventana flotante
            def callback_stream(chunk):
                if ui_comm: ui_comm.update_stream_signal.emit(chunk)
                
            if ui_comm: ui_comm.show_stream_signal.emit()
            texto_final = estructurar_texto_con_ia(texto_limpio, modo=modo_seleccionado, stream_callback=callback_stream)
            if ui_comm: ui_comm.hide_stream_signal.emit()
            
            guardar_log(texto_limpio, texto_final, modo_seleccionado)
            
            if not is_external:
                if target_app_name: activate_app(target_app_name)
                try: paste_text_natively(texto_final + "\n")
                except Exception as e: print(e)
            else:
                try:
                    copiar_al_portapapeles(texto_final + "\n")
                    notify_mac("✅ IA completada. ¡Lista para pegar (Cmd+V)!")
                except Exception as e: print(e)
    
    if ui_comm: ui_comm.hide_signal.emit()

def stop_recording():
    global is_recording, listener_thread, ui_comm, target_app_name
    if not is_recording: return
    is_recording = False
    if listener_thread: listener_thread.join()

    if audio_frames:
        recording = np.concatenate(audio_frames, axis=0).flatten()
        recording_limpia = aislar_voz_humana(recording, SAMPLE_RATE)
        if recording_limpia is None or len(recording_limpia) < (SAMPLE_RATE * 0.5):
            if ui_comm: ui_comm.hide_signal.emit()
            return
        sf.write(OUTPUT_FILENAME_TEMPLATE, recording_limpia, SAMPLE_RATE)
        process_audio_file(OUTPUT_FILENAME_TEMPLATE, is_external=False)

def handle_audio_file_selected(file_path):
    threading.Thread(target=process_audio_file, args=(file_path, True), daemon=True).start()

def handle_text_file_selected(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            threading.Thread(target=process_text_direct, args=(file.read(), False), daemon=True).start()
    except Exception as e: print(e)

def handle_clipboard_process(auto_paste=False):
    global target_app_name
    target_app_name = get_active_app_name()
    texto_portapapeles = leer_del_portapapeles()
    if texto_portapapeles:
        threading.Thread(target=process_text_direct, args=(texto_portapapeles, auto_paste), daemon=True).start()
    else:
        notify_mac("⚠️ El portapapeles está vacío o no contiene texto.")

def check_shutdown_requested():
    return shutdown_requested

def main():
    global notification, keyboard_listener, ui_comm

    signal.signal(signal.SIGINT, signal_handler)
    
    notification = Notification(
        shutdown_callback=check_shutdown_requested,
        file_selected_callback=handle_audio_file_selected,
        text_file_selected_callback=handle_text_file_selected,
        clipboard_process_callback=handle_clipboard_process
    )

    ui_comm = UICommunicator()
    ui_comm.show_recording_signal.connect(notification.show_recording)
    ui_comm.show_processing_signal.connect(notification.show_processing)
    ui_comm.show_structuring_signal.connect(notification.show_structuring) 
    ui_comm.hide_signal.connect(notification.hide)
    ui_comm.quit_signal.connect(notification.quit)

    # Conectar y mantener viva la Ventana Fantasma
    stream_overlay = StreamOverlay()
    ui_comm.show_stream_signal.connect(stream_overlay.clear_and_show)
    ui_comm.hide_stream_signal.connect(stream_overlay.hide)
    ui_comm.update_stream_signal.connect(stream_overlay.append_text)

    try:
        notification.setAttribute(Qt.WA_ShowWithoutActivating)
        notification.setWindowFlags(notification.windowFlags() | Qt.WindowDoesNotAcceptFocus | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
    except Exception:
        pass

    print("=== VERY FAST DICTATION (MEDICAL EDITION) ===")
    print("Aplicación lista. Interfaz de Ventana Fantasma activada.")
    
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    try:
        notification.app.exec()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()