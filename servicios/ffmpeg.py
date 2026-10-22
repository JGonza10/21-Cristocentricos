"""Lo básico de ffmpeg: duración, audio para Whisper, brillo y silencios. La edición está en estilo.py."""
import json
import re
import shutil
import subprocess


class ErrorFfmpeg(Exception):
    pass


def _ejecutar(args: list[str], cwd: str | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    if shutil.which(args[0]) is None:
        raise ErrorFfmpeg(f"No se encontró {args[0]}. Instálalo con: winget install Gyan.FFmpeg")
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise ErrorFfmpeg(r.stderr[-1500:])
    return r


def duracion(ruta: str) -> float:
    r = _ejecutar(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", ruta])
    return float(json.loads(r.stdout)["format"]["duration"])


def audio_16k(ruta: str):
    """Audio mono a 16 kHz como arreglo float32 (lo que espera Whisper), decodificado con ffmpeg."""
    import numpy as np
    if shutil.which("ffmpeg") is None:
        raise ErrorFfmpeg("No se encontró ffmpeg. Instálalo con: winget install Gyan.FFmpeg")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", ruta, "-vn",
                        "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, timeout=1800)
    if r.returncode != 0:
        raise ErrorFfmpeg(r.stderr.decode("utf-8", "replace")[-1500:])
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0


def brillo_promedio(ruta: str, inicio: float, fin: float) -> float | None:
    """Brillo medio (0–255) de unos cuadros del tramo, para saber si hay que aclarar el video."""
    try:
        r = _ejecutar(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{inicio:.2f}", "-t", f"{max(fin - inicio, 1):.2f}",
                       "-i", ruta, "-vf", "fps=1,scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                       "-an", "-f", "null", "-"])
    except ErrorFfmpeg:
        return None
    valores = [float(v) for v in re.findall(r"YAVG=([\d.]+)", r.stderr)]
    return sum(valores) / len(valores) if valores else None


def silencios(ruta: str, ruido_db: int = -35, minimo_s: float = 1.5) -> list[tuple[float, float]]:
    """Tramos de silencio [(inicio, fin), ...] según el filtro silencedetect."""
    r = _ejecutar(["ffmpeg", "-hide_banner", "-nostats", "-i", ruta, "-vn",
                   "-af", f"silencedetect=noise={ruido_db}dB:d={minimo_s}", "-f", "null", "-"])
    return parsear_silencios(r.stderr)


def parsear_silencios(texto: str) -> list[tuple[float, float]]:
    tramos, inicio = [], None
    for linea in texto.splitlines():
        if m := re.search(r"silence_start: (-?[\d.]+)", linea):
            inicio = max(float(m.group(1)), 0.0)
        elif (m := re.search(r"silence_end: ([\d.]+)", linea)) and inicio is not None:
            tramos.append((inicio, float(m.group(1))))
            inicio = None
    return tramos
