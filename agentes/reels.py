"""Agente de reels (fase 4).

Cuando llega una grabación a grabaciones/:
  1. faster-whisper la transcribe (con marcas de tiempo por segmento).
  2. Se buscan frases clave y se arman candidatos de 30 a 55 s (reglas de CLAUDE.md §2.1).
  3. Se eligen 5 momentos sin traslape, repartidos en el evento.
  4. ffmpeg los pasa a vertical 9:16 con subtítulos y el nombre del canal.
  5. Cada reel entra a la bandeja como pendiente.
  6. Con esos momentos se arma el carrusel de escenas (agentes/carrusel.py).
"""
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.bandeja import actualizar_por_agente, crear_paquete
from app.extensiones import db
from app.modelos import Grabacion, Paquete, ahora
from servicios import ffmpeg, whisper

from . import fechas

EXTENSIONES = {".mp4", ".mkv", ".mov", ".webm", ".flv"}
SEGUNDOS_ESTABLE = 60     # el archivo no debe cambiar en este tiempo (OBS terminó de escribir)
DURACION_MIN, DURACION_MAX, DURACION_IDEAL = 30.0, 55.0, 45.0
RECORTE_MIN, RECORTE_MAX = 5.0, 59.0
CUANTOS = 5

ORDINALES = {"primer": "primer", "segundo": "segundo", "tercer": "tercer", "cuarto": "cuarto", "quinto": "quinto"}

# (tipo, peso, patrón). Orden = prioridad de §2.1: misterio > intenciones > oración.
PATRONES = [
    ("misterio", 3.0, re.compile(r"\b(primer|segundo|tercer|cuarto|quinto)\s+misterio", re.I)),
    ("intenciones", 2.0, re.compile(r"\bintenci[oó]n", re.I)),
    ("oracion", 1.0, re.compile(r"dios te salve|padre nuestro|gloria al padre|santa mar[ií]a,? madre", re.I)),
    ("cierre", 1.5, re.compile(r"en el nombre del padre|bendici[oó]n|ave mar[ií]a pur[ií]sima", re.I)),
]
ETIQUETAS = {"intenciones": "Intenciones", "oracion": "Oración", "cierre": "Cierre y bendición",
             None: "Momento del evento"}


# --- Reglas para elegir los momentos (funciones puras, fáciles de probar) -----------

def _clasificar(texto: str, posicion: float) -> tuple[str | None, float, str | None]:
    """Tipo, peso y ordinal (si es anuncio de misterio) de un segmento de texto.

    `posicion` va de 0 (inicio del evento) a 1 (final): el cierre solo cuenta al final.
    """
    for tipo, peso, patron in PATRONES:
        m = patron.search(texto)
        if not m or (tipo == "cierre" and posicion < 0.85):
            continue
        return tipo, peso, (m.group(1).lower() if tipo == "misterio" else None)
    return None, 0.0, None


def _silencio_en(silencios, a: float, b: float) -> float:
    return sum(max(0.0, min(b, s1) - max(a, s0)) for s0, s1 in silencios)


def candidatos(segmentos: list, silencios: list, duracion: float) -> list[dict]:
    """Ventanas de 30–55 s que empiezan al inicio de una frase y terminan al final de otra.

    Puntaje = cada tipo de frase clave cuenta una vez (así no gana solo la ventana con más
    "Dios te salve") + premio si la ventana ABRE con la frase clave − silencios − lejanía de 45 s.
    """
    salida = []
    total = max(duracion, 1.0)
    info = [_clasificar(s[2], s[0] / total) for s in segmentos]
    pesos = {tipo: peso for tipo, peso, _ in PATRONES}
    for i, seg in enumerate(segmentos):
        mejor = None
        tipos: set = set()
        ordinal = None
        for j in range(i, len(segmentos)):
            if info[j][0]:
                tipos.add(info[j][0])
                ordinal = ordinal or info[j][2]
            largo = segmentos[j][1] - seg[0]
            if largo > DURACION_MAX:
                break
            if largo < DURACION_MIN:
                continue
            puntaje = sum(pesos[t] for t in tipos) + info[i][1] * 1.5
            puntaje -= 4.0 * _silencio_en(silencios, seg[0], segmentos[j][1]) / largo
            puntaje -= abs(largo - DURACION_IDEAL) / 50.0
            if mejor is None or puntaje > mejor["puntaje"]:
                principal = max(tipos, key=lambda t: pesos[t]) if tipos else None
                mejor = {"inicio": seg[0], "fin": segmentos[j][1], "puntaje": round(puntaje, 3),
                         "tipo": principal, "ordinal": ordinal if principal == "misterio" else None}
        if mejor:
            salida.append(mejor)
    return salida


