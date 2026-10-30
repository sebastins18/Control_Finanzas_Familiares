
"""Prueba de conexión SQLite para el Seguimiento 1."""

import sqlite3
from contextlib import closing

from src.db import db_path


def check_connection(path=None):
    """Verifica la conexión SQLite y cierra los recursos correctamente."""

    target = path or db_path()

    # closing garantiza el cierre de la conexión, incluso si hay errores.
    with closing(sqlite3.connect(str(target))) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='usuarios'"
        ).fetchone()[0]

        if count != 1:
            raise RuntimeError(
                "La base no está inicializada. "
                "Ejecute: py scripts/init_db.py"
            )

        version = connection.execute(
            "SELECT sqlite_version()"
        ).fetchone()[0]

        return version


if __name__ == "__main__":
    from src.db import cli_errors
    with cli_errors():
        print(f"Conexión SQLite OK. Versión: {check_connection()}")
