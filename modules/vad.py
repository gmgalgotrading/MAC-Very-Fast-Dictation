import torch
import numpy as np
import warnings

# Ocultamos los warnings técnicos de PyTorch para mantener tu terminal limpia
warnings.filterwarnings("ignore", category=UserWarning)

print("🛡️ Cargando motor Silero VAD (Filtro Anti-Ruidos)...")

# Cargamos el modelo VAD de alta precisión
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False,
                              onnx=False)

(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

def aislar_voz_humana(audio_array, sample_rate=16000):
    """
    Analiza el array de audio y recorta quirúrgicamente solo los fragmentos con voz humana.
    Si todo el audio es ruido de fondo o silencio, devuelve None.
    """
    # Convertimos el array de numpy a un tensor 1D de PyTorch
    audio_tensor = torch.from_numpy(audio_array).float()
    if audio_tensor.ndim > 1:
        audio_tensor = audio_tensor.squeeze()

    # Silero analiza el audio y extrae las marcas de tiempo donde se habla
    speech_timestamps = get_speech_timestamps(audio_tensor, model, sampling_rate=sample_rate)

    if not speech_timestamps:
        return None  # No hay voz humana en toda la grabación

    # Unimos solo los fragmentos donde hay voz, eliminando el resto
    audio_filtrado = collect_chunks(speech_timestamps, audio_tensor)
    
    return audio_filtrado.numpy()