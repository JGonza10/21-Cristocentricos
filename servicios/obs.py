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
# Método 2 = Windows Graphics Capture: el de siempre (DXGI) sale negro en laptops con dos tarjetas de video.
CAPTURA = {"method": 2, "capture_cursor": False}
EXE = Path(os.path.expandvars(r"%ProgramFiles%")) / "obs-studio" / "bin" / "64bit" / "obs64.exe"
CONFIG_OBS = Path(os.path.expandvars(r"%APPDATA%\obs-studio"))


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
    salida = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True)
    if b"obs64.exe" in salida.stdout:   # en bytes: tasklist responde en la página de códigos de la consola
        return
    # Si OBS se cerró mal (apagón, se cerró a la fuerza) deja estas marcas y al abrir pregunta si quiere el
    # «modo seguro», esperando un clic. Con OBS cerrado son marcas viejas: se quitan para que abra solo.
    for marca in (CONFIG_OBS / ".sentinel").glob("run_*"):
        marca.unlink(missing_ok=True)
    subprocess.Popen([str(EXE), "--minimize-to-tray", "--disable-shutdown-check", "--disable-updater"],
                     cwd=str(EXE.parent), creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def _conectar(esperar: float = 0):
    """Cliente de OBS; si `esperar`, abre OBS y reintenta hasta ese número de segundos."""
    limite = time.monotonic() + esperar
    if esperar:
        abrir()
    while True:
        try:
            c = _cliente()
            c.get_record_status()          # recién abierto, OBS contesta 207 («no está listo») unos segundos
            return c
        except ErrorObs:
            if time.monotonic() >= limite:
                raise
        except Exception as e:  # noqa: BLE001 — OBSSDKRequestError mientras carga
            if time.monotonic() >= limite:
                raise ErrorObs("OBS se abrió pero todavía no está listo. Intenta en unos segundos.") from e
        time.sleep(2)


def _preparar(c) -> None:
    """Carpeta de grabación = grabaciones/ y escena con pantalla + audio (solo la primera vez)."""
    carpeta = Path(current_app.config["GRABACIONES_DIR"]).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)
    c.set_record_directory(str(carpeta))
    escenas = [e["sceneName"] for e in c.get_scene_list().scenes]
    if ESCENA not in escenas:
        # El audio del escritorio y el micrófono ya vienen como audio global de OBS: solo falta la pantalla.
        c.create_scene(ESCENA)
        c.create_input(ESCENA, "Pantalla", "monitor_capture", CAPTURA, True)
    # Sin pantalla elegida OBS graba negro: se elige el monitor principal (su id cambia en cada PC).
    monitores = [m for m in c.get_input_properties_list_property_items("Pantalla", "monitor_id").property_items
                 if m["itemEnabled"]]
    if monitores:
        principal = next((m for m in monitores if "principal" in m["itemName"].lower()
                          or "primary" in m["itemName"].lower()), monitores[0])
        c.set_input_settings("Pantalla", {**CAPTURA, "monitor_id": principal["itemValue"]}, True)
    c.set_current_program_scene(ESCENA)


def estado() -> dict:
    if not instalado():
        return {"instalado": False, "conectado": False, "grabando": False}
    try:
        c = _cliente()
    except ErrorObs as e:
        return {"instalado": True, "conectado": False, "grabando": False, "mensaje": str(e)}
    try:
        r = c.get_record_status()
    except Exception:  # noqa: BLE001 — recién abierto todavía no contesta
        return {"instalado": True, "conectado": True, "grabando": False, "mensaje": "OBS está cargando."}
    return {"instalado": True, "conectado": True, "grabando": bool(r.output_active),
            "duracion": r.output_timecode if r.output_active else None}


def iniciar() -> dict:
    c = _conectar(esperar=25)
    if not c.get_record_status().output_active:
        _preparar(c)
        c.start_record()
        time.sleep(1.5)                    # la grabación arranca un instante después de pedirla
    return estado()


def detener() -> dict:
    c = _conectar()
    if c.get_record_status().output_active:
        c.stop_record()
        time.sleep(1.5)
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
    _sin_asistente()
    return password


def _sin_asistente() -> None:
    """Marca OBS como ya usado: si no, al abrirlo la primera vez muestra el asistente de configuración,
    que deja a OBS esperando un clic y sin contestar las órdenes de la app."""
    import configparser
    ini = CONFIG_OBS / "user.ini"
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str                      # OBS distingue mayúsculas en las claves
    if ini.exists():
        cfg.read(ini, encoding="utf-8-sig")
    if not cfg.has_section("General"):
        cfg.add_section("General")
    cfg.set("General", "FirstRun", "true")
    ini.parent.mkdir(parents=True, exist_ok=True)
    with ini.open("w", encoding="utf-8-sig") as f:
        cfg.write(f, space_around_delimiters=False)
