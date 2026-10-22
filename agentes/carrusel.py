"""Agente de imágenes de difusión.

En cuanto el evento tiene tema (al guardarlo, o cada 15 minutos hasta 14 días antes) se arma un
carrusel de 5 láminas 1080×1350: invitación, el tema, en vivo, intenciones y cierre.

Colores de las piezas para redes: blanco y vino (CLAUDE.md §4.4), no el morado de la app.
"""
from datetime import date
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from app.bandeja import crear_paquete
from app.extensiones import db
from app.modelos import Paquete, Tema

from . import fechas

ANCHO, ALTO = 1080, 1350
MARGEN = 96
DIAS_ANTES = 14   # la difusión se arma en cuanto hay tema, hasta 2 semanas antes

BLANCO = "#ffffff"
CREMA = "#fbf9f7"
VINO = "#7a1c2e"
VINO_SUAVE = "#f3e4e7"
TEXTO = "#3a1420"
ORO = "#8f6b10"
VINO_MEDIO = "#8e2b3e"
VINO_LINEA = "#9c4255"
ROSA_LINEA = "#e5c9cf"

REDES_EN_VIVO = ["YouTube", "Facebook", "Instagram", "TikTok", "Canal de TV"]
CITA_DEFECTO = ("Hagan lo que Él les diga.", "Jn 2,5")


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


def _pie(d, numero: int, color_texto: str, color_linea: str, alto: int = ALTO, total: int = 5) -> None:
    canal = current_app.config["CANAL_NOMBRE"]
    d.line([(MARGEN, alto - 130), (ANCHO - MARGEN, alto - 130)], fill=color_linea, width=2)
    d.text((MARGEN, alto - 104), canal, font=_fuente("negrita", 30), fill=color_texto)
    if numero:
        f = _fuente("semi", 28)
        marca = f"{numero} / {total}"
        d.text((ANCHO - MARGEN - d.textlength(marca, font=f), alto - 102), marca, font=f, fill=color_texto)


def _lienzo(fondo: str, alto: int = ALTO) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (ANCHO, alto), fondo)
    return img, ImageDraw.Draw(img)


def _marco(d, color, alto: int = ALTO) -> None:
    d.rounded_rectangle([36, 36, ANCHO - 36, alto - 36], radius=28, outline=color, width=3)


def _tema(f: date) -> Tema | None:
    return db.session.get(Tema, f)


def _titulo(f: date) -> str:
    t = _tema(f)
    return t.titulo if t else "Evento en vivo"


def _cita(f: date) -> tuple[str, str]:
    """(frase, referencia). La cita del tema puede venir como «Frase (Jn 2,5)» o solo la frase."""
    t = _tema(f)
    if not t or not t.cita:
        return CITA_DEFECTO
    texto = t.cita.strip()
    if texto.endswith(")") and "(" in texto:
        frase, ref = texto.rsplit("(", 1)
        return frase.strip(), ref[:-1].strip()
    return texto, ""


def _caja_fecha(d, f: date, y: int) -> int:
    caja = [MARGEN + 40, y, ANCHO - MARGEN - 40, y + 250]
    d.rounded_rectangle(caja, radius=26, fill=VINO)
    fecha_txt = fechas.nombre_fecha(f)
    ft = _ajustar(d, fecha_txt, "extra", 64, caja[2] - caja[0] - 60, 1)
    d.text(((ANCHO - d.textlength(fecha_txt, font=ft)) / 2, caja[1] + 52), fecha_txt, font=ft, fill=BLANCO)
    hora = "10:00 am · hora CDMX"
    fh = _fuente("semi", 40)
    d.text(((ANCHO - d.textlength(hora, font=fh)) / 2, caja[1] + 150), hora, font=fh, fill=VINO_SUAVE)
    return caja[3]


# --- Difusión: carrusel de 5 láminas -------------------------------------------------