def elegir_momentos(segmentos: list, silencios: list, duracion: float, cuantos: int = CUANTOS) -> list[dict]:
    """Los `cuantos` mejores momentos, sin traslape y repartidos (uno por tercio si se puede)."""
    cands = sorted(candidatos(segmentos, silencios, duracion), key=lambda c: -c["puntaje"])
    parte = max(duracion, 1.0) / cuantos
    elegidos: list[dict] = []

    def libre(c):
        return all(c["fin"] + 2 <= e["inicio"] or c["inicio"] >= e["fin"] + 2 for e in elegidos)

    usados = set()
    for c in cands:                      # 1a pasada: un momento por cada parte del evento
        t = min(int(c["inicio"] // parte), cuantos - 1)
        if len(elegidos) < cuantos and t not in usados and libre(c):
            elegidos.append(c)
            usados.add(t)
    for c in cands:                      # 2a pasada: completar con los mejores que queden
        if len(elegidos) < cuantos and libre(c):
            elegidos.append(c)
    return sorted(elegidos, key=lambda c: c["inicio"])


def etiqueta(momento: dict) -> str:
    if momento.get("tipo") == "misterio" and momento.get("ordinal"):
        return f"Anuncio del {ORDINALES[momento['ordinal']]} misterio"
    return ETIQUETAS.get(momento.get("tipo"), ETIQUETAS[None])


def _tiempo_srt(s: float) -> str:
    ms = int(round(max(s, 0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    seg, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{seg:02},{ms:03}"


def srt_para(segmentos: list, inicio: float, fin: float, ancho: int = 28) -> str:
    """Subtítulos .srt del tramo [inicio, fin], con tiempos desde 0 y máximo 2 renglones."""
    bloques = []
    for s0, s1, texto in segmentos:
        if s1 <= inicio or s0 >= fin or not texto.strip():
            continue
        a, b = max(s0, inicio) - inicio, min(s1, fin) - inicio
        renglones = textwrap.wrap(texto.strip(), ancho)
        trozos = [renglones[k:k + 2] for k in range(0, len(renglones), 2)]
        letras = sum(len(" ".join(t)) for t in trozos) or 1
        t = a
        for trozo in trozos:
            dur = (b - a) * len(" ".join(trozo)) / letras
            bloques.append((t, t + dur, "\n".join(trozo)))
            t += dur
    return "\n".join(f"{n}\n{_tiempo_srt(a)} --> {_tiempo_srt(b)}\n{texto}\n"
                     for n, (a, b, texto) in enumerate(bloques, start=1))


def texto_reel(fecha, momento: dict, segmentos: list) -> str:
    frase = " ".join(s[2] for s in segmentos if s[1] > momento["inicio"] and s[0] < momento["fin"])
    frase = textwrap.shorten(frase, 180, placeholder="…") if frase else ""
    canal = current_app.config["CANAL_NOMBRE"].replace(" ", "")
    from app.temas import titulo_de
    tema = titulo_de(fecha)
    lineas = [f"“{frase}”", ""] if frase else []
    lineas.append(f"{tema} · {fechas.nombre_fecha(fecha)}" if tema else f"Evento · {fechas.nombre_fecha(fecha)}")
    lineas += ["En vivo cada lunes y viernes a las 10:00 am (hora CDMX). Síguenos para no perdértelo.", "",
               f"#{canal} #Reels #Fe #Oración #Católicos #Reflexión"]
    return "\n".join(lineas)


# --- Trabajo con archivos -----------------------------------------------------------

def _dir_grabaciones() -> Path:
    d = Path(current_app.config["GRABACIONES_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render(grab: Grabacion, inicio: float, fin: float, carpeta_rel: str) -> None:
    salida = Path(current_app.config["PAQUETES_DIR"]) / carpeta_rel / "reel.mp4"
    ffmpeg.cortar_vertical(
        str(_dir_grabaciones() / grab.nombre), inicio, fin, srt_para(grab.segmentos or [], inicio, fin),
        current_app.config["CANAL_NOMBRE"], Path(current_app.config["FUENTES_DIR"]) / "PublicSans_700Bold.ttf",
        salida, mejorar=current_app.config.get("MEJORAR_VIDEO", True))


def procesar(grab: Grabacion) -> list[Paquete]:
    """Transcribe una grabación, elige 3 momentos, genera los reels y los manda a la bandeja."""
    ruta = _dir_grabaciones() / grab.nombre
    grab.estado, grab.error, grab.actualizado = "procesando", None, ahora()
    db.session.commit()
    try:
        grab.duracion = ffmpeg.duracion(str(ruta))
        db.session.commit()   # sin escritura abierta durante la transcripción: bloquearía a los demás agentes
        if grab.segmentos is None:
            current_app.logger.info("Transcribiendo %s (puede tardar varios minutos)", grab.nombre)
            grab.segmentos = whisper.transcribir(str(ruta), current_app.config["WHISPER_MODELO"])
            db.session.commit()
        momentos = elegir_momentos(grab.segmentos, ffmpeg.silencios(str(ruta)), grab.duracion)
        if not momentos:
            raise ValueError("sin momentos")
        nuevos = []
        from app.temas import titulo_de
        tema = titulo_de(grab.fecha_evento)
        for k, m in enumerate(momentos, start=1):
            carpeta_rel = f"{grab.fecha_evento.isoformat()}/reel-{grab.id}-{k}"
            _render(grab, m["inicio"], m["fin"], carpeta_rel)
            nuevos.append(crear_paquete(
                "reel", grab.fecha_evento, f"Reel {k} · {tema or etiqueta(m)}"[:120],
                texto_reel(grab.fecha_evento, m, grab.segmentos), carpeta=carpeta_rel, archivos=["reel.mp4"],
                datos={"grabacion_id": grab.id, "inicio": m["inicio"], "fin": m["fin"],
                       "duracion_fuente": grab.duracion, "tipo": m["tipo"], "momento": "despues"}))
        try:   # el carrusel de escenas es extra: si falla, los reels igual quedan
            from .carrusel import carrusel_de_escenas
            p = carrusel_de_escenas(grab.fecha_evento, ruta, momentos, grab.segmentos)
            if p:
                nuevos.append(p)
        except Exception:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.exception("No se pudo armar el carrusel de escenas de %s", grab.nombre)
            grab = db.session.get(Grabacion, grab.id)
        grab.estado = "lista"
    except Exception as e:  # noqa: BLE001 — cualquier fallo queda registrado y visible
        db.session.rollback()
        current_app.logger.exception("Falló el procesamiento de %s", grab.nombre)
        grab = db.session.get(Grabacion, grab.id)
        grab.estado = "error"
        grab.error = ("No encontramos momentos de 30 a 55 segundos con voz en esta grabación."
                      if isinstance(e, ValueError) and str(e) == "sin momentos"
                      else "No se pudo procesar la grabación. Revisa datos/logs/worker.log.")
        nuevos = []
    grab.actualizado = ahora()
    db.session.commit()
    return nuevos


def revisar_carpeta() -> list[Paquete]:
    """Registra grabaciones nuevas y procesa las que ya terminaron de copiarse."""
    nuevos = []
    for ruta in sorted(_dir_grabaciones().iterdir()):
        if not ruta.is_file() or ruta.suffix.lower() not in EXTENSIONES or len(ruta.name) > 200:
            continue
        st = ruta.stat()
        grab = Grabacion.query.filter_by(nombre=ruta.name).first()
        if grab is None:
            momento = datetime.fromtimestamp(st.st_mtime, timezone.utc)
            db.session.add(Grabacion(nombre=ruta.name, tamano=st.st_size,
                                     fecha_evento=fechas.fecha_de_grabacion(momento)))
            db.session.commit()
            continue                       # se procesa en la siguiente vuelta, si ya no cambió
        if grab.estado != "nueva":
            continue
        quieto = datetime.now().timestamp() - st.st_mtime >= SEGUNDOS_ESTABLE
        if st.st_size != grab.tamano or not quieto:
            grab.tamano = st.st_size        # OBS sigue escribiendo
            db.session.commit()
            continue
        nuevos += procesar(grab)
    return nuevos


def aplicar_recortes() -> int:
    """Regenera los reels a los que alguien les ajustó inicio/fin en la bandeja."""
    hechos = 0
    for p in Paquete.query.filter_by(tipo="reel", estado="pendiente").all():
        datos = dict(p.datos or {})
        recorte = datos.get("recortar")
        if not recorte:
            continue
        grab = db.session.get(Grabacion, datos.get("grabacion_id"))
        if grab is None or not (_dir_grabaciones() / grab.nombre).exists():
            datos.pop("recortar")
            datos["error_recorte"] = "Ya no está la grabación original; no se pudo recortar."
            actualizar_por_agente(p.id, {"datos": datos}, "error", datos["error_recorte"])
            continue
        try:
            _render(grab, recorte["inicio"], recorte["fin"], p.carpeta)
        except Exception:  # noqa: BLE001
            current_app.logger.exception("Falló el recorte del paquete %s", p.id)
            datos.pop("recortar")
            datos["error_recorte"] = "No se pudo regenerar el video. Intenta con otros tiempos."
            actualizar_por_agente(p.id, {"datos": datos}, "error", datos["error_recorte"])
            continue
        datos.update(inicio=recorte["inicio"], fin=recorte["fin"])
        datos.pop("recortar")
        datos.pop("error_recorte", None)
        actualizar_por_agente(p.id, {"datos": datos}, "recortado",
                              f"{recorte['inicio']:.1f} s a {recorte['fin']:.1f} s")
        hechos += 1
    return hechos
