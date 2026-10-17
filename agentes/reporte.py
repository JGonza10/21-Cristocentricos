"""Agente de reportes: arma solo el reporte semanal con los datos del sistema (sin IA).

Corre los lunes a las 8 am y reporta la semana anterior (lunes a domingo). También se puede
generar a mano desde Inicio. Incluye el resumen de cada evento ("resumen del vivo"), quién
dirigió y apoyó, qué pasó en la bandeja, cómo quedó cada red, los seguidores contra la meta y
una lista de "qué mejorar" calculada con reglas.
"""
from datetime import date, timedelta

from flask import current_app

from app.extensiones import db
from app.modelos import REDES, Grabacion, Paquete, Publicacion, Reporte, Seguidores, Turno, ahora

from . import fechas

NOMBRE_RED = {"instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube"}


def lunes_de(d: date) -> date:
    return d - timedelta(d.weekday())


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _seguidores(hasta: date) -> dict:
    """Último conteo capturado por red hasta esa fecha: {red: (fecha, cantidad)}."""
    resultado = {}
    for red in REDES:
        s = Seguidores.query.filter(Seguidores.red == red, Seguidores.fecha <= hasta) \
            .order_by(Seguidores.fecha.desc()).first()
        if s:
            resultado[red] = (s.fecha, s.cantidad)
    return resultado


def _tema(f: date) -> str:
    from app.modelos import Tema
    t = db.session.get(Tema, f)
    return t.titulo if t else "Sin tema"


def _evento(f: date, hoy: date) -> dict:
    turnos = Turno.query.filter_by(fecha=f).all()
    dirige = next((t.integrante.nombre for t in turnos if t.rol == "dirige"), None)
    apoyan = [t.integrante.nombre for t in turnos if t.rol == "apoya"]
    grab = Grabacion.query.filter_by(fecha_evento=f).order_by(Grabacion.id.desc()).first()
    paquetes = Paquete.query.filter_by(fecha_evento=f).all()
    por_estado = {e: sum(1 for p in paquetes if p.estado == e) for e in ("pendiente", "aprobado", "rechazado")}
    pubs = {}
    for p in paquetes:
        for x in p.publicaciones:
            pubs.setdefault(x.red, {}).setdefault(x.estado, 0)
            pubs[x.red][x.estado] += 1
    return {
        "fecha": f.isoformat(), "nombre": fechas.nombre_fecha(f), "tema": _tema(f),
        "ya_paso": f < hoy or (f == hoy and fechas.ahora_cdmx() >= fechas.fin(f)),
        "dirige": dirige, "apoyan": apoyan,
        "grabacion": {"nombre": grab.nombre, "estado": grab.estado,
                      "minutos": round(grab.duracion / 60) if grab.duracion else None} if grab else None,
        "reels": sum(1 for p in paquetes if p.tipo == "reel"),
        "carrusel": any(p.tipo == "carrusel" for p in paquetes),
        "bandeja": por_estado,
        "publicaciones": pubs,
    }


