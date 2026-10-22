"""Edición de reels con el estilo del cliente (2026-10-19).

Todo vive en la carpeta `estilo_cliente/` de la raíz del proyecto:

    estilo_cliente/
      referencia/     el video que entregó el cliente como muestra (puede haber varios)
      herramientas/   imágenes (PNG con transparencia), animaciones (MOV/WEBM con alfa, GIF, MP4),
                      intro y cierre, música y fuentes que se usan para que el reel quede igual
      estilo.json     la "receta": qué herramienta va, dónde, en qué segundo, y cómo se mejora el video
      analisis/       lo que sale de `flask --app app estilo-analizar` (cuadros y medidas de la referencia)
      pruebas/        reels de prueba de `flask --app app estilo-probar`

Un reel se arma con UNA sola llamada a ffmpeg:
  1. Corta el tramo del video limpio (celular) y lo mejora: luz según el brillo del tramo, contraste,
     color, quita grano, nitidez (enfoque) y audio sin ruido exterior con volumen parejo.
  2. Lo encuadra a vertical (por defecto 1080×1920).
  3. Encima pone las capas del cliente (imágenes y animaciones) en su posición y tiempo.
  4. Encima pone los textos ({tema}, {fecha}…) y los subtítulos, hechos como imágenes con Pillow
     (así no dependen de las fuentes instaladas en Windows).
  5. Mezcla la música (si hay) y pega la intro y el cierre del cliente (si hay).

Los tiempos `desde`/`hasta` de capas y textos son segundos del reel (sin contar la intro).
Un número negativo cuenta desde el final: `"desde": -3` = los últimos 3 segundos. `hasta: null` = hasta el final.
"""
import copy
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .ffmpeg import ErrorFfmpeg, _ejecutar, brillo_promedio, duracion

VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".gif", ".m4v"}
IMAGEN = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

# Receta por defecto: el look actual de Cristocéntricos (vino y oro). Se copia a estilo.json la
# primera vez; cuando llegue la referencia del cliente se ajusta a lo que él pide.
ESTILO_BASE = {
    "activo": True,
    "nota": "Receta por defecto. Ajústala a la referencia del cliente (ver LEEME.md).",
    "formato": {"ancho": 1080, "alto": 1920, "fps": 30, "encuadre": "fondo_difuminado", "foco_y": 0.35,
                "color_relleno": "#000000"},
    "duracion": {"min": 30, "max": 55, "ideal": 45},
    "mejora": {"luz": True, "contraste": 1.05, "saturacion": 1.06, "gamma": 1.0, "nitidez": 0.6,
               "quitar_grano": True, "quitar_ruido": True, "volumen_lufs": -14},
    "intro": None,
    "cierre": None,
    "capas": [],
    "textos": [
        {"texto": "† {canal}", "fuente": "Spectral_700Bold.ttf", "tamano": 46, "color": "#FFFFFF",
         "fondo": "#7A1C2EE6", "x": "centro", "y": 150, "desde": 0, "hasta": None},
        {"texto": "{tema}", "fuente": "Spectral_700Bold.ttf", "tamano": 62, "color": "#7A1C2E",
         "fondo": "#FFFFFFEE", "x": "centro", "y": 1600, "desde": 0, "hasta": 3.2, "ancho_max": 900},
        {"texto": "En vivo lunes y viernes · 10:00 a. m.", "fuente": "PublicSans_700Bold.ttf", "tamano": 40,
         "color": "#7A1C2E", "fondo": "#FFFFFFF0", "x": "centro", "y": 1600, "desde": -3, "hasta": None},
    ],
    "subtitulos": {"activo": True, "fuente": "PublicSans_800ExtraBold.ttf", "tamano": 50, "color": "#FFFFFF",
                   "fondo": "#7A1C2EE0", "y": 1600, "caracteres_por_renglon": 24, "mayusculas": False},
    "musica": None,
    "fundido": 0.25,
    "negro_final": 0,
    "quitar_pausas": {"activo": False, "minimo": 0.6, "margen": 0.15, "ruido_db": -35},
    "transiciones": {"tipo": "corte", "duracion": 0.27},
}


class ErrorEstilo(Exception):
    pass


# --- Carpeta y receta ---------------------------------------------------------------

def preparar_carpeta(raiz: Path) -> Path:
    """Crea estilo_cliente/ con sus subcarpetas y la receta por defecto si no existen."""
    raiz = Path(raiz)
    for sub in ("referencia", "herramientas", "analisis", "pruebas"):
        (raiz / sub).mkdir(parents=True, exist_ok=True)
    receta = raiz / "estilo.json"
    if not receta.exists():
        receta.write_text(json.dumps(ESTILO_BASE, ensure_ascii=False, indent=2), encoding="utf-8")
    return raiz


def _mezclar(base: dict, extra: dict) -> dict:
    r = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        r[k] = _mezclar(r[k], v) if isinstance(v, dict) and isinstance(r.get(k), dict) else v
    return r


