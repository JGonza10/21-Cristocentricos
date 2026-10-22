"""Worker de agentes: la segunda ventana de iniciar.bat.

    python -m agentes.worker

Horarios (hora CDMX):
  - cada minuto ........ latido (para que Inicio sepa que el worker está vivo)
  - cada 2 minutos ...... difusión de los eventos con tema (próximas 2 semanas; el tema puede
                          guardarse desde la nube, que no arma imágenes)
  - cada 5 minutos ...... estado de la laptop (estilo del cliente, Gmail) para la nube
  - cada 5 minutos ...... avisos del tema por correo
  - cada minuto ......... ideas por voz a texto
  - cada 2 minutos ...... revisar grabaciones/ (además, watchdog avisa al instante)
  - cada 30 segundos .... recortes de reels pedidos desde Material
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

from . import avisos, carrusel, ideas, reels
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
                          lambda r: f"{_plural(len(r), 'pieza de difusión nueva', 'piezas de difusión nuevas')} en Material"
                          if r else "Al día"),
                  "interval", minutes=2, id="carrusel", next_run_time=ahora + timedelta(seconds=5))
    sched.add_job(trabajo("laptop", reportar_laptop, lambda r: r), "interval", minutes=5, id="laptop",
                  next_run_time=ahora + timedelta(seconds=15))
    sched.add_job(trabajo("avisos", avisos.tarea, lambda n: f"{_plural(n, 'aviso enviado', 'avisos enviados')}"),
                  "interval", minutes=5, id="avisos", next_run_time=ahora + timedelta(seconds=25))
    sched.add_job(trabajo("ideas", ideas.tarea, lambda n: f"{_plural(n, 'idea transcrita', 'ideas transcritas')}"),
                  "interval", minutes=1, id="ideas", next_run_time=ahora + timedelta(seconds=30))
    sched.add_job(trabajo("reels", reels.revisar_carpeta,
                          lambda r: f"{_plural(len(r), 'reel nuevo', 'reels nuevos')} en Material"
                          if r else "Esperando grabaciones"),
                  "interval", minutes=2, id="reels", next_run_time=ahora + timedelta(seconds=10))
    sched.add_job(trabajo("recortes", reels.aplicar_recortes, lambda n: f"{n} recortes aplicados"),
                  "interval", seconds=30, id="recortes")
    return sched


def reportar_laptop() -> str:
    """Guarda en la base lo que solo sabe la laptop, para que la nube lo muestre en Inicio."""
    import json

    from app.panel import estado_laptop
    return json.dumps(estado_laptop(), ensure_ascii=False)


class AvisoGrabaciones(FileSystemEventHandler):
    """Cuando aparece o cambia un video en grabaciones/, adelanta la revisión de reels."""

    def __init__(self, sched: BlockingScheduler):
        self.sched = sched

    def on_any_event(self, evento):
        if evento.is_directory or Path(evento.src_path).suffix.lower() not in reels.EXTENSIONES:
            return
        # Se espera a que el archivo deje de cambiar (puede seguir copiándose).
        cuando = datetime.now(CDMX) + timedelta(seconds=reels.SEGUNDOS_ESTABLE + 5)
        self.sched.modify_job("reels", next_run_time=cuando)


def main() -> None:
    app = create_app()
    if app.config["EN_NUBE"]:
        raise SystemExit("El worker corre en la laptop (MODO=local), no en la nube: ahí están los videos.")
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
