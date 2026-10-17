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
    # Datos extra del agente. Reels: {"grabacion_id", "inicio", "fin", "duracion_fuente", "recortar"}
    datos = db.Column(db.JSON)

    revisado_por = db.relationship("Usuario")
    publicaciones = db.relationship("Publicacion", order_by="Publicacion.id",
                                    cascade="all, delete-orphan", back_populates="paquete")
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
            "datos": dict(self.datos or {}),
            "publicaciones": [x.a_dict() for x in self.publicaciones],
        }

    @property
    def ya_publicado(self) -> bool:
        return any(x.estado == "publicado" for x in self.publicaciones)


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


# --- Publicación (fases 5 y 8) ------------------------------------------------------

REDES = ("instagram", "facebook", "tiktok", "youtube")
# listo_manual = la carpeta subir_manual/<red>/ está lista; falta que alguien la suba.
ESTADOS_PUBLICACION = ("listo_manual", "subiendo", "publicado", "error", "sin_configurar")


class Publicacion(db.Model):
    """Cómo va un paquete aprobado en cada red social."""
    __tablename__ = "publicaciones"
    __table_args__ = (db.UniqueConstraint("paquete_id", "red"),)

    id = db.Column(db.Integer, primary_key=True)
    paquete_id = db.Column(db.Integer, db.ForeignKey("paquetes.id"), nullable=False, index=True)
    red = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    ruta = db.Column(db.String(300))     # carpeta de subir_manual (relativa a paquetes/)
    url = db.Column(db.String(300))      # enlace cuando se publicó automáticamente
    intentos = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.String(300))    # mensaje amable; el detalle va al log
    actualizado = db.Column(db.DateTime, default=ahora, nullable=False)

    paquete = db.relationship("Paquete", back_populates="publicaciones")

    def a_dict(self) -> dict:
        return {"red": self.red, "estado": self.estado, "ruta": self.ruta, "url": self.url,
                "error": self.error, "actualizado": _iso(self.actualizado)}


# --- Grabaciones (fase 4) -----------------------------------------------------------

class Grabacion(db.Model):
    """Cada video que llega a grabaciones/. Evita procesar dos veces el mismo archivo."""
    __tablename__ = "grabaciones"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), unique=True, nullable=False)
    tamano = db.Column(db.BigInteger, nullable=False, default=0)
    fecha_evento = db.Column(db.Date)
    estado = db.Column(db.String(20), nullable=False, default="nueva")  # nueva/procesando/lista/error
    duracion = db.Column(db.Float)
    segmentos = db.Column(db.JSON)       # transcripción: [[inicio, fin, texto], ...]
    error = db.Column(db.String(300))
    creado = db.Column(db.DateTime, default=ahora, nullable=False)
    actualizado = db.Column(db.DateTime, default=ahora, nullable=False)

    def a_dict(self) -> dict:
        return {"id": self.id, "nombre": self.nombre, "estado": self.estado, "error": self.error,
                "fecha_evento": self.fecha_evento.isoformat() if self.fecha_evento else None,
                "duracion": self.duracion, "actualizado": _iso(self.actualizado)}


# --- Equipo y turnos (fase 6) -------------------------------------------------------

ROLES_TURNO = ("dirige", "apoya")


class Integrante(db.Model):
    """Persona del equipo. No tiene cuenta: solo nombre y correo para las invitaciones."""
    __tablename__ = "integrantes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    correo = db.Column(db.String(120))   # vacío si se dio de baja (derecho de cancelación)
    puede_dirigir = db.Column(db.Boolean, nullable=False, default=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    aviso_privacidad = db.Column(db.DateTime)  # cuándo se le informó el aviso
    creado = db.Column(db.DateTime, default=ahora, nullable=False)

    def a_dict(self) -> dict:
        return {"id": self.id, "nombre": self.nombre, "correo": self.correo,
                "puede_dirigir": self.puede_dirigir, "activo": self.activo,
                "aviso_privacidad": _iso(self.aviso_privacidad)}


class Turno(db.Model):
    """Quién dirige y quién apoya en un evento."""
    __tablename__ = "turnos"
    __table_args__ = (db.UniqueConstraint("fecha", "integrante_id"),)

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    rol = db.Column(db.String(10), nullable=False)
    integrante_id = db.Column(db.Integer, db.ForeignKey("integrantes.id"), nullable=False)
    automatico = db.Column(db.Boolean, nullable=False, default=False)
    creado = db.Column(db.DateTime, default=ahora, nullable=False)

    integrante = db.relationship("Integrante")

    def a_dict(self) -> dict:
        return {"rol": self.rol, "automatico": self.automatico, "integrante": self.integrante.a_dict()}


class EventoCalendario(db.Model):
    """La cita de Google Calendar de cada evento (para actualizarlo si cambian los turnos)."""
    __tablename__ = "eventos_calendario"

    fecha = db.Column(db.Date, primary_key=True)
    google_id = db.Column(db.String(200))
    invitados = db.Column(db.JSON)       # correos a los que ya se invitó
    estado = db.Column(db.String(20), nullable=False, default="pendiente")  # pendiente/enviada/error
    error = db.Column(db.String(300))
    actualizado = db.Column(db.DateTime, default=ahora, nullable=False)


# --- Estado de los agentes ----------------------------------------------------------

class EstadoAgente(db.Model):
    """Último latido y último resultado de cada agente (para la pantalla de Inicio)."""
    __tablename__ = "estado_agentes"

    nombre = db.Column(db.String(30), primary_key=True)
    latido = db.Column(db.DateTime)
    ultimo_ok = db.Column(db.DateTime)
    mensaje = db.Column(db.String(300))
    error = db.Column(db.Boolean, nullable=False, default=False)

    def a_dict(self) -> dict:
        return {"nombre": self.nombre, "latido": _iso(self.latido), "ultimo_ok": _iso(self.ultimo_ok),
                "mensaje": self.mensaje, "error": self.error}


# --- Avance guiado por evento, reporte semanal y seguidores ------------------------

PASOS_EVENTO = ("turnos", "prepara", "vivo", "grabacion", "reels", "carrusel",
                "bandeja", "publicacion", "redes", "registro", "mides")


class AvancePaso(db.Model):
    """Lo que alguien marcó a mano en un paso del evento: hecho u omitido (no era necesario).

    Los pasos que el sistema puede comprobar solo (turno asignado, grabación, reels…) no
    necesitan fila: se calculan en app/avance.py. Una fila aquí siempre gana sobre lo automático.
    """
    __tablename__ = "avance_pasos"

    fecha = db.Column(db.Date, primary_key=True)
    paso = db.Column(db.String(20), primary_key=True)
    estado = db.Column(db.String(10), nullable=False)    # hecho / omitido
    nota = db.Column(db.String(200))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    creado = db.Column(db.DateTime, default=ahora, nullable=False)

    usuario = db.relationship("Usuario")


class Reporte(db.Model):
    """Reporte semanal que arma solo el agente de reportes (lunes 8 am) con los datos del sistema."""
    __tablename__ = "reportes"

    semana = db.Column(db.Date, primary_key=True)       # lunes de la semana reportada
    datos = db.Column(db.JSON, nullable=False)
    creado = db.Column(db.DateTime, default=ahora, nullable=False)


class Seguidores(db.Model):
    """Seguidores por red capturados a mano (las redes no los dan sin cuentas conectadas)."""
    __tablename__ = "seguidores"
    __table_args__ = (db.UniqueConstraint("fecha", "red"),)

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    red = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