def cargar(raiz: Path) -> dict:
    """La receta de estilo.json completada con los valores por defecto. Avisa claro si el JSON está mal."""
    receta = Path(raiz) / "estilo.json"
    if not receta.exists():
        return copy.deepcopy(ESTILO_BASE)
    try:
        datos = json.loads(receta.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ErrorEstilo(f"estilo.json tiene un error en el renglón {e.lineno}: {e.msg}.") from None
    if not isinstance(datos, dict):
        raise ErrorEstilo("estilo.json debe ser un objeto { ... }.")
    return _mezclar(ESTILO_BASE, datos)


def herramienta(raiz: Path, nombre: str, opcional: bool = False) -> Path | None:
    """Ruta de un archivo de herramientas/ (no deja salirse de la carpeta).

    Sin extensión (p. ej. "temas/2026-10-23") busca .png, .jpg, .jpeg, .webp, .mp4 y .mov.
    Con `opcional`, si no existe devuelve None en lugar de error.
    """
    base = (Path(raiz) / "herramientas").resolve()
    ruta = (base / nombre).resolve()
    if base not in ruta.parents and ruta != base:
        raise ErrorEstilo(f"La herramienta «{nombre}» debe estar dentro de estilo_cliente/herramientas.")
    candidatos = [ruta]
    if not ruta.suffix:
        candidatos += [ruta.with_name(ruta.name + e) for e in
                       (".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG", ".JPEG", ".mp4", ".mov", ".MP4", ".MOV")]
    for c in candidatos:
        if c.is_file():
            return c
    if opcional:
        return None
    raise ErrorEstilo(f"No encontré la herramienta «{nombre}» en estilo_cliente/herramientas.")


def _fuente(raiz: Path, fuentes_dir: Path, nombre: str, tamano: int) -> ImageFont.FreeTypeFont:
    for carpeta in (Path(raiz) / "herramientas", Path(fuentes_dir)):
        if (carpeta / nombre).is_file():
            return ImageFont.truetype(str(carpeta / nombre), int(tamano))
    raise ErrorEstilo(f"No encontré la fuente «{nombre}» (ponla en estilo_cliente/herramientas).")


def color(texto: str | None) -> tuple | None:
    """'#RRGGBB' o '#RRGGBBAA' a (r, g, b, a)."""
    if not texto:
        return None
    t = texto.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", t):
        raise ErrorEstilo(f"Color no válido: {texto} (usa #RRGGBB o #RRGGBBAA).")
    v = [int(t[i:i + 2], 16) for i in range(0, len(t), 2)]
    return tuple(v + [255] * (4 - len(v)))


def tramo(desde, hasta, dur: float) -> tuple[float, float]:
    """Convierte desde/hasta (negativos = desde el final, None = final) a segundos absolutos del reel."""
    a = 0.0 if desde is None else float(desde)
    b = dur if hasta is None else float(hasta)
    a = dur + a if a < 0 else a
    b = dur + b if b < 0 else b
    return max(0.0, min(a, dur)), max(0.0, min(b, dur))


# --- Textos y subtítulos como imágenes ----------------------------------------------

def _renglones(d: ImageDraw.ImageDraw, texto: str, f, ancho_max: float) -> list[str]:
    renglones = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if actual and d.textlength(prueba, font=f) > ancho_max:
                renglones.append(actual)
                actual = palabra
            else:
                actual = prueba
        renglones.append(actual)
    return renglones


def _renglones_abajo_largo(d: ImageDraw.ImageDraw, texto: str, f, ancho_max: float) -> list[str] | None:
    """Corte en 2 renglones con el de abajo más largo (como los títulos del cliente). None = no aplica."""
    palabras = texto.split()
    opciones = []
    for k in range(1, len(palabras)):
        r1, r2 = " ".join(palabras[:k]), " ".join(palabras[k:])
        w1, w2 = d.textlength(r1, font=f), d.textlength(r2, font=f)
        if w1 <= w2 <= ancho_max:
            opciones.append((w2, [r1, r2]))
    return min(opciones)[1] if opciones else None


def _caja(lienzo: Image.Image, raiz, fuentes_dir, t: dict, texto: str, visibles: int | None = None) -> None:
    """Dibuja un texto (con caja de fondo y sombra opcionales) sobre el lienzo transparente.

    `visibles` = cuántas letras se ven (efecto máquina de escribir): el texto se acomoda completo
    y solo se dibujan las primeras letras, así cada letra aparece en su lugar final.
    """
    W, H = lienzo.size
    f = _fuente(raiz, fuentes_dir, t.get("fuente", "PublicSans_700Bold.ttf"), t.get("tamano", 48))
    d = ImageDraw.Draw(lienzo)
    renglones = _renglones(d, texto, f, t.get("ancho_max", W - 120))
    if t.get("corte") == "abajo_largo" and len(renglones) == 2 and "\n" not in texto:
        renglones = _renglones_abajo_largo(d, texto, f, t.get("ancho_max", W - 120)) or renglones
    alto_r = f.size * float(t.get("interlineado", 1.2))
    anchos = [d.textlength(r, font=f) for r in renglones]
    pad_x, pad_y = t.get("relleno", [30, 18])
    bw, bh = max(anchos) + 2 * pad_x, alto_r * len(renglones) + 2 * pad_y
    x = t.get("x", "centro")
    x0 = (W - bw) / 2 if x == "centro" else float(x) - bw / 2 if t.get("x_es_centro") else float(x)
    # y = centro vertical de la caja; con "ancla": "arriba", y = donde empieza el primer renglón
    y0 = float(t.get("y", H * 0.8)) - (pad_y if t.get("ancla") == "arriba" else bh / 2)
    fondo = color(t.get("fondo"))
    if fondo:
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), t.get("radio", 22), fill=fondo)
    tinta = color(t.get("color", "#FFFFFF"))
    contorno = color(t.get("contorno"))
    grosor = int(t.get("grosor_contorno", 3)) if contorno else 0
    posiciones, quedan = [], len(texto) if visibles is None else visibles
    for k, (r, w) in enumerate(zip(renglones, anchos)):
        if quedan <= 0:
            break
        trozo = r[:quedan]
        quedan -= len(r) + 1
        alinear = t.get("alinear", "centro")
        tx = x0 + pad_x if alinear == "izquierda" else x0 + (bw - w) / 2
        posiciones.append(((tx, y0 + pad_y + k * alto_r), trozo))
    if t.get("sombra"):
        capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(capa)
        sombra = color(t.get("color_sombra", "#000000B4"))
        dx, dy = t.get("desplazamiento_sombra", [0, 3])
        for (tx, ty), trozo in posiciones:
            ds.text((tx + dx, ty + dy), trozo, font=f, fill=sombra, stroke_width=grosor + 1, stroke_fill=sombra)
        capa = capa.filter(ImageFilter.GaussianBlur(float(t.get("difuminado_sombra", 5))))
        lienzo.alpha_composite(capa)
        d = ImageDraw.Draw(lienzo)
    for (tx, ty), trozo in posiciones:
        d.text((tx, ty), trozo, font=f, fill=tinta, stroke_width=grosor, stroke_fill=contorno)


