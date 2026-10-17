"""Grabación del evento: controlar OBS y subir un video desde otra computadora.

    GET  /api/obs                 estado de OBS (instalado, conectado, grabando)
    POST /api/obs/iniciar         abre OBS si hace falta y empieza a grabar en grabaciones/
    POST /api/obs/detener         detiene la grabación
    POST /api/grabaciones/subir   sube un video por partes (cabeceras X-Archivo, X-Inicio, X-Total, X-Fecha)

La subida por partes deja trabajar desde la otra computadora (por Tailscale) aunque el video pese
varios GB: cada parte es de unos MB y, si se corta, se reanuda donde se quedó.
"""
import os
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from flask import Blueprint, current_app, jsonify, request

from .seguridad import login_requerido

bp = Blueprint("grabar", __name__, url_prefix="/api")

EXTENSIONES = {".mp4", ".mkv", ".mov", ".webm", ".flv"}
PARTE_MAX = 16 * 1024 * 1024
TOTAL_MAX = 20 * 1024 ** 3
ESPACIO_LIBRE = 1024 ** 3


def _error(mensaje: str, codigo: int = 400, **extra):
    return jsonify(error=mensaje, **extra), codigo


@bp.get("/obs")
@login_requerido
def obs_estado():
    from servicios import obs
    return jsonify(obs.estado())


@bp.post("/obs/iniciar")
@login_requerido
def obs_iniciar():
    from servicios import obs
    try:
        return jsonify(obs.iniciar())
    except obs.ErrorObs as e:
        return _error(str(e), 503)


@bp.post("/obs/detener")
@login_requerido
def obs_detener():
    from servicios import obs
    try:
        return jsonify(obs.detener())
    except obs.ErrorObs as e:
        return _error(str(e), 503)


def _nombre_seguro(crudo: str) -> str | None:
    nombre = Path(unquote(crudo or "")).name
    base, ext = os.path.splitext(nombre)
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(" .")[:100]
    if not base or ext.lower() not in EXTENSIONES:
        return None
    return base + ext.lower()


@bp.post("/grabaciones/subir")
@login_requerido
def subir():
    request.max_content_length = PARTE_MAX
    nombre = _nombre_seguro(request.headers.get("X-Archivo", ""))
    if not nombre:
        return _error("Solo se pueden subir videos (.mp4, .mkv, .mov, .webm o .flv).")
    try:
        inicio = int(request.headers.get("X-Inicio", ""))
        total = int(request.headers.get("X-Total", ""))
        fecha = date.fromisoformat(request.headers.get("X-Fecha", ""))
    except ValueError:
        return _error("La solicitud no es válida.")
    if not 0 < total <= TOTAL_MAX or not 0 <= inicio < total:
        return _error("El tamaño del video no es válido (máximo 20 GB).")
    from agentes import fechas
    if not fechas.es_dia_de_evento(fecha) or fecha > fechas.hoy_cdmx():
        return _error("Elige un evento que ya haya pasado (lunes o viernes).")

    destino = Path(current_app.config["GRABACIONES_DIR"])
    temporal = destino / ".subiendo" / f"{nombre}.parte"
    temporal.parent.mkdir(parents=True, exist_ok=True)
    if inicio == 0:
        if shutil.disk_usage(destino).free < total + ESPACIO_LIBRE:
            return _error("No hay espacio suficiente en el disco de esta computadora.", 507)
        temporal.write_bytes(b"")
    actual = temporal.stat().st_size if temporal.exists() else 0
    if actual != inicio:
        return _error("La subida se desfasó; se reanuda desde donde se quedó.", 409, recibido=actual)
    datos = request.get_data(cache=False)
    if not datos or inicio + len(datos) > total:
        return _error("La parte recibida no es válida.")
    with temporal.open("ab") as f:
        f.write(datos)
    recibido = inicio + len(datos)
    if recibido < total:
        return jsonify(recibido=recibido, listo=False)

    final = destino / nombre
    n = 1
    while final.exists():
        final = destino / f"{Path(nombre).stem}-{n}{Path(nombre).suffix}"
        n += 1
    temporal.replace(final)
    # La fecha del evento sale de la fecha del archivo: se ajusta a la del evento elegido.
    marca = fechas.fin(fecha).timestamp()
    os.utime(final, (marca, marca))
    current_app.logger.info("Video subido: %s (%s bytes) para el %s", final.name, total, fecha)
    return jsonify(recibido=recibido, listo=True, nombre=final.name)
