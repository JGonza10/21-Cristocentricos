"""Fechas de los rosarios: lunes (gozosos) y viernes (dolorosos), 10 a 11 am, hora CDMX."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CDMX = ZoneInfo("America/Mexico_City")
HORA_INICIO = time(10, 0)
HORA_FIN = time(11, 0)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

# weekday(): lunes = 0, viernes = 4
MISTERIOS = {
    0: {
        "tipo": "gozosos",
        "nombre": "Misterios gozosos",
        "lista": [
            ("La Anunciación del ángel a María", "Lc 1,26-38"),
            ("La Visitación de María a su prima Isabel", "Lc 1,39-56"),
            ("El Nacimiento del Hijo de Dios en Belén", "Lc 2,1-20"),
            ("La Presentación de Jesús en el templo", "Lc 2,22-38"),
            ("El Niño Jesús perdido y hallado en el templo", "Lc 2,41-52"),
        ],
    },
    4: {
        "tipo": "dolorosos",
        "nombre": "Misterios dolorosos",
        "lista": [
            ("La oración de Jesús en el huerto", "Lc 22,39-46"),
            ("La flagelación del Señor", "Jn 19,1"),
            ("La coronación de espinas", "Mt 27,27-31"),
            ("Jesús con la cruz a cuestas camino del Calvario", "Jn 19,17"),
            ("La crucifixión y muerte del Señor", "Lc 23,33-46"),
        ],
    },
}


def ahora_cdmx() -> datetime:
    return datetime.now(CDMX)


def hoy_cdmx() -> date:
    return ahora_cdmx().date()


def es_dia_de_rosario(d: date) -> bool:
    return d.weekday() in MISTERIOS


def misterios(d: date) -> dict:
    return MISTERIOS[d.weekday()]


def nombre_fecha(d: date) -> str:
    """'Lunes 19 de octubre'"""
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"


def inicio(d: date) -> datetime:
    return datetime.combine(d, HORA_INICIO, CDMX)


def fin(d: date) -> datetime:
    return datetime.combine(d, HORA_FIN, CDMX)


def proximos_rosarios(desde: date, dias: int) -> list[date]:
    """Días de rosario entre `desde` y `desde + dias` (incluidos)."""
    return [desde + timedelta(n) for n in range(dias + 1) if es_dia_de_rosario(desde + timedelta(n))]


def fecha_de_grabacion(momento: datetime) -> date:
    """La fecha (CDMX) a la que pertenece una grabación según la hora en que se guardó."""
    return momento.astimezone(CDMX).date()
