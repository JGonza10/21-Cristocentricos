"""Modelos de la base de datos (SQLite)."""
from datetime import datetime, timezone

from .extensiones import db


def ahora() -> datetime:
    """Fecha y hora actual en UTC (sin zona, así la guarda SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(40), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(80), nullable=False)
    hash_password = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    creado = db.Column(db.DateTime, default=ahora, nullable=False)
    ultimo_acceso = db.Column(db.DateTime)

    def a_dict(self) -> dict:
        return {"id": self.id, "usuario": self.usuario, "nombre": self.nombre}


class IntentoLogin(db.Model):
    """Registro de cada intento de inicio de sesión (para el bloqueo temporal)."""
    __tablename__ = "intentos_login"

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(40), nullable=False, index=True)
    ip = db.Column(db.String(45), nullable=False, index=True)
    exito = db.Column(db.Boolean, nullable=False)
    fecha = db.Column(db.DateTime, default=ahora, nullable=False, index=True)


# --- Bandeja de aprobación (fase 2) -------------------------------------------------

TIPOS_PAQUETE = ("carrusel", "reel")
ESTADOS_PAQUETE = ("pendiente", "aprobado", "rechazado")


class Paquete(db.Model):
    """Un carrusel o un reel que preparó un agente y espera visto bueno humano.

    Los archivos viven en `paquetes/<carpeta>/`; aquí solo se guardan sus nombres.
    `version` sube con cada cambio: así, si los dos aprobadores tienen abierta la
    bandeja, el segundo en actuar recibe un aviso en lugar de pisar al primero.
    """
    __tablename__ = "paquetes"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    fecha_evento = db.Column(db.Date, nullable=False, index=True)
    titulo = db.Column(db.String(120), nullable=False)
    texto = db.Column(db.Text, nullable=False, default="")
    carpeta = db.Column(db.String(200), nullable=False, default="")
    archivos = db.Column(db.JSON, nullable=False, default=list)
    estado = db.Column(db.String(20), nullable=False, default="pendiente", index=True)
    motivo_rechazo = db.Column(db.String(300))
    version = db.Column(db.Integer, nullable=False, default=1)
    creado = db.Column(db.DateTime, default=ahora, nullable=False)
    actualizado = db.Column(db.DateTime, default=ahora, nullable=False)
    revisado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    revisado_en = db.Column(db.DateTime)

    revisado_por = db.relationship("Usuario")
    historial = db.relationship("HistorialPaquete", order_by="HistorialPaquete.id",
                                cascade="all, delete-orphan", back_populates="paquete")

    def a_dict(self) -> dict:
        return {
            "id": self.id, "tipo": self.tipo, "fecha_evento": self.fecha_evento.isoformat(),
            "titulo": self.titulo, "texto": self.texto, "archivos": list(self.archivos or []),
            "estado": self.estado, "motivo_rechazo": self.motivo_rechazo, "version": self.version,
            "creado": _iso(self.creado), "actualizado": _iso(self.actualizado),
            "revisado_por": self.revisado_por.nombre if self.revisado_por else None,
            "revisado_en": _iso(self.revisado_en),
        }


class HistorialPaquete(db.Model):
    """Quién hizo qué y cuándo con cada paquete (creado, editado, aprobado...)."""
    __tablename__ = "historial_paquetes"

    id = db.Column(db.Integer, primary_key=True)
    paquete_id = db.Column(db.Integer, db.ForeignKey("paquetes.id"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))  # vacío = lo hizo un agente
    accion = db.Column(db.String(20), nullable=False)
    detalle = db.Column(db.String(300))
    fecha = db.Column(db.DateTime, default=ahora, nullable=False)

    paquete = db.relationship("Paquete", back_populates="historial")
    usuario = db.relationship("Usuario")

    def a_dict(self) -> dict:
        return {"accion": self.accion, "detalle": self.detalle, "fecha": _iso(self.fecha),
                "quien": self.usuario.nombre if self.usuario else "Agente"}


def _iso(fecha: datetime | None) -> str | None:
    """Fecha UTC en texto ISO con 'Z', para que el navegador la pase a su hora local."""
    return fecha.isoformat(timespec="seconds") + "Z" if fecha else None
