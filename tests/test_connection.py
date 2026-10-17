"""Pruebas de conectividad SQLite del MVP (modelo real de cinco tablas).

Usa una base temporal independiente, sin afectar data/finanzas.sqlite3.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import db


class SQLiteConnectionTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tempdir.name) / "test.sqlite3"
        self.env_patch = patch.dict(os.environ, {"DB_PATH": str(self.db_file)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.tempdir.cleanup()

    def test_create_schema_and_connect(self):
        db.init_db()
        self.assertTrue(self.db_file.exists())
        with db.connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertTrue(
                {"usuarios", "categorias", "cuentas", "movimientos", "presupuestos"}
                .issubset(tables)
            )
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertTrue(connection.execute("SELECT sqlite_version()").fetchone()[0])
            self.assertTrue(connection.execute("PRAGMA foreign_key_list(movimientos)").fetchall())

    def test_idempotent_init(self):
        db.init_db()
        db.init_db()
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM categorias").fetchone()[0], 8)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM cuentas").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
