"""Comandos de consola: flask --app app crear-usuario / cambiar-password / limpiar-datos."""
import shutil
from pathlib import Path

import click
from flask import current_app

from .extensiones import db
from .modelos import Evento, Integrante, IntentoLogin, Usuario, evento_integrantes
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

    @app.cli.command("limpiar-datos")
    @click.option("--con-usuarios", is_flag=True, help="También borra las cuentas (luego hay que crearlas otra vez).")
    @click.confirmation_option(prompt="Se borrarán eventos, equipo e imágenes. ¿Continuar?")
    def limpiar_datos(con_usuarios):
        """Deja la base de datos en blanco para empezar de cero."""
        db.session.execute(evento_integrantes.delete())
        Evento.query.delete()
        Integrante.query.delete()
        IntentoLogin.query.delete()
        if con_usuarios:
            Usuario.query.delete()
        db.session.commit()
        paquetes = Path(current_app.config["PAQUETES_DIR"])
        if paquetes.exists():
            shutil.rmtree(paquetes)
        cuentas = "y cuentas " if con_usuarios else ""
        click.echo(f"Listo: eventos, equipo, imágenes {cuentas}borrados.")
