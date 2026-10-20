"""Worker de agentes: la segunda ventana de iniciar.bat.

    python -m agentes.worker

Horarios (hora CDMX):
  - cada minuto ........ latido (para que Inicio sepa que el worker está vivo)
  - cada 15 minutos ..... difusión de los eventos con tema (próximas 2 semanas)
  - cada 5 minutos ...... avisos del tema por correo
  - cada minuto ......... ideas por voz a texto · grabación automática con OBS (solo si OBS_AUTO=1)
  - cada 2 minutos ...... revisar grabaciones/ (además, watchdog avisa al instante)
  - cada 30 segundos .... recortes de reels pedidos desde la bandeja
  Solo con VERSION_CORTA=0 (proceso completo de la v1.0):
  - cada 3 minutos ...... publicar lo aprobado
  - domingo 6:00 pm ..... reparto de turnos de la semana · cada 10 min invitaciones de Calendar
  - lunes 8:00 am ....... reporte semanal de la semana anterior
"""
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app import create_app
from app.extensiones import db

from . import avisos, carrusel, grabacion, ideas, publicacion, reels, reporte, turnos
from .estado import latido
from .fechas import CDMX


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def crear_planificador(app) -> BlockingScheduler:
    sched = BlockingScheduler(timezone=CDMX, executors={"default": ThreadPoolExecutor(3)},
                              job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300})

    def trabajo(nombre: str, funcion, describir):
        def correr():
            with app.app_context():
                try:
                    resultado = funcion()
                    latido(nombre, describir(resultado), ok=True)
                except Exception:  # noqa: BLE001 — un agente que falla no tumba a los demás
                    app.logger.exception("Falló el agente %s", nombre)
                    db.session.rollback()   # si no, el latido de abajo también falla
                    latido(nombre, "Falló la última vez. Revisa datos/logs/app.log.", error=True)
        return correr

    ahora = datetime.now(CDMX)
    sched.add_job(trabajo("worker", lambda: None, lambda _: "Activo"), "interval", minutes=1,
                  id="latido", next_run_time=ahora)
    sched.add_job(trabajo("carrusel", carrusel.tarea,
                          lambda r: f"{_plural(len(r), 'pieza de difusión nueva', 'piezas de difusión nuevas')} en la bandeja"
                          if r else "Al día"),
                  "interval", minutes=15, id="carrusel", next_run_time=ahora + timedelta(seconds=5))
    sched.add_job(trabajo("avisos", avisos.tarea, lambda n: f"{_plural(n, 'aviso enviado', 'avisos enviados')}"),
                  "interval", minutes=5, id="avisos", next_run_time=ahora + timedelta(seconds=25))
    sched.add_job(trabajo("ideas", ideas.tarea, lambda n: f"{_plural(n, 'idea transcrita', 'ideas transcritas')}"),
                  "interval", minutes=1, id="ideas", next_run_time=ahora + timedelta(seconds=30))
    sched.add_job(trabajo("grabacion", grabacion.tarea, lambda m: m),
                  "interval", minutes=1, id="grabacion", next_run_time=ahora + timedelta(seconds=35))
    sched.add_job(trabajo("reels", reels.revisar_carpeta,
                          lambda r: f"{_plural(len(r), 'reel nuevo', 'reels nuevos')} en la bandeja"
                          if r else "Esperando grabaciones"),
                  "interval", minutes=2, id="reels", next_run_time=ahora + timedelta(seconds=10))
    sched.add_job(trabajo("recortes", reels.aplicar_recortes, lambda n: f"{n} recortes aplicados"),
                  "interval", seconds=30, id="recortes")
    if app.config.get("VERSION_CORTA", True):
        # Versión corta: sin turnos, invitaciones, publicación ni reporte semanal (ocultos, no borrados).
        sched.add_job(trabajo("bitacora", _archivar, lambda n: f"{_plural(n, 'evento archivado', 'eventos archivados')}"),
                      "cron", hour="*", minute=7, id="bitacora", next_run_time=ahora + timedelta(seconds=40))
        return sched
    sched.add_job(trabajo("publicacion", publicacion.tarea,
                          lambda n: f"{_plural(n, 'paquete aprobado', 'paquetes aprobados')} revisados"),
                  "interval", minutes=3, id="publicacion", next_run_time=ahora + timedelta(seconds=15))
    sched.add_job(trabajo("turnos", turnos.tarea_reparto,
                          lambda r: f"Reparto del domingo: {_plural(len(r), 'turno asignado', 'turnos asignados')}"),
                  "cron", day_of_week="sun", hour=18, minute=0, id="reparto")
    sched.add_job(trabajo("invitaciones", turnos.sincronizar_invitaciones,
                          lambda n: f"{_plural(n, 'invitación actualizada', 'invitaciones actualizadas')}"),
                  "interval", minutes=10, id="invitaciones", next_run_time=ahora + timedelta(seconds=20))
    sched.add_job(trabajo("bitacora", _archivar, lambda n: f"{_plural(n, 'evento archivado', 'eventos archivados')}"),
                  "cron", hour="*", minute=7, id="bitacora", next_run_time=ahora + timedelta(seconds=40))
    sched.add_job(trabajo("reporte", reporte.tarea_semanal, lambda s: f"Reporte de la semana del {s.day}/{s.month} listo"),
                  "cron", day_of_week="mon", hour=8, minute=0, id="reporte")
    return sched


def _archivar() -> int:
    from app.avance import archivar_pasados
    return archivar_pasados()


class AvisoGrabaciones(FileSystemEventHandler):
    """Cuando aparece o cambia un video en grabaciones/, adelanta la revisión de reels."""

    def __init__(self, sched: BlockingScheduler):
        self.sched = sched

    def on_any_event(self, evento):
        if evento.is_directory or Path(evento.src_path).suffix.lower() not in reels.EXTENSIONES:
            return
        # Se espera a que el archivo deje de cambiar (OBS puede seguir escribiendo).
        cuando = datetime.now(CDMX) + timedelta(seconds=reels.SEGUNDOS_ESTABLE + 5)
        self.sched.modify_job("reels", next_run_time=cuando)


def main() -> None:
    app = create_app()
    manejador = RotatingFileHandler(Path(app.config["LOG_DIR"]) / "worker.log", maxBytes=1_000_000,
                                    backupCount=5, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(manejador)
    logging.getLogger("apscheduler").addHandler(manejador)

    carpeta = Path(app.config["GRABACIONES_DIR"])
    carpeta.mkdir(parents=True, exist_ok=True)
    from servicios.estilo import preparar_carpeta
    preparar_carpeta(Path(app.config["ESTILO_DIR"]))
    sched = crear_planificador(app)
    vigilante = Observer()
    vigilante.schedule(AvisoGrabaciones(sched), str(carpeta), recursive=False)
    vigilante.start()
    print(f"Agentes de {app.config['CANAL_NOMBRE']} trabajando (no cierres esta ventana).")
    print(f"Vigilando: {carpeta}  (pon aquí el video limpio del celular)")
    print(f"Estilo del cliente: {app.config['ESTILO_DIR']}")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        vigilante.stop()
        vigilante.join()


if __name__ == "__main__":
    main()
