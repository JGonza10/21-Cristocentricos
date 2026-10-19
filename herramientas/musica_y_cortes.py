"""Pasa la música de un video (el del cliente) a otro (el nuestro) y suaviza los cortes.

Qué hace, en orden:
  1. Saca el audio del video del cliente (opcional: solo un tramo con --musica-inicio/--musica-fin).
  2. Si la música dura menos que nuestro video, la repite con un fundido de 2 s para que no se note.
  3. (Opcional) Detecta los cortes bruscos de nuestro video y los cambia por un fundido corto.
  4. Fundido de entrada y salida de la música, y si nuestro video trae voz, baja la música
     cuando alguien habla (ducking).
  5. Normaliza el volumen a -14 LUFS (lo que esperan Instagram, TikTok y YouTube).

Uso (PowerShell, con ffmpeg en el PATH):
  python herramientas\\musica_y_cortes.py --cliente cliente.mp4 --nuestro fatima.mp4 --salida fatima_final.mp4 --suavizar-cortes

Solo usa ffmpeg/ffprobe; no instala nada ni manda nada a internet.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def ejecutar(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"ffmpeg falló:\n{r.stderr[-2000:]}")
    return r


def info(ruta):
    r = ejecutar(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                  "-of", "json", str(ruta)])
    datos = json.loads(r.stdout)
    tipos = {s["codec_type"] for s in datos.get("streams", [])}
    return float(datos["format"]["duration"]), "audio" in tipos


def detectar_cortes(ruta, umbral):
    """Segundos donde la imagen cambia de golpe (cambio de escena)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(ruta), "-an", "-vf",
                        f"scdet=t={umbral}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [float(t) for t in re.findall(r"lavfi\.scd\.time: ([\d.]+)", r.stderr)]


def tramos(duracion, cortes, fundido):
    """Parte el video en tramos; junta los que quedan muy cortos para el fundido."""
    minimo = fundido * 2.5
    puntos = [0.0]
    for c in sorted(cortes):
        if c - puntos[-1] >= minimo and duracion - c >= minimo:
            puntos.append(c)
    puntos.append(duracion)
    return list(zip(puntos[:-1], puntos[1:]))


