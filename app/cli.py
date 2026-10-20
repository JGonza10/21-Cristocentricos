"""Comandos de consola: flask --app app crear-usuario / cambiar-password / paquete-demo."""
from datetime import date, timedelta
from pathlib import Path

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
            "carrusel", lunes, f"Invitación al evento del lunes {lunes.day}",
            "Te invitamos a rezar juntos en el evento en vivo este lunes a las 10:00 am "
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
        """Genera ya el carrusel de un evento. Ejemplo: flask --app app carrusel 2026-10-19"""
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

    @app.cli.command("repartir")
    def repartir():
        """Reparte ya los turnos vacíos de las próximas 2 semanas."""
        from agentes.fechas import hoy_cdmx, proximos_eventos
        from agentes.turnos import repartir as repartir_turnos
        nuevos = repartir_turnos(proximos_eventos(hoy_cdmx(), 14))
        click.echo(f"{len(nuevos)} turnos asignados.")

    @app.cli.command("obs-configurar")
    def obs_configurar():
        """Activa el control de OBS desde la app (websocket con contraseña nueva en el .env)."""
        from pathlib import Path

        from servicios import obs
        if not obs.instalado():
            raise click.ClickException("OBS no está instalado. Instálalo con: winget install OBSProject.OBSStudio")
        password = obs.configurar()
        env = Path(current_app.root_path).parent / ".env"
        lineas = [x for x in env.read_text(encoding="utf-8").splitlines() if not x.startswith("OBS_PASSWORD=")]
        lineas.append(f"OBS_PASSWORD={password}")
        env.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        click.echo("Listo: OBS acepta órdenes de la app. Cierra y vuelve a abrir OBS y reinicia iniciar.bat.")

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
