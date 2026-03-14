import requests
import json
import re
import threading
import time
import sys
import os

def cargar_glosario_externo():
    ruta_glosario = "diccionario_metaforas.txt"
    if os.path.exists(ruta_glosario):
        try:
            with open(ruta_glosario, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Error al leer el diccionario: {e}")
            return ""
    else:
        print("⚠️ No se encontró el archivo 'diccionario_metaforas.txt'. Trabajando sin glosario.")
        return ""

PROMPTS_SISTEMA = {
    "consulta": """Actúa como un médico especialista y documentalista clínico experto. Tu tarea es analizar la transcripción bruta de una consulta médica y generar un informe clínico estructurado.

🚨 FILTRO DE RELEVANCIA CLÍNICA (¡PASO PREVIO!):
Antes de hacer nada, evalúa el texto bruto. Si la transcripción es una prueba de audio (ej. "un, dos, tres"), ruido de fondo, o NO contiene absolutamente ningún dato médico, síntoma o contexto clínico, ABORTA la generación de la plantilla. Responde ÚNICA Y EXCLUSIVAMENTE con esta frase exacta y no escribas nada más:
"La conversación no contiene datos de entrevista médico-paciente."

🚨 INSTRUCCIÓN CRÍTICA DE DIARIZACIÓN SEMÁNTICA:
La transcripción que vas a leer es un diálogo continuo sin etiquetas de hablantes. Antes de redactar, debes separar e identificar mentalmente los roles basándote estrictamente en el contexto clínico:
- PACIENTE: Es quien describe los síntomas, la intensidad del dolor, los tiempos de evolución y el mecanismo de la lesión.
- DOCTOR: Es quien hace las preguntas, narra la exploración física en voz alta, emite el diagnóstico y propone el tratamiento.
Es VITAL que asignes cada dato al sujeto correcto. No atribuyas dudas del paciente al doctor, ni decisiones del doctor al paciente.

{GLOSARIO_PLACEHOLDER}

Debes generar ESTRICTAMENTE la siguiente estructura utilizando formato Markdown:

### SÍNTESIS PARA LA HISTORIA CLÍNICA
- Antecedentes: 
- Motivo de consulta: 
- Tiempo de evolución: 
- Sintomatología actual: 
- Exploración física: 
- Pruebas complementarias: 
- Diagnóstico: 
- Plan de tratamiento:

---

### Resumen Detallado de la Consulta
**1. Datos del Paciente:** **2. Motivo de Consulta y Síntomas:** **3. Hallazgos en la Exploración Física:** **4. Pruebas de Imagen:** **5. Diagnóstico:** ---

### Explicación y Justificación del Tratamiento Propuesto
**El Problema (Mecanismo de la Lesión):** **El Objetivo del Tratamiento:** **La Solución Propuesta:** **Justificación:** REGLAS ESTRICTAS:
- Si un dato no aparece, escribe "No especificado".
- Basa tu respuesta ÚNICAMENTE en la transcripción. NO inventes datos.
""",

    "historial": """Actúa como un jefe de traumatología brillante y experto en síntesis clínica. Se te proporcionará un volcado bruto de notas de historia clínica con ruido administrativo y abreviaturas médicas (MO = Médula Ósea, IA = Intraarticular, LLI/LLE = Ligamentos Laterales, ECO = Ecografía, CAR = Cirugía Artroscópica, PROLO = Proloterapia, PRP = Plasma rico en plaquetas, PPP = Plasma pobre en plaquetas, MFAT = Injerto de grasa microfreagmentado).

🚨 FILTRO DE RELEVANCIA CLÍNICA:
Si el texto proporcionado no contiene ningún dato médico ni de historial clínico (ej. es una prueba de texto aleatoria o charla trivial), ABORTA el proceso y responde ÚNICA Y EXCLUSIVAMENTE con esta frase:
"El texto proporcionado no contiene datos válidos de historial clínico."

Tu tarea es leer los datos, filtrarlos y transformarlos en un INFORME CLÍNICO UNIFICADO, ORDENADO Y CRONOLÓGICO.

Debes estructurar tu respuesta ESTRICTAMENTE utilizando este formato Markdown:

### RESUMEN DE HISTORIAL CLÍNICO
**1. Datos del Paciente y Antecedentes:** (Extrae edad, sexo, cirugías previas y tratamientos. Traduce siglas como CAR a Cirugía Artroscópica).
**2. Evolución Cronológica:** (Redacta un resumen narrativo y fluido. INVIERTE EL ORDEN de las fechas si es necesario para empezar por lo antiguo).
**3. Pruebas Diagnósticas:** (Resume los hallazgos de pruebas de imagen. Si solo dice ECO, no inventes una Resonancia).
**4. Diagnóstico Final:** (Sintetiza la conclusión médica).

---

### PLAN TERAPÉUTICO Y JUSTIFICACIÓN
**Protocolo Propuesto:** (¡ATENCIÓN! A menudo el texto tiene una frase inicial de 'PLAN' que resume el tratamiento y, justo debajo, el listado real de sesiones. NO LAS SUMES NI LAS DUPLIQUES. Deduce el número real de sesiones basándote en el listado final. Escríbelo usando viñetas como 'Sesión 1:', 'Sesión 2:', etc.).
**Pauta Médica y Cuidados:** (REGLA ESTRICTA: Si en el texto original no hay medicamentos ni ejercicios escritos, DEBES ESCRIBIR LITERALMENTE "No especificado en las notas clínicas". NUNCA te inventes AINEs, NSAIDs, hielo ni rehabilitación).

**Fundamento Biológico por Terapias:** (Desglosa en una lista con viñetas el mecanismo de acción científico:
- PRP: Factores de crecimiento, angiogénesis.
- Células mesenquimales de médula ósea (MO): Inmunomodulación, potencial condrogénico.
- Proloterapia: Uso de dextrosa hipertónica para inflamar y retensar.)

**Justificación Clínica Integral:** (Párrafo brillante explicando por qué esta combinación evita una cirugía mayor en este paciente).

REGLA DE ORO: NO INVENTES DATOS. Eres brillante en la justificación biológica, pero debes ser un robot calculador copiando los datos, sesiones y medicación del paciente. No asumas nada que no esté explícitamente escrito.""",

    "conferencia_parcial": """Actúa como un asistente médico de investigación. Vas a leer un FRAGMENTO de una conferencia médica.
Tu tarea es extraer los datos médicos, tratamientos y conclusiones de este fragmento para que luego otro médico los unifique.

REGLAS ESTRICTAS:
1. FILTRA EL RUIDO: Ignora por completo anécdotas personales, chascarrillos, saludos o paja.
2. CORRIGE LA TRANSCRIPCIÓN: Detecta y corrige mentalmente el "Spanglish" (ej. "capacity natural de curación and regeneration") y los errores evidentes del micrófono (ej. si dice "gluco cultura", asume que es "glucopuntura").
3. SÍNTESIS EXTREMA: Sé muy conciso. Extrae solo la "carne" científica. Agrupa conceptos, no hagas listas interminables.
4. FILTRO DE RELEVANCIA: Si el fragmento es solo charla trivial o una prueba de micrófono sin valor médico, devuelve EXACTAMENTE la frase "Sin datos médicos relevantes en este bloque".
🚨 REGLA DE IDIOMA INQUEBRANTABLE: DEBES REDACTAR TU RESPUESTA ÚNICA Y EXCLUSIVAMENTE EN ESPAÑOL DE ESPAÑA. TRADUCE TODO TÉRMINO EN INGLÉS AL ESPAÑOL MÉDICO.""",

    "conferencia": """Actúa como un médico especialista, catedrático y redactor científico experto. Tu tarea es analizar transcripciones brutas (o resúmenes parciales) de una ponencia y generar un resumen académico magistral, estructurado y fácil de estudiar.

🚨 FILTRO DE RELEVANCIA CLÍNICA:
Si el texto bruto proporcionado es una prueba de audio sin sentido o no contiene datos médicos de una ponencia, ABORTA el proceso y responde ÚNICA Y EXCLUSIVAMENTE:
"El texto proporcionado no contiene datos válidos de una conferencia médica."

🚨 REGLAS CRÍTICAS PARA LA REDACCIÓN (ANTI-FRANKENSTEIN):
1. FUSIÓN Y COHESIÓN: Redacta párrafos hilados y fluidos. Si varios casos clínicos demuestran lo mismo, agrúpalos en un solo concepto. NO hagas listas de la compra repetitivas ni apiles viñetas que digan lo mismo con distintas palabras.
2. TRADUCCIÓN Y CORRECCIÓN: El texto original puede contener "Spanglish" o errores del micrófono. Ignora ese ruido. 
3. ELIMINACIÓN DE PAJA: Omite cualquier referencia a anécdotas, tiempos de la charla, pausas o preguntas irrelevantes.
4. REGLA DE IDIOMA INQUEBRANTABLE: TODA LA REDACCIÓN FINAL, SIN EXCEPCIÓN, DEBE GENERARSE EN ESPAÑOL DE ESPAÑA.

Debes generar ESTRICTAMENTE la siguiente estructura utilizando formato Markdown (usa negritas y listas agrupadas para organizar visualmente la información):

### 1. TEMA PRINCIPAL Y OBJETIVO DE LA PONENCIA
(Define de forma concisa el tema central y el objetivo principal).

### 2. CONCEPTOS FISIOPATOLÓGICOS Y BIOMECÁNICOS
(Sintetiza la base teórica y anatómica. Agrupa las ideas afines para que la lectura sea fluida).

### 3. ARSENAL TERAPÉUTICO Y MANEJO CLÍNICO
(Detalla los tratamientos, fármacos, concentraciones y técnicas quirúrgicas. Agrupa por técnica, ej. "Proloterapia: indicaciones y uso", "PRP: indicaciones y uso").

### 4. EVIDENCIA CIENTÍFICA Y CASOS PRÁCTICOS
(Agrupa los casos clínicos por patología o técnica utilizada. Sintetiza la evolución sin redundancias. Si no hay casos, indica "No se han detallado casos").

### 5. CONCLUSIONES CLAVE (TAKE-HOME MESSAGES)
(Extrae un máximo de 5 puntos fundamentales, directos y potentes que resuman la esencia de la ponencia)."""
}

def _llamar_ollama(instrucciones_sistema, texto_usuario, modelo_ia, mensaje_spinner="Analizando texto...", stream_callback=None):
    payload = {
        "model": modelo_ia,
        "messages": [
            {"role": "system", "content": instrucciones_sistema},
            {"role": "user", "content": texto_usuario}
        ],
        "stream": True,
        "options": {
            "temperature": 0.1,  
            "num_ctx": 8192      
        }
    }

    estado_spinner = {"mensaje": mensaje_spinner, "activo": True}
    
    def animacion_spinner():
        # Separé el spinner de la consola (puntos) del de la Ventana Fantasma (Relojes)
        caracteres_term = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        caracteres_gui = ['🕛', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚']
        i = 0
        
        while estado_spinner["activo"]:
            texto_terminal = estado_spinner["mensaje"].ljust(60)
            char_term = caracteres_term[i % len(caracteres_term)]
            
            # Pinta los puntos clásicos solo en la consola negra
            sys.stdout.write(f'\r\033[93;40m {char_term} {texto_terminal} \033[0m')
            sys.stdout.flush()
            
            # --- ENVÍA LOS RELOJES ANIMADOS A LA VENTANA FANTASMA ---
            if stream_callback:
                char_gui = caracteres_gui[i % len(caracteres_gui)]
                stream_callback(f"__SPINNER__ {char_gui}  {estado_spinner['mensaje']}  {char_gui}")
                
            time.sleep(0.2) # Velocidad ajustada para que los relojes giren elegantes (5 frames por seg)
            i += 1

    hilo_spinner = threading.Thread(target=animacion_spinner)
    hilo_spinner.start()

    tiempo_inicio = time.time()

    try:
        respuesta = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
        respuesta.raise_for_status()
        
        # --- LA IA DESPIERTA: CAMBIAMOS EL TEXTO DEL CARTEL NARANJA AL VUELO ---
        estado_spinner["mensaje"] = f"REDACTANDO CON IA ({modelo_ia.upper()})..."
            
        texto_estructurado = ""
        
        for linea in respuesta.iter_lines():
            if linea:
                try:
                    datos = json.loads(linea)
                    fragmento = datos.get("message", {}).get("content", "")
                    texto_estructurado += fragmento
                    
                    if stream_callback:
                        stream_callback(fragmento)
                        
                except json.JSONDecodeError:
                    pass
        
        # --- TERMINA DE ESCRIBIR: APAGAMOS EL RELOJ ---
        estado_spinner["activo"] = False
        hilo_spinner.join() 
        
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        # Borramos el cartel naranja de la Ventana Fantasma
        if stream_callback:
            stream_callback("__SPINNER_CLEAR__")
        
        tiempo_total = time.time() - tiempo_inicio
        minutos, segundos = divmod(tiempo_total, 60)
        
        if minutos > 0:
            print(f"\033[92m✅ Tarea completada en {int(minutos)} min y {segundos:.1f} seg.\033[0m\n")
        else:
            print(f"\033[92m✅ Tarea completada en {segundos:.1f} seg.\033[0m\n")
        
        return re.sub(r'<think>.*?</think>', '', texto_estructurado, flags=re.DOTALL).strip()
        
    except Exception as e:
        estado_spinner["activo"] = False
        hilo_spinner.join()
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        if stream_callback:
            stream_callback("__SPINNER_CLEAR__")
            
        print(f"\n\033[91;40mError al conectar con la IA local: {e}\033[0m")
        return f"--- ERROR DE ESTRUCTURACIÓN ---\n\n{texto_usuario}"


def estructurar_texto_con_ia(texto_bruto: str, modo: str = "consulta", stream_callback=None) -> str:
    if len(texto_bruto.strip()) < 20:
        return texto_bruto

    instrucciones_sistema = PROMPTS_SISTEMA.get(modo, PROMPTS_SISTEMA["consulta"])

    if modo == "consulta":
        glosario_actual = cargar_glosario_externo()
        if glosario_actual:
            bloque_traduccion = "REGLA DE TRADUCCIÓN DE METÁFORAS DEL DOCTOR:\nCuando en la transcripción el doctor use las siguientes explicaciones o metáforas con el paciente, debes traducirlas ESTRICTAMENTE a los siguientes términos médicos en el informe:\n" + glosario_actual
            instrucciones_sistema = instrucciones_sistema.replace("{GLOSARIO_PLACEHOLDER}", bloque_traduccion)
        else:
            instrucciones_sistema = instrucciones_sistema.replace("{GLOSARIO_PLACEHOLDER}", "")
            
        modelo_ia = "qwen2.5"
        texto_usuario = f"Aquí tienes el texto bruto:\n\n{texto_bruto}\n\nATENCIÓN: Responde utilizando ESTRICTAMENTE la estructura Markdown indicada en el sistema."
        return _llamar_ollama(instrucciones_sistema, texto_usuario, modelo_ia, f"Despertando a {modelo_ia.upper()} (Modo CONSULTA)...", stream_callback)

    elif modo == "historial":
        modelo_ia = "deepseek-r1:14b"
        texto_usuario = f"Aquí tienes el texto bruto:\n\n{texto_bruto}\n\nATENCIÓN: Invierte el orden cronológico. Redacta una justificación brillante basándote solo en los datos reales."
        return _llamar_ollama(instrucciones_sistema, texto_usuario, modelo_ia, f"Despertando a {modelo_ia.upper()} (Modo HISTORIAL)...", stream_callback)

    elif modo == "conferencia":
        modelo_ia = "deepseek-r1:14b"
        palabras = texto_bruto.split()
        
        LIMITE_PALABRAS = 6000
        
        if len(palabras) > LIMITE_PALABRAS:
            print(f"\n\033[93m⚠️ Conferencia muy larga detectada ({len(palabras)} palabras). Activando Troceador Inteligente...\033[0m")
            fragmentos = []
            
            for i in range(0, len(palabras), LIMITE_PALABRAS):
                inicio = max(0, i - 100) if i > 0 else 0
                fragmento = " ".join(palabras[inicio:i + LIMITE_PALABRAS])
                fragmentos.append(fragmento)
            
            resumenes_parciales = []
            instrucciones_parciales = PROMPTS_SISTEMA["conferencia_parcial"]
            
            for idx, frag in enumerate(fragmentos):
                print(f"\n\033[96m--- PROCESANDO BLOQUE {idx + 1} DE {len(fragmentos)} ---\033[0m")
                texto_usuario_parcial = f"Fragmento de conferencia ({idx + 1}/{len(fragmentos)}):\n\n{frag}\n\nExtrae los conceptos clínicos ignorando el ruido y el Spanglish. 🚨 RECUERDA: ESCRIBE TU RESPUESTA ÚNICA Y EXCLUSIVAMENTE EN ESPAÑOL DE ESPAÑA."
                
                resumen = _llamar_ollama(instrucciones_parciales, texto_usuario_parcial, modelo_ia, f"Analizando bloque {idx + 1} de {len(fragmentos)}...", stream_callback)
                if resumen:
                    resumenes_parciales.append(resumen)
            
            print("\n\033[92m✨ FUSIONANDO y unificando todos los resúmenes parciales...\033[0m")
            texto_unificado = "\n\n--- SIGUIENTE BLOQUE DE LA CONFERENCIA ---\n\n".join(resumenes_parciales)
            
            texto_usuario_final = f"Aquí tienes los resúmenes parciales de una conferencia muy larga:\n\n{texto_unificado}\n\nATENCIÓN CRÍTICA: FUSIONA los conceptos repetidos. Elimina redundancias. Redacta un documento fluido y brillante aplicando estrictamente la plantilla de los 5 apartados. 🚨 RECUERDA: REDACTA ABSOLUTAMENTE TODO EL DOCUMENTO EN ESPAÑOL DE ESPAÑA."
            
            return _llamar_ollama(instrucciones_sistema, texto_usuario_final, modelo_ia, "Sintetizando resumen final de conferencia...", stream_callback)
            
        else:
            texto_usuario = f"Aquí tienes la transcripción bruta de la conferencia:\n\n{texto_bruto}\n\nATENCIÓN CRÍTICA: Recuerda ignorar el Spanglish, corregir términos mal transcritos y aplicar estrictamente la plantilla académica de los 5 apartados. 🚨 REDACTA TODO ESTRICTAMENTE EN ESPAÑOL DE ESPAÑA."
            return _llamar_ollama(instrucciones_sistema, texto_usuario, modelo_ia, f"Despertando a {modelo_ia.upper()} (Modo CONFERENCIA)...", stream_callback)