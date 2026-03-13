import requests
import json
import re

# --- DICCIONARIO DE PROMPTS ---
PROMPTS_SISTEMA = {
    "consulta": """Actúa como un médico especialista y documentalista clínico experto. Tu tarea es analizar la transcripción bruta de una consulta médica y extraer la información para generar un informe clínico estructurado, claro, detallado y profesional.

Debes generar ESTRICTAMENTE la siguiente estructura utilizando formato Markdown (usa negritas y viñetas para facilitar la lectura):

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
**1. Datos del Paciente:** (Extrae quién es y qué le ocurre a nivel general).
**2. Motivo de Consulta y Síntomas:** (Detalla el dolor, la inestabilidad, qué empeora o alivia los síntomas).
**3. Hallazgos en la Exploración Física:** (Detalla las pruebas manuales realizadas por el médico y sus resultados).
**4. Pruebas de Imagen:** (Divide esta sección en los hallazgos de Ecografía, Resonancia, Radiografías, etc.).
**5. Diagnóstico:** (Proporciona la conclusión diagnóstica médica final).
**6. Tratmiento Propuesto:** (proporciona de forma clara el tratamiento propuesto)

---

### Explicación y Justificación del Tratamiento Propuesto
**El Problema (Mecanismo de la Lesión):** (Explica la causa raíz fisiológica o biomecánica de la lesión).
**El Objetivo del Tratamiento:** (Define qué busca conseguir el médico a largo plazo).
**La Solución Propuesta:** (Detalla en qué consiste el procedimiento, paso a paso y su fundamento biológico).
**Justificación:** (Enumera en una lista de puntos por qué este tratamiento es el adecuado).

REGLAS ESTRICTAS:
- Rellena todos los campos de la SÍNTESIS de forma muy concisa. Si algún dato no aparece en la transcripción, escribe "No especificado".
- Utiliza un lenguaje clínico pero accesible para el desarrollo detallado.
- Basa tu respuesta ÚNICAMENTE en la transcripción proporcionada. NO inventes datos, diagnósticos ni tratamientos.""",

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
        modelo_ia = "qwen3.5"   # Artillería pesada para razonamiento complejo
        recordatorio = "ATENCIÓN: Recuerda aplicar estrictamente la plantilla de los 5 apartados que te he dado en las instrucciones del sistema."
    else:
        # Nota: Qwen2.5 es rapidísimo, pero vigila si respeta bien este prompt largo. Si no, súbelo a Qwen3.5.
        modelo_ia = "qwen2.5"   
        recordatorio = "ATENCIÓN: Responde utilizando ESTRICTAMENTE la estructura Markdown de 'Historia Clínica' y 'Tratamiento Propuesto' indicada en el sistema. Nada más."

    payload = {
        "model": modelo_ia,
        "messages": [
            {"role": "system", "content": instrucciones_sistema},
            {"role": "user", "content": f"Aquí tienes la transcripción bruta de la consulta:\n\n{texto_bruto}\n\n{recordatorio}"}
        ],
        "stream": True,
        "options": {
            "temperature": 0.1,  # Temperatura baja ideal para datos clínicos (evita alucinaciones)
            "num_ctx": 8192      
        }
    }

    try:
        respuesta = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
        respuesta.raise_for_status()
        
        texto_estructurado = ""
        print(f"\n\033[96m--- REDACTANDO CON IA ({modelo_ia.upper()} EN DIRECTO) ---\033[0m")
        print("\033[96m", end="")
        
        for linea in respuesta.iter_lines():
            if linea:
                try:
                    datos = json.loads(linea)
                    fragmento = datos.get("message", {}).get("content", "")
                    texto_estructurado += fragmento
                    
                    if "<think>" in fragmento:
                        print("\033[90m", end="") 
                        
                    print(fragmento, end="", flush=True)
                    
                    if "</think>" in fragmento:
                        print("\033[0m\n\033[96m", end="") 
                        
                except json.JSONDecodeError:
                    pass
                    
        print("\033[0m\n\033[96m--------------------------------------\033[0m\n")
        
        texto_final_limpio = re.sub(r'<think>.*?</think>', '', texto_estructurado, flags=re.DOTALL).strip()
        
        return texto_final_limpio
        
    except Exception as e:
        print(f"\nError al conectar con la IA local: {e}")
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