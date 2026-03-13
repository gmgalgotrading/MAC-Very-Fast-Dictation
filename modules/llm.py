import requests
import json
import re
import threading
import time
import sys

# --- GLOSARIO DE TRADUCCIÓN CLÍNICA ---
GLOSARIO_CLINICO = """
REGLA DE TRADUCCIÓN DE METÁFORAS DEL DOCTOR:
Cuando en la transcripción el doctor use las siguientes explicaciones o metáforas con el paciente, debes traducirlas ESTRICTAMENTE a los siguientes términos médicos en el informe:
- "Rueda de coche poco sujeta", "traqueteo", "cloc cloc" -> Inestabilidad articular por laxitud ligamentosa.
- "Hacer pequeñas heridas para que al cicatrizar encoja" -> Terapia regenerativa / Proloterapia ligamentosa.
- "Sacar células de la médula ósea" -> Aspirado de médula ósea (BMAC).
- "Sacar células de la grasa" -> Injerto de grasa microfragmentada
- "Sacar sangre para que cure" -> Infiltración de Plasma Rico en Plaquetas (PRP) / Factores de crecimiento.
- "Pan para hoy y hambre para mañana" -> Tratamiento puramente sintomático que no aborda la etiología mecánica.
- "La gota que colma el vaso" -> Descompensación aguda de una patología degenerativa crónica.
- "Bisagra oxidada" -> Artrosis severa con rigidez articular
- "Bisagra que chirría" -> Artrosis moderada-severa con ruidos articulares
- "Tornillos aflojados" o "anclajes débiles" -> Laxitud en la entesis e inestabilidad ligamentosa.
- "Una obra que empezó la construcción y se dejó abandonada" -> Lesión crónica con interrupción de la cascada fisiológica de cicatrización.
- "Reclutar más obreros y reclutar más material" -> Estímulo biológico para favorecer la regeneración tisular.
- "Poner el aceite lubricante en el motor pero las piezas están inestables" -> Infiltración intraarticular sin corrección de la inestabilidad biomecánica subyacente.
- "Casa en ruinas", "cimientos estropeados" o "paredes caídas" -> Artrosis crónica avanzada con daño estructural extenso (cartílago, menisco y hueso subcondral).
- "Pintar las paredes" o "hacer una reforma a medias" -> Tratamiento paliativo aislado que fracasará a largo plazo por no abordar la unidad funcional completa.
- "Incendio" o "volcán en erupción" -> Sinovitis activa con componente inflamatorio agudo.
- "Tratar la articulación como un órgano" -> Abordaje terapéutico integral que combina la estabilización biomecánica con la regeneración biológica.
"""

