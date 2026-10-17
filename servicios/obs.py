"""Control de OBS Studio por su websocket (v5, viene incluido desde OBS 28).

La app abre OBS si no está abierto, le dice que grabe en la carpeta grabaciones/ y arranca o detiene
la grabación. La escena "Cristocéntricos" captura la pantalla completa (donde está StreamYard) y el
audio de la PC; se crea sola la primera vez. Configuración inicial: `flask --app app obs-configurar`.
"""
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

from flask import current_app

ESCENA = "Cristocéntricos"
EXE = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "obs-studio" / "bin" / "64bit" / "obs64.exe"
CONFIG_OBS = Path(os.environ.get("APPDATA", "")) / "obs-studio"


class ErrorObs(Exception):
    pass


def instalado() -> bool:
    return EXE.exists()


def _cliente():
    import obsws_python as obs
    password = current_app.config.get("OBS_PASSWORD") or ""
    if not password:
        raise ErrorObs("Falta configurar OBS: corre «flask --app app obs-configurar».")
    try:
        return obs.ReqClient(host="localhost", port=int(current_app.config.get("OBS_PUERTO", 4455)),
                             password=password, timeout=3)
    except Exception as e:  # noqa: BLE001 — ConnectionRefused, auth, timeout…
        raise ErrorObs("OBS no está abierto o no acepta la conexión.") from e


def abrir() -> None:
    """Abre OBS minimizado si no está corriendo (necesita su carpeta como directorio de trabajo)."""
    if not instalado():
        raise ErrorObs("OBS no está instalado en esta computadora.")
    salida = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True, text=True)
    if "obs64.exe" in salida.stdout:
        return
    subprocess.Popen([str(EXE), "--minimize-to-tray", "--disable-shutdown-check", "--disable-updater"],
                     cwd=str(EXE.parent), creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def _conectar(esperar: float = 0):
    """Cliente de OBS; si `esperar`, abre OBS y reintenta hasta ese número de segundos."""
    limite = time.monotonic() + esperar
    if esperar:
        abrir()
    while True:
        try:
            return _cliente()
        except ErrorObs:
            if time.monotonic() >= limite:
                raise
            time.sleep(2)


def _preparar(c) -> None:
    """Carpeta de grabación = grabaciones/ y escena con pantalla + audio (solo la primera vez)."""
    carpeta = Path(current_app.config["GRABACIONES_DIR"]).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)
    c.set_record_directory(str(carpeta))
    escenas = [e["sceneName"] for e in c.get_scene_list().scenes]
    if ESCENA not in escenas:
        c.create_scene(ESCENA)
        c.create_input(ESCENA, "Pantalla", "monitor_capture", {"monitor": 0, "capture_cursor": False}, True)
        c.create_input(ESCENA, "Audio de la PC", "wasapi_output_capture", {}, True)
    c.set_current_program_scene(ESCENA)


def estado() -> dict:
    if not instalado():
        return {"instalado": False, "conectado": False, "grabando": False}
    try:
        c = _cliente()
    except ErrorObs as e:
        return {"instalado": True, "conectado": False, "grabando": False, "mensaje": str(e)}
    r = c.get_record_status()
    return {"instalado": True, "conectado": True, "grabando": bool(r.output_active),
            "duracion": r.output_timecode if r.output_active else None}


def iniciar() -> dict:
    c = _conectar(esperar=25)
    if not c.get_record_status().output_active:
        _preparar(c)
        c.start_record()
    return estado()


def detener() -> dict:
    c = _conectar()
    if c.get_record_status().output_active:
        c.stop_record()
    return estado()


def configurar() -> str:
    """Activa el websocket de OBS con una contraseña nueva. Devuelve la contraseña (va al .env)."""
    password = secrets.token_urlsafe(18)
    archivo = CONFIG_OBS / "plugin_config" / "obs-websocket" / "config.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    datos = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    datos.update({"server_enabled": True, "server_port": 4455, "auth_required": True,
                  "server_password": password, "alerts_enabled": False, "first_load": False})
    archivo.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    return password