def _invitacion(f: date, alto: int = ALTO, numero: int = 1) -> Image.Image:
    img, d = _lienzo(CREMA, alto)
    _marco(d, VINO_SUAVE, alto)
    ancho = ANCHO - 2 * MARGEN
    extra = (alto - ALTO) // 2
    _cruz(d, (ANCHO / 2, 230 + extra), 96, VINO)
    _etiqueta(d, (0, 330 + extra), "Evento en vivo · te invitamos", ORO, 30, centrado_en=ANCHO / 2)
    ft = _ajustar(d, _titulo(f), "titulo", 104, ancho, 3)
    y = _parrafo(d, (MARGEN, 400 + extra), _titulo(f), ft, TEXTO, ancho, interlineado=1.08, centrado=True)
    fin = _caja_fecha(d, f, y + 50)
    t = _tema(f)
    if t and t.descripcion:
        fd = _ajustar(d, t.descripcion, "cita", 46, ancho, 3)
        _parrafo(d, (MARGEN, fin + 50), t.descripcion, fd, VINO, ancho, centrado=True)
    _pie(d, numero, TEXTO, VINO_SUAVE, alto)
    return img


def _el_tema(f: date) -> Image.Image:
    img, d = _lienzo(BLANCO)
    ancho = ANCHO - 2 * MARGEN
    t = _tema(f)
    _etiqueta(d, (MARGEN, 130), "De qué vamos a hablar", ORO, 28)
    ft = _ajustar(d, _titulo(f), "titulo", 96, ancho, 4)
    y = _parrafo(d, (MARGEN, 190), _titulo(f), ft, VINO, ancho, interlineado=1.05)
    if t and t.descripcion:
        y = _parrafo(d, (MARGEN, y + 40), t.descripcion, _ajustar(d, t.descripcion, "texto", 46, ancho, 6),
                     TEXTO, ancho, interlineado=1.4)
    frase, ref = _cita(f)
    y = max(y + 60, 760)
    d.rounded_rectangle([MARGEN, y, ANCHO - MARGEN, y + 300], radius=26, fill=VINO_SUAVE)
    fc = _ajustar(d, f"“{frase}”", "cita", 52, ancho - 80, 3)
    yy = _parrafo(d, (MARGEN + 40, y + 40), f"“{frase}”", fc, VINO, ancho - 80, interlineado=1.15)
    if ref:
        d.text((MARGEN + 40, yy + 10), ref, font=_fuente("semi", 32), fill=ORO)
    _pie(d, 2, TEXTO, VINO_SUAVE)
    return img


