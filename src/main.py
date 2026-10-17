"""Prueba de conexión SQLite para el Seguimiento 1."""
import sqlite3
from scripts.init_db import db_path

def check_connection(path=None):
    target = path or db_path()
    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='usuarios'"
        ).fetchone()[0]
        if count != 1:
            raise RuntimeError("La base no está inicializada. Ejecute: python scripts/init_db.py")
        return connection.execute("SELECT sqlite_version()").fetchone()[0]

if __name__ == "__main__":
    print(f"Conexión SQLite OK. Versión: {check_connection()}")
