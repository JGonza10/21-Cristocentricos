"""Comandos de consola: flask --app app crear-usuario / cambiar-password / paquete-demo."""
from datetime import date, timedelta

import click
from flask import current_app

from .bandeja import crear_paquete
from .extensiones import db
from .modelos import Usuario
from .seguridad import hashear, normalizar_usuario, problema_password


def _pedir_password() -> str:
    while True:
        p = click.prompt("Contraseña", hide_input=True, confirmation_prompt="Repite la contraseña")
        problema = problema_password(p)
        if problema is None:
            return p
        click.echo(problema)


def registrar(app):
    @app.cli.command("crear-usuario")
    def crear_usuario():
        """Crea una cuenta (máximo MAX_USUARIOS)."""
        maximo = current_app.config["MAX_USUARIOS"]
        if Usuario.query.count() >= maximo:
            raise click.ClickException(f"Ya existen {maximo} usuarios, que es el máximo permitido.")
        usuario = normalizar_usuario(click.prompt("Usuario o correo (minúsculas, sin espacios)"))
        if not usuario:
            raise click.ClickException("Usuario no válido: 3 a 40 caracteres, solo a-z, 0-9, punto, guion.")
        if Usuario.query.filter_by(usuario=usuario).first():
            raise click.ClickException("Ese usuario ya existe.")
        nombre = click.prompt("Nombre para mostrar").strip()[:80]
        if not nombre:
            raise click.ClickException("El nombre no puede ir vacío.")
        db.session.add(Usuario(usuario=usuario, nombre=nombre, hash_password=hashear(_pedir_password())))
        db.session.commit()
        click.echo(f"Usuario '{usuario}' creado.")

    @app.cli.command("cambiar-password")
    @click.argument("usuario")
    def cambiar_password(usuario):
        """Cambia la contraseña de un usuario existente."""
        u = Usuario.query.filter_by(usuario=normalizar_usuario(usuario)).first()
        if not u:
            raise click.ClickException("No existe ese usuario.")
        u.hash_password = hashear(_pedir_password())
        db.session.commit()
        click.echo("Contraseña actualizada.")

    @app.cli.command("paquete-demo")
    def paquete_demo():
        """Mete un carrusel y un reel de ejemplo a la bandeja (para probarla sin agentes)."""
        hoy = date.today()
        lunes = hoy + timedelta(days=(0 - hoy.weekday()) % 7 or 7)
        crear_paquete(
            "carrusel", lunes, f"Invitación al rosario del lunes {lunes.day}",
            "Te invitamos a rezar juntos el Santo Rosario en vivo este lunes a las 10:00 am "
            "(hora CDMX). Meditaremos los misterios gozosos.\n\n"
            "Deja tus intenciones en los comentarios.\n\n#SantoRosario #Cristocéntricos #MisteriosGozosos")
        crear_paquete(
            "reel", hoy, "Reel 1 · Anuncio del primer misterio",
            "Primer misterio gozoso: la Anunciación del ángel a María.\n\n#SantoRosario #Cristocéntricos")
        click.echo("Listo: 2 paquetes de ejemplo en la bandeja (pestaña Contenido).")

    @app.cli.command("carrusel")
    @click.argument("fecha")
    @click.option("--forzar", is_flag=True, help="Genera otro aunque ya exista uno para esa fecha.")
    def carrusel(fecha, forzar):
        """Genera ya el carrusel de un rosario. Ejemplo: flask --app app carrusel 2026-10-19"""
        from agentes.carrusel import preparar_carrusel
        try:
            f = date.fromisoformat(fecha)
            p = preparar_carrusel(f, forzar=forzar)
        except ValueError as e:
            raise click.ClickException(f"Fecha no válida (usa AAAA-MM-DD, lunes o viernes): {e}") from None
        click.echo(f"Carrusel listo en la bandeja (paquete {p.id})." if p
                   else "Ya existe un carrusel para esa fecha. Usa --forzar para hacer otro.")

    @app.cli.command("reels-reintentar")
    @click.argument("archivo")
    def reels_reintentar(archivo):
        """Vuelve a procesar una grabación que falló. Ejemplo: flask --app app reels-reintentar rosario.mkv"""
        from .modelos import Grabacion
        g = Grabacion.query.filter_by(nombre=archivo).first()
        if g is None:
            raise click.ClickException("No hay ninguna grabación registrada con ese nombre.")
        g.estado, g.error = "nueva", None
        db.session.commit()
        click.echo("Listo: el worker la procesará en los próximos minutos.")

    @app.cli.command("repartir")
    def repartir():
        """Reparte ya los turnos vacíos de las próximas 2 semanas."""
        from agentes.fechas import hoy_cdmx, proximos_rosarios
        from agentes.turnos import repartir as repartir_turnos
        nuevos = repartir_turnos(proximos_rosarios(hoy_cdmx(), 14))
        click.echo(f"{len(nuevos)} turnos asignados.")

    @app.cli.command("google-autorizar")
    def google_autorizar():
        """Abre el navegador para autorizar YouTube y Google Calendar (una sola vez)."""
        from servicios.google import autorizar
        try:
            token = autorizar()
        except FileNotFoundError as e:
            raise click.ClickException(
                f"Falta {e}. Descárgalo de Google Cloud Console (ver README, sección Google).") from None
        click.echo(f"Autorizado. Token guardado en {token} (no lo compartas ni lo subas a git).")
