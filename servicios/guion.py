"""Guion del programa: PDF → Markdown, limpieza y frases para difusión (todo local, sin API)."""
import io
import re
import unicodedata

from pypdf import PdfReader

# Secciones que ya no van en el programa (se quitan con todo y su contenido).
SECCIONES_QUITADAS = ("intenciones recibidas", "cita biblica")

# Rezos fijos: no sirven como frase de difusión.
REZOS = ("dios te salve", "padre nuestro", "gloria al padre", "santa maria", "creo en dios", "amen")

PALABRAS_CLAVE = ("jesus", "dios", "cristo", "fe", "miedo", "confia", "confianza", "padre", "maria", "jaculatoria",
                  "espiritu", "amor", "paz", "esperanza", "corazon", "familia", "vida")

# Frases de presentación o de paso: no se comparten solas.
_RELLENO = re.compile(r"\b(yo soy|bienvenid|nos vemos|gracias|quedate|hoy quiero|te tengo|mencionar|nombrar|espero)\b")

_TITULO_NUM = re.compile(r"^\s*(\d+)\s*[.)-]\s*(.+?)\s*:?\s*$")
_ETIQUETA = re.compile(r"^\s*([^:]{3,60}):\s*(.*)$")
_INDICACION = re.compile(r"^\s*([a-z]\))\s+(.*)$")
_VINETA = re.compile(r"^\s*[-•]\s+")
_NOTA_MAYUS = re.compile(r"\s*\(([A-ZÁÉÍÓÚÑ ]{3,})\)")


def _es_etiqueta(texto: str) -> bool:
    """«Frase Introductoria», «GANCHO (resumen…)», «ESTRUCTURA»: 1 a 3 palabras con mayúscula."""
    palabras = re.sub(r"\(.*?\)", "", texto).split()
    return 1 <= len(palabras) <= 3 and all(p[:1].isupper() for p in palabras)


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos. «¡Jesús!» → «jesus»."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]+", " ", t).strip()


def pdf_a_texto(datos: bytes) -> str:
    lector = PdfReader(io.BytesIO(datos))
    return "\n".join((p.extract_text() or "") for p in lector.pages)


def texto_a_markdown(texto: str) -> str:
    """Une las líneas cortadas del PDF en párrafos y marca títulos e indicaciones."""
    bloques: list[str] = []
    parrafo: list[str] = []

    def cerrar():
        if parrafo:
            bloques.append(" ".join(parrafo))
            parrafo.clear()

    for linea in texto.splitlines():
        linea = re.sub(r"\s+", " ", linea).strip()
        if not linea:
            cerrar()
            continue
        if m := _TITULO_NUM.match(linea):
            cerrar()
            bloques.append(f"## {m.group(1)}. {m.group(2).rstrip(':')}")
            continue
        linea = _NOTA_MAYUS.sub("", _VINETA.sub("", linea)).replace("!!", "!").replace("¡¡", "¡")
        if (m := _ETIQUETA.match(linea)) and _es_etiqueta(m.group(1)):
            cerrar()
            bloques.append(f"## {re.sub(r'\s*\(.*?\)', '', m.group(1)).strip().capitalize()}")
            if m.group(2):
                parrafo.append(m.group(2))
            continue
        if linea.isupper() and len(linea) < 80:
            cerrar()
            titulo = linea.strip('¨"').capitalize()
            bloques.append(f"# {titulo}" if not bloques else f"## {titulo}")
            continue
        if m := _INDICACION.match(linea):
            cerrar()
            bloques.append(f"> {m.group(1)} {m.group(2)}")
            continue
        if bloques and bloques[-1][:1] in "#>" and not parrafo and linea[:1].islower():
            bloques[-1] += " " + linea  # el título o la indicación siguió en otra línea
            continue
        parrafo.append(linea)
    cerrar()
    return "\n\n".join(bloques).strip() + "\n"


def quitar_secciones(md: str, secciones: tuple[str, ...] = SECCIONES_QUITADAS) -> str:
    """Quita «intenciones recibidas» y «cita bíblica» (título y contenido hasta el siguiente título)."""
    salida, saltando = [], False
    for linea in md.splitlines():
        if linea.startswith("#"):
            saltando = any(s in normalizar(linea) for s in secciones)
        if not saltando:
            salida.append(linea)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(salida)).strip() + "\n"


def convertir(datos: bytes) -> str:
    return quitar_secciones(texto_a_markdown(pdf_a_texto(datos)))


def texto_leible(md: str) -> str:
    """Solo lo que se lee en voz alta: sin títulos ni indicaciones."""
    return "\n".join(l for l in md.splitlines() if l.strip() and not l.lstrip().startswith(("#", ">")))


def frases_difusion(md: str, tema: str = "", n: int = 8) -> list[str]:
    """Elige las frases más compartibles del guion con reglas simples."""
    claves = set(PALABRAS_CLAVE) | set(normalizar(tema).split())
    sin_rezos = quitar_secciones(md, ("oracion", "rosario", "evangelio", "lectura"))
    candidatas = re.split(r"(?<=[.!?:])\s+", texto_leible(sin_rezos).replace("\n", " "))
    puntuadas, vistas = [], set()
    for orden, frase in enumerate(candidatas):
        frase = frase.strip(" ¡!:")
        base = normalizar(frase)
        if (not 25 <= len(frase) <= 170 or base in vistas or not frase.lstrip("¿¡«\"")[:1].isupper()
                or any(base.startswith(r) for r in REZOS) or _RELLENO.search(base)):
            continue
        vistas.add(base)
        palabras = set(base.split())
        puntos = 2 * len(palabras & claves) + (2 if "?" in frase else 0) + (1 if len(frase) <= 100 else 0)
        if puntos < 2:
            continue
        puntuadas.append((puntos, orden, frase))
    mejores = sorted(puntuadas, key=lambda x: (-x[0], x[1]))[:n]
    return [f for _, _, f in sorted(mejores, key=lambda x: x[1])]
