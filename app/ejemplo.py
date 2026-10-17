"""Modo ejemplo: una copia aparte de la app (base datos/ejemplo.db, puerto 5022) con datos inventados
para revisar cómo funciona todo el proceso sin tocar los datos reales. La arranca ejemplo.bat.

Siembra eventos anteriores ya completos (con grabación, reels, carrusel, publicaciones y reporte),
turnos en el calendario y seguidores. El evento más reciente queda en el paso 1, y el botón
«Avanzar el ejemplo» hace lo que haría el sistema (o la persona) en el paso en el que va.

    GET  /api/ejemplo             {"activo": true}
    POST /api/ejemplo/avanzar     simula el paso actual del evento que se está viendo {"fecha"?}
    POST /api/ejemplo/reiniciar   borra los datos de ejemplo y los vuelve a sembrar

Este blueprint solo se registra con EJEMPLO=1; la app real nunca lo tiene.
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

from .extensiones import db
from .modelos import (AvancePaso, EstadoAgente, EventoCalendario, Grabacion, HistorialPaquete, Integrante,
                      Paquete, Publicacion, Reporte, Seguidores, Turno, ahora)
from .seguridad import login_requerido

bp = Blueprint("ejemplo", __name__, url_prefix="/api/ejemplo")

GENTE = [("María López", True), ("José Hernández", True), ("Ana Ruiz", True),
         ("Pedro Gómez", False), ("Lucía Torres", False)]
SEGUIDORES_BASE = {"instagram": 310, "facebook": 220, "tiktok": 95, "youtube": 140}
TABLAS = (Publicacion, HistorialPaquete, Paquete, Grabacion, AvancePaso, Reporte, Seguidores, Turno,
          EventoCalendario, Integrante, EstadoAgente)


def _evento_demo(hoy_dt: datetime) -> date:
    """El evento más reciente que ya terminó: es el que queda en el paso 1."""
    from agentes import fechas
    d = hoy_dt.date()
    while not (fechas.es_dia_de_evento(d) and fechas.fin(d) <= hoy_dt):
        d -= timedelta(1)
    return d


def _turnos(f: date, gente: list[Integrante], n: int) -> None:
    dirigen = [i for i in gente if i.puede_dirigir]
    db.session.add(Turno(fecha=f, rol="dirige", integrante=dirigen[n % len(dirigen)]))
    db.session.add(Turno(fecha=f, rol="apoya", integrante=gente[(n + 3) % len(gente)]))


def _grabacion(f: date) -> Grabacion:
    g = Grabacion(nombre=f"evento-{f.isoformat()}.mp4", tamano=1_800_000_000, fecha_evento=f, estado="lista",
                  duracion=3540.0, segmentos=[[0, 6, "En el nombre del Padre, del Hijo y del Espíritu Santo."]])
    db.session.add(g)
    db.session.flush()
    return g


def _reels(f: date, g: Grabacion) -> list[Paquete]:
    from agentes import fechas
    lista = fechas.misterios(f)["lista"]
    reels = []
    for n, (misterio, cita) in enumerate(lista[:3]):
        p = Paquete(tipo="reel", fecha_evento=f, titulo=f"Reel {n + 1} · {misterio}",
                    texto=f"{misterio} ({cita}).\n\nÚnete al evento en vivo cada lunes y viernes a las 10 am."
                          "\n\n#SantoRosario #Cristocéntricos",
                    datos={"grabacion_id": g.id, "inicio": 600 * (n + 1), "fin": 600 * (n + 1) + 45})
        p.historial.append(HistorialPaquete(accion="creado", detalle="Ejemplo"))
        db.session.add(p)
        reels.append(p)
    return reels


def _carrusel(f: date) -> Paquete:
    from agentes import fechas
    p = Paquete(tipo="carrusel", fecha_evento=f, titulo=f"Carrusel · {fechas.nombre_fecha(f)}",
                texto=f"{fechas.misterios(f)['nombre']}: meditemos juntos cada misterio.\n\n#SantoRosario #Cristocéntricos")
    p.historial.append(HistorialPaquete(accion="creado", detalle="Ejemplo"))
    db.session.add(p)
    return p


def _revisar(paquetes: list[Paquete], rechazar: int = 1) -> None:
    """Aprueba todos menos el último `rechazar` reels."""
    reels = [p for p in paquetes if p.tipo == "reel"]
    for p in paquetes:
        if p.estado != "pendiente":
            continue
        if rechazar and p in reels[-rechazar:]:
            p.estado, p.motivo_rechazo = "rechazado", "Ejemplo: el corte empieza a media frase."
        else:
            p.estado = "aprobado"
        p.revisado_en = ahora()
        p.historial.append(HistorialPaquete(accion=p.estado, detalle="Ejemplo"))


def _publicar(paquetes: list[Paquete], todo_publicado: bool) -> None:
    for p in paquetes:
        if p.estado != "aprobado" or p.publicaciones:
            continue
        redes = ("instagram", "facebook", "youtube", "tiktok") if p.tipo == "reel" else ("instagram", "facebook")
        for red in redes:
            auto = red == "youtube"
            estado = "publicado" if todo_publicado or auto else "listo_manual"
            p.publicaciones.append(Publicacion(red=red, estado=estado, intentos=1,
                                               ruta=None if auto else f"subir_manual/{red}/ejemplo-{p.id}"))


def _completo(f: date, gente: list[Integrante], n: int) -> None:
    _turnos(f, gente, n)
    db.session.add(AvancePaso(fecha=f, paso="prepara", estado="hecho", nota="Ejemplo: intenciones, guion y lista listos."))
    db.session.add(AvancePaso(fecha=f, paso="registro", estado="omitido", nota="La hoja de registro aún no existe."))
    g = _grabacion(f)
    paquetes = _reels(f, g) + [_carrusel(f)]
    db.session.flush()
    _revisar(paquetes)
    _publicar(paquetes, todo_publicado=True)


def sembrar(hoy_dt: datetime | None = None) -> date:
    """Llena la base de ejemplo. Devuelve la fecha del evento que queda en el paso 1."""
    from agentes import fechas, reporte
    hoy_dt = hoy_dt or fechas.ahora_cdmx()
    demo = _evento_demo(hoy_dt)

    gente = [Integrante(nombre=n, correo=f"{n.split()[0].lower()}@ejemplo.invalid", puede_dirigir=d,
                        aviso_privacidad=ahora()) for n, d in GENTE]
    db.session.add_all(gente)
    db.session.flush()

    anteriores = [f for f in fechas.proximos_eventos(demo - timedelta(24), 24) if f < demo]
    for n, f in enumerate(anteriores):
        _completo(f, gente, n)

    # Calendario: próximos eventos, unos asignados y otros con hueco.
    for n, f in enumerate(fechas.proximos_eventos(demo + timedelta(1), 21)):
        if n % 3 != 2:
            _turnos(f, gente, n + len(anteriores))

    # Seguidores capturados cada lunes.
    lunes = [reporte.lunes_de(anteriores[0]) + timedelta(7 * k) for k in range(5)]
    for k, l in enumerate(x for x in lunes if x <= hoy_dt.date()):
        for red, base in SEGUIDORES_BASE.items():
            db.session.add(Seguidores(fecha=l, red=red, cantidad=base + k * (12 + len(red))))
    db.session.commit()

    # Reporte de cada semana ya cerrada; los eventos de la semana del demo lo marcan a mano.
    for semana in sorted({reporte.lunes_de(f) for f in anteriores}):
        if semana < reporte.lunes_de(demo):
            reporte.generar(semana)
    for f in anteriores:
        if reporte.lunes_de(f) == reporte.lunes_de(demo):
            db.session.add(AvancePaso(fecha=f, paso="mides", estado="hecho", nota="Ejemplo: su reporte sale el próximo lunes."))
    db.session.commit()
    return demo


def vaciar() -> None:
    for t in TABLAS:
        t.query.delete()
    db.session.commit()


def avanzar(f: date) -> str:
    """Hace lo que toca en el paso actual de ese evento. Devuelve qué se simuló."""
    from agentes import reporte

    from .avance import avance
    actual = avance(f)["actual"]
    if actual is None:
        return "Este evento ya completó todo el proceso."
    paquetes = Paquete.query.filter_by(fecha_evento=f).all()
    gente = Integrante.query.filter_by(activo=True).all()

    if actual == "turnos":
        Turno.query.filter_by(fecha=f).delete()
        _turnos(f, gente, f.day)
        texto = "Se asignó quién dirige y quién apoya (en la app real lo haces en el calendario)."
    elif actual == "prepara":
        db.session.add(AvancePaso(fecha=f, paso="prepara", estado="hecho", nota="Ejemplo: intenciones, guion y lista listos."))
        texto = "Se marcó la preparación con Claude (en la app real lo marcas tú)."
    elif actual == "vivo":
        db.session.add(AvancePaso(fecha=f, paso="vivo", estado="hecho", nota="Ejemplo: el evento ya se transmitió."))
        texto = "Se dio por hecho el evento en vivo."
    elif actual == "grabacion":
        Grabacion.query.filter_by(fecha_evento=f).delete()
        _grabacion(f)
        texto = "Llegó la grabación a la carpeta y quedó procesada (en la app real lo hace el agente)."
    elif actual == "reels":
        g = Grabacion.query.filter_by(fecha_evento=f).first() or _grabacion(f)
        _reels(f, g)
        texto = "El agente de reels mandó 3 reels a la bandeja. Puedes verlos en Contenido."
    elif actual == "carrusel":
        _carrusel(f)
        texto = "El agente del carrusel mandó el carrusel a la bandeja."
    elif actual == "bandeja":
        _revisar(paquetes)
        texto = "Se revisó la bandeja: 3 aprobados y 1 rechazado (en la app real lo haces tú en Contenido)."
    elif actual == "publicacion":
        _publicar(paquetes, todo_publicado=False)
        texto = "El agente de publicación subió a YouTube y dejó Instagram, Facebook y TikTok listos para subir a mano."
    elif actual == "redes":
        for p in paquetes:
            for x in p.publicaciones:
                if x.estado in ("listo_manual", "error", "subiendo"):
                    x.estado, x.actualizado = "publicado", ahora()
        texto = "Se subió a mano lo que faltaba en cada red."
    elif actual == "registro":
        db.session.add(AvancePaso(fecha=f, paso="registro", estado="hecho", nota="Ejemplo: anotado en la hoja de registro."))
        texto = "Se anotó el video en la hoja de registro."
    else:  # mides
        db.session.commit()
        reporte.generar(f)
        texto = "El sistema armó el reporte semanal. Ábrelo con «Ver reporte»."
    db.session.commit()
    return texto


@bp.get("")
@login_requerido
def ver():
    return jsonify(activo=True)


@bp.post("/avanzar")
@login_requerido
def ruta_avanzar():
    from .avance import ErrorAvance, _fecha, avance, evento_activo
    texto = (request.get_json(silent=True) or {}).get("fecha")
    try:
        f = _fecha(texto) if texto else evento_activo()
    except ErrorAvance as e:
        return jsonify(error=e.mensaje), e.codigo
    return jsonify(mensaje=avanzar(f), avance=avance(f))


@bp.post("/reiniciar")
@login_requerido
def ruta_reiniciar():
    vaciar()
    demo = sembrar()
    return jsonify(mensaje="Ejemplo reiniciado.", fecha=demo.isoformat())
