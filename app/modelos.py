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


evento_integrantes = db.Table(
    "evento_integrantes",
    db.Column("evento_id", db.Integer, db.ForeignKey("eventos.id", ondelete="CASCADE"), primary_key=True),
    db.Column("integrante_id", db.Integer, db.ForeignKey("integrantes.id", ondelete="CASCADE"), primary_key=True),
)

# Lista de la revisión técnica del día (paso 3). El orden es el que se ve en pantalla.
REVISION = {
    "audio": "Audio y micrófono probados",
    "streamyard": "StreamYard abierto con las redes conectadas",
    "grabacion": "Grabación guardándose en la carpeta grabaciones",
    "reloj": "Reloj en vivo listo",
    "prompter": "Prompter abierto en la tableta y siguiendo la voz",
}


class Integrante(db.Model):
    """Nombre de una persona del equipo (sin cuenta en la app)."""
    __tablename__ = "integrantes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), unique=True, nullable=False)
    creado = db.Column(db.DateTime, default=ahora, nullable=False)

    def a_dict(self) -> dict:
        return {"id": self.id, "nombre": self.nombre}


class Evento(db.Model):
    """Un programa en vivo: fecha, tema y guion, y el avance de sus pasos."""
    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, unique=True, nullable=False, index=True)
    hora = db.Column(db.String(5), default="10:00", nullable=False)
    tema = db.Column(db.String(120), default="", nullable=False)
    guion_md = db.Column(db.Text, default="", nullable=False)
    frases = db.Column(db.JSON, default=list, nullable=False)
    revision = db.Column(db.JSON, default=dict, nullable=False)
    # Con qué datos se hicieron las imágenes; si cambian el tema o la fecha, hay que regenerarlas.
    imagenes_firma = db.Column(db.String(200))
    actualizado = db.Column(db.DateTime, default=ahora, onupdate=ahora, nullable=False)
    integrantes = db.relationship(Integrante, secondary=evento_integrantes, order_by=Integrante.nombre,
                                  backref="eventos")

    def firma(self) -> str:
        return f"{self.fecha.isoformat()}|{self.hora}|{self.tema}|{'|'.join(self.frases[:2])}"

    def pasos(self) -> dict:
        p1 = bool(self.tema.strip() and self.guion_md.strip())
        p2 = p1 and self.imagenes_firma == self.firma()
        p3 = p2 and all(self.revision.get(k) for k in REVISION)
        return {"datos": p1, "imagenes": p2, "revision": p3}

    def a_dict(self, completo: bool = True) -> dict:
        d = {"fecha": self.fecha.isoformat(), "hora": self.hora, "tema": self.tema, "pasos": self.pasos(),
             "integrantes": [i.a_dict() for i in self.integrantes]}
        if completo:
            d.update(guion_md=self.guion_md, frases=self.frases, revision=self.revision,
                     revision_items=[{"id": k, "texto": v} for k, v in REVISION.items()],
                     imagenes=[f"/api/eventos/{d['fecha']}/imagenes/{i}.png" for i in range(1, 6)]
                     if self.imagenes_firma else [])
        return d
