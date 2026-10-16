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
        usuario = normalizar_usuario(click.prompt("Usuario (minúsculas, sin espacios)"))
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
