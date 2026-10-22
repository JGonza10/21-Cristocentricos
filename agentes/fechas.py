"""Fechas de los eventos, 10 a 11 am, hora CDMX.

Lunes y viernes son los días fijos (siempre aparecen en el calendario, con o sin tema). Desde el
2026-10-21 cualquier otro día también puede tener evento: basta con guardarle un tema
(ver `app.temas.dias_de_evento`).
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

CDMX = ZoneInfo("America/Mexico_City")
HORA_INICIO = time(10, 0)
HORA_FIN = time(11, 0)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

# weekday(): lunes = 0 ... domingo = 6. Días que siempre tienen evento.
DIAS_FIJOS = (0, 4)

GOZOSOS = {
    "tipo": "gozosos",
    "nombre": "Misterios gozosos",
    "lista": [
        ("La Anunciación del ángel a María", "Lc 1,26-38"),
        ("La Visitación de María a su prima Isabel", "Lc 1,39-56"),
        ("El Nacimiento del Hijo de Dios en Belén", "Lc 2,1-20"),
        ("La Presentación de Jesús en el templo", "Lc 2,22-38"),
        ("El Niño Jesús perdido y hallado en el templo", "Lc 2,41-52"),
    ],
}
DOLOROSOS = {
    "tipo": "dolorosos",
    "nombre": "Misterios dolorosos",
    "lista": [
        ("La oración de Jesús en el huerto", "Lc 22,39-46"),
        ("La flagelación del Señor", "Jn 19,1"),
        ("La coronación de espinas", "Mt 27,27-31"),
        ("Jesús con la cruz a cuestas camino del Calvario", "Jn 19,17"),
        ("La crucifixión y muerte del Señor", "Lc 23,33-46"),
    ],
}
GLORIOSOS = {
    "tipo": "gloriosos",
    "nombre": "Misterios gloriosos",
    "lista": [
        ("La Resurrección del Señor", "Mc 16,1-7"),
        ("La Ascensión del Señor al cielo", "Hch 1,6-11"),
        ("La venida del Espíritu Santo", "Hch 2,1-4"),
        ("La Asunción de María al cielo", "Ap 12,1"),
        ("La Coronación de María como Reina del cielo y de la tierra", "Ap 12,1"),
    ],
}
LUMINOSOS = {
    "tipo": "luminosos",
    "nombre": "Misterios luminosos",
    "lista": [
        ("El Bautismo de Jesús en el Jordán", "Mt 3,13-17"),
        ("Las bodas de Caná", "Jn 2,1-11"),
        ("El anuncio del Reino de Dios", "Mc 1,14-15"),
        ("La Transfiguración del Señor", "Lc 9,28-36"),
        ("La institución de la Eucaristía", "Lc 22,14-20"),
    ],
}
# Los misterios que la Iglesia propone para cada día de la semana.
MISTERIOS = {0: GOZOSOS, 1: DOLOROSOS, 2: GLORIOSOS, 3: LUMINOSOS, 4: DOLOROSOS, 5: GOZOSOS, 6: GLORIOSOS}


def ahora_cdmx() -> datetime:
    return datetime.now(CDMX)


def hoy_cdmx() -> date:
    return ahora_cdmx().date()


def es_dia_fijo(d: date) -> bool:
    """Lunes o viernes: siempre hay evento, tenga tema o no."""
    return d.weekday() in DIAS_FIJOS


def misterios(d: date) -> dict:
    return MISTERIOS[d.weekday()]


def nombre_fecha(d: date) -> str:
    """'Lunes 19 de octubre'"""
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"


def inicio(d: date) -> datetime:
    return datetime.combine(d, HORA_INICIO, CDMX)


def fin(d: date) -> datetime:
    return datetime.combine(d, HORA_FIN, CDMX)


def proximos_fijos(desde: date, dias: int) -> list[date]:
    """Lunes y viernes entre `desde` y `desde + dias` (incluidos). Con los demás días de evento
    (los que tienen tema) usa `app.temas.dias_de_evento`."""
    return [desde + timedelta(n) for n in range(dias + 1) if es_dia_fijo(desde + timedelta(n))]


def fecha_de_grabacion(momento: datetime) -> date:
    """La fecha (CDMX) a la que pertenece una grabación según la hora en que se guardó."""
    return momento.astimezone(CDMX).date()
