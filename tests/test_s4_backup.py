"""Respaldo SQLite sin sobrescribir la base origen."""
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src import db
from scripts.backup_sqlite_s4 import backup


class S4BackupTests(unittest.TestCase):
    def test_online_backup_integrity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / 'original.sqlite3'
            copy = Path(folder) / 'backup.sqlite3'
            with patch.dict(os.environ, {'DB_PATH':str(original),
                                          'FINANZAS_INITIAL_ADMIN_PASSWORD':'ClavePruebaRespaldo2026!',
                                          'APP_BASE_PATH':'/finanzas'}):
                db.init_db()
                with db.connect() as con:
                    con.execute("UPDATE usuarios SET nombre='Prueba de respaldo' WHERE id_usuario=1")
                    original_count = con.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
                backup(copy)
                self.assertTrue(copy.exists())
                with closing(sqlite3.connect(copy)) as con:
                    self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                    self.assertEqual(con.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0], original_count)
                    self.assertEqual(con.execute("SELECT nombre FROM usuarios WHERE id_usuario=1").fetchone()[0],
                                     'Prueba de respaldo')
                with self.assertRaises(FileExistsError):
                    backup(copy)
                with self.assertRaises(ValueError):
                    backup(original)


if __name__ == '__main__':
    unittest.main()
