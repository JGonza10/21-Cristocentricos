"""Transcripción local con faster-whisper (sin API de pago, todo en esta PC)."""
from functools import lru_cache


@lru_cache(maxsize=1)
def _modelo(nombre: str):
    # Se importa aquí: tarda en cargar y solo lo necesita el agente de reels.
    from faster_whisper import WhisperModel
    # int8 en CPU: funciona en cualquier PC sin tarjeta de video.
    return WhisperModel(nombre, device="cpu", compute_type="int8")


def transcribir(ruta: str, modelo: str = "small") -> list[list]:
    """Devuelve [[inicio, fin, texto], ...] en segundos. La primera vez descarga el modelo (~500 MB)."""
    segmentos, _info = _modelo(modelo).transcribe(
        ruta, language="es", vad_filter=True, beam_size=5,
        initial_prompt="Santo Rosario. Dios te salve, María. Padre nuestro. Gloria al Padre. Misterio.",
    )
    return [[round(s.start, 2), round(s.end, 2), s.text.strip()] for s in segmentos if s.text.strip()]
