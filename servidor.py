"""Servidor para el uso diario (waitress). En la laptop solo escucha en esta PC; en la nube (MODO=nube)
escucha en 0.0.0.0 y en el PORT que da Railway."""
import os

from waitress import serve

from app import create_app

if __name__ == "__main__":
    aplicacion = create_app()  # también carga el .env
    host = os.environ.get("HOST") or ("0.0.0.0" if aplicacion.config["EN_NUBE"] else "127.0.0.1")
    puerto = int(os.environ.get("PORT", "5021"))
    print(f"Cristocéntricos listo en http://localhost:{puerto}  (no cierres esta ventana)")
    serve(aplicacion, host=host, port=puerto, threads=8)