def _en_vivo(f: date, alto: int = ALTO, numero: int = 3) -> Image.Image:
    img, d = _lienzo(VINO, alto)
    ancho = ANCHO - 2 * MARGEN
    extra = (alto - ALTO) // 2
    d.ellipse([MARGEN, 136 + extra, MARGEN + 30, 166 + extra], fill=BLANCO)
    _etiqueta(d, (MARGEN + 50, 136 + extra), "En vivo", BLANCO, 30)
    y = _parrafo(d, (MARGEN, 220 + extra), "Acompáñanos desde donde estés", _fuente("titulo", 96), BLANCO, ancho,
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
    _pie(d, numero, BLANCO, VINO_LINEA, alto)
    return img


def _intenciones(f: date) -> Image.Image:
    img, d = _lienzo(VINO_SUAVE)
    ancho = ANCHO - 2 * MARGEN
    d.rounded_rectangle([MARGEN - 24, 170, ANCHO - MARGEN + 24, ALTO - 210], radius=34, fill=BLANCO)
    _cruz(d, (ANCHO / 2, 360), 80, VINO)
    _etiqueta(d, (0, 450), "Tus intenciones", ORO, 30, centrado_en=ANCHO / 2)
    y = _parrafo(d, (MARGEN + 20, 520), "¿Por quién quieres que oremos?", _fuente("titulo", 88), TEXTO,
                 ancho - 40, interlineado=1.08, centrado=True)
    _parrafo(d, (MARGEN + 40, y + 40),
             "Escríbelas en los comentarios o por mensaje y las presentaremos durante el evento.",
             _fuente("texto", 42), TEXTO, ancho - 80, interlineado=1.4, centrado=True)
    _pie(d, 4, TEXTO, ROSA_LINEA)
    return img


def _cierre(f: date, alto: int = ALTO, numero: int = 5) -> Image.Image:
    img, d = _lienzo(CREMA, alto)
    _marco(d, VINO_SUAVE, alto)
    ancho = ANCHO - 2 * MARGEN
    extra = (alto - ALTO) // 2
    frase, ref = _cita(f)
    d.text((MARGEN, 160 + extra), "“", font=_fuente("titulo", 220), fill=VINO_SUAVE)
    y = _parrafo(d, (MARGEN, 330 + extra), frase, _ajustar(d, frase, "cita", 96, ancho, 4), VINO, ancho,
                 interlineado=1.1)
    if ref:
        d.text((MARGEN, y + 30), ref, font=_fuente("semi", 34), fill=ORO)
    y += 150
    d.line([(MARGEN, y), (MARGEN + 120, y)], fill=ORO, width=4)
    y = _parrafo(d, (MARGEN, y + 50), "Te esperamos", _fuente("titulo", 84), TEXTO, ancho)
    _parrafo(d, (MARGEN, y + 10), f"{fechas.nombre_fecha(f)}\n10:00 am · hora CDMX", _fuente("semi", 42), TEXTO,
             ancho, interlineado=1.35)
    _pie(d, numero, TEXTO, VINO_SUAVE, alto)
    return img


DIAPOSITIVAS = [_invitacion, _el_tema, _en_vivo, _intenciones, _cierre]


def _hashtags() -> str:
    canal = current_app.config["CANAL_NOMBRE"].replace(" ", "")
    return f"#{canal} #EnVivo #Fe #Oración #Católicos #Dios #Reflexión"


def texto_difusion(f: date) -> str:
    t = _tema(f)
    enlace = current_app.config["CANAL_ENLACE"]
    lineas = [f"🙏 {_titulo(f)}", ""]
    if t and t.descripcion:
        lineas += [t.descripcion, ""]
    lineas += [f"📅 {fechas.nombre_fecha(f)} · 10:00 am (hora CDMX)",
               "📺 En vivo por YouTube, Facebook, Instagram, TikTok y Canal de TV.", "",
               "Déjanos tus intenciones en los comentarios y compártelo con quien lo necesite. 🤍"]
    if enlace:
        lineas += ["", f"Síguelo en vivo: {enlace}"]
    lineas += ["", _hashtags()]
    return "\n".join(lineas)


def generar_imagenes(f: date, carpeta: Path) -> list[str]:
    carpeta.mkdir(parents=True, exist_ok=True)
    nombres = []
    for i, dibujar in enumerate(DIAPOSITIVAS, start=1):
        nombre = f"{i}.png"
        dibujar(f).save(carpeta / nombre, "PNG", optimize=True)
        nombres.append(nombre)
    return nombres


def _existentes(f: date, tipo: str, cual: str) -> list[Paquete]:
    """Piezas ya hechas por este agente. Las invitaciones viejas (sin «momento», con los misterios)
    no cuentan: así, al ponerle tema al evento, sale la difusión nueva."""
    return [p for p in Paquete.query.filter_by(tipo=tipo, fecha_evento=f).all()
            if (p.datos or {}).get("momento") == cual]


def preparar_difusion(f: date, forzar: bool = False) -> list[Paquete]:
    """Las 5 imágenes de difusión. Sin `forzar`, no repite lo que ya existe."""
    from app.temas import es_dia_de_evento
    if not es_dia_de_evento(f):
        raise ValueError(f"{f} no tiene evento (no es lunes ni viernes y no tiene tema).")
    nuevos = []
    previos = _existentes(f, "carrusel", "antes")
    if forzar or not previos:
        rel = f"{f.isoformat()}/difusion" + (f"-{len(previos) + 1}" if previos else "")
        archivos = generar_imagenes(f, Path(current_app.config["PAQUETES_DIR"]) / rel)
        nuevos.append(crear_paquete("carrusel", f, f"Difusión · {_titulo(f)}"[:120], texto_difusion(f),
                                    carpeta=rel, archivos=archivos, datos={"momento": "antes"}))
    return nuevos


def preparar_carrusel(f: date, forzar: bool = False) -> Paquete | None:
    """Para el comando «flask carrusel»: arma la difusión y devuelve su carrusel."""
    nuevos = [p for p in preparar_difusion(f, forzar) if p.tipo == "carrusel"]
    return nuevos[0] if nuevos else None


def tarea() -> list[Paquete]:
    """Cada hora: arma la difusión de los eventos con tema de las próximas 2 semanas que no la tengan.

    Sin tema no se arma (el tema es lo que la hace atractiva); el aviso de Inicio pide ponerlo.
    """
    ahora = fechas.ahora_cdmx()
    nuevos = []
    from app.temas import dias_de_evento
    for f in dias_de_evento(ahora.date(), DIAS_ANTES):
        if ahora >= fechas.inicio(f) or _tema(f) is None:
            continue
        hechos = preparar_difusion(f)
        if hechos:
            current_app.logger.info("Difusión del %s lista en Material (%s piezas)", f, len(hechos))
            nuevos += hechos
    return nuevos
