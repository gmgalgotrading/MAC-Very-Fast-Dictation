import os
os.environ["QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM"] = "1"

import time
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
import sys
import signal
from PySide6.QtCore import QObject, Signal, Qt

# --- Configuration ---
DOUBLE_PRESS_INTERVAL = 0.3  
SAMPLE_RATE = 44100  
CHANNELS = 1  
OUTPUT_FILENAME_TEMPLATE = "recording.wav"
FRAMES_PER_BUFFER = 1024
SILENCE_THRESHOLD = 0.001  

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

ui_comm = None

# --- Funciones de Control de Ventanas y Notificaciones (macOS) ---
def get_active_app_name():
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True, text=True, check=True
            )
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
    """Lanza una notificación nativa en el centro de notificaciones del Mac."""
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(['osascript', '-e', script])

def signal_handler(sig, frame):
    global shutdown_requested, is_recording, keyboard_listener, notification, shutdown_in_progress, ui_comm
    if shutdown_in_progress:
        return
    shutdown_in_progress = True
    print("\nCerrando aplicación...")
    shutdown_requested = True

    if is_recording:
        stop_recording()
    if keyboard_listener:
        keyboard_listener.stop()
    if ui_comm:
        ui_comm.quit_signal.emit()
    sys.exit(0)

def on_press(key):
    global last_key_press_time, last_alt_press_time, is_recording, audio_frames, target_app_name
    try:
        current_time = time.time()
        
        # --- LÓGICA 1: Doble Ctrl para el Micrófono ---
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            time_since_last_press = current_time - last_key_press_time
            last_key_press_time = current_time

            if is_recording:
                stop_recording()
            elif time_since_last_press < DOUBLE_PRESS_INTERVAL:
                start_recording()
                
        # --- LÓGICA 2: Doble Option/Alt para el Portapapeles ---
        elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            time_since_last_alt = current_time - last_alt_press_time
            last_alt_press_time = current_time
            
            if time_since_last_alt < DOUBLE_PRESS_INTERVAL:
                if not is_recording:
                    target_app_name = get_active_app_name()
                    print(f"\n⌨️ Atajo detectado: Doble Option/Alt. Procesando portapapeles para [{target_app_name}]...")
                    # Le pasamos auto_paste=True para que pegue automáticamente al terminar
                    handle_clipboard_process(auto_paste=True)
    except Exception as e:
        pass

def record_audio():
    global audio_frames
    audio_frames = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32") as stream:
        while is_recording:
            frames, overflowed = stream.read(FRAMES_PER_BUFFER)
            audio_frames.append(frames)

def start_recording():
    global is_recording, listener_thread, ui_comm, target_app_name
    if is_recording:
        return
    
    target_app_name = get_active_app_name()
    modo_actual = notification.current_mode if notification else "consulta"
    print(f"\n▶ Grabando para [{target_app_name}] en modo [{modo_actual.upper()}]")
    
    if ui_comm:
        ui_comm.show_recording_signal.emit()
        
    is_recording = True
    listener_thread = threading.Thread(target=record_audio)
    listener_thread.start()

def process_text_direct(texto_bruto, auto_paste=False):
    """Procesa directamente un texto saltándose la fase de transcripción de Whisper."""
    global ui_comm, notification, target_app_name
    
    if not texto_bruto or len(texto_bruto.strip()) < 10:
        print("❌ El texto es demasiado corto o está vacío. Abortando.")
        return

    print(f"\n\033[92m--- TEXTO DE ENTRADA (DIRECTO) ---\n{texto_bruto[:300]}...\n[...]\n----------------------------------\033[0m\n")

    modo_seleccionado = notification.current_mode if notification else "consulta"
    print(f"🧠 Fase 2: Estructurando texto con IA (Modo: {modo_seleccionado})...")
    
    if ui_comm:
        ui_comm.show_structuring_signal.emit()
    
    start_time_p2 = time.time()
    texto_final = estructurar_texto_con_ia(texto_bruto, modo=modo_seleccionado)
    elapsed_p2 = time.time() - start_time_p2
    
    print(f"⏱️ [Fase 2 completada en {elapsed_p2:.2f} segundos]")
    
    if auto_paste:
        print("📋 Texto procesado. Pegando automáticamente en la aplicación destino...")
        if target_app_name:
            print(f"Saltando de vuelta a: {target_app_name}")
            activate_app(target_app_name)
        try:
            paste_text_natively(texto_final + "\n")
        except Exception as e:
            print(f"Error nativo al pegar: {e}")
    else:
        print("📋 Texto procesado. Copiando al portapapeles...")
        try:
            copiar_al_portapapeles(texto_final + "\n")
            notify_mac("✅ IA completada. ¡El texto estructurado está listo para pegar (Cmd+V)!")
        except Exception as e:
            print(f"Error al copiar al portapapeles: {e}")

    if ui_comm:
        ui_comm.hide_signal.emit()