def trozos_subtitulos(segmentos: list, inicio: float, fin: float, por_renglon: int = 24,
                      max_palabras: int = 0, renglones: int = 2) -> list[tuple]:
    """[(a, b, texto)] en segundos del reel, con el tiempo repartido por letras.

    Bloques de hasta `renglones` renglones de `por_renglon` letras; con `max_palabras` > 0, además,
    bloques cortos de pocas palabras (como los subtítulos automáticos de CapCut).
    """
    salida = []
    for s0, s1, texto in segmentos or []:
        if s1 <= inicio or s0 >= fin or not str(texto).strip():
            continue
        a, b = max(s0, inicio) - inicio, min(s1, fin) - inicio
        bloques = []
        if max_palabras:
            actual: list[str] = []
            for palabra in str(texto).split():
                prueba = " ".join(actual + [palabra])
                if actual and (len(actual) >= max_palabras or len(prueba) > por_renglon * renglones):
                    bloques.append(" ".join(actual))
                    actual = [palabra]
                else:
                    actual.append(palabra)
            if actual:
                bloques.append(" ".join(actual))
            bloques = ["\n".join(textwrap.wrap(x, por_renglon)[:renglones]) for x in bloques]
        else:
            lineas = textwrap.wrap(str(texto).strip(), por_renglon)
            bloques = ["\n".join(lineas[k:k + renglones]) for k in range(0, len(lineas), renglones)]
        letras = sum(len(x) for x in bloques) or 1
        t = a
        for bl in bloques:
            d = (b - a) * len(bl) / letras
            salida.append((round(t, 3), round(t + d, 3), bl))
            t += d
    return salida


def pista_de_textos(estilo: dict, raiz, fuentes_dir, dur: float, valores: dict, subs: list, carpeta: Path) -> Path | None:
    """Una sola pista de imágenes (ffconcat) con todos los textos y subtítulos ya compuestos por tramo.

    Así ffmpeg hace un solo overlay aunque haya cientos de subtítulos.
    """
    fmt = estilo["formato"]
    W, H = int(fmt["ancho"]), int(fmt["alto"])
    eventos = []   # (a, b, tipo, dato)
    for t in estilo.get("textos") or []:
        try:
            texto = str(t.get("texto", "")).format(**valores)
        except (KeyError, IndexError, ValueError):
            raise ErrorEstilo(f"El texto «{t.get('texto')}» usa un dato que no existe. "
                              f"Disponibles: {', '.join('{' + k + '}' for k in valores)}.") from None
        if not texto.strip():
            continue
        a, b = tramo(t.get("desde"), t.get("hasta"), dur)
        if b - a <= 0.05:
            continue
        if t.get("efecto") == "maquina":            # las letras aparecen una a una
            vel = float(t.get("letras_por_segundo", 14))
            n = len(texto)
            pasos = sorted({max(1, round(n * i / 40)) for i in range(1, 41)}) if n > 40 else list(range(1, n + 1))
            tiempos = [a + k / vel for k in pasos]
            for (k, ta), tb in zip(zip(pasos, tiempos), tiempos[1:] + [b]):
                if k < n and ta < b:
                    eventos.append((ta, min(tb, b), "texto", (t, texto, k)))
            fin_escritura = min(a + n / vel, b)
            if b - fin_escritura > 0.01:
                eventos.append((fin_escritura, b, "texto", (t, texto, None)))
        else:
            eventos.append((a, b, "texto", (t, texto, None)))
    st = estilo.get("subtitulos") or {}
    if st.get("activo", True):
        # Los subtítulos no tapan los textos que estén en el mismo lugar (gancho y cierre).
        ocupados = sorted((a, b) for a, b, _, (t, *_) in eventos
                          if abs(float(t.get("y", 0)) - float(st.get("y", 0))) < 150)
        unidos: list[list[float]] = []
        for a, b in ocupados:                        # p. ej. los mil pasitos de la máquina de escribir
            if unidos and a <= unidos[-1][1] + 0.01:
                unidos[-1][1] = max(unidos[-1][1], b)
            else:
                unidos.append([a, b])
        for a, b, tx in subs:
            for oa, ob in unidos:                    # el subtítulo espera a que se quite el texto
                if a < ob and b > oa:
                    if a >= oa:
                        a = ob
                    else:
                        b = oa
            if b - a <= 0.25:
                continue
            tx = tx.upper() if st.get("mayusculas") else tx
            if st.get("efecto") == "palabras":       # las palabras aparecen una a una, ya en su lugar
                palabras = tx.replace("\n", " \n ").split(" ")
                total = sum(len(w) for w in palabras if w != "\n") or 1
                t, visibles = a, 0
                for w in palabras:
                    visibles += len(w) + (0 if w == "\n" else 1)
                    if w == "\n":
                        visibles -= 1
                        continue
                    d = (b - a) * len(w) / total
                    eventos.append((t, min(t + d, b), "sub", (tx, visibles - 1)))
                    t += d
            else:
                eventos.append((a, b, "sub", (tx, None)))
    if not eventos:
        return None
    cortes = sorted({0.0, dur, *[e[0] for e in eventos], *[e[1] for e in eventos]})
    cache, lista = {}, []
    sub_estilo = {"ancho_max": W - 100, "relleno": [28, 16], "radio": 20, "x": "centro",
                  **{k: v for k, v in st.items() if k not in ("activo", "caracteres_por_renglon", "mayusculas",
                                                              "max_palabras", "renglones", "efecto")}}
    for a, b in zip(cortes, cortes[1:]):
        if b - a < 0.001:
            continue
        activos = tuple(i for i, e in enumerate(eventos) if e[0] <= a + 1e-6 and e[1] >= b - 1e-6)
        if activos not in cache:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for i in activos:
                _, _, tipo, dato = eventos[i]
                if tipo == "texto":
                    _caja(img, raiz, fuentes_dir, dato[0], dato[1], dato[2])
                else:
                    _caja(img, raiz, fuentes_dir, sub_estilo, dato[0], dato[1])
            nombre = f"txt{len(cache):04d}.png"
            img.save(carpeta / nombre)
            cache[activos] = nombre
        lista.append((cache[activos], b - a))
    ruta = carpeta / "textos.ffconcat"
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("ffconcat version 1.0\n")
        for nombre, d in lista:
            fh.write(f"file '{nombre}'\nduration {d:.3f}\n")
        fh.write(f"file '{lista[-1][0]}'\n")
    return ruta


