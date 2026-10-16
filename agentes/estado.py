"""Latido de cada agente: así la pantalla de Inicio sabe si el worker está corriendo."""
from app.extensiones import db
from app.modelos import EstadoAgente, ahora


def latido(nombre: str, mensaje: str | None = None, ok: bool = False, error: bool = False) -> None:
    """Registra que el agente sigue vivo. `ok` marca un trabajo terminado; `error`, un fallo."""
    e = db.session.get(EstadoAgente, nombre) or EstadoAgente(nombre=nombre)
    e.latido = ahora()
    if mensaje is not None:
        e.mensaje = mensaje[:300]
        e.error = error
    if ok:
        e.ultimo_ok = e.latido
    db.session.add(e)
    db.session.commit()
