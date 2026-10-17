"""Reporte semanal automático y captura de seguidores.

    GET  /api/reportes                 semanas con reporte (las más recientes primero)
    GET  /api/reportes/<lunes>         un reporte
    POST /api/reportes/generar         {"semana": "AAAA-MM-DD"} (opcional; por omisión, la semana actual)
    GET  /api/seguidores               último conteo por red
    PUT  /api/seguidores               {"instagram": 120, "facebook": 300, ...} con fecha de hoy
"""
from datetime import date

from flask import Blueprint, current_app, g, jsonify, request

from .extensiones import db
from .modelos import REDES, Reporte, Seguidores
from .seguridad import login_requerido

bp = Blueprint("reportes", __name__, url_prefix="/api")

MAX_SEGUIDORES = 10_000_000


def _error(mensaje: str, codigo: int = 400):
    return jsonify(error=mensaje), codigo


@bp.get("/reportes")
@login_requerido
def listar():
    filas = Reporte.query.order_by(Reporte.semana.desc()).limit(26).all()
    return jsonify(reportes=[{"semana": r.semana.isoformat(), "titulo": r.datos.get("titulo"),
                              "creado": r.creado.isoformat() + "Z"} for r in filas])


@bp.get("/reportes/<semana>")
@login_requerido
def ver(semana: str):
    try:
        r = db.session.get(Reporte, date.fromisoformat(semana))
    except ValueError:
        return _error("Fecha no válida.")
    if not r:
        return _error("Todavía no hay reporte de esa semana.", 404)
    return jsonify(reporte=r.datos, creado=r.creado.isoformat() + "Z")


@bp.post("/reportes/generar")
@login_requerido
def generar():
    from agentes import fechas, reporte
    d = request.get_json(silent=True) or {}
    try:
        semana = date.fromisoformat(d["semana"]) if d.get("semana") else fechas.hoy_cdmx()
    except (TypeError, ValueError):
        return _error("Fecha no válida.")
    if semana > fechas.hoy_cdmx():
        return _error("No se puede reportar una semana que no ha empezado.")
    r = reporte.generar(semana)
    current_app.logger.info("Reporte de la semana %s generado por %s", r.semana, g.usuario.usuario)
    return jsonify(reporte=r.datos, creado=r.creado.isoformat() + "Z")


@bp.get("/seguidores")
@login_requerido
def ver_seguidores():
    resultado = {}
    for red in REDES:
        s = Seguidores.query.filter_by(red=red).order_by(Seguidores.fecha.desc()).first()
        if s:
            resultado[red] = {"cantidad": s.cantidad, "fecha": s.fecha.isoformat()}
    return jsonify(seguidores=resultado, meta=current_app.config.get("META_SEGUIDORES", 1000))


@bp.put("/seguidores")
@login_requerido
def capturar_seguidores():
    from agentes.fechas import hoy_cdmx
    d = request.get_json(silent=True)
    if not isinstance(d, dict) or not d:
        return _error("Escribe los seguidores de al menos una red.")
    hoy = hoy_cdmx()
    for red, cantidad in d.items():
        if red not in REDES:
            return _error("Red no válida.")
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or not 0 <= cantidad <= MAX_SEGUIDORES:
            return _error("Escribe un número entero de seguidores.")
    for red, cantidad in d.items():
        s = Seguidores.query.filter_by(fecha=hoy, red=red).first() or Seguidores(fecha=hoy, red=red)
        s.cantidad = cantidad
        db.session.add(s)
    db.session.commit()
    current_app.logger.info("Seguidores capturados por %s", g.usuario.usuario)
    return ver_seguidores()
