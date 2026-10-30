"""S2: pruebas HTTP reales sobre SQLite temporal; no se toca la base del curso."""
import os
import tempfile
import threading
import unittest
from datetime import date
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import db
from src.app import Handler


class Seguimiento2HttpCrud(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DB_PATH': str(Path(self.tmp.name) / 'test.sqlite3'),
            'APP_BASE_PATH': '/finanzas',
            'FINANZAS_INITIAL_ADMIN_PASSWORD': 'ClaveSoloParaPruebas2026!',
        })
        self.env.start()
        db.init_db()
        with db.connect() as cx:
            self.categoria = cx.execute(
                "SELECT id_categoria FROM categorias WHERE tipo='gasto' AND nombre='Alimentación'"
            ).fetchone()[0]
            self.cuenta = cx.execute(
                "SELECT id_cuenta FROM cuentas WHERE nombre='Cuenta principal'"
            ).fetchone()[0]
            self.crc = cx.execute(
                "SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'"
            ).fetchone()[0]
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}/finanzas'
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.env.stop()
        self.tmp.cleanup()

    def get(self, path='/'):
        with self.opener.open(self.base + path, timeout=5) as response:
            return response.status, response.read().decode('utf-8'), response.geturl()

    def post(self, path, data):
        payload = urlencode(data).encode('utf-8')
        with self.opener.open(Request(self.base + path, data=payload), timeout=5) as response:
            return response.status, response.read().decode('utf-8'), response.geturl()

    def login(self):
        code, html, uri = self.post('/login', {
            'usuario': 'admin', 'contrasena': 'ClaveSoloParaPruebas2026!'
        })
        self.assertEqual(code, 200)
        self.assertTrue(uri.endswith('/finanzas/perfiles/elegir'), uri)
        code, html, uri = self.post('/perfiles/seleccionar', {'id_perfil':'1'})
        self.assertTrue(uri.endswith('/finanzas/'), uri)
        self.assertIn('PANEL FINANCIERO', html.upper())

    def form(self, amount, description='Evidencia ficticia S2'):
        return {
            'tipo': 'gasto', 'monto': amount,
            'id_categoria': str(self.categoria), 'id_cuenta': str(self.cuenta),
            'fecha': date.today().isoformat(), 'descripcion': description,
        }

    def count(self):
        with db.connect() as cx:
            return cx.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]

    def test_crud_completo_desde_http_con_autenticacion(self):
        code, _, uri = self.get('/')
        self.assertEqual(code, 200)
        self.assertTrue(uri.endswith('/finanzas/login'), uri)
        self.login()
        self.assertEqual(self.count(), 0)

        self.post('/movimientos', self.form('85.00'))
        self.assertEqual(self.count(), 1)
        with db.connect() as cx:
            movement_id = cx.execute('SELECT id_movimiento FROM movimientos').fetchone()[0]
        _, html, _ = self.get('/')
        self.assertIn('Evidencia ficticia S2', html)
        self.assertIn(f'/finanzas/?editar={movement_id}', html)
        _, edit_html, _ = self.get(f'/?editar={movement_id}')
        self.assertIn('Editar movimiento', edit_html)

        self.post(f'/movimientos/{movement_id}/actualizar',
                  self.form('95.00', 'Movimiento editado S2'))
        with db.connect() as cx:
            row = cx.execute(
                'SELECT monto_centimos, descripcion FROM movimientos WHERE id_movimiento=?',
                (movement_id,)
            ).fetchone()
            self.assertEqual((row['monto_centimos'], row['descripcion']),
                             (9500, 'Movimiento editado S2'))
        self.assertIn('Movimiento editado S2', self.get('/')[1])

        self.post(f'/movimientos/{movement_id}/eliminar', {})
        self.assertEqual(self.count(), 0)
        self.assertNotIn('Movimiento editado S2', self.get('/')[1])

    def test_presupuesto_y_alertas_80_y_100_por_http(self):
        self.login()
        today = date.today()
        self.post('/presupuestos', {
            'id_categoria': str(self.categoria),
            'anio': str(today.year), 'mes': str(today.month),
            'monto_limite': '100.00', 'id_moneda': str(self.crc),
        })
        self.post('/movimientos', self.form('85.00'))
        self.assertIn('Cerca del límite', self.get('/')[1])
        with db.connect() as cx:
            movement_id = cx.execute('SELECT id_movimiento FROM movimientos').fetchone()[0]
        self.post(f'/movimientos/{movement_id}/actualizar', self.form('105.00'))
        self.assertIn('Excedido', self.get('/')[1])
        self.post(f'/movimientos/{movement_id}/eliminar', {})
        self.assertIn('Bajo control', self.get('/')[1])

    def test_solicitud_invalida_no_modifica_sqlite(self):
        self.login()
        with self.assertRaises(HTTPError) as exc:
            self.post('/movimientos', self.form('-10.00'))
        self.assertEqual(exc.exception.code, 400)
        self.assertEqual(self.count(), 0)

    def test_post_sin_sesion_no_guarda_datos(self):
        status, _, url = self.post('/movimientos', self.form('500.00'))
        self.assertEqual(status, 200)  # urllib siguió 303 hasta login
        self.assertTrue(url.endswith('/finanzas/login'))
        self.assertEqual(self.count(), 0)


if __name__ == '__main__':
    unittest.main()
