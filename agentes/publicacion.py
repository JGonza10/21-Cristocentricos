"""Agente de publicación (fase 5, con la opción automática de Meta de la fase 8).

Regla de oro: SOLO toca paquetes aprobados por una persona. Antes de cada subida vuelve a
leer el estado desde la base, por si alguien lo regresó a pendientes en ese momento.

Por cada red:
  - YouTube (reels): sube directo en PRIVADO si Google está autorizado.
  - Facebook / Instagram: automático solo si META_AUTO=1 y la red lo permite.
  - Todo lo demás: carpeta paquetes/<fecha>/subir_manual/<red>/<paquete>/ con los
    archivos y un texto.txt listo para copiar y pegar.
"""
import shutil
from pathlib import Path

from flask import current_app

from app.bandeja import paquetes_aprobados
from app.extensiones import db
from app.modelos import Paquete, Publicacion, ahora
from servicios import google, meta, youtube

REDES_POR_TIPO = {
    "carrusel": ["instagram", "facebook", "tiktok"],
    "reel": ["instagram", "facebook", "tiktok", "youtube"],
}
MAX_INTENTOS = 3


def _raiz() -> Path:
    return Path(current_app.config["PAQUETES_DIR"])


def _archivos(p: Paquete) -> list[Path]:
    return [_raiz() / p.carpeta / a for a in p.archivos]


def texto_para(p: Paquete, red: str) -> str:
    if red == "youtube":
        return f"TÍTULO:\n{titulo_youtube(p)}\n\nDESCRIPCIÓN:\n{p.texto}\n"
    return p.texto + "\n"


def titulo_youtube(p: Paquete) -> str:
    return f"{p.titulo} · Santo Rosario #Shorts"[:100]


def carpeta_manual(p: Paquete, red: str) -> str:
    """Prepara subir_manual/<red>/<tipo>-<id>/ y devuelve su ruta relativa a paquetes/."""
    rel = f"{p.fecha_evento.isoformat()}/subir_manual/{red}/{p.tipo}-{p.id}"
    destino = _raiz() / rel
    destino.mkdir(parents=True, exist_ok=True)
    for archivo in _archivos(p):
        shutil.copy2(archivo, destino / archivo.name)
    (destino / "texto.txt").write_text(texto_para(p, red), encoding="utf-8")
    return rel


def _sigue_aprobado(pid: int) -> bool:
    db.session.expire_all()
    p = db.session.get(Paquete, pid)
    return p is not None and p.estado == "aprobado"


def _automatico(red: str, tipo: str) -> bool:
    if red == "youtube":
        return tipo == "reel" and google.configurado()
    return meta.soporta(red, tipo)


def _subir(p: Paquete, red: str) -> str:
    if red == "youtube":
        return youtube.subir(str(_archivos(p)[0]), titulo_youtube(p), p.texto)
    return meta.publicar(red, p.tipo, _archivos(p), p.texto)


def publicar_paquete(p: Paquete) -> None:
    if not _sigue_aprobado(p.id):         # doble candado: nunca publicar sin aprobación
        return
    p = db.session.get(Paquete, p.id)
    for red in REDES_POR_TIPO[p.tipo]:
        pub = Publicacion.query.filter_by(paquete_id=p.id, red=red).first()
        if pub and (pub.estado in ("publicado", "listo_manual", "subiendo") or pub.intentos >= MAX_INTENTOS):
            continue
        pub = pub or Publicacion(paquete_id=p.id, red=red, estado="subiendo")
        if not _automatico(red, p.tipo):
            pub.ruta, pub.estado, pub.error = carpeta_manual(p, red), "listo_manual", None
            pub.actualizado = ahora()
            db.session.add(pub)
            db.session.commit()
            continue
        if not _sigue_aprobado(p.id):
            return
        pub.estado, pub.actualizado = "subiendo", ahora()
        db.session.add(pub)
        db.session.commit()
        try:
            pub.url = _subir(p, red)
            pub.estado, pub.error = "publicado", None
            current_app.logger.info("Paquete %s publicado en %s: %s", p.id, red, pub.url)
        except Exception:  # noqa: BLE001
            current_app.logger.exception("Falló la publicación del paquete %s en %s", p.id, red)
            pub.intentos += 1
            pub.estado = "error"
            pub.error = (f"No se pudo publicar en {red.capitalize()}. Se reintentará."
                         if pub.intentos < MAX_INTENTOS
                         else f"No se pudo publicar en {red.capitalize()}. Usa «Reintentar» o súbelo a mano.")
            if pub.intentos >= MAX_INTENTOS and not pub.ruta:
                pub.ruta = carpeta_manual(p, red)   # plan B: dejarlo listo para subir a mano
        pub.actualizado = ahora()
        db.session.commit()


def tarea() -> int:
    """Lo que corre el worker cada pocos minutos."""
    aprobados = paquetes_aprobados()
    for p in aprobados:
        publicar_paquete(p)
    return len(aprobados)
