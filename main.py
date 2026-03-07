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
import pyperclip
import sys
import signal
from PySide6.QtCore import QObject, Signal, Qt

# --- Configuration ---
DOUBLE_PRESS_INTERVAL = 0.3  # Seconds
SAMPLE_RATE = 44100  # Hertz
CHANNELS = 1  # Mono
OUTPUT_FILENAME_TEMPLATE = "recording.wav"
FRAMES_PER_BUFFER = 1024
SILENCE_THRESHOLD = 0.001  # BAJADO DRÁSTICAMENTE: 0.001 capta hasta susurros

# --- State ---
last_key_press_time = 0
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
    hide_signal = Signal()
    quit_signal = Signal()

ui_comm = None

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
            time.sleep(0.2)
        except Exception:
            pass

def get_timestamp_str():
    return time.strftime("%Y%m%d_%H%M%S")

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
    global last_key_press_time, is_recording, audio_frames
    try:
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            current_time = time.time()
            time_since_last_press = current_time - last_key_press_time
            last_key_press_time = current_time

            if is_recording:
                stop_recording()
            elif time_since_last_press < DOUBLE_PRESS_INTERVAL:
                start_recording()
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
    print(f"\n▶ Doble pulsación. Grabando para la app: {target_app_name}")
    
    if ui_comm:
        ui_comm.show_recording_signal.emit()
        
    is_recording = True
    listener_thread = threading.Thread(target=record_audio)
    listener_thread.start()

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
        
        # 1. BLOQUEO DE SILENCIO CON MEDIDOR VISUAL
        rms = np.sqrt(np.mean(recording**2))
        print(f"🔊 Nivel de audio registrado: {rms:.4f}")
        
        if rms < SILENCE_THRESHOLD:
            print("❌ Silencio absoluto detectado. Abortando transcripción para evitar alucinaciones.")
            if ui_comm:
                ui_comm.hide_signal.emit()
            return

        print("⏳ Procesando con Whisper...")
        if ui_comm:
            ui_comm.show_processing_signal.emit()

        filename = OUTPUT_FILENAME_TEMPLATE
        sf.write(filename, recording, SAMPLE_RATE)
        transcript = transcribe(filename)
        
        if transcript:
            texto_limpio = re.sub(r'[\u4e00-\u9fff]+', '', transcript).strip()
            texto_limpio = re.sub(r'(.)\1{10,}', '', texto_limpio)
            
            texto_lower = texto_limpio.lower().strip()
            
            # 2. FILTRO DE ALUCINACIONES PURAS:
            alucinaciones_exactas = [
                "anatomía y patología", "anatomía y patología.", "anatomía y patología:",
                "decordim please control to end", "recording please control to end",
                "subtítulos realizados por la comunidad de amara.org", "gracias."
            ]
            
            es_alucinacion = texto_lower in alucinaciones_exactas
            
            if not es_alucinacion and len(texto_limpio) > 1:
                if target_app_name:
                    activate_app(target_app_name)
                paste_text(texto_limpio + " ")
    
    if ui_comm:
        ui_comm.hide_signal.emit()

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.1) # Pequeña pausa para asegurar que el portapapeles de Mac se ha actualizado
    try:
        controller = keyboard.Controller()
        if sys.platform == "darwin":
            with controller.pressed(keyboard.Key.cmd):
                controller.press("v")
                controller.release("v")
        else:
            with controller.pressed(keyboard.Key.ctrl):
                controller.press("v")
                controller.release("v")
        print("✅ Texto pegado con éxito.")
    except Exception as e:
        print("Error pegando: ", e)

def check_shutdown_requested():
    return shutdown_requested

def main():
    global notification, keyboard_listener, ui_comm

    signal.signal(signal.SIGINT, signal_handler)
    notification = Notification(shutdown_callback=check_shutdown_requested)

    ui_comm = UICommunicator()
    ui_comm.show_recording_signal.connect(notification.show_recording)
    ui_comm.show_processing_signal.connect(notification.show_processing)
    ui_comm.hide_signal.connect(notification.hide)
    ui_comm.quit_signal.connect(notification.quit)

    try:
        notification.setAttribute(Qt.WA_ShowWithoutActivating)
        notification.setWindowFlags(notification.windowFlags() | Qt.WindowDoesNotAcceptFocus | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
    except Exception:
        pass

    print("=== VERY FAST DICTATION (MEDICAL EDITION) ===")
    print("Aplicación lista.")
    
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    try:
        notification.app.exec()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()