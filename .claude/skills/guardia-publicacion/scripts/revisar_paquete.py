"""Revisa un paquete de paquetes/<fecha>/ antes de darlo por listo para subir.

Uso: python revisar_paquete.py paquetes/2026-10-19
Sale con 0 si todo está bien, 1 si hay fallas.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REDES = {"instagram", "facebook", "tiktok", "youtube", "tv"}
PERMITIDAS = {".mp4", ".png", ".jpg", ".jpeg", ".txt", ".json"}
NOMBRES_PROHIBIDOS = re.compile(r"^(\.env.*|client_secret.*|token.*|.*\.(db|sqlite3|log))$", re.I)
TEXTO_SECRETO = re.compile(r"SECRET_KEY\s*=|refresh_token|client_secret|-----BEGIN", re.I)
MAX_SEG = 60
MAX_MB = 250


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def revisar_video(ruta: Path, fallas: list) -> None:
    if not shutil.which("ffprobe"):
        fallas.append(f"{ruta.name}: no se encontró ffprobe (instala ffmpeg) para revisar el video")
        return
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", str(ruta)],
        capture_output=True, text=True, check=False,
    )
    if salida.returncode != 0:
        fallas.append(f"{ruta.name}: ffprobe no pudo leerlo (¿archivo dañado?)")
        return
    info = json.loads(salida.stdout or "{}")
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video or video.get("codec_name") != "h264":
        fallas.append(f"{ruta.name}: el video debe ser H.264")
    elif (video.get("width"), video.get("height")) != (1080, 1920):
        fallas.append(f"{ruta.name}: mide {video.get('width')}×{video.get('height')}, debe ser 1080×1920")
    if not audio or audio.get("codec_name") != "aac":
        fallas.append(f"{ruta.name}: el audio debe ser AAC")
    duracion = float(info.get("format", {}).get("duration") or 0)
    if not 0 < duracion < MAX_SEG:
        fallas.append(f"{ruta.name}: dura {duracion:.1f} s, debe ser menor a {MAX_SEG} s")
    if ruta.stat().st_size > MAX_MB * 1024 * 1024:
        fallas.append(f"{ruta.name}: pesa más de {MAX_MB} MB")


def revisar_imagen(ruta: Path, fallas: list) -> None:
    try:
        from PIL import Image
    except ImportError:
        return  # sin Pillow no se revisan medidas
    try:
        with Image.open(ruta) as img:
            if img.size != (1080, 1350):
                fallas.append(f"{ruta.name}: mide {img.size[0]}×{img.size[1]}, debe ser 1080×1350")
    except OSError:
        fallas.append(f"{ruta.name}: no se pudo abrir la imagen")


def revisar(paquete: Path) -> list:
    fallas = []
    base = paquete / "subir_manual"
    if not base.is_dir():
        return [f"No existe {base}"]

    for ruta in paquete.rglob("*"):
        nombre = ruta.relative_to(paquete)
        if ruta.is_symlink():
            fallas.append(f"{nombre}: es un enlace simbólico, no se permite")
            continue
        if not ruta.is_file():
            continue
        if NOMBRES_PROHIBIDOS.match(ruta.name):
            fallas.append(f"{nombre}: parece un secreto o dato interno, sácalo del paquete")
        elif ruta.suffix.lower() not in PERMITIDAS:
            fallas.append(f"{nombre}: tipo de archivo no permitido")

    for carpeta in sorted(p for p in base.iterdir() if p.is_dir()):
        red = carpeta.name
        if red not in REDES:
            fallas.append(f"{red}/: red desconocida")
            continue
        texto = carpeta / "texto.txt"
        if not texto.is_file():
            fallas.append(f"{red}/: falta texto.txt")
        else:
            try:
                contenido = texto.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                fallas.append(f"{red}/texto.txt: no está en UTF-8")
                contenido = ""
            if not contenido.strip():
                fallas.append(f"{red}/texto.txt: está vacío")
            if TEXTO_SECRETO.search(contenido):
                fallas.append(f"{red}/texto.txt: contiene algo que parece un secreto")

        videos = sorted(carpeta.glob("*.mp4"))
        imagenes = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
        for v in videos:
            revisar_video(v, fallas)
        if red == "tiktok" and imagenes:
            fallas.append("tiktok/: solo lleva video, quita las imágenes")
        if red in {"instagram", "facebook"} and imagenes and not 1 <= len(imagenes) <= 10:
            fallas.append(f"{red}/: el carrusel debe tener de 1 a 10 imágenes")
        for img in imagenes:
            revisar_imagen(img, fallas)
        if not videos and not imagenes:
            fallas.append(f"{red}/: no tiene nada que subir")

    manifiesto = paquete / "manifiesto.json"
    if manifiesto.is_file():
        try:
            datos = json.loads(manifiesto.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            datos = None
            fallas.append("manifiesto.json: no es JSON válido")
        for item in (datos or {}).get("archivos", []):
            ruta = (paquete / str(item.get("ruta", ""))).resolve()
            if not ruta.is_relative_to(paquete.resolve()):
                fallas.append(f"manifiesto.json: ruta fuera del paquete ({item.get('ruta')})")
            elif not ruta.is_file():
                fallas.append(f"manifiesto.json: falta {item.get('ruta')}")
            elif sha256(ruta) != item.get("sha256"):
                fallas.append(f"{item.get('ruta')}: cambió después de aprobarse (sha256 distinto)")
    return fallas


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    paquete = Path(sys.argv[1])
    fallas = revisar(paquete)
    if fallas:
        print(f"✗ {paquete}: {len(fallas)} problema(s)")
        for f in fallas:
            print(f"  - {f}")
        return 1
    print(f"✓ {paquete}: listo para subir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
