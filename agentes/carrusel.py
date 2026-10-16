"""Agente de carrusel (fase 3).

Dos días antes de cada lunes y viernes genera 5 imágenes de invitación (1080×1350) en
blanco y vino, más el texto para publicar, y las deja en la bandeja como pendientes:

  1. Invitación   2. Misterios del día   3. En vivo   4. Intenciones   5. Cierre
"""
from datetime import date
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from app.bandeja import crear_paquete
from app.modelos import Paquete

from . import fechas

ANCHO, ALTO = 1080, 1350
MARGEN = 96

# Colores de las piezas para redes (CLAUDE.md §4.4): no usan el morado de la app.
BLANCO = "#ffffff"
CREMA = "#fbf9f7"
VINO = "#7a1c2e"
VINO_SUAVE = "#f3e4e7"
TEXTO = "#3a1420"
ORO = "#8f6b10"
# Tonos intermedios del vino para la diapositiva de fondo vino y sus líneas
VINO_MEDIO = "#8e2b3e"
VINO_LINEA = "#9c4255"
ROSA_LINEA = "#e5c9cf"

REDES_EN_VIVO = ["YouTube", "Facebook", "Instagram", "TikTok", "Canal de TV"]


# --- Utilidades de dibujo -----------------------------------------------------------

def _fuente(nombre: str, tamano: int) -> ImageFont.FreeTypeFont:
    archivos = {
        "titulo": "Spectral_700Bold.ttf",
        "cita": "Spectral_400Regular_Italic.ttf",
        "texto": "PublicSans_400Regular.ttf",
        "semi": "PublicSans_600SemiBold.ttf",
        "negrita": "PublicSans_700Bold.ttf",
        "extra": "PublicSans_800ExtraBold.ttf",
    }
    return ImageFont.truetype(str(Path(current_app.config["FUENTES_DIR"]) / archivos[nombre]), tamano)


def _ancho(d: ImageDraw.ImageDraw, texto: str, fuente, espaciado: float = 0) -> float:
    return d.textlength(texto, font=fuente) + espaciado * max(len(texto) - 1, 0)


def _partir(d: ImageDraw.ImageDraw, texto: str, fuente, ancho_max: float) -> list[str]:
    """Parte un texto en renglones que quepan en `ancho_max`."""
    renglones: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if actual and _ancho(d, prueba, fuente) > ancho_max:
                renglones.append(actual)
                actual = palabra
            else:
                actual = prueba
        renglones.append(actual)
    return renglones


def _parrafo(d, xy, texto, fuente, color, ancho_max, interlineado=1.25, centrado=False) -> int:
    """Escribe un párrafo con saltos de línea automáticos. Devuelve la y donde terminó."""
    x, y = xy
    alto = fuente.size * interlineado
    for renglon in _partir(d, texto, fuente, ancho_max):
        rx = x + (ancho_max - _ancho(d, renglon, fuente)) / 2 if centrado else x
        d.text((rx, y), renglon, font=fuente, fill=color)
        y += alto
    return int(y)


def _ajustar(d, texto, nombre_fuente, tamano, ancho_max, max_renglones) -> ImageFont.FreeTypeFont:
    """Baja el tamaño de letra hasta que el texto quepa en `max_renglones`."""
    while tamano > 28:
        f = _fuente(nombre_fuente, tamano)
        if len(_partir(d, texto, f, ancho_max)) <= max_renglones:
            return f
        tamano -= 4
    return _fuente(nombre_fuente, tamano)


def _etiqueta(d, xy, texto, color, tamano=26, centrado_en: float | None = None) -> None:
    """Texto pequeño en mayúsculas con espacio entre letras (eyebrow)."""
    f = _fuente("negrita", tamano)
    texto = texto.upper()
    espacio = tamano * 0.16
    x, y = xy
    if centrado_en is not None:
        x = centrado_en - _ancho(d, texto, f, espacio) / 2
    for letra in texto:
        d.text((x, y), letra, font=f, fill=color)
        x += d.textlength(letra, font=f) + espacio


