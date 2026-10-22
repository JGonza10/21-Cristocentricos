"""Comandos de consola: flask --app app crear-usuario / cambiar-password / material-vaciar / estilo-...."""
from datetime import date
from pathlib import Path

import click
from flask import current_app

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

    @app.cli.command("carrusel")
    @click.argument("fecha")
    @click.option("--forzar", is_flag=True, help="Genera otras aunque ya existan para esa fecha.")
    def carrusel(fecha, forzar):
        """Genera ya las 5 imágenes de difusión de un evento. Ejemplo: flask --app app carrusel 2026-10-23"""
        from agentes.carrusel import preparar_carrusel
        try:
            f = date.fromisoformat(fecha)
            p = preparar_carrusel(f, forzar=forzar)
        except ValueError as e:
            raise click.ClickException(f"Fecha no válida (usa AAAA-MM-DD; lunes, viernes o un día con tema): {e}") from None
        click.echo("Las 5 imágenes de difusión ya están en Material." if p
                   else "Ya existen imágenes para esa fecha. Usa --forzar para hacer otras.")

    @app.cli.command("copiar-base")
    @click.option("--destino", envvar="DESTINO_URL", prompt="URL de la base destino (no se muestra)", hide_input=True,
                  help="URL de PostgreSQL (en Railway: DATABASE_PUBLIC_URL). También se lee de DESTINO_URL.")
    def copiar_base(destino):
        """Copia los datos de esta base (la SQLite de la laptop) a otra vacía (la PostgreSQL de Railway).

        Se copia todo menos los intentos de login y los latidos de los agentes. Si la base destino
        ya tiene cuentas o temas, no se toca nada.
        """
        from sqlalchemy import create_engine, func, inspect, select, text

        from . import url_base_de_datos
        omitir = {"intentos_login", "estado_agentes"}
        motor = create_engine(url_base_de_datos(destino.strip()))
        db.metadata.create_all(motor)
        with motor.connect() as con:
            for tabla in ("usuarios", "temas"):
                if con.execute(select(func.count()).select_from(db.metadata.tables[tabla])).scalar():
                    raise click.ClickException(f"La base destino ya tiene datos en «{tabla}»: no se copió nada.")
        copiadas = {}
        with db.engine.connect() as origen, motor.begin() as con:
            for tabla in db.metadata.sorted_tables:          # en orden: primero las que otras referencian
                if tabla.name in omitir or not inspect(db.engine).has_table(tabla.name):
                    continue
                filas = [dict(f) for f in origen.execute(select(tabla)).mappings()]
                if filas:
                    con.execute(tabla.insert(), filas)
                copiadas[tabla.name] = len(filas)
            if motor.dialect.name == "postgresql":           # que los id nuevos sigan después de los copiados
                for tabla in db.metadata.sorted_tables:
                    if "id" in tabla.c and tabla.c.id.autoincrement in (True, "auto") and tabla.name not in omitir:
                        siguiente = (con.execute(select(func.max(tabla.c.id))).scalar() or 0) + 1
                        con.execute(text("SELECT setval(pg_get_serial_sequence(:tabla, 'id'), :valor, false)"),
                                    {"tabla": tabla.name, "valor": siguiente})
        for nombre, n in copiadas.items():
            click.echo(f"  {nombre}: {n}")
        click.echo("Listo: datos copiados.")

    @app.cli.command("material-vaciar")
    @click.option("--si", is_flag=True, help="No preguntar.")
    def material_vaciar(si):
        """Borra todo lo de la pestaña Material (imágenes, reels y sus archivos) para empezar de cero."""
        from .bandeja import vaciar_material
        if not si:
            click.confirm("Se borrarán todas las imágenes y reels de Material. ¿Continuar?", abort=True)
        r = vaciar_material()
        click.echo(f"Listo: {r['paquetes']} piezas y {r['grabaciones']} grabaciones sin video borradas.")

    @app.cli.command("reels-reintentar")
    @click.argument("archivo")
    def reels_reintentar(archivo):
        """Vuelve a procesar una grabación que falló. Ejemplo: flask --app app reels-reintentar evento.mkv"""
        from .modelos import Grabacion
        g = Grabacion.query.filter_by(nombre=archivo).first()
        if g is None:
            raise click.ClickException("No hay ninguna grabación registrada con ese nombre.")
        g.estado, g.error = "nueva", None
        db.session.commit()
        click.echo("Listo: el worker la procesará en los próximos minutos.")

    @app.cli.command("estilo-analizar")
    def estilo_analizar():
        """Mide el video de referencia del cliente y saca cuadros para armar estilo.json.

        Toma cada video de estilo_cliente/referencia/ y deja estilo_cliente/analisis/<nombre>/
        con hoja.jpg (todos los cuadros juntos), cuadros/ y datos.json.
        """
        from servicios import estilo
        raiz = estilo.preparar_carpeta(Path(app.config["ESTILO_DIR"]))
        videos = [v for v in sorted((raiz / "referencia").iterdir())
                  if v.is_file() and v.suffix.lower() in estilo.VIDEO]
        if not videos:
            raise click.ClickException(f"Pon el video del cliente en {raiz / 'referencia'} y vuelve a correrlo.")
        for v in videos:
            click.echo(f"Analizando {v.name}…")
            d = estilo.analizar(v, raiz / "analisis" / v.stem)
            click.echo(f"  {d['ancho']}×{d['alto']} · {d['duracion']} s · {len(d['cortes_de_escena'])} cortes · "
                       f"brillo {d['brillo_promedio']} · volumen {d['volumen_lufs']} LUFS")
        herramientas = [h.name for h in sorted((raiz / "herramientas").iterdir()) if h.is_file()]
        click.echo(f"Herramientas encontradas ({len(herramientas)}): {', '.join(herramientas) or 'ninguna'}")
        click.echo(f"Listo. Revisa {raiz / 'analisis'} y ajusta {raiz / 'estilo.json'}.")

    @app.cli.command("estilo-probar")
    @click.argument("video")
    @click.option("--inicio", type=float, default=0.0, help="Segundo donde empieza el reel de prueba.")
    @click.option("--fin", type=float, default=30.0, help="Segundo donde termina.")
    @click.option("--tema", default="Tema de prueba", help="Texto para {tema}.")
    @click.option("--fecha", default="", help="Fecha del evento AAAA-MM-DD (para la imagen del tema).")
    def estilo_probar(video, inicio, fin, tema, fecha):
        """Hace un reel de prueba con estilo.json, sin tocar la base de datos.

        Ejemplo: flask --app app estilo-probar grabaciones/celular.mp4 --inicio 120 --fin 160
        El resultado queda en estilo_cliente/pruebas/.
        """
        from datetime import datetime
        from servicios import estilo
        raiz = estilo.preparar_carpeta(Path(app.config["ESTILO_DIR"]))
        ruta = Path(video)
        if not ruta.is_file():
            raise click.ClickException(f"No encontré el video {ruta}.")
        salida = raiz / "pruebas" / f"prueba_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        try:
            r = estilo.editar_reel(str(ruta), inicio, fin, salida, raiz, Path(app.config["FUENTES_DIR"]),
                                   [], {"tema": tema, "fecha": fecha, "fecha_iso": fecha,
                                        "canal": app.config["CANAL_NOMBRE"], "frase": ""})
        except estilo.ErrorEstilo as e:
            raise click.ClickException(str(e)) from None
        click.echo(f"Listo: {salida} ({r['duracion']} s, {r['capas']} capas).")

    @app.cli.command("google-autorizar")
    def google_autorizar():
        """Abre el navegador para autorizar Gmail (avisos del tema al equipo), una sola vez."""
        from servicios.google import autorizar
        try:
            token = autorizar()
        except FileNotFoundError as e:
            raise click.ClickException(
                f"Falta {e}. Descárgalo de Google Cloud Console (ver README, sección Google).") from None
        click.echo(f"Autorizado. Token guardado en {token} (no lo compartas ni lo subas a git).")
