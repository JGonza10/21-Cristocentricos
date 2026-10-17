"""Estadísticas para el dashboard: GET /api/estadisticas?desde=AAAA-MM-DD&hasta=AAAA-MM-DD

El usuario elige el periodo. Junta en una sola respuesta lo que piden las gráficas: cada evento
del periodo (tema, pasos, video, piezas, publicaciones), cómo se cumplió cada paso, el estado de
las piezas, los seguidores capturados por red y las ideas por semana.
"""
from collections import Counter
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from .extensiones import db
from .modelos import PASOS_EVENTO, REDES, BitacoraEvento, Idea, Paquete, Seguidores, Tema
from .seguridad import login_requerido

bp = Blueprint("estadisticas", __name__, url_prefix="/api")

MAX_DIAS = 731          # hasta 2 años de una vez
DIAS_POR_OMISION = 90


def _fecha(texto: str | None, defecto: date) -> date:
    if not texto:
        return defecto
    return date.fromisoformat(texto)


def _evento(f: date, registro: dict) -> dict:
    """Una fila por evento: de la bitácora si ya pasó y se archivó; si no, calculado en vivo."""
    from agentes import fechas

    from .avance import avance
    b = db.session.get(BitacoraEvento, f)
    if b:
        pasos, hechos, total = b.pasos, b.hechos, b.total
    else:
        a = avance(f)
        pasos, hechos, total = {p["id"]: p["estado"] for p in a["pasos"]}, a["hechos"], a["total"]
    r = registro.get(f.isoformat(), {})
    tema = db.session.get(Tema, f)
    return {
        "fecha": f.isoformat(), "evento": fechas.nombre_fecha(f), "tema": tema.titulo if tema else "",
        "hechos": hechos, "total": total, "pasos": pasos, "minutos": r.get("minutos", 0),
        "difusion": r.get("difusion", 0), "reels": r.get("reels", 0), "carrusel": bool(r.get("carrusel")),
        "aprobados": r.get("aprobados", 0), "rechazados": r.get("rechazados", 0),
        "publicadas": {red: r.get(red, 0) for red in REDES},
    }


@bp.get("/estadisticas")
@login_requerido
def estadisticas():
    from agentes import fechas

    from .reportes import _registro
    hoy = fechas.hoy_cdmx()
    try:
        hasta = _fecha(request.args.get("hasta"), hoy)
        desde = _fecha(request.args.get("desde"), hasta - timedelta(DIAS_POR_OMISION))
    except ValueError:
        return jsonify(error="Fecha no válida."), 400
    if desde > hasta or (hasta - desde).days > MAX_DIAS:
        return jsonify(error="Elige un periodo de hasta 2 años, con la fecha inicial antes de la final."), 400

    from .avance import _tuvo_actividad
    registro = {r["fecha"]: r for r in _registro()}
    dias = [desde + timedelta(n) for n in range((hasta - desde).days + 1)]
    # Los pasados que nunca se trabajaron (antes de usar la app) no cuentan: solo ensuciarían las gráficas.
    eventos = [_evento(f, registro) for f in dias
               if fechas.es_dia_de_evento(f) and (f >= hoy or _tuvo_actividad(f))]

    con_avance = [e for e in eventos if e["hechos"]]
    pasos = [{"id": p, "hecho": sum(e["pasos"].get(p) == "hecho" for e in con_avance),
              "omitido": sum(e["pasos"].get(p) == "omitido" for e in con_avance), "de": len(con_avance)}
             for p in PASOS_EVENTO]

    piezas = Counter(p.estado for p in Paquete.query.filter(Paquete.fecha_evento.between(desde, hasta)))

    seguidores = {red: [] for red in REDES}
    for s in Seguidores.query.filter(Seguidores.fecha.between(desde, hasta)).order_by(Seguidores.fecha):
        if s.red in seguidores:
            seguidores[s.red].append({"fecha": s.fecha.isoformat(), "cantidad": s.cantidad})

    ideas = Counter()
    for i in Idea.query.all():
        dia = i.creado.date()
        if desde <= dia <= hasta:
            ideas[(dia - timedelta(dia.weekday())).isoformat()] += 1

    pasados = [e for e in eventos if e["fecha"] < hoy.isoformat()]
    return jsonify(
        desde=desde.isoformat(), hasta=hasta.isoformat(), eventos=eventos, pasos=pasos,
        piezas={k: piezas.get(k, 0) for k in ("pendiente", "aprobado", "rechazado")},
        seguidores=seguidores, ideas=[{"semana": k, "ideas": v} for k, v in sorted(ideas.items())],
        resumen={
            "eventos": len(pasados),
            "proximos": len(eventos) - len(pasados),
            "con_tema": sum(bool(e["tema"]) for e in pasados),
            "con_video": sum(e["minutos"] > 0 for e in pasados),
            "minutos": sum(e["minutos"] for e in pasados),
            "piezas": sum(piezas.values()),
            "publicadas": sum(sum(e["publicadas"].values()) for e in eventos),
            "ideas": sum(ideas.values()),
        },
    )
