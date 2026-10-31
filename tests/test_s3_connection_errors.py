"""Error de conexion (Seguimiento 3): que hace la aplicacion si SQLite no responde.

No hay motor secundario (perfil A). Se comprueba el manejo de fallos del unico motor:
respuesta 503 generica sin filtrar el error interno, ninguna escritura parcial y
servidor operativo despues de recuperarse.
"""
import sqlite3
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src import db
from tests.test_s3_normal import S3HttpBase


class S3ConnectionErrorTests(S3HttpBase):
    def test_read_failure_returns_generic_503_and_server_recovers(self):
        with patch.object(db, 'connect', side_effect=sqlite3.OperationalError('ruta-secreta-interna')):
            with self.assertRaises(HTTPError) as caught:
                self.get('/')
        self.assertEqual(caught.exception.code, 503)
        body = caught.exception.read().decode()
        caught.exception.close()
        self.assertIn('Base de datos no disponible', body)
        self.assertNotIn('ruta-secreta-interna', body)
        self.assertIn('MisFinanzas', self.get('/'))

    def test_write_failure_returns_503_and_saves_nothing(self):
        before = self.count_movements()
        with patch.object(db, 'connect', side_effect=sqlite3.OperationalError('ruta-secreta-interna')):
            with self.assertRaises(HTTPError) as caught:
                self.post(self.form(), '/movimientos')
        self.assertEqual(caught.exception.code, 503)
        self.assertNotIn('ruta-secreta-interna', caught.exception.read().decode())
        caught.exception.close()
        self.assertEqual(self.count_movements(), before)

    def test_locked_database_is_reported_as_busy_without_partial_write(self):
        before = self.count_movements()
        locked = sqlite3.OperationalError('database is locked')
        locked.sqlite_errorcode = sqlite3.SQLITE_BUSY
        with patch.object(db, 'connect', side_effect=locked):
            with self.assertRaises(HTTPError) as caught:
                self.post(self.form(), '/movimientos')
        self.assertEqual(caught.exception.code, 503)
        self.assertIn('ocupada', caught.exception.read().decode())
        caught.exception.close()
        self.assertEqual(self.count_movements(), before)


if __name__ == '__main__':
    unittest.main()