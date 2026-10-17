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


def cuadro(ruta: str, segundo: float, salida: Path) -> None:
    """Guarda la imagen del video en ese segundo (para el carrusel de escenas)."""
    _ejecutar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{max(segundo, 0):.2f}",
               "-i", ruta, "-frames:v", "1", "-vf", "scale=1920:-2", str(salida)])


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


def ajuste_de_imagen(brillo: float | None) -> str:
    """Filtro eq de ffmpeg: aclara lo oscuro, baja un poco lo quemado y da un toque de contraste y color."""
    delta = 0.0 if brillo is None else max(-0.06, min(0.12, (115 - brillo) / 255))
    return f"eq=brightness={delta:.3f}:contrast=1.06:saturation=1.10"


def video_de_imagenes(imagenes: list[Path], salida: Path, segundos: float = 5) -> None:
    """Video vertical con las imágenes una tras otra, con acercamiento lento y fundidos."""
    salida.parent.mkdir(parents=True, exist_ok=True)
    cuadros = int(segundos * 30)
    entradas, filtros = [], []
    for i, img in enumerate(imagenes):
        entradas += ["-i", str(Path(img).resolve())]   # una sola imagen: zoompan genera los cuadros
        filtros.append(
            f"[{i}:v]scale=1080:1920,zoompan=z='min(zoom+0.0006,1.06)':d={cuadros}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={segundos - 0.4}:d=0.4,setsar=1[v{i}]")
    union = "".join(f"[v{i}]" for i in range(len(imagenes))) + f"concat=n={len(imagenes)}:v=1:a=0,format=yuv420p[v]"
    _ejecutar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entradas,
               "-filter_complex", ";".join(filtros) + ";" + union, "-map", "[v]",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-movflags", "+faststart", str(salida.resolve())])


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
                    fuente_ttf: Path, salida: Path, mejorar: bool = True) -> None:
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
        # Mejora automática: luz, contraste y color según el brillo del tramo; volumen parejo (loudnorm).
        ajuste = ajuste_de_imagen(brillo_promedio(entrada, inicio, fin)) + "," if mejorar else ""
        audio = ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] if mejorar else []
        filtro = (
            f"[0:v]{ajuste}split=2[a][b];"
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
            "-r", "30", *audio, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            str(salida.resolve()),
        ], cwd=tmp)