# --- DICCIONARIO DE PROMPTS ---
PROMPTS_SISTEMA = {
    "consulta": f"""Actúa como un médico especialista y documentalista clínico experto. Tu tarea es analizar la transcripción bruta de una consulta médica y generar un informe clínico estructurado.

{GLOSARIO_CLINICO}

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

A CONTINUACIÓN, TE MUESTRO UN EJEMPLO DE CÓMO DEBES RESPONDER. ESTO ES SOLO UN EJEMPLO DE REFERENCIA:

<ejemplo_transcripcion>
"Cuando la rodilla está en extensión completa, los ligamentos laterales deben de sujetarla y no deberían de dejar hacer estos movimientos, como ocurre en la rodilla sana, la derecha. Cuando movemos en la izquierda, sin embargo, se abre sobre todo por fuera y también por dentro y además duele ahí... [RESTO DE LA TRANSCRIPCIÓN OMITIDA POR BREVEDAD EN EL EJEMPLO]"
</ejemplo_transcripcion>

<ejemplo_respuesta_ideal>
### SÍNTESIS PARA LA HISTORIA CLÍNICA

- **Antecedentes:** Paciente varón. La lesión actual no es secundaria a un traumatismo agudo único, sino de carácter crónico y degenerativo.
- **Motivo de consulta:** Dolor en la rodilla izquierda y sensación de inestabilidad.
- **Tiempo de evolución:** Proceso crónico y de larga evolución, insidioso, no reciente.
- **Sintomatología actual:** Dolor en la interlínea medial. Sensación de que la rodilla "se abre" y presenta un "traqueteo". Mejora con rodillera.
- **Exploración física:** Bostezo lateral (externo) positivo. Bostezo medial (interno) discreto. Hidrops discreto. Cajón anterior negativo.
- **Pruebas complementarias:** Ecografía muestra rotura del menisco interno y ligamento lateral interno laxo. RM confirma rotura horizontal del menisco interno.
- **Diagnóstico:** Laxitud crónica de los ligamentos laterales de la rodilla izquierda. Meniscopatía interna secundaria a la inestabilidad crónica.
- **Plan de tratamiento:** Tratamiento biológico (proloterapia o terapia regenerativa) en tres sesiones (la primera con sedación, extrayendo células de médula ósea; segunda y tercera con sangre periférica) para tensar los ligamentos laxos y tratar la lesión meniscal.

---

### Resumen Detallado de la Consulta
**1. Datos del Paciente:** Hombre con lesión crónica en la rodilla izquierda.
**2. Motivo de Consulta y Síntomas:** Dolor en la cara interna (interlínea medial). Inestabilidad ("traqueteo"). El uso de rodillera alivia la inestabilidad pero, si aprieta demasiado, le provoca hinchazón distal (tobillo/pantorrilla).
**3. Hallazgos en la Exploración Física:** Bostezo lateral positivo, bostezo medial discreto, leve derrame (hidrops) y cajón anterior negativo.
**4. Pruebas de Imagen:** En la ecografía se observa rotura meniscal interna y destensamiento del ligamento lateral interno. La resonancia magnética confirma la rotura horizontal del menisco interno y la laxitud ligamentosa (sin rotura aguda).
**5. Diagnóstico:** Laxitud crónica de ligamentos laterales (medial y lateral) e inestabilidad, asociada a meniscopatía interna.

---

### Explicación y Justificación del Tratamiento Propuesto
**El Problema (Mecanismo de la Lesión):** Los ligamentos laterales están destensados por microtraumatismos acumulados a lo largo de los años. Esta laxitud genera un movimiento anómalo ("traqueteo") que termina rompiendo el menisco.
**El Objetivo del Tratamiento:** Corregir la inestabilidad mecánica de base (tensar los ligamentos) para evitar que la lesión progrese, abordando la causa y no solo el síntoma.
**La Solución Propuesta:** Provocar microheridas en los ligamentos para que, al cicatrizar, el tejido se retraiga y recupere la tensión. Se realizará en 3 sesiones separadas por tres semanas: la 1ª extrayendo células de médula ósea (con sedación) y la 2ª y 3ª obteniendo factores de crecimiento de sangre periférica (sin sedación).
**Justificación:** Trata el problema biomecánico de raíz (laxitud), utiliza el potencial biológico del paciente para la cicatrización y actúa simultáneamente sobre la tensión ligamentosa y la rotura meniscal.
</ejemplo_respuesta_ideal>
""",

    "historial": """Actúa como un jefe de traumatología brillante y experto en síntesis clínica. Se te proporcionará un volcado bruto de notas de historia clínica con ruido administrativo y abreviaturas médicas (MO = Médula Ósea, IA = Intraarticular, LLI/LLE = Ligamentos Laterales, ECO = Ecografía, CAR = Cirugía Artroscópica, PROLO = Proloterapia, LLI = Ligamento lateral interno, LLE = Ligamento lateral externo, LCA = Ligamento cruzado anterior, MFAT = Injerto de grasa microfragmentada).

Tu tarea es leer estos datos, filtrarlos y transformarlos en un INFORME CLÍNICO UNIFICADO, ORDENADO Y CRONOLÓGICO.

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

    "conferencia": """Actúa como un médico especialista, catedrático y redactor científico experto. Tu tarea es analizar la transcripción bruta de una ponencia o conferencia médica y extraer la información clave para generar un resumen académico estructurado, riguroso y fácil de estudiar.

Debes generar ESTRICTAMENTE la siguiente estructura utilizando formato Markdown (usa negritas y listas con viñetas para organizar visualmente la información):

### 1. TEMA PRINCIPAL Y OBJETIVO DE LA PONENCIA
(Define de forma concisa el tema central de la charla y el objetivo principal que el ponente intenta transmitir).

### 2. CONCEPTOS FISIOPATOLÓGICOS Y BIOMECÁNICOS
(Resume en viñetas los conceptos teóricos fundamentales, mecanismos de la enfermedad, anatomía o fisiopatología explicados en la charla).

### 3. ARSENAL TERAPÉUTICO Y MANEJO CLÍNICO
(Detalla en viñetas los tratamientos, fármacos, técnicas quirúrgicas o algoritmos de decisión mencionados. Explica brevemente la indicación o justificación de cada uno según el ponente).

### 4. EVIDENCIA CIENTÍFICA Y CASOS PRÁCTICOS
(Describe los estudios clínicos, estadísticas, artículos o ejemplos de casos de pacientes que el ponente haya utilizado para ilustrar su postura. Si no menciona ninguno, escribe "No se han detallado casos o estudios específicos").

### 5. CONCLUSIONES CLAVE (TAKE-HOME MESSAGES)
(Extrae en una lista de 3 a 5 puntos fundamentales los mensajes más importantes que el ponente quiere que la audiencia recuerde).

REGLAS ESTRICTAS:
- Utiliza un lenguaje médico, académico y profesional.
- Basa tu respuesta ÚNICAMENTE en la transcripción proporcionada. NO inventes datos, porcentajes, estudios ni tratamientos que no haya dicho el ponente.
- NO añadas texto introductorio (como "Aquí está el resumen") ni de despedida. Empieza directamente por el primer título."""
}


def estructurar_texto_con_ia(texto_bruto: str, modo: str = "consulta") -> str:
    """Envía la transcripción a Ollama usando el endpoint nativo de CHAT."""
    
    if len(texto_bruto.strip()) < 20:
        return texto_bruto

    instrucciones_sistema = PROMPTS_SISTEMA.get(modo, PROMPTS_SISTEMA["consulta"])

# --- EL SEMÁFORO INTELIGENTE (ENRUTAMIENTO DINÁMICO) ---
    if modo == "conferencia":
        modelo_ia = "qwen3.5"   # Artillería pesada
        recordatorio = "ATENCIÓN: Recuerda aplicar estrictamente la plantilla de los 5 apartados."
    elif modo == "historial":
        # ¡AQUÍ ESTÁ EL CAMBIO! Ponemos a DeepSeek-R1 al mando de los historiales
        modelo_ia = "deepseek-r1:14b"  # Cambia a "14b" si descargaste la versión más grande
        recordatorio = "ATENCIÓN: Invierte el orden de las fechas para que la evolución sea cronológica. Ignora la burocracia. Redacta una justificación médica brillante basándote en los datos reales del paciente."
    else:
        modelo_ia = "qwen2.5"   # Consulta (Rápido y letal con el Few-Shot)
        recordatorio = "ATENCIÓN: Responde utilizando ESTRICTAMENTE la estructura Markdown indicada en el sistema. No olvides usar las **negritas** en los títulos de cada apartado tal y como se muestra en el ejemplo. No añadas nada más."
    
    payload = {
        "model": modelo_ia,
        "messages": [
            {"role": "system", "content": instrucciones_sistema},
            {"role": "user", "content": f"Aquí tienes el texto bruto:\n\n{texto_bruto}\n\n{recordatorio}"}
        ],
        "stream": True,
        "options": {
            "temperature": 0.1,  
            "num_ctx": 8192      
        }
    }

    # --- CONFIGURACIÓN DEL SPINNER ANIMADO ---
    evento_parar = threading.Event()
    
    def animacion_spinner():
        caracteres = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        while not evento_parar.is_set():
            sys.stdout.write(f'\r\033[93;40m {caracteres[i % len(caracteres)]} Despertando a {modelo_ia.upper()} y analizando texto... \033[0m')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    hilo_spinner = threading.Thread(target=animacion_spinner)
    hilo_spinner.start()

    try:
        respuesta = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
        respuesta.raise_for_status()
        
        evento_parar.set()
        hilo_spinner.join()
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        texto_estructurado = ""
        print(f"\033[96;40m--- REDACTANDO CON IA ({modelo_ia.upper()} EN DIRECTO - MODO {modo.upper()}) ---\033[0m")
        print("\033[96;40m", end="")
        
        for linea in respuesta.iter_lines():
            if linea:
                try:
                    datos = json.loads(linea)
                    fragmento = datos.get("message", {}).get("content", "")
                    texto_estructurado += fragmento
                    
                    if "<think>" in fragmento:
                        print("\033[90;40m", end="") 
                        
                    print(fragmento, end="", flush=True)
                    
                    if "</think>" in fragmento:
                        print("\033[0m\n\033[96;40m", end="") 
                        
                except json.JSONDecodeError:
                    pass
                    
        print("\033[0m\n\033[96;40m--------------------------------------\033[0m\n")
        
        texto_final_limpio = re.sub(r'<think>.*?</think>', '', texto_estructurado, flags=re.DOTALL).strip()
        
        return texto_final_limpio
        
    except Exception as e:
        evento_parar.set()
        hilo_spinner.join()
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        print(f"\n\033[91;40mError al conectar con la IA local: {e}\033[0m")
        return f"--- ERROR DE ESTRUCTURACIÓN ---\n\n{texto_bruto}"

    # ANTIGUO PROMPT SISTEMA

    #prompt_sistema = """Eres un asistente médico experto. Toma esta transcripción de una consulta y conviértela en una historia clínica estructurada en formato SOAP (Subjetivo, Objetivo, Análisis, Plan).
    #Reglas estrictas:
    #1. Extrae ÚNICAMENTE información clínicamente relevante. Ignora saludos y charla trivial.
    #2. Utiliza lenguaje médico técnico, profesional y objetivo (ej. cambia "me duele la rodilla al doblarla" por "gonalgia a la flexión").
    #3. Si un apartado no se menciona en la conversación, pon "No se especifican datos".
    #4. Devuelve SOLO el texto formateado final, listo para ser pegado. No hagas introducciones ni uses código."""

            #"repeat_penalty": 1.05,   # <-- CORRECCIÓN: Relajamos el castigo para que escriba fluido
            #"num_predict": 1500       # El freno físico contra bucles infinitos se mantiene