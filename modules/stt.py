import mlx_whisper

print("Cargando modelo Whisper Turbo (alta precisión médica)...")

MODEL_PATH = "mlx-community/whisper-large-v3-turbo"

def transcribe(audio_file_path):
    try:
        # Diccionario plano. Sin palabras en MAYÚSCULAS completas ni dos puntos,
        # para evitar que Whisper se confunda y las imprima en el texto final.
        contexto_clinico = (
            "Academia Española de Medicina Regenerativa, ORTOBIOMSK, ITRAMED, Gonzalo Mora, "
            "Logroño, Hernández, cirujano ortopédico, terapias biológicas, proloterapia, "
            "plasma rico en plaquetas, PRP, células mesenquimales, médula ósea, "
            "inyección intraarticular, intraósea, inyecciones epidurales caudales, suero, "
            "dextrosa, plastias intervenidas, meniscectomía, tejidos laxos, colagénicos, "
            "hueso subcondral, membrana sinovial, entesis, cartílago, menisco, meniscopatía, "
            "lesiones condrales, parameniscitis, inestabilidad crónica, inestabilidad lumbopélvica, "
            "ligamentos iliolumbares, interespinales, coronarios, facetas, disco, discopatía, "
            "artrosis de rodilla, rodilla artrósica, ligamento cruzado, lateral interno, "
            "lateral externo, laxitud ligamentosa, bostezo, cajón anterior, estenosis de canal lumbar, "
            "clínica radicular, rizartrosis, biotensegridad, fundamento fisiopatológico, "
            "respuesta tisular, sinergismo."
        )

        result = mlx_whisper.transcribe(
            audio_file_path,
            path_or_hf_repo=MODEL_PATH,
            language="es",
            initial_prompt=contexto_clinico
        )
        return result["text"]
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return ""

if __name__ == "__main__":
    print(transcribe("recording.wav"))