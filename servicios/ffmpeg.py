"""Todo lo que se hace con ffmpeg: duración, silencios y el corte vertical con subtítulos."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ESTILO_SUBTITULOS = (
    "FontName=Public Sans,Bold=1,FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00201030,"
    "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=62,MarginL=20,MarginR=20"
)


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


def cortar_vertical(entrada: str, inicio: float, fin: float, srt: str, canal: str,
                    fuente_ttf: Path, salida: Path) -> None:
    """Corta [inicio, fin] y lo pasa a 1080×1920: video al centro sobre su propio fondo
    difuminado, subtítulos quemados y el nombre del canal arriba.

    Los filtros de ffmpeg se confunden con rutas de Windows ("C:\\..."), así que se
    trabaja en una carpeta temporal con nombres simples: subs.srt, canal.txt y fuente.ttf.
    """
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "subs.srt").write_text(srt, encoding="utf-8")
        (t / "canal.txt").write_text(canal, encoding="utf-8")
        shutil.copy(fuente_ttf, t / "fuente.ttf")
        filtro = (
            "[0:v]split=2[a][b];"
            "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "boxblur=24:2,eq=brightness=-0.10[fondo];"
            "[b]scale=1080:1920:force_original_aspect_ratio=decrease[frente];"
            "[fondo][frente]overlay=(W-w)/2:(H-h)/2,"
            f"subtitles=subs.srt:fontsdir=.:force_style='{ESTILO_SUBTITULOS}',"
            "drawtext=fontfile=fuente.ttf:textfile=canal.txt:fontcolor=white:fontsize=50:"
            "x=(w-text_w)/2:y=150:box=1:boxcolor=0x7a1c2e@0.88:boxborderw=22,"
            "format=yuv420p[v]"
        )
        _ejecutar([
            "ffmpeg", "-hide_banner", "-y", "-ss", f"{inicio:.2f}", "-t", f"{fin - inicio:.2f}",
            "-i", str(Path(entrada).resolve()), "-filter_complex", filtro,
            "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-r", "30", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            str(salida.resolve()),
        ], cwd=tmp)
