"""Copia de ejemplo de la app para revisar el proceso completo con datos inventados.

Usa su propia base (datos/ejemplo.db) y el puerto 5022; no toca los datos reales ni corre los
agentes. Entras con tu mismo usuario y contraseña (se copian de la base real).

    python ejemplo.py              arranca (siembra el ejemplo si la base no existe)
    python ejemplo.py --reiniciar  borra el ejemplo y lo vuelve a sembrar antes de arrancar
"""
import os
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BASE = RAIZ / "datos" / "ejemplo.db"
BASE_REAL = RAIZ / "datos" / "cristocentricos.db"
PUERTO = 5022

os.environ["DATABASE_URL"] = f"sqlite:///{BASE.as_posix()}"
os.environ["EJEMPLO"] = "1"


def _copiar_usuarios(db, Usuario):
    """Trae las cuentas de la base real (solo usuario, nombre y hash) para entrar igual."""
    if not BASE_REAL.exists():
        return
    con = sqlite3.connect(f"file:{BASE_REAL.as_posix()}?mode=ro", uri=True)
    try:
        filas = con.execute("SELECT usuario, nombre, hash_password FROM usuarios WHERE activo = 1").fetchall()
    finally:
        con.close()
    for usuario, nombre, hash_password in filas:
        u = Usuario.query.filter_by(usuario=usuario).first() or Usuario(usuario=usuario)
        u.nombre, u.hash_password = nombre, hash_password
        db.session.add(u)
    db.session.commit()


if __name__ == "__main__":
    from waitress import serve

    reiniciar = "--reiniciar" in sys.argv
    nueva = not BASE.exists()
    from app import create_app
    from app import ejemplo
    from app.extensiones import db
    from app.modelos import Integrante, Usuario

    aplicacion = create_app({"SESSION_COOKIE_NAME": "cristo_ejemplo"})
    with aplicacion.app_context():
        _copiar_usuarios(db, Usuario)
        if reiniciar or nueva or Integrante.query.count() == 0:
            ejemplo.vaciar()
            demo = ejemplo.sembrar()
            print(f"Ejemplo sembrado: el {demo.isoformat()} queda en el paso 1.")
    print(f"EJEMPLO de Cristocéntricos en http://localhost:{PUERTO}  (datos inventados; no cierres esta ventana)")
    serve(aplicacion, host="127.0.0.1", port=PUERTO)
