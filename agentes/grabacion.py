"""Agente de grabación: los días de evento abre OBS y graba solo de 9:55 a 11:05 (si OBS_AUTO=1).

Así nadie tiene que acordarse de darle clic. También se puede grabar o detener desde la app.
"""
from datetime import datetime, timedelta

from flask import current_app

from servicios import obs

from . import fechas

ANTES = timedelta(minutes=5)
DESPUES = timedelta(minutes=5)


def tarea(ahora: datetime | None = None) -> str:
    if not current_app.config.get("OBS_AUTO") or not obs.instalado():
        return "Grabación automática apagada"
    ahora = ahora or fechas.ahora_cdmx()
    hoy = ahora.date()
    if not fechas.es_dia_de_evento(hoy):
        return "Hoy no hay evento"
    desde, hasta = fechas.inicio(hoy) - ANTES, fechas.fin(hoy) + DESPUES
    if desde <= ahora < hasta:
        e = obs.iniciar()
        return "Grabando el evento" if e.get("grabando") else "No se pudo empezar a grabar"
    if hasta <= ahora < hasta + timedelta(minutes=30):
        try:
            obs.detener()
        except obs.ErrorObs:
            pass
        return "Grabación del evento terminada"
    return "Esperando la hora del evento"