def armar_filtro(args, dur_nuestro, tiene_voz, dur_musica):
    f = []
    # --- Video: fundidos en los cortes ---
    if args.suavizar_cortes or args.cortes:
        cortes = args.cortes or detectar_cortes(args.nuestro, args.umbral)
        partes = tramos(dur_nuestro, cortes, args.fundido_corte)
    else:
        partes = [(0.0, dur_nuestro)]
    print(f"Cortes suavizados: {len(partes) - 1}")

    D = args.fundido_corte
    for i, (a, b) in enumerate(partes):
        f.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,"
                 f"fps={args.fps},format=yuv420p,settb=AVTB[v{i}]")
        if tiene_voz:
            f.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,"
                     f"aformat=sample_rates=48000:channel_layouts=stereo[a{i}]")
    ultimo_v, ultimo_a, acumulado = "v0", "a0", partes[0][1] - partes[0][0]
    for i in range(1, len(partes)):
        offset = acumulado - D
        f.append(f"[{ultimo_v}][v{i}]xfade=transition={args.transicion}:duration={D}:"
                 f"offset={offset:.3f}[xv{i}]")
        ultimo_v = f"xv{i}"
        if tiene_voz:
            f.append(f"[{ultimo_a}][a{i}]acrossfade=d={D}:c1=tri:c2=tri[xa{i}]")
            ultimo_a = f"xa{i}"
        acumulado += (partes[i][1] - partes[i][0]) - D
    dur_final = acumulado

    # --- Música: tramo elegido, repetida con fundido si es corta ---
    ini = args.musica_inicio or 0.0
    fin = args.musica_fin or dur_musica
    largo = fin - ini
    X = 2.0  # fundido entre repeticiones
    veces = 1
    while largo * veces - X * (veces - 1) < dur_final:
        veces += 1
    # Cada repetición es una entrada aparte (1..veces): asplit + acrossfade se atora en ffmpeg.
    for i in range(veces):
        f.append(f"[{i + 1}:a]atrim=start={ini:.3f}:end={fin:.3f},asetpts=PTS-STARTPTS,"
                 f"aformat=sample_rates=48000:channel_layouts=stereo[r{i}]")
    if veces == 1:
        f.append("[r0]anull[m]")
    else:
        prev = "r0"
        for i in range(1, veces):
            f.append(f"[{prev}][r{i}]acrossfade=d={X}:c1=qsin:c2=qsin[rm{i}]")
            prev = f"rm{i}"
        f.append(f"[{prev}]anull[m]")
    salida_fade = max(dur_final - args.fundido_final, 0)
    f.append(f"[m]atrim=end={dur_final:.3f},volume={args.volumen},"
             f"afade=t=in:d={args.fundido_inicio},"
             f"afade=t=out:st={salida_fade:.3f}:d={args.fundido_final}[mus]")

    # --- Mezcla con la voz (si hay) y volumen para redes ---
    if tiene_voz and not args.sin_voz:
        f.append(f"[{ultimo_a}]asplit=2[voz1][voz2]")
        f.append("[mus][voz1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck]")
        f.append("[duck][voz2]amix=inputs=2:duration=first:normalize=0[mez]")
        mezcla = "mez"
    else:
        mezcla = "mus"
    f.append(f"[{mezcla}]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    f.append(f"[{ultimo_v}]fade=t=in:d=0.5,fade=t=out:st={max(dur_final - 0.8, 0):.3f}:d=0.8[vout]")
    return ";".join(f), dur_final, veces


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cliente", required=True, type=Path, help="video del cliente (de aquí sale la música)")
    p.add_argument("--nuestro", required=True, type=Path, help="nuestro video (Virgen de Fátima)")
    p.add_argument("--salida", required=True, type=Path)
    p.add_argument("--musica-inicio", type=float, help="segundo donde empieza la música en el video del cliente")
    p.add_argument("--musica-fin", type=float, help="segundo donde termina la música en el video del cliente")
    p.add_argument("--volumen", type=float, default=1.0, help="volumen de la música antes de mezclar (1.0 = igual)")
    p.add_argument("--fundido-inicio", type=float, default=1.5)
    p.add_argument("--fundido-final", type=float, default=3.0)
    p.add_argument("--suavizar-cortes", action="store_true", help="cambia cortes bruscos por fundidos")
    p.add_argument("--cortes", type=float, nargs="*", help="segundos de los cortes a mano (si la detección falla)")
    p.add_argument("--umbral", type=float, default=10.0, help="sensibilidad de detección de cortes: menos = detecta más (5–20)")
    p.add_argument("--fundido-corte", type=float, default=0.5, help="duración de cada fundido entre tomas")
    p.add_argument("--transicion", default="fade", help="fade, fadewhite, dissolve, smoothleft, circleopen…")
    p.add_argument("--sin-voz", action="store_true", help="descarta el audio original de nuestro video")
    p.add_argument("--fps", type=int, default=30)
    args = p.parse_args()

    for ruta in (args.cliente, args.nuestro):
        if not ruta.is_file():
            sys.exit(f"No encuentro el archivo: {ruta}")
    dur_musica, cliente_audio = info(args.cliente)
    if not cliente_audio:
        sys.exit("El video del cliente no trae audio.")
    dur_nuestro, tiene_voz = info(args.nuestro)
    if args.musica_fin and args.musica_fin > dur_musica:
        sys.exit(f"--musica-fin pasa del final del video del cliente ({dur_musica:.1f} s).")

    filtro, dur_final, veces = armar_filtro(args, dur_nuestro, tiene_voz, dur_musica)
    entradas = ["-i", str(args.nuestro)] + ["-i", str(args.cliente)] * veces
    ejecutar(["ffmpeg", "-y", "-hide_banner", *entradas,
              "-filter_complex", filtro, "-map", "[vout]", "-map", "[aout]",
              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(args.salida)])
    print(f"Listo: {args.salida} ({dur_final:.1f} s)")


if __name__ == "__main__":
    main()