def process_audio_file(file_path, is_external=False):
    """Procesa audios (fase 1 Whisper + fase 2 LLM)."""
    global ui_comm, target_app_name, notification
    
    origen = "Externo" if is_external else "Micrófono"
    print(f"⏳ Fase 1: Transcribiendo con Whisper ({origen})...")
    if ui_comm:
        ui_comm.show_processing_signal.emit()

    start_time_p1 = time.time()
    transcript = transcribe(file_path)
    elapsed_p1 = time.time() - start_time_p1
    print(f"⏱️ [Fase 1 completada en {elapsed_p1:.2f} segundos]")
    
    if transcript:
        print(f"\n\033[92m--- TRANSCRIPCIÓN BRUTA (WHISPER) ---\n{transcript}\n-------------------------------------\033[0m\n")
        
        texto_limpio = re.sub(r'[\u4e00-\u9fff]+', '', transcript).strip()
        texto_limpio = re.sub(r'(.)\1{10,}', '', texto_limpio)
        texto_lower = texto_limpio.lower().strip()
        
        alucinaciones_exactas = [
            "anatomía y patología", "anatomía y patología.", "anatomía y patología:",
            "decordim please control to end", "recording please control to end",
            "subtítulos realizados por la comunidad de amara.org", "gracias."
        ]
        
        es_alucinacion = texto_lower in alucinaciones_exactas
        
        if not es_alucinacion and len(texto_limpio) > 1:
            modo_seleccionado = notification.current_mode if notification else "consulta"
            print(f"🧠 Fase 2: Estructurando texto con IA (Modo: {modo_seleccionado})...")
            
            if ui_comm:
                ui_comm.show_structuring_signal.emit()
            
            start_time_p2 = time.time()
            texto_final = estructurar_texto_con_ia(texto_limpio, modo=modo_seleccionado)
            elapsed_p2 = time.time() - start_time_p2
            print(f"⏱️ [Fase 2 completada en {elapsed_p2:.2f} segundos]")
            
            if not is_external:
                if target_app_name:
                    print(f"Saltando de vuelta a: {target_app_name}")
                    activate_app(target_app_name)
                try:
                    paste_text_natively(texto_final + "\n")
                except Exception as e:
                    print(f"Error nativo al pegar: {e}")
            else:
                print("📋 Archivo procesado. Copiando al portapapeles...")
                try:
                    copiar_al_portapapeles(texto_final + "\n")
                    notify_mac("✅ IA completada. ¡El texto está listo para pegar (Cmd+V)!")
                except Exception as e:
                    print(f"Error al copiar al portapapeles: {e}")
    
    if ui_comm:
        ui_comm.hide_signal.emit()

def stop_recording():
    global is_recording, listener_thread, ui_comm, target_app_name
    if not is_recording:
        return

    print("⏹ Grabación detenida. Evaluando audio...")
    is_recording = False
    if listener_thread:
        listener_thread.join()

    if audio_frames:
        recording = np.concatenate(audio_frames, axis=0)
        
        rms = np.sqrt(np.mean(recording**2))
        print(f"🔊 Nivel de audio registrado: {rms:.4f}")
        
        if rms < SILENCE_THRESHOLD:
            print("❌ Silencio absoluto detectado. Abortando.")
            if ui_comm:
                ui_comm.hide_signal.emit()
            return

        filename = OUTPUT_FILENAME_TEMPLATE
        sf.write(filename, recording, SAMPLE_RATE)
        
        process_audio_file(filename, is_external=False)

def handle_audio_file_selected(file_path):
    print(f"\n📂 Iniciando procesamiento de AUDIO en hilo secundario: {file_path}")
    threading.Thread(target=process_audio_file, args=(file_path, True), daemon=True).start()

def handle_text_file_selected(file_path):
    print(f"\n📄 Leyendo archivo de TEXTO: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            texto_bruto = file.read()
        # Los archivos subidos a mano no se auto-pegan, solo van al portapapeles
        threading.Thread(target=process_text_direct, args=(texto_bruto, False), daemon=True).start()
    except Exception as e:
        print(f"❌ Error al leer el archivo de texto: {e}")

def handle_clipboard_process(auto_paste=False):
    texto_portapapeles = leer_del_portapapeles()
    if texto_portapapeles:
        print("\n📋 Texto recuperado del portapapeles con éxito.")
        threading.Thread(target=process_text_direct, args=(texto_portapapeles, auto_paste), daemon=True).start()
    else:
        print("\n❌ El portapapeles está vacío o no contiene texto.")
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

    try:
        notification.setAttribute(Qt.WA_ShowWithoutActivating)
        notification.setWindowFlags(notification.windowFlags() | Qt.WindowDoesNotAcceptFocus | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
    except Exception:
        pass

    print("=== VERY FAST DICTATION (MEDICAL EDITION) ===")
    print("Aplicación lista. Soporte de Audio, Archivos de Texto y Portapapeles activado.")
    print("Atajos activos:")
    print("  - Doble Ctrl: Grabar audio (Auto-pega el resultado)")
    print("  - Doble Option (Alt): Procesar texto copiado (Auto-pega el resultado)")
    
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    try:
        notification.app.exec()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()