"""Calendario del equipo (fase 6): reparto automático de turnos e invitaciones.

- Domingo 6 pm (hora CDMX): se reparten los turnos de la semana que empieza.
- Reparto justo: le toca a quien lleva menos turnos en los últimos 90 días (y entre
  empatados, a quien hace más que no participa). Nadie tiene dos roles el mismo día.
- Cada hora se revisan las invitaciones de los próximos 14 días: si cambió quién
  participa, se actualiza el evento de Google Calendar.
"""
from datetime import date, timedelta

from flask import current_app
from sqlalchemy import func

from app.extensiones import db
from app.modelos import EventoCalendario, Integrante, Turno, ahora
from servicios import calendario, google

from . import fechas

DIAS_HISTORIAL = 90


def turnos_de(f: date) -> dict:
    ts = Turno.query.filter_by(fecha=f).order_by(Turno.id).all()
    return {"dirige": next((t for t in ts if t.rol == "dirige"), None), "apoyan": [t for t in ts if t.rol == "apoya"]}


def _carga(desde: date) -> dict[int, tuple[int, date]]:
    """{integrante_id: (cuántos turnos desde `desde`, fecha de su último turno)}"""
    filas = (db.session.query(Turno.integrante_id, func.count(Turno.id), func.max(Turno.fecha))
             .filter(Turno.fecha >= desde).group_by(Turno.integrante_id).all())
    return {i: (n, ultimo) for i, n, ultimo in filas}


def repartir(dias: list[date]) -> list[Turno]:
    """Llena los huecos (quién dirige y quién apoya) de cada día. No cambia lo ya asignado."""
    if not dias:
        return []
    apoyos = current_app.config["APOYOS_POR_EVENTO"]
    carga = _carga(min(dias) - timedelta(DIAS_HISTORIAL))
    activos = Integrante.query.filter_by(activo=True).order_by(Integrante.id).all()
    nuevos = []

    def orden(i: Integrante):
        n, ultimo = carga.get(i.id, (0, date.min))
        return (n, ultimo, i.id)

    for f in sorted(dias):
        actuales = turnos_de(f)
        ocupados = {t.integrante_id for t in Turno.query.filter_by(fecha=f)}
        elegir = []
        if actuales["dirige"] is None:
            elegir.append(("dirige", [i for i in activos if i.puede_dirigir]))
        elegir += [("apoya", activos)] * max(apoyos - len(actuales["apoyan"]), 0)
        for rol, opciones in elegir:
            libres = sorted((i for i in opciones if i.id not in ocupados), key=orden)
            if not libres:
                continue
            i = libres[0]
            t = Turno(fecha=f, rol=rol, integrante_id=i.id, automatico=True)
            db.session.add(t)
            nuevos.append(t)
            ocupados.add(i.id)
            n, ultimo = carga.get(i.id, (0, date.min))
            carga[i.id] = (n + 1, max(ultimo, f))
    db.session.commit()
    return nuevos


def semana_siguiente(hoy: date) -> list[date]:
    """Lunes y viernes de la semana que empieza después de `hoy` (pensado para el domingo)."""
    lunes = hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)
    return [lunes, lunes + timedelta(4)]


def tarea_reparto() -> list[Turno]:
    nuevos = repartir(semana_siguiente(fechas.hoy_cdmx()))
    sincronizar_invitaciones()
    return nuevos


def _descripcion(f: date) -> str:
    from app.temas import tema_de
    t = turnos_de(f)
    tema = tema_de(f)
    lineas = [f"Tema: {tema.titulo}" if tema else "Tema: por definir", "10:00 a 11:00 am (hora CDMX)", ""]
    if tema and tema.descripcion:
        lineas[1:1] = [tema.descripcion]
    if t["dirige"]:
        lineas.append(f"Dirige: {t['dirige'].integrante.nombre}")
    if t["apoyan"]:
        lineas.append("Apoya: " + ", ".join(x.integrante.nombre for x in t["apoyan"]))
    lineas += ["", f"Invitación automática de {current_app.config['CANAL_NOMBRE']}."]
    return "\n".join(lineas)


def _titulo_evento(f: date) -> str:
    from app.temas import titulo_de
    tema = titulo_de(f)
    return f"Evento en vivo · {tema}" if tema else f"Evento en vivo · {fechas.nombre_fecha(f)}"


def sincronizar_invitaciones(dias: int = 14) -> int:
    """Crea o actualiza los eventos de Calendar cuyo equipo cambió. Devuelve cuántos tocó."""
    if not google.configurado():
        return 0
    hoy = fechas.hoy_cdmx()
    tocados = 0
    for f in fechas.proximos_eventos(hoy, dias):
        t = turnos_de(f)
        participantes = ([t["dirige"]] if t["dirige"] else []) + t["apoyan"]
        correos = sorted({x.integrante.correo for x in participantes if x.integrante.correo})
        ev = db.session.get(EventoCalendario, f) or EventoCalendario(fecha=f)
        if not correos and not ev.google_id:
            continue
        if ev.estado == "enviada" and sorted(ev.invitados or []) == correos:
            continue
        try:
            ev.google_id = calendario.sincronizar(
                f, current_app.config["GOOGLE_CALENDAR_ID"],
                _titulo_evento(f), _descripcion(f), correos, ev.google_id)
            ev.invitados, ev.estado, ev.error = correos, "enviada", None
            tocados += 1
        except Exception:  # noqa: BLE001
            current_app.logger.exception("No se pudo sincronizar la invitación del %s", f)
            ev.estado, ev.error = "error", "No se pudo enviar la invitación. Se reintentará en una hora."
        ev.actualizado = ahora()
        db.session.add(ev)
        db.session.commit()
    return tocados
