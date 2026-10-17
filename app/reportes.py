"""Reporte semanal automático y captura de seguidores.

    GET  /api/reportes                 semanas con reporte (las más recientes primero)
    GET  /api/reportes/<lunes>         un reporte
    POST /api/reportes/generar         {"semana": "AAAA-MM-DD"} (opcional; por omisión, la semana actual)
    GET  /api/seguidores               último conteo por red
    PUT  /api/seguidores               {"instagram": 120, "facebook": 300, ...} con fecha de hoy
    GET  /api/registro[.csv]           registro de cada evento (sustituye a la hoja de Google Sheets)
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


def _registro() -> list[dict]:
    """Una fila por evento que ya tiene grabación o contenido: lo que antes iba a la hoja de registro."""
    from agentes import fechas

    from .avance import momento
    from .modelos import Grabacion, Paquete, Tema
    filas = {}
    for g_ in Grabacion.query.filter(Grabacion.fecha_evento.isnot(None)).all():
        filas.setdefault(g_.fecha_evento, {})["grabacion"] = g_
    for p in Paquete.query.all():
        filas.setdefault(p.fecha_evento, {}).setdefault("paquetes", []).append(p)
    salida = []
    for f in sorted(filas, reverse=True):
        d = filas[f]
        grab, paquetes = d.get("grabacion"), d.get("paquetes", [])
        tema = db.session.get(Tema, f)
        pubs = [x for p in paquetes for x in p.publicaciones]
        salida.append({
            "fecha": f.isoformat(), "evento": fechas.nombre_fecha(f), "tema": tema.titulo if tema else "",
            "video": grab.nombre if grab else "", "minutos": round((grab.duracion or 0) / 60) if grab else 0,
            "difusion": sum(momento(p) == "antes" for p in paquetes),
            "reels": sum(p.tipo == "reel" and momento(p) == "despues" for p in paquetes),
            "carrusel": any(p.tipo == "carrusel" and momento(p) == "despues" for p in paquetes),
            "aprobados": sum(p.estado == "aprobado" for p in paquetes),
            "rechazados": sum(p.estado == "rechazado" for p in paquetes),
            **{red: sum(x.red == red and x.estado == "publicado" for x in pubs) for red in REDES},
        })
    return salida


@bp.get("/registro")
@login_requerido
def registro():
    return jsonify(registro=_registro())


@bp.get("/registro.csv")
@login_requerido
def registro_csv():
    import csv
    import io
    filas = _registro()
    buf = io.StringIO()
    columnas = ["fecha", "evento", "tema", "video", "minutos", "difusion", "reels", "carrusel", "aprobados",
                "rechazados", *REDES]
    w = csv.DictWriter(buf, fieldnames=columnas)
    w.writeheader()
    for f in filas:
        # Texto que empiece con = + - @ se abriría como fórmula en Excel: se le antepone un apóstrofo.
        w.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in f.items()})
    return current_app.response_class("\ufeff" + buf.getvalue(), mimetype="text/csv",
                                      headers={"Content-Disposition": "attachment; filename=registro-eventos.csv"})
