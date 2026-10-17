"""Pruebas mínimas reproducibles de SQLite para S1."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.init_db import initialize
from src.main import check_connection

class SQLiteConnectionTest(unittest.TestCase):
    def test_create_schema_and_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            initialize(path)
            self.assertTrue(check_connection(path))
            with sqlite3.connect(path) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM monedas").fetchone()[0], 2
                )
                self.assertEqual(
                    connection.execute("PRAGMA foreign_key_list(gastos)").fetchall() != [], True
                )

    def test_idempotent_init(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            initialize(path)
            initialize(path)
            with sqlite3.connect(path) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM monedas").fetchone()[0],2)

if __name__ == "__main__":
    unittest.main()
