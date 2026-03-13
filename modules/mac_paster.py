from AppKit import NSPasteboard, NSStringPboardType
import Quartz
import time

def copiar_al_portapapeles(texto: str):
    """Escribe el texto en el portapapeles general de macOS de forma nativa."""
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(texto, NSStringPboardType)

def leer_del_portapapeles() -> str:
    """Lee el texto actual del portapapeles general de macOS."""
    pb = NSPasteboard.generalPasteboard()
    texto = pb.stringForType_(NSStringPboardType)
    return texto if texto else ""

def simular_cmd_v():
    """Simula la pulsación física de Cmd + V usando CoreGraphics."""
    # El código virtual para la tecla 'v' en el teclado Mac es 9
    v_keycode = 9

    # 1. Crear el evento de "Tecla V presionada"
    evento_pulsar = Quartz.CGEventCreateKeyboardEvent(None, v_keycode, True)
    Quartz.CGEventSetFlags(evento_pulsar, Quartz.kCGEventFlagMaskCommand)

    # 2. Crear el evento de "Tecla V soltada"
    evento_soltar = Quartz.CGEventCreateKeyboardEvent(None, v_keycode, False)
    Quartz.CGEventSetFlags(evento_soltar, Quartz.kCGEventFlagMaskCommand)

    # 3. Enviar los eventos directamente al sistema
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, evento_pulsar)
    time.sleep(0.05)  # Micro-pausa para que la app médica tenga tiempo de leerlo
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, evento_soltar)

def paste_text_natively(text: str):
    """Función principal a llamar desde el script."""
    copiar_al_portapapeles(text)
    # Damos un instante al SO para que registre el cambio en el portapapeles
    time.sleep(0.1)
    simular_cmd_v()
    print("✅ Texto inyectado vía Quartz.")