# --- ffmpeg --------------------------------------------------------------------------

def tiene_audio(ruta: str) -> bool:
    r = _ejecutar(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", ruta])
    return bool(r.stdout.strip())


def tamano_visible(ruta: str) -> tuple[int, int]:
    """Ancho y alto como se ve el video (los celulares guardan la rotación aparte), en pares."""
    r = _ejecutar(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=width,height:stream_side_data=rotation:stream_tags=rotate", "-of", "json", ruta])
    st = (json.loads(r.stdout).get("streams") or [{}])[0]
    w, h = int(st.get("width", 1080)), int(st.get("height", 1920))
    rot = st.get("tags", {}).get("rotate") or next((d.get("rotation") for d in st.get("side_data_list", [])
                                                     if "rotation" in d), 0)
    if abs(int(float(rot or 0))) % 180 == 90:
        w, h = h, w
    return w - w % 2, h - h % 2


def _zoom(z: float, w: int, h: int, foco_y: float = 0.3) -> str:
    """Acercamiento (punch-in) de un tramo: recorta al centro y regresa al mismo tamaño."""
    cw, ch = int(w / z) // 2 * 2, int(h / z) // 2 * 2
    return f",crop={cw}:{ch}:{(w - cw) // 2}:{int((h - ch) * foco_y)},scale={w}:{h}:flags=lanczos"


def _encuadre(fmt: dict, entrada: str, salida: str) -> str:
    W, H, fps = int(fmt["ancho"]), int(fmt["alto"]), fmt.get("fps", 30)
    modo = fmt.get("encuadre", "fondo_difuminado")
    if modo == "llenar":
        fy = float(fmt.get("foco_y", 0.35))
        return (f"[{entrada}]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{fy:.3f},fps={fps},setsar=1[{salida}]")
    if modo == "ajustar":
        rel = fmt.get("color_relleno", "#000000").lstrip("#")[:6]
        return (f"[{entrada}]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{rel},fps={fps},setsar=1[{salida}]")
    return (f"[{entrada}]split=2[{salida}_a][{salida}_b];"
            f"[{salida}_a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2,"
            f"eq=brightness=-0.10[{salida}_f];"
            f"[{salida}_b]scale={W}:{H}:force_original_aspect_ratio=decrease[{salida}_c];"
            f"[{salida}_f][{salida}_c]overlay=(W-w)/2:(H-h)/2,fps={fps},setsar=1[{salida}]")


def filtro_mejora(m: dict, brillo: float | None) -> str:
    """Luz, contraste, color, grano y enfoque del video."""
    partes = []
    if m.get("quitar_grano"):
        partes.append("hqdn3d=2:1.5:3:3")
    delta = 0.0
    if m.get("luz") and brillo is not None:
        delta = max(-0.06, min(0.12, (115 - brillo) / 255))
    partes.append(f"eq=brightness={delta:.3f}:contrast={m.get('contraste', 1.0)}:"
                  f"saturation={m.get('saturacion', 1.0)}:gamma={m.get('gamma', 1.0)}")
    if m.get("nitidez"):
        partes.append(f"unsharp=5:5:{float(m['nitidez']):.2f}:5:5:0")
    return ",".join(partes)


def filtro_audio(m: dict) -> str:
    """Quita ruido exterior (zumbidos, aire, ventiladores) y deja el volumen parejo para redes."""
    partes = ["aresample=48000", "aformat=channel_layouts=stereo"]
    if m.get("quitar_ruido"):
        partes += ["highpass=f=80", "lowpass=f=12000", "afftdn=nf=-25",
                   "acompressor=threshold=-20dB:ratio=3:attack=10:release=200"]
    if m.get("volumen_lufs") is not None:
        partes.append(f"loudnorm=I={float(m['volumen_lufs'])}:TP=-1.5:LRA=9")
    return ",".join(partes)


def _normalizar_clip(i: int, fmt: dict, audio: bool, dur: float, etiqueta: str) -> list[str]:
    """Intro o cierre al mismo tamaño, cuadros por segundo y audio que el reel."""
    W, H, fps = int(fmt["ancho"]), int(fmt["alto"]), fmt.get("fps", 30)
    f = [f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},setsar=1,"
         f"format=yuv420p[{etiqueta}v]"]
    if audio:
        f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[{etiqueta}a]")
    else:
        f.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{dur:.3f}[{etiqueta}a]")
    return f


def partes_con_voz(entrada: str, inicio: float, fin: float, cfg: dict | None) -> list[tuple[float, float]]:
    """Tramos del video (segundos de la grabación) que se quedan al quitar las pausas largas.

    Así edita el cliente: corta los silencios para que el reel vaya al grano. Se deja un margen
    para que no se coman sílabas. Sin `quitar_pausas`, un solo tramo [inicio, fin].
    """
    if not cfg or not cfg.get("activo"):
        return [(inicio, fin)]
    from .ffmpeg import parsear_silencios
    minimo = float(cfg.get("minimo", 0.6))
    margen = float(cfg.get("margen", 0.15))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{inicio:.3f}", "-t", f"{fin - inicio:.3f}",
                        "-i", str(entrada), "-vn", "-af", f"silencedetect=noise={cfg.get('ruido_db', -35)}dB:d={minimo}",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    cortes = [(inicio + a + margen, inicio + b - margen) for a, b in parsear_silencios(r.stderr)
              if b - a - 2 * margen > 0.1]
    partes, t = [], inicio
    for a, b in cortes:
        if a > t:
            partes.append((t, a))
        t = max(t, b)
    if fin > t:
        partes.append((t, fin))
    partes = [(a, b) for a, b in partes if b - a >= 0.25]
    return partes or [(inicio, fin)]


def a_salida(t: float, partes: list, puentes: list | None = None) -> float:
    """Segundo de la grabación → segundo del reel.

    `puentes[k]` = segundos de cuadros intermedios que se agregan después del tramo k (transición).
    Si `t` cae en una pausa cortada, va al puente (o al inicio del siguiente tramo).
    """
    puentes = puentes or [0.0] * len(partes)
    off = 0.0
    for k, (a, b) in enumerate(partes):
        if t < a:
            return off
        if t <= b:
            return off + t - a
        off += b - a
        extra = puentes[k] if k < len(puentes) else 0.0
        if k + 1 < len(partes) and t < partes[k + 1][0]:
            return off + min(t - b, extra)
        off += extra
    return off


def segmentos_en_reel(segmentos: list, partes: list, puentes: list | None = None) -> list:
    """Los segmentos de Whisper pasados a la línea de tiempo del reel ya sin pausas."""
    ini, fin = partes[0][0], partes[-1][1]
    salida = []
    for s0, s1, texto in segmentos or []:
        if s1 <= ini or s0 >= fin:
            continue
        a, b = a_salida(max(s0, ini), partes, puentes), a_salida(min(s1, fin), partes, puentes)
        if b - a > 0.15:
            salida.append([round(a, 3), round(b, 3), texto])
    return salida


def puentes_de(partes: list, cfg: dict | None, fps: float) -> list[float]:
    """Segundos de cuadros intermedios en cada corte (0 = corte seco). Nunca más largo que la pausa quitada."""
    tipo = (cfg or {}).get("tipo", "corte")
    if tipo not in ("morph", "disolver"):
        return [0.0] * max(len(partes) - 1, 0)
    dmax = float((cfg or {}).get("duracion", 0.27))
    salida = []
    for (_, b), (a2, _) in zip(partes, partes[1:]):
        d = int(min(dmax, a2 - b) * fps) / fps
        salida.append(round(d, 4) if d >= 2 / fps else 0.0)
    return salida


def _puente(fc: list, k: int, fin_a: float, ini_b: float, d: float, fps: float, modo: str) -> str:
    """Cuadros intermedios entre el último cuadro del tramo k y el primero del k+1.

    `morph`: minterpolate con flujo óptico (la cabeza y las manos se mueven poco a poco de una toma a
    la otra). `disolver`: mezcla suave de las dos. Devuelve la etiqueta del clip de `d` segundos.
    """
    f = 1.0 / fps
    fc.append(f"[ul{k}]trim=start={max(fin_a - 2.5 * f, 0):.4f}:end={fin_a:.4f},setpts=PTS-STARTPTS,"
              f"reverse,trim=end_frame=1,setpts=PTS-STARTPTS,loop=1:1:0[L{k}]")
    fc.append(f"[pr{k}]trim=start={ini_b:.4f}:end={ini_b + 2.5 * f:.4f},setpts=PTS-STARTPTS,"
              f"trim=end_frame=1,setpts=PTS-STARTPTS,loop=1:1:0[F{k}]")
    # Bloques de 16 px y búsqueda amplia: con cabeceos grandes evita el «doble rostro».
    mi = ("mi_mode=mci:mc_mode=aobmc:me_mode=bidir:mb_size=16:search_param=128:vsbmc=1:scd=none"
          if modo == "morph" else "mi_mode=blend:scd=none")
    # Cuadros en 0 y f (último de A, repetido), f+d y 2f+d (primero de B, repetido): minterpolate
    # solo calcula los cuadros que faltan entre f y f+d (necesita 2 cuadros de cada lado).
    fc.append(f"[L{k}][F{k}]concat=n=2,setpts='(N*{f:.6f}+gte(N,2)*{d - f:.6f})/TB',minterpolate=fps={fps}:{mi},"
              f"trim=start={1.5 * f:.4f}:end={d + 1.5 * f:.4f},setpts=PTS-STARTPTS[pu{k}]")
    return f"[pu{k}]"


def editar_reel(entrada: str, inicio: float, fin: float, salida: Path, raiz: Path, fuentes_dir: Path,
                segmentos: list | None = None, valores: dict | None = None, estilo: dict | None = None) -> dict:
    """Arma el reel [inicio, fin] de `entrada` con la receta de estilo. Devuelve un resumen."""
    raiz = Path(raiz)
    estilo = estilo or cargar(raiz)
    fmt, mej = estilo["formato"], estilo["mejora"]
    W, H, fps = int(fmt["ancho"]), int(fmt["alto"]), fmt.get("fps", 30)
    if fin - inicio <= 0.5:
        raise ErrorEstilo("El tramo del reel es demasiado corto.")
    valores = {"tema": "", "fecha": "", "fecha_iso": "", "canal": "", "frase": "", **(valores or {})}
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    partes = partes_con_voz(entrada, inicio, fin, estilo.get("quitar_pausas"))
    trans = estilo.get("transiciones") or {}
    puentes = puentes_de(partes, trans, fps)
    dur = round(sum(b - a for a, b in partes) + sum(puentes), 3)
    st = estilo.get("subtitulos") or {}
    subs = trozos_subtitulos(segmentos_en_reel(segmentos or [], partes, puentes), 0, dur,
                             int(st.get("caracteres_por_renglon", 24)), int(st.get("max_palabras", 0)),
                             int(st.get("renglones", 2)))

    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        args = ["ffmpeg", "-hide_banner", "-nostats", "-y",
                "-ss", f"{inicio:.3f}", "-t", f"{fin - inicio:.3f}", "-i", str(Path(entrada).resolve())]
        n = 1
        fc = []
        con_audio = tiene_audio(entrada)
        brillo = brillo_promedio(entrada, inicio, fin) if mej.get("luz") else None

        # 1. Mejora, cortes de pausas (con cuadros intermedios) y encuadre del video principal
        np_ = len(partes)
        rel = [(a - inicio, b - inicio) for a, b in partes]
        base = f"[0:v]fps={fps},{filtro_mejora(mej, brillo)}"
        if np_ == 1:
            fc.append(f"{base},setpts=PTS-STARTPTS[m0]")
            if con_audio:
                fc.append("[0:a]asetpts=PTS-STARTPTS[ac]")
        else:
            con_puente = [k for k, d in enumerate(puentes) if d > 0]
            salidas = [f"[vs{k}]" for k in range(np_)] + [f"[ul{k}]" for k in con_puente] + [f"[pr{k}]" for k in con_puente]
            fc.append(f"{base},split={len(salidas)}" + "".join(salidas))
            if con_audio:
                fc.append(f"[0:a]asplit={np_}" + "".join(f"[as{k}]" for k in range(np_)))
            union, piezas = "", 0
            for k, (a, b) in enumerate(rel):
                extra = puentes[k] if k < len(puentes) else 0.0
                fc.append(f"[vs{k}]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[vp{k}]")
                union += f"[vp{k}]"
                piezas += 1
                if con_audio:   # el audio del puente es el de la pausa real (ambiente), así no se nota
                    fin_a = b + extra
                    fc.append(f"[as{k}]atrim=start={a:.4f}:end={fin_a:.4f},asetpts=PTS-STARTPTS,"
                              f"afade=t=in:d=0.03,afade=t=out:st={max(fin_a - a - 0.05, 0):.4f}:d=0.05[ap{k}]")
                if extra:
                    union += _puente(fc, k, b, rel[k + 1][0], extra, fps, trans.get("tipo"))
                    piezas += 1
            fc.append(union + f"concat=n={piezas}:v=1:a=0[m0]")
            if con_audio:
                fc.append("".join(f"[ap{k}]" for k in range(np_)) + f"concat=n={np_}:v=0:a=1[ac]")
        fc.append(_encuadre(fmt, "m0", "m1"))
        actual = "m1"

        # 2. Capas del cliente (imágenes y animaciones)
        usadas = 0
        for k, c in enumerate(estilo.get("capas") or []):
            try:
                nombre = str(c["archivo"]).format(**valores)
            except (KeyError, IndexError, ValueError):
                raise ErrorEstilo(f"La capa «{c.get('archivo')}» usa un dato que no existe.") from None
            ruta = herramienta(raiz, nombre, opcional=bool(c.get("opcional")))
            if ruta is None:
                continue
            ext = ruta.suffix.lower()
            a, b = tramo(c.get("desde"), c.get("hasta"), dur)
            if b - a <= 0.05:
                continue
            if ext in IMAGEN:
                args += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(ruta)]
            elif ext in VIDEO:
                if c.get("repetir", False):
                    args += ["-stream_loop", "-1"]
                if ext == ".gif":
                    args += ["-ignore_loop", "0"] if c.get("repetir", False) else []
                args += ["-t", f"{b - a:.3f}", "-i", str(ruta)]
            else:
                raise ErrorEstilo(f"«{nombre}» no es imagen ni animación.")
            filtros = [f"fps={fps}", "format=rgba"]
            if c.get("croma"):          # fondo verde/negro de la animación → transparente
                filtros.insert(0, f"colorkey=0x{c['croma'].lstrip('#')[:6]}:{c.get('croma_similitud', 0.3)}:0.1")
            cw, ch = int(c.get("ancho", -1)), int(c.get("alto", -1))
            if cw > 0 and ch > 0 and c.get("ajuste", "cubrir") == "cubrir":
                filtros.append(f"scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch}")
            elif cw > 0 or ch > 0:
                filtros.append(f"scale={cw}:{ch}")
            if c.get("opacidad", 1) < 1:
                filtros.append(f"colorchannelmixer=aa={float(c['opacidad']):.2f}")
            if ext in VIDEO:
                filtros.append(f"setpts=PTS-STARTPTS+{a:.3f}/TB")
            fd = float(c.get("fundido", 0.3))
            if fd:
                filtros.append(f"fade=t=in:st={a:.3f}:d={fd}:alpha=1")
                if b < dur - 0.01:
                    filtros.append(f"fade=t=out:st={max(b - fd, a):.3f}:d={fd}:alpha=1")
            fc.append(f"[{n}:v]" + ",".join(filtros) + f"[c{k}]")
            x = c.get("x", 0)
            y = c.get("y", 0)
            x = "(W-w)/2" if x == "centro" else str(x)
            y = "(H-h)/2" if y == "centro" else str(y)
            fc.append(f"[{actual}][c{k}]overlay={x}:{y}:eof_action=pass:enable='between(t,{a:.3f},{b:.3f})'[o{k}]")
            actual = f"o{k}"
            n += 1
            usadas += 1

        # 3. Textos y subtítulos
        pista = pista_de_textos(estilo, raiz, fuentes_dir, dur, valores, subs, tmpd)
        if pista:
            args += ["-f", "concat", "-safe", "0", "-i", pista.name]
            fc.append(f"[{n}:v]fps={fps},format=rgba[tx]")
            fc.append(f"[{actual}][tx]overlay=0:0:eof_action=pass[t1]")
            actual = "t1"
            n += 1
        fd = float(estilo.get("fundido") or 0)
        cola = f",fade=t=in:d={fd},fade=t=out:st={max(dur - fd, 0):.3f}:d={fd}" if fd else ""
        fc.append(f"[{actual}]format=yuv420p{cola},trim=duration={dur:.3f}[vp]")

        # Audio del reel (+ música)
        if con_audio:
            fc.append(f"[ac]{filtro_audio(mej)}[ap0]")
        else:
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{dur:.3f}[ap0]")
        musica = estilo.get("musica")
        if musica and musica.get("archivo"):
            args += ["-stream_loop", "-1", "-t", f"{dur:.3f}", "-i", str(herramienta(raiz, musica["archivo"]))]
            vol = float(musica.get("volumen", 0.12))
            fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol}[mu]")
            fc.append("[ap0][mu]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[ap1]")
            n += 1
        else:
            fc.append("[ap0]anull[ap1]")
        fc.append(f"[ap1]apad,atrim=0:{dur:.3f},afade=t=out:st={max(dur - 0.3, 0):.3f}:d=0.3[ap]")

        # 4. Intro y cierre
        partes_finales = []
        total = dur
        for cual in ("intro", "cierre"):
            clip = estilo.get(cual)
            if not clip or not clip.get("archivo"):
                continue
            ruta = herramienta(raiz, clip["archivo"])
            if ruta.suffix.lower() in IMAGEN:
                dclip = float(clip.get("segundos", 2))
                args += ["-loop", "1", "-framerate", str(fps), "-t", f"{dclip:.3f}", "-i", str(ruta)]
                audio_clip = False
            else:
                dclip = duracion(str(ruta))
                if clip.get("segundos"):
                    dclip = min(dclip, float(clip["segundos"]))
                args += ["-t", f"{dclip:.3f}", "-i", str(ruta)]
                audio_clip = tiene_audio(str(ruta))
            if clip.get("audio"):              # p. ej. la música del cierre del cliente
                ruta_a = herramienta(raiz, clip["audio"])
                args += ["-i", str(ruta_a)]
                fc += _normalizar_clip(n, fmt, False, dclip, cual)[:1]
                ganancia = float(clip.get("ganancia_db", 0))
                fc.append(f"[{n + 1}:a]aresample=48000,aformat=channel_layouts=stereo,volume={ganancia}dB,"
                          f"apad,atrim=0:{dclip:.3f},afade=t=in:d=0.02[{cual}a]")
                n += 1
            else:
                fc += _normalizar_clip(n, fmt, audio_clip, dclip, cual)
            partes_finales.append((cual, f"[{cual}v][{cual}a]"))
            total += dclip
            n += 1
        orden = [p for c, p in partes_finales if c == "intro"] + ["[vp][ap]"] + \
                [p for c, p in partes_finales if c == "cierre"]
        negro = float(estilo.get("negro_final") or 0)
        if len(orden) > 1:
            fc.append("".join(orden) + "concat=n=" + str(len(orden)) + ":v=1:a=1[vc2][aout]")
            ultimo = "vc2"
        else:
            fc.append("[vp]null[vc2]")
            fc.append("[ap]anull[aout]")
            ultimo = "vc2"
        if negro:
            fc.append(f"[{ultimo}]fade=t=out:st={max(total - negro, 0):.3f}:d={negro}[vout]")
            fc.append(f"[aout]afade=t=out:st={max(total - negro, 0):.3f}:d={negro},alimiter=limit=0.95[afin]")
        else:
            fc.append(f"[{ultimo}]null[vout]")
            fc.append("[aout]alimiter=limit=0.95[afin]")
        mapa = ["-map", "[vout]", "-map", "[afin]"]

        args += ["-filter_complex", ";".join(fc), *mapa, "-r", str(fps),
                 "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(salida.resolve())]
        _ejecutar(args, cwd=tmp, timeout=3600)
    return {"duracion": round(total, 2), "subtitulos": len(subs), "capas": usadas, "ancho": W, "alto": H,
            "tramos": len(partes), "transiciones": sum(1 for d in puentes if d),
            "sin_pausas": round(fin - inicio - dur, 2)}


# --- Análisis de la referencia del cliente -----------------------------------------

def _probe(ruta: str) -> dict:
    r = _ejecutar(["ffprobe", "-v", "error", "-show_entries",
                   "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels",
                   "-of", "json", ruta])
    return json.loads(r.stdout)


def analizar(ruta: Path, salida: Path, max_cuadros: int = 36) -> dict:
    """Mide la referencia (tamaño, duración, cortes, brillo, color, volumen) y saca cuadros para revisarla.

    Deja en `salida/`: cuadros/*.jpg (uno por cada corte de escena y cada 2 s), hoja.jpg (todos juntos)
    y datos.json. Con eso se arma estilo.json para que los reels queden igual.
    """
    ruta, salida = Path(ruta), Path(salida)
    cuadros = salida / "cuadros"
    if cuadros.exists():
        shutil.rmtree(cuadros)
    cuadros.mkdir(parents=True)
    info = _probe(str(ruta))
    dur = float(info["format"]["duration"])
    video = next((s for s in info["streams"] if s.get("codec_type") == "video"), {})
    num, _, den = str(video.get("r_frame_rate", "30/1")).partition("/")
    fps = round(float(num) / float(den or 1), 2) if float(den or 1) else 30

    # Cortes de escena
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-vf",
                        "select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    cortes = [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]

    # Brillo y saturación (1 cuadro por segundo)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-vf",
                        "fps=1,scale=320:-2,signalstats,metadata=print", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    yavg = [float(v) for v in re.findall(r"YAVG=([\d.]+)", r.stderr)]
    savg = [float(v) for v in re.findall(r"SATAVG=([\d.]+)", r.stderr)]

    # Volumen (LUFS integrados)
    lufs = None
    if any(s.get("codec_type") == "audio" for s in info["streams"]):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        lufs = float(m[-1]) if m else None

    # Cuadros: cortes + cada 2 s
    tiempos = sorted({0.3, *cortes, *[t + 0.4 for t in cortes], *[float(t) for t in range(2, int(dur), 2)]})
    tiempos = [t for t in tiempos if t < dur - 0.05]
    if len(tiempos) > max_cuadros:
        paso = len(tiempos) / max_cuadros
        tiempos = [tiempos[int(i * paso)] for i in range(max_cuadros)]
    hechos = []
    for t in tiempos:
        destino = cuadros / f"t{t:07.2f}.jpg"
        try:
            _ejecutar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(ruta),
                       "-frames:v", "1", "-vf", "scale=540:-2", str(destino)])
            hechos.append((t, destino))
        except ErrorFfmpeg:
            continue
    if hechos:
        _hoja(hechos, salida / "hoja.jpg")
    datos = {
        "archivo": ruta.name, "duracion": round(dur, 2), "ancho": video.get("width"), "alto": video.get("height"),
        "fps": fps, "cortes_de_escena": cortes, "brillo_promedio": round(sum(yavg) / len(yavg), 1) if yavg else None,
        "saturacion_promedio": round(sum(savg) / len(savg), 1) if savg else None, "volumen_lufs": lufs,
        "cuadros": [p.name for _, p in hechos],
    }
    (salida / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return datos


def _hoja(cuadros: list, destino: Path, columnas: int = 6) -> None:
    """Todos los cuadros en una sola imagen, con su segundo, para ver la edición de un vistazo."""
    imgs = [(t, Image.open(p).convert("RGB")) for t, p in cuadros]
    w = 270
    h = max(int(im.height * w / im.width) for _, im in imgs)
    filas = (len(imgs) + columnas - 1) // columnas
    hoja = Image.new("RGB", (columnas * w, filas * (h + 26)), (20, 20, 20))
    d = ImageDraw.Draw(hoja)
    for i, (t, im) in enumerate(imgs):
        x, y = (i % columnas) * w, (i // columnas) * (h + 26)
        hoja.paste(im.resize((w, int(im.height * w / im.width))), (x, y + 26))
        d.text((x + 6, y + 6), f"{t:.1f} s", fill=(255, 220, 120))
    hoja.save(destino, quality=88)
