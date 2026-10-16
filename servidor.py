"""Servidor para el uso diario (waitress). Solo escucha en esta PC por defecto."""
import os

from waitress import serve

from app import create_app

if __name__ == "__main__":
    aplicacion = create_app()  # también carga el .env
    host = os.environ.get("HOST", "127.0.0.1")
    puerto = int(os.environ.get("PORT", "5021"))
    print(f"Cristocéntricos listo en http://localhost:{puerto}  (no cierres esta ventana)")
    serve(aplicacion, host=host, port=puerto)
