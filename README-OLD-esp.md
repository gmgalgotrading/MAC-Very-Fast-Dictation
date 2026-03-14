```
# Very Fast Dictation - Medical Edition 🩺⚡️

Una herramienta de transcripción y estructuración clínica ultrarrápida impulsada por Inteligencia Artificial local, diseñada específicamente para entornos médicos y optimizada para macOS (Apple Silicon). 

Permite a los profesionales de la salud dictar consultas en tiempo real, resumir historiales médicos caóticos o transcribir largas conferencias magistrales, transformando el texto en bruto en informes académicos perfectamente estructurados. Todo el procesamiento se realiza **100% en local**, garantizando la privacidad absoluta del paciente.

---

## ✨ Características Principales

* 🎙️ **Transcripción de Alta Precisión:** Utiliza *Whisper Turbo* combinado con un filtro anti-ruido (*Silero VAD*) para capturar la voz humana aislando el ruido de fondo de la consulta.
* 🧠 **Estructuración Inteligente (LLM Local):** Integración directa con **Ollama** para usar modelos de vanguardia (`DeepSeek-R1:14b` y `Qwen2.5`), extrayendo el contexto médico sin alucinaciones ni redundancias.
* 👻 **Interfaz "Ventana Fantasma":** Una UI translúcida, flotante y minimalista que no roba el foco del ratón. Inmune a las transiciones del Finder de macOS, muestra el progreso de la IA en tiempo real al estilo terminal *cyberpunk*.
* ⏱️ **Cronómetros Dinámicos Nativos:** Seguimiento exacto del tiempo de transcripción y razonamiento de la IA con animaciones nativas sin consumo extra de RAM.
* ⚡ **Disparadores por Atajos:** Integración profunda con macOS. Inicia grabaciones o procesa el portapapeles en un instante mediante atajos de teclado invisibles.

---

## ⚙️ Modos de Funcionamiento

La aplicación opera desde la barra de menú superior de tu Mac (System Tray) y ofrece tres modos especializados:

1.  **Consulta Clínica (`qwen2.5`):** Analiza un diálogo continuo sin etiquetas, separa semánticamente al doctor del paciente, traduce metáforas coloquiales a terminología médica (mediante un glosario personalizable) y genera un informe SOAP completo.
2.  **Resumen de Historial (`deepseek-r1:14b`):** Toma un volcado de notas caóticas, siglas y pruebas de laboratorio, lo ordena cronológicamente y redacta un plan terapéutico con justificación biológica basada puramente en la evidencia del texto.
3.  **Conferencia Médica (`deepseek-r1:14b`):** Procesa ponencias de gran longitud. Incluye un **Troceador Inteligente** que fragmenta audios masivos (más de 6.000 palabras), extrae los conceptos fisiopatológicos, elimina la "paja" y el *Spanglish*, y unifica todo en un resumen académico brillante sin redundancias.

---

## 🛠️ Requisitos Previos

* **Sistema Operativo:** macOS (Altamente recomendado Apple Silicon M1/M2/M3/M4 para un rendimiento óptimo de los LLMs).
* **Python:** Versión 3.12 o superior. Se recomienda usar [uv](https://github.com/astral-sh/uv) como gestor de paquetes.
* **Ollama:** Debes tener [Ollama](https://ollama.com/) instalado y ejecutándose en segundo plano.
* **Modelos LLM:** Descarga los modelos necesarios abriendo tu terminal y ejecutando:
    ```bash
    ollama run qwen2.5
    ollama run deepseek-r1:14b
    ```

---

## 🚀 Instalación y Uso

**1. Clonar el repositorio:**
```bash
git clone [https://github.com/tu-usuario/MAC-Very-Fast-Dictation.git](https://github.com/tu-usuario/MAC-Very-Fast-Dictation.git)
cd MAC-Very-Fast-Dictation
```

**2. Instalar dependencias:**

Bash

```
uv sync
```

*(Asegúrate de tener instaladas dependencias del sistema como `ffmpeg` si vas a procesar archivos de audio externos).*

**3. Diccionario de Metáforas (Opcional):** Puedes crear un archivo llamado `diccionario_metaforas.txt` en la raíz del proyecto para que la IA sepa cómo traducir tus explicaciones habituales a los pacientes a lenguaje médico técnico.

**4. Ejecutar la aplicación:**

Bash

```
uv run main.py
```

------

## ⌨️ Flujo de Trabajo (Atajos Rápídos)

Una vez que la aplicación esté corriendo (verás el icono en la barra superior de tu Mac), el flujo es completamente invisible:

- **`Doble pulsación de Ctrl (Control)`:** Inicia la grabación de audio. Vuelve a hacer doble pulsación para detenerla y comenzar a transcribir.
- **`Doble pulsación de Alt (Option)`:** Lee el texto que tengas actualmente copiado en el portapapeles y lo manda directamente a estructurar con la IA.
- **Archivos externos:** Desde el icono de la barra de menú puedes subir directamente archivos `.mp3`, `.wav` o `.txt` larguísimos (como transcripciones de conferencias enteras).

Al terminar, la aplicación pegará automáticamente el resultado si tienes un editor de texto abierto, o lo guardará en el portapapeles lanzando una **Alerta Persistente de macOS** para que nunca pierdas el informe. Además, se guarda una copia de seguridad en la carpeta local `logs/`.

------

## 🔒 Privacidad y Aviso Legal

Esta aplicación está diseñada bajo el principio de **Privacidad por Diseño (Privacy by Design)**.

- Ningún dato de audio ni de texto abandona tu ordenador. Todo el reconocimiento de voz y el procesamiento de los modelos de lenguaje ocurre localmente en el silicio de tu Mac.
- **Aviso:** Esta es una herramienta de asistencia a la redacción. Los modelos de Inteligencia Artificial pueden cometer errores u omitir datos. El profesional médico es el **único responsable** de revisar, auditar y firmar la veracidad clínica del texto final antes de incorporarlo a la historia clínica oficial del paciente.

------

*Desarrollado con ❤️ para optimizar el tiempo médico y recuperar el contacto humano en la consulta.*