def _cruz(d, centro, tam, color) -> None:
    cx, cy = centro
    g = max(tam // 7, 4)
    d.rectangle([cx - g / 2, cy - tam / 2, cx + g / 2, cy + tam / 2], fill=color)
    d.rectangle([cx - tam * 0.32, cy - tam * 0.2 - g / 2, cx + tam * 0.32, cy - tam * 0.2 + g / 2], fill=color)


def _pie(d, numero: int, color_texto: str, color_linea: str) -> None:
    canal = current_app.config["CANAL_NOMBRE"]
    d.line([(MARGEN, ALTO - 130), (ANCHO - MARGEN, ALTO - 130)], fill=color_linea, width=2)
    d.text((MARGEN, ALTO - 104), canal, font=_fuente("negrita", 30), fill=color_texto)
    f = _fuente("semi", 28)
    marca = f"{numero} / 5"
    d.text((ANCHO - MARGEN - d.textlength(marca, font=f), ALTO - 102), marca, font=f, fill=color_texto)


def _lienzo(fondo: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (ANCHO, ALTO), fondo)
    return img, ImageDraw.Draw(img)


def _marco(d, color) -> None:
    d.rounded_rectangle([36, 36, ANCHO - 36, ALTO - 36], radius=28, outline=color, width=3)


# --- Las 5 diapositivas -------------------------------------------------------------

def _invitacion(f: date) -> Image.Image:
    img, d = _lienzo(CREMA)
    _marco(d, VINO_SUAVE)
    ancho = ANCHO - 2 * MARGEN
    _cruz(d, (ANCHO / 2, 250), 96, VINO)
    _etiqueta(d, (0, 350), "Evento en vivo", ORO, 30, centrado_en=ANCHO / 2)
    y = _parrafo(d, (MARGEN, 420), "Te invitamos a rezar juntos", _fuente("titulo", 104), TEXTO, ancho,
                 interlineado=1.08, centrado=True)
    # Bloque vino con la fecha y la hora
    caja = [MARGEN + 40, y + 50, ANCHO - MARGEN - 40, y + 300]
    d.rounded_rectangle(caja, radius=26, fill=VINO)
    fecha_txt = fechas.nombre_fecha(f)
    ft = _ajustar(d, fecha_txt, "extra", 64, caja[2] - caja[0] - 60, 1)
    d.text(((ANCHO - d.textlength(fecha_txt, font=ft)) / 2, caja[1] + 52), fecha_txt, font=ft, fill=BLANCO)
    hora = "10:00 am · hora CDMX"
    fh = _fuente("semi", 40)
    d.text(((ANCHO - d.textlength(hora, font=fh)) / 2, caja[1] + 150), hora, font=fh, fill=VINO_SUAVE)
    _parrafo(d, (MARGEN, caja[3] + 60), fechas.misterios(f)["nombre"], _fuente("cita", 52), VINO, ancho, centrado=True)
    _pie(d, 1, TEXTO, VINO_SUAVE)
    return img


def _misterios(f: date) -> Image.Image:
    img, d = _lienzo(BLANCO)
    m = fechas.misterios(f)
    ancho = ANCHO - 2 * MARGEN
    _etiqueta(d, (MARGEN, 120), f"Los misterios del {fechas.DIAS[f.weekday()]}", ORO, 28)
    _parrafo(d, (MARGEN, 170), m["nombre"], _fuente("titulo", 92), VINO, ancho, interlineado=1.05)
    y = 350
    f_num = _fuente("titulo", 58)
    f_texto = _fuente("semi", 44)
    f_cita = _fuente("texto", 30)
    for i, (nombre, cita) in enumerate(m["lista"], start=1):
        d.ellipse([MARGEN, y, MARGEN + 84, y + 84], fill=VINO_SUAVE)
        n = str(i)
        d.text((MARGEN + 42 - d.textlength(n, font=f_num) / 2, y + 2), n, font=f_num, fill=VINO)
        fin_y = _parrafo(d, (MARGEN + 116, y + 6), nombre, f_texto, TEXTO, ancho - 116, interlineado=1.18)
        d.text((MARGEN + 116, fin_y + 4), cita, font=f_cita, fill=ORO)
        y = max(y + 104, fin_y + 46) + 44
    _pie(d, 2, TEXTO, VINO_SUAVE)
    return img


def _en_vivo(f: date) -> Image.Image:
    img, d = _lienzo(VINO)
    ancho = ANCHO - 2 * MARGEN
    # Punto "en vivo"
    d.ellipse([MARGEN, 136, MARGEN + 30, 166], fill=BLANCO)
    _etiqueta(d, (MARGEN + 50, 136), "En vivo", BLANCO, 30)
    y = _parrafo(d, (MARGEN, 220), "Acompáñanos desde donde estés", _fuente("titulo", 96), BLANCO, ancho,
                 interlineado=1.06)
    y += 50
    f_red = _fuente("negrita", 44)
    for red in REDES_EN_VIVO:
        d.rounded_rectangle([MARGEN, y, ANCHO - MARGEN, y + 96], radius=22, fill=VINO_MEDIO)
        d.text((MARGEN + 40, y + 22), red, font=f_red, fill=BLANCO)
        y += 116
    enlace = current_app.config["CANAL_ENLACE"]
    detalle = f"{fechas.nombre_fecha(f)} · 10:00 am" + (f"\n{enlace}" if enlace else "")
    _parrafo(d, (MARGEN, y + 20), detalle, _fuente("semi", 36), VINO_SUAVE, ancho, interlineado=1.35)
    _pie(d, 3, BLANCO, VINO_LINEA)
    return img


def _intenciones(f: date) -> Image.Image:
    img, d = _lienzo(VINO_SUAVE)
    ancho = ANCHO - 2 * MARGEN
    d.rounded_rectangle([MARGEN - 24, 170, ANCHO - MARGEN + 24, ALTO - 210], radius=34, fill=BLANCO)
    _cruz(d, (ANCHO / 2, 360), 80, VINO)
    _etiqueta(d, (0, 450), "Tus intenciones", ORO, 30, centrado_en=ANCHO / 2)
    y = _parrafo(d, (MARGEN + 20, 520), "¿Por quién quieres que recemos?", _fuente("titulo", 88), TEXTO,
                 ancho - 40, interlineado=1.08, centrado=True)
    _parrafo(d, (MARGEN + 40, y + 40),
             "Escríbelas en los comentarios y las presentaremos a la Virgen María durante el evento.",
             _fuente("texto", 42), TEXTO, ancho - 80, interlineado=1.4, centrado=True)
    _pie(d, 4, TEXTO, ROSA_LINEA)
    return img


def _cierre(f: date) -> Image.Image:
    img, d = _lienzo(CREMA)
    _marco(d, VINO_SUAVE)
    ancho = ANCHO - 2 * MARGEN
    d.text((MARGEN, 160), "“", font=_fuente("titulo", 220), fill=VINO_SUAVE)
    y = _parrafo(d, (MARGEN, 330), "Hagan lo que Él les diga.", _fuente("cita", 96), VINO, ancho, interlineado=1.1)
    d.text((MARGEN, y + 30), "Jn 2,5", font=_fuente("semi", 34), fill=ORO)
    y += 150
    d.line([(MARGEN, y), (MARGEN + 120, y)], fill=ORO, width=4)
    y = _parrafo(d, (MARGEN, y + 50), "Te esperamos", _fuente("titulo", 84), TEXTO, ancho)
    _parrafo(d, (MARGEN, y + 10), f"{fechas.nombre_fecha(f)}\n10:00 am · hora CDMX", _fuente("semi", 42), TEXTO,
             ancho, interlineado=1.35)
    _pie(d, 5, TEXTO, VINO_SUAVE)
    return img


DIAPOSITIVAS = [_invitacion, _misterios, _en_vivo, _intenciones, _cierre]


# --- Texto y paquete ----------------------------------------------------------------

def texto_carrusel(f: date) -> str:
    m = fechas.misterios(f)
    enlace = current_app.config["CANAL_ENLACE"]
    canal = current_app.config["CANAL_NOMBRE"].replace(" ", "")
    lineas = [
        "🙏 Evento en vivo",
        "",
        f"{fechas.nombre_fecha(f)} · 10:00 am (hora CDMX)",
        f"Meditaremos los {m['nombre'].lower()}.",
        "",
        "Deja tus intenciones en los comentarios y las presentaremos a la Virgen durante el evento.",
    ]
    if enlace:
        lineas += ["", f"Síguelo en vivo: {enlace}"]
    lineas += ["", f"#SantoRosario #{canal} #Misterios{m['tipo'].capitalize()} #RosarioEnVivo #Fe #Oración"]
    return "\n".join(lineas)


def generar_imagenes(f: date, carpeta: Path) -> list[str]:
    carpeta.mkdir(parents=True, exist_ok=True)
    nombres = []
    for i, dibujar in enumerate(DIAPOSITIVAS, start=1):
        nombre = f"{i}.png"
        dibujar(f).save(carpeta / nombre, "PNG", optimize=True)
        nombres.append(nombre)
    return nombres


def preparar_carrusel(f: date, forzar: bool = False) -> Paquete | None:
    """Genera el carrusel de un evento y lo mete a la bandeja.

    No hace nada si ya hay uno (pendiente, aprobado o rechazado), salvo con `forzar=True`.
    """
    if not fechas.es_dia_de_evento(f):
        raise ValueError(f"{f} no es lunes ni viernes.")
    existentes = Paquete.query.filter_by(tipo="carrusel", fecha_evento=f).count()
    if existentes and not forzar:
        return None
    carpeta_rel = f"{f.isoformat()}/carrusel" + (f"-{existentes + 1}" if existentes else "")
    carpeta = Path(current_app.config["PAQUETES_DIR"]) / carpeta_rel
    archivos = generar_imagenes(f, carpeta)
    m = fechas.misterios(f)
    return crear_paquete("carrusel", f, f"Invitación al evento del {fechas.nombre_fecha(f).lower()}",
                         texto_carrusel(f), carpeta=carpeta_rel, archivos=archivos,
                         datos={"misterios": m["tipo"]})


def tarea() -> list[Paquete]:
    """Lo que corre el worker cada hora: prepara los carruseles de los próximos 2 días.

    Revisa hoy, mañana y pasado mañana; así, si la PC estuvo apagada justo 2 días antes,
    se pone al corriente en cuanto se enciende (mientras el evento no haya empezado).
    """
    ahora = fechas.ahora_cdmx()
    nuevos = []
    for f in fechas.proximos_eventos(ahora.date(), 2):
        if ahora >= fechas.inicio(f):
            continue
        p = preparar_carrusel(f)
        if p:
            current_app.logger.info("Carrusel del %s listo en la bandeja (paquete %s)", f, p.id)
            nuevos.append(p)
    return nuevos