def calcular(semana: date, hoy: date | None = None) -> dict:
    """Datos del reporte de la semana que empieza en `semana` (lunes)."""
    hoy = hoy or fechas.hoy_cdmx()
    fin = semana + timedelta(6)
    eventos = [_evento(f, hoy) for f in fechas.proximos_eventos(semana, 6)]

    # Equipo: cuántas veces dirigió y apoyó cada quien
    equipo = {}
    for t in Turno.query.filter(Turno.fecha.between(semana, fin)).all():
        e = equipo.setdefault(t.integrante.nombre, {"dirige": 0, "apoya": 0})
        e["dirige" if t.rol == "dirige" else "apoya"] += 1

    # Publicaciones de la semana por red
    redes = {r: {} for r in REDES}
    consulta = db.session.query(Publicacion).join(Paquete).filter(Paquete.fecha_evento.between(semana, fin))
    for x in consulta.all():
        redes.setdefault(x.red, {}).setdefault(x.estado, 0)
        redes[x.red][x.estado] += 1

    # Seguidores contra la meta
    meta = current_app.config.get("META_SEGUIDORES", 1000)
    ahora_seg = _seguidores(fin)
    antes_seg = _seguidores(semana - timedelta(1))
    seguidores = {
        "meta": meta,
        "por_red": {r: {"cantidad": c, "fecha": f.isoformat(), "cambio": c - antes_seg[r][1] if r in antes_seg else None}
                    for r, (f, c) in ahora_seg.items()},
    }
    total = sum(c for _, c in ahora_seg.values())
    seguidores["total"] = total if ahora_seg else None
    seguidores["avance_pct"] = round(min(100, total * 100 / meta)) if ahora_seg and meta else None

    totales = {
        "eventos": len(eventos),
        "con_grabacion": sum(1 for e in eventos if e["grabacion"]),
        "reels": sum(e["reels"] for e in eventos),
        "carruseles": sum(1 for e in eventos if e["carrusel"]),
        "aprobados": sum(e["bandeja"]["aprobado"] for e in eventos),
        "rechazados": sum(e["bandeja"]["rechazado"] for e in eventos),
        "pendientes": sum(e["bandeja"]["pendiente"] for e in eventos),
        "publicadas": sum(c.get("publicado", 0) for c in redes.values()),
        "por_subir": sum(c.get("listo_manual", 0) for c in redes.values()),
        "con_error": sum(c.get("error", 0) for c in redes.values()),
    }
    return {
        "semana": semana.isoformat(), "fin": fin.isoformat(),
        "titulo": f"Semana del {semana.day} de {fechas.MESES[semana.month - 1]} al {fin.day} de {fechas.MESES[fin.month - 1]}",
        "totales": totales, "eventos": eventos, "equipo": equipo, "redes": redes,
        "seguidores": seguidores, "mejorar": _que_mejorar(eventos, totales, redes, seguidores, semana),
    }


def _que_mejorar(eventos, totales, redes, seguidores, semana) -> list[str]:
    avisos = []
    for e in eventos:
        if e["ya_paso"] and not e["dirige"]:
            avisos.append(f"El {e['nombre'].lower()} no tuvo a nadie asignado para dirigir.")
        if e["ya_paso"] and not e["grabacion"]:
            avisos.append(f"No llegó la grabación del {e['nombre'].lower()}: revisa que OBS o StreamYard guarden en la carpeta grabaciones.")
        if e["grabacion"] and e["grabacion"]["estado"] == "error":
            avisos.append(f"La grabación del {e['nombre'].lower()} no se pudo procesar.")
    if totales["pendientes"]:
        avisos.append(f"Quedaron {_plural(totales['pendientes'], 'paquete', 'paquetes')} sin revisar en la bandeja.")
    revisados = totales["aprobados"] + totales["rechazados"]
    if revisados >= 3 and totales["rechazados"] * 2 > revisados:
        avisos.append("Se rechazó más de la mitad de lo que llegó: conviene revisar cómo se eligen los momentos de los reels.")
    for red, c in redes.items():
        if c.get("error"):
            avisos.append(f"{NOMBRE_RED.get(red, red)}: {_plural(c['error'], 'publicación falló', 'publicaciones fallaron')}.")
        if c.get("listo_manual"):
            avisos.append(f"{NOMBRE_RED.get(red, red)}: {_plural(c['listo_manual'], 'publicación espera', 'publicaciones esperan')} subirse a mano.")
    proximos = fechas.proximos_eventos(semana + timedelta(7), 6)
    sin_dirige = [f for f in proximos if not Turno.query.filter_by(fecha=f, rol="dirige").first()]
    if sin_dirige:
        avisos.append(f"La próxima semana hay {_plural(len(sin_dirige), 'evento', 'eventos')} sin quién dirija.")
    if seguidores["total"] is None:
        avisos.append("Captura los seguidores de cada red para medir el avance hacia la meta.")
    elif seguidores["total"] < seguidores["meta"]:
        faltan = seguidores["meta"] - seguidores["total"]
        avisos.append(f"Faltan {faltan:,} seguidores para la meta de {seguidores['meta']:,}.")
    return avisos or ["Todo salió bien esta semana."]


def generar(semana: date) -> Reporte:
    """Calcula y guarda (o reemplaza) el reporte de esa semana."""
    semana = lunes_de(semana)
    r = db.session.get(Reporte, semana) or Reporte(semana=semana)
    r.datos = calcular(semana)
    r.creado = ahora()
    db.session.add(r)
    db.session.commit()
    return r


def tarea_semanal() -> date:
    """Lunes 8 am: reporte de la semana que acaba de terminar."""
    semana = lunes_de(fechas.hoy_cdmx()) - timedelta(7)
    generar(semana)
    return semana
