"""Ajustes de SQLite y migración sencilla: agrega columnas nuevas sin borrar datos.

db.create_all() crea las tablas que faltan, pero no agrega columnas a una tabla que ya
existe. Aquí se comparan los modelos con la base y se agrega lo que falte con
ALTER TABLE ... ADD COLUMN (todas las columnas nuevas aceptan vacío).
"""
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine

from .extensiones import db


@event.listens_for(Engine, "connect")
def _pragmas_sqlite(conexion, _registro):
    """WAL deja que el servidor y el worker usen la base al mismo tiempo sin bloquearse."""
    if type(conexion).__module__.startswith("sqlite3"):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def migrar() -> list[str]:
    """Agrega las columnas que falten. Devuelve la lista de lo que agregó."""
    inspector = inspect(db.engine)
    agregadas = []
    for tabla in db.metadata.sorted_tables:
        if not inspector.has_table(tabla.name):
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla.name)}
        for columna in tabla.columns:
            if columna.name in existentes:
                continue
            tipo = columna.type.compile(dialect=db.engine.dialect)
            # Nombres y tipos salen de los modelos (código), nunca de datos del usuario.
            with db.engine.begin() as con:
                con.execute(text(f'ALTER TABLE "{tabla.name}" ADD COLUMN "{columna.name}" {tipo}'))
            agregadas.append(f"{tabla.name}.{columna.name}")
    return agregadas
