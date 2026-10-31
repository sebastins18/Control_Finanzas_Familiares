"""Caso normal (Seguimiento 3): alta, edicion y borrado de un movimiento por HTTP.

Verifica el flujo correcto de punta a punta con una sesion real en una base temporal.
Si una operacion basica falla, las pruebas de error no tienen sentido.
"""
import os
import tempfile
import threading
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener

from src import app, db, read_cache, request_ctx
from tests.helpers_multicurrency import close_app_log_handlers
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class S3HttpBase(unittest.TestCase):
    """Servidor HTTP real, sesion de admin y base temporal (portable a Linux)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'DB_PATH': str(Path(self.tmp.name) / 'test.sqlite'),
                                           'FINANZAS_INITIAL_ADMIN_PASSWORD': TEST_ADMIN_PASSWORD})
        self.env.start()
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        read_cache.clear()
        db.init_db()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.post({'usuario': 'admin', 'contrasena': TEST_ADMIN_PASSWORD}, '/login')
        self.post({'id_perfil': 1}, '/perfiles/seleccionar')
        with db.connect() as c:
            self.account = c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=1 ORDER BY id_cuenta LIMIT 1').fetchone()[0]
            self.category = c.execute("SELECT id_categoria FROM categorias WHERE id_perfil=1 AND tipo='gasto' ORDER BY id_categoria LIMIT 1").fetchone()[0]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.SESSIONS.clear()
        read_cache.clear()
        close_app_log_handlers()
        self.env.stop()
        self.tmp.cleanup()

    def post(self, data, path):
        with self.opener.open(self.base + path, data=urlencode(data).encode(), timeout=5) as r:
            return r.read().decode()

    def get(self, path):
        with self.opener.open(self.base + path, timeout=5) as r:
            return r.read().decode()

    def count_movements(self):
        with db.connect() as c:
            return c.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]

    def form(self, amount='1250.50', description='S3 caso normal'):
        return {'tipo': 'gasto', 'id_categoria': str(self.category), 'id_cuenta': str(self.account),
                'monto': amount, 'fecha': '2026-10-15', 'descripcion': description}


class S3NormalCaseTests(S3HttpBase):
    def test_create_read_update_delete_movement(self):
        with db.connect() as c:
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=10000000 WHERE id_cuenta=?', (self.account,))
        self.post(self.form(), '/movimientos')
        with db.connect() as c:
            movement_id = c.execute("SELECT id_movimiento FROM movimientos WHERE descripcion='S3 caso normal'").fetchone()[0]
        self.assertIn('S3 caso normal', self.get('/'))

        self.post(self.form('2000.00', 'S3 editado'), f'/movimientos/{movement_id}/actualizar')
        with db.connect() as c:
            row = c.execute('SELECT monto_centimos, descripcion FROM movimientos WHERE id_movimiento=?', (movement_id,)).fetchone()
        self.assertEqual((row['monto_centimos'], row['descripcion']), (200000, 'S3 editado'))

        self.post({}, f'/movimientos/{movement_id}/eliminar')
        self.assertEqual(self.count_movements(), 0)


if __name__ == '__main__':
    unittest.main()