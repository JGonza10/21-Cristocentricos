"""Imágenes de difusión (1080×1350, blanco y vino) con el tema y la fecha del evento. Pillow, local."""
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "assets" / "fuentes"
ANCHO, ALTO = 1080, 1350
MARGEN = 96

BLANCO, PERLA, VINO, VINO_SUAVE, TEXTO, ORO = "#ffffff", "#fbf9f7", "#7a1c2e", "#f3e4e7", "#3a1420", "#8f6b10"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
REDES = "Instagram · Facebook · TikTok · YouTube"


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"


def hora_bonita(hora: str) -> str:
    h, m = (int(x) for x in hora.split(":"))
    sufijo = "am" if h < 12 else "pm"
    return f"{(h - 1) % 12 + 1}:{m:02d} {sufijo}"


def _spectral(tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / "Spectral-Bold.ttf"), tam)


def _sans(tam: int, peso: str = "Regular") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FUENTES / "PublicSans-Variable.ttf"), tam)
    f.set_variation_by_name(peso)
    return f


def _partir(dib: ImageDraw.ImageDraw, texto: str, fuente, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if dib.textlength(prueba, font=fuente) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + ([actual] if actual else [])


def _bloque(dib, texto, fuente, y, color, interlineado=1.18, centrado=True, ancho=ANCHO - 2 * MARGEN) -> int:
    """Escribe el texto partido en líneas y devuelve la y donde terminó."""
    alto = int(fuente.size * interlineado)
    for linea in _partir(dib, texto, fuente, ancho):
        x = (ANCHO - dib.textlength(linea, font=fuente)) / 2 if centrado else MARGEN
        dib.text((x, y), linea, font=fuente, fill=color)
        y += alto
    return y


def _titulo_que_quepa(dib, texto, maximo=118, minimo=64, lineas_max=4):
    tam = maximo
    while tam > minimo and len(_partir(dib, texto, _spectral(tam), ANCHO - 2 * MARGEN)) > lineas_max:
        tam -= 6
    return _spectral(tam)


def _lienzo(fondo=BLANCO):
    img = Image.new("RGB", (ANCHO, ALTO), fondo)
    dib = ImageDraw.Draw(img)
    dib.rectangle((40, 40, ANCHO - 40, ALTO - 40), outline=VINO, width=3)
    return img, dib


def _marca(dib, y=110, color=VINO):
    f = _sans(30, "Bold")
    texto = "†  CRISTOCÉNTRICOS"
    dib.text(((ANCHO - dib.textlength(texto, font=f)) / 2, y), texto, font=f, fill=color)


def _pie(dib, numero: int, color=TEXTO):
    f = _sans(26, "SemiBold")
    texto = f"{numero} / 5"
    dib.text(((ANCHO - dib.textlength(texto, font=f)) / 2, ALTO - 120), texto, font=f, fill=color)


def _medio(dib, alto_contenido: int) -> int:
    return max(220, (ALTO - alto_contenido) // 2)


def lamina_invitacion(tema: str, fecha: date, hora: str) -> Image.Image:
    img, dib = _lienzo()
    _marca(dib)
    f_tit = _titulo_que_quepa(dib, tema)
    alto_tit = len(_partir(dib, tema, f_tit, ANCHO - 2 * MARGEN)) * int(f_tit.size * 1.18)
    y = _medio(dib, alto_tit + 300)
    y = _bloque(dib, "TE INVITAMOS", _sans(34, "Bold"), y, ORO) + 30
    y = _bloque(dib, tema, f_tit, y, VINO) + 50
    dib.rounded_rectangle((MARGEN + 80, y, ANCHO - MARGEN - 80, y + 170), radius=28, fill=VINO_SUAVE)
    y = _bloque(dib, fecha_larga(fecha), _sans(46, "Bold"), y + 30, TEXTO)
    _bloque(dib, f"{hora_bonita(hora)} · en vivo", _sans(40), y + 6, TEXTO)
    _pie(dib, 1)
    return img


def lamina_frase(frase: str, numero: int, etiqueta: str) -> Image.Image:
    img, dib = _lienzo(PERLA)
    _marca(dib)
    f = _titulo_que_quepa(dib, frase, maximo=86, minimo=50, lineas_max=7)
    alto = len(_partir(dib, frase, f, ANCHO - 2 * MARGEN)) * int(f.size * 1.25)
    y = _medio(dib, alto + 120)
    y = _bloque(dib, etiqueta.upper(), _sans(32, "Bold"), y, ORO) + 40
    dib.line((ANCHO / 2 - 60, y, ANCHO / 2 + 60, y), fill=VINO, width=4)
    _bloque(dib, frase, f, y + 50, TEXTO, interlineado=1.25)
    _pie(dib, numero)
    return img


def lamina_en_vivo(tema: str, fecha: date, hora: str) -> Image.Image:
    img, dib = _lienzo(VINO)
    dib.rectangle((40, 40, ANCHO - 40, ALTO - 40), outline=BLANCO, width=3)
    _marca(dib, color=BLANCO)
    y = _medio(dib, 560)
    dib.rounded_rectangle((ANCHO / 2 - 150, y, ANCHO / 2 + 150, y + 76), radius=38, fill=BLANCO)
    f = _sans(38, "ExtraBold")
    x = (ANCHO - dib.textlength("EN VIVO", font=f) + 34) / 2
    dib.ellipse((x - 34, y + 28, x - 14, y + 48), fill=VINO)
    dib.text((x, y + 14), "EN VIVO", font=f, fill=VINO)
    y = _bloque(dib, hora_bonita(hora), _spectral(150), y + 130, BLANCO) + 10
    y = _bloque(dib, fecha_larga(fecha), _sans(48, "Bold"), y, BLANCO) + 50
    _bloque(dib, REDES, _sans(34, "SemiBold"), y, VINO_SUAVE)
    _pie(dib, 4, color=VINO_SUAVE)
    return img


def lamina_cierre(fecha: date, hora: str) -> Image.Image:
    img, dib = _lienzo()
    _marca(dib)
    y = _medio(dib, 520)
    y = _bloque(dib, "Te esperamos", _spectral(120), y, VINO) + 60
    y = _bloque(dib, "Comparte esta invitación con alguien que lo necesite.", _sans(44), y, TEXTO) + 50
    _bloque(dib, f"{fecha_larga(fecha)} · {hora_bonita(hora)}", _sans(40, "Bold"), y, ORO)
    _pie(dib, 5)
    return img


def generar(tema: str, fecha: date, hora: str, frases: list[str], carpeta: Path) -> list[Path]:
    """Crea las 5 imágenes en `carpeta` (1.png … 5.png) y devuelve sus rutas."""
    carpeta.mkdir(parents=True, exist_ok=True)
    frase1 = frases[0] if frases else tema
    frase2 = frases[1] if len(frases) > 1 else "Un espacio para vivir con Cristo en el centro de tu vida."
    laminas = [
        lamina_invitacion(tema, fecha, hora),
        lamina_frase(frase1, 2, tema),
        lamina_frase(frase2, 3, "Para reflexionar"),
        lamina_en_vivo(tema, fecha, hora),
        lamina_cierre(fecha, hora),
    ]
    rutas = []
    for i, img in enumerate(laminas, 1):
        ruta = carpeta / f"{i}.png"
        img.save(ruta, "PNG", optimize=True)
        rutas.append(ruta)
    return rutas
