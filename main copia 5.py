import os
os.environ["QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM"] = "1"

import time
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
import numpy as np
import threading
import queue
import re  # <--- NUEVA IMPORTACIÓN PARA LIMPIEZA DE TEXTO
from modules.stt import transcribe
from modules.ui import Notification
import pyperclip
import sys
import subprocess
import signal
from PySide6.QtCore import QObject, Signal, Qt

# --- Configuration ---
DOUBLE_PRESS_INTERVAL = 0.3  # Seconds
SAMPLE_RATE = 44100  # Hertz
CHANNELS = 1  # Mono
FRAMES_PER_BUFFER = 1024

# --- Tiempos y Umbrales (Afinados contra alucinaciones) ---
MAX_CHUNK_TIME = 10.0      # Límite estricto
MIN_CHUNK_TIME = 1.5       # MÍNIMO de grabación (evita mandar solo respiraciones cortas)
SILENCE_PAUSE = 1.0        # Corte inteligente
AUTO_STOP_SILENCE = 5.0    # Apagado automático
SILENCE_THRESHOLD = 0.015  # UMBRAL SUBIDO: Ignora más el ruido de fondo y ventiladores

# --- State ---
last_key_press_time = 0
is_recording = False
listener_thread = None
notification = None
keyboard_listener = None
shutdown_requested = False
shutdown_in_progress = False

# --- Hilo de Transcripción Continua ---
transcription_queue = queue.Queue()
transcriber_thread = None

class UICommunicator(QObject):
    show_signal = Signal()
    hide_signal = Signal()
    quit_signal = Signal()

ui_comm = None

def transcription_worker():
    """Procesa el audio en la sombra y filtra las alucinaciones de la IA."""
    # Lista negra de alucinaciones típicas con ruido de fondo
    ALUCINACIONES = ["okay", "yeah", "ok", "thank you", "gracias", "sí", "yes", "ah", "oh", "you", "and"]

    while True:
        task = transcription_queue.get()
        if task is None:
            break
        
        filename = task
        transcript = transcribe(filename)
        
        if transcript:
            texto_limpio = transcript.strip()
            # Quitamos puntos y comas para comparar bien la palabra
            texto_sin_puntuacion = re.sub(r'[^\w\s]', '', texto_limpio.lower()).strip()
            
            # FILTRO: Solo pega si NO es una alucinación y tiene más de 1 letra
            if texto_sin_puntuacion not in ALUCINACIONES and len(texto_sin_puntuacion) > 1:
                paste_text(texto_limpio + " ")
        
        try:
            os.remove(filename)
        except Exception:
            pass
        
        transcription_queue.task_done()

def get_timestamp_str():
    return time.strftime("%Y%m%d_%H%M%S")

def signal_handler(sig, frame):
    global shutdown_requested, is_recording, keyboard_listener, notification, shutdown_in_progress, ui_comm
    if shutdown_in_progress:
        return
    shutdown_in_progress = True
    print("\nShutting down...")
    shutdown_requested = True
    
    if is_recording:
        stop_recording()
    if keyboard_listener:
        keyboard_listener.stop()
    if ui_comm:
        ui_comm.quit_signal.emit()
        
    transcription_queue.put(None)
    sys.exit(0)

def on_press(key):
    global last_key_press_time, is_recording

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
        print(f"An error occurred: {e}")

def record_audio():
    global is_recording, ui_comm
    audio_frames = []
    start_time = time.time()
    silence_frames = 0
    chunk_counter = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32") as stream:
        print("Recording started...")
        while is_recording:
            frames, overflowed = stream.read(FRAMES_PER_BUFFER)
            audio_frames.append(frames)

            rms = np.sqrt(np.mean(frames**2))
            current_time = time.time()

            if rms < SILENCE_THRESHOLD:
                silence_frames += 1
            else:
                silence_frames = 0

            silence_seconds = silence_frames * (FRAMES_PER_BUFFER / SAMPLE_RATE)
            chunk_duration = current_time - start_time

            if silence_seconds >= AUTO_STOP_SILENCE:
                print("\nSin conversación detectada. Apagando micrófono de seguridad...")
                if ui_comm:
                    ui_comm.hide_signal.emit()
                is_recording = False
                break

            # CORTE INTELIGENTE: Requiere superar el MIN_CHUNK_TIME para no mandar suspiros
            if (chunk_duration >= MAX_CHUNK_TIME) or (silence_seconds >= SILENCE_PAUSE and chunk_duration > MIN_CHUNK_TIME):
                if len(audio_frames) > (MIN_CHUNK_TIME * SAMPLE_RATE / FRAMES_PER_BUFFER): 
                    recording = np.concatenate(audio_frames, axis=0)
                    filename = f"chunk_{chunk_counter}_{get_timestamp_str()}.wav"
                    sf.write(filename, recording, SAMPLE_RATE)
                    
                    transcription_queue.put(filename)
                    chunk_counter += 1

                audio_frames = []
                start_time = time.time()

    if len(audio_frames) > (0.5 * SAMPLE_RATE / FRAMES_PER_BUFFER):
        recording = np.concatenate(audio_frames, axis=0)
        filename = f"chunk_final_{get_timestamp_str()}.wav"
        sf.write(filename, recording, SAMPLE_RATE)
        transcription_queue.put(filename)

def start_recording():
    global is_recording, listener_thread, ui_comm
    if is_recording:
        return
    print("Double-press detected. Starting recording.")
    if ui_comm:
        ui_comm.show_signal.emit()
    is_recording = True
    listener_thread = threading.Thread(target=record_audio)
    listener_thread.start()

def stop_recording():
    global is_recording, listener_thread, ui_comm
    if not is_recording:
        return
    print("Stopping recording...")
    if ui_comm:
        ui_comm.hide_signal.emit()
    is_recording = False
    if listener_thread:
        listener_thread.join()

def paste_text(text):
    pyperclip.copy(text)
    if sys.platform == "darwin":
        success = False
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
                capture_output=True, text=True, check=False
            )
            success = result.returncode == 0
        except Exception:
            success = False

        if not success:
            try:
                controller = keyboard.Controller()
                with controller.pressed(keyboard.Key.cmd):
                    controller.press("v")
                    controller.release("v")
                success = True
            except Exception:
                success = False
    else:
        modifier = keyboard.Key.ctrl
        controller = keyboard.Controller()
        with controller.pressed(modifier):
            controller.press("v")
            controller.release("v")
    print("Pasted: " + text)

def check_shutdown_requested():
    return shutdown_requested

def main():
    global notification, keyboard_listener, ui_comm, transcriber_thread

    signal.signal(signal.SIGINT, signal_handler)

    transcriber_thread = threading.Thread(target=transcription_worker, daemon=True)
    transcriber_thread.start()

    notification = Notification(shutdown_callback=check_shutdown_requested)

    ui_comm = UICommunicator()
    ui_comm.show_signal.connect(notification.show)
    ui_comm.hide_signal.connect(notification.hide)
    ui_comm.quit_signal.connect(notification.quit)

    try:
        notification.setAttribute(Qt.WA_ShowWithoutActivating)
        notification.setWindowFlags(notification.windowFlags() | Qt.WindowDoesNotAcceptFocus | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint)
    except Exception:
        pass

    print("Application started.")
    print("Press Ctrl twice quickly to start recording.")
    print("Press Ctrl again to stop.")
    
    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    try:
        notification.app.exec()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()