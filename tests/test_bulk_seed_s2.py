"""La carga masiva se confirma o revierte como una transacción."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src import db
from scripts.seed_bulk_s2 import bulk_load

class BulkSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DB_PATH':str(Path(self.tmp.name)/'test.sqlite3')})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
    def test_bulk_transaction_and_idempotence(self):
        self.assertEqual(bulk_load(1000),1000)
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM movimientos WHERE descripcion LIKE 'SIM-S2-%'").fetchone()[0],1000)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(bulk_load(1000),0)
    def test_reject_large_unintended_load(self):
        with self.assertRaises(ValueError):
            bulk_load(100001)
