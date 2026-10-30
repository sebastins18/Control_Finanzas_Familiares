import os
import tempfile
import threading
import unittest
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

from src import db
from src.app import Handler, currency


class TestFinanzas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(os.environ, {'DB_PATH': str(Path(self.tmp.name) / 'test.sqlite3')})
        self.env_patch.start()
        db.init_db()
        with db.connect() as cx:
            self.cat_income = cx.execute("SELECT id_categoria FROM categorias WHERE nombre='Salario'").fetchone()[0]
            self.cat_expense = cx.execute("SELECT id_categoria FROM categorias WHERE nombre='Alimentación'").fetchone()[0]
            self.account = cx.execute('SELECT id_cuenta FROM cuentas ORDER BY id_cuenta LIMIT 1').fetchone()[0]

    def tearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    def form(self, kind='gasto', amount='250.50', category=None):
        return dict(tipo=kind, monto=amount, id_categoria=str(category or self.cat_expense),
                    id_cuenta=str(self.account), fecha=date.today().isoformat(), descripcion='Compra ficticia')

    def test_schema_and_wal(self):
        with db.connect() as cx:
            self.assertEqual(cx.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            self.assertEqual(cx.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertGreaterEqual(len(cx.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()), 5)

    def test_crud_movements(self):
        db.save_movement(self.form())
        data = db.dashboard(date.today().year, date.today().month)
        self.assertEqual(data['expense'], 25050)
        with db.connect() as cx:
            ident = cx.execute('SELECT id_movimiento FROM movimientos').fetchone()[0]
        modified = self.form(amount='90.00')
        db.save_movement(modified, ident)
        self.assertEqual(db.dashboard(date.today().year, date.today().month)['expense'], 9000)
        db.remove_movement(ident)
        self.assertEqual(db.dashboard(date.today().year, date.today().month)['expense'], 0)

    def test_budget(self):
        today = date.today()
        db.save_budget(dict(id_categoria=str(self.cat_expense), anio=str(today.year), mes=str(today.month), monto_limite='200'))
        db.save_movement(self.form(amount='180'))
        budgets = db.dashboard(today.year, today.month)['budgets']
        self.assertEqual(budgets[0]['gastado'], 18000)
        self.assertEqual(budgets[0]['limite'], 20000)

    def test_reject_invalid_amount_and_type(self):
        for bad in ('-1', '0', 'abc', '1.999'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                db.save_movement(self.form(amount=bad))
        with self.assertRaises(ValueError):
            db.save_movement(self.form(category=self.cat_income))
        with db.connect() as cx:
            self.assertEqual(cx.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0], 0)

    def test_sql_injection_is_not_executed(self):
        malicious = self.form()
        malicious['descripcion'] = "'); DROP TABLE movimientos; --"
        db.save_movement(malicious)
        with db.connect() as cx:
            self.assertEqual(cx.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0], 1)

    def test_money_display(self):
        self.assertEqual(currency(125050), '₡1.250,50')
        self.assertEqual(currency(-100), '−₡1,00')


class TestHttp(unittest.TestCase):
    form = TestFinanzas.form

    def setUp(self):
        TestFinanzas.setUp(self)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        TestFinanzas.tearDown(self)

    def logged_in(self):
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        payload = urlencode({'usuario': 'admin', 'contrasena': 'admin123!'}).encode()
        with opener.open(Request(self.base + '/login', data=payload), timeout=3) as result:
            self.assertEqual(result.status, 200)
        with opener.open(Request(self.base + '/perfiles/seleccionar', data=urlencode({'id_perfil':'1'}).encode()),timeout=3) as result:
            self.assertEqual(result.status,200)
        return opener

    def test_http_200_and_health(self):
        opener = self.logged_in()
        with opener.open(self.base + '/') as result:
            body = result.read().decode('utf-8')
            self.assertIn('MisFinanzas',body)
            self.assertEqual(result.status,200)
        with opener.open(self.base + '/health') as result:
            self.assertIn('"status": "ok"',result.read().decode('utf-8'))

    def test_http_create_and_invalid(self):
        opener = self.logged_in()
        payload = urlencode(self.form()).encode()
        with opener.open(Request(self.base + '/movimientos', data=payload), timeout=3) as result:
            self.assertEqual(result.status,200)  # 303 seguido por urllib
        self.assertEqual(db.dashboard(date.today().year, date.today().month)['expense'], 25050)
        invalid = urlencode(self.form(amount='-300')).encode()
        with self.assertRaises(HTTPError) as context:
            opener.open(Request(self.base+'/movimientos', data=invalid), timeout=3)
        self.assertEqual(context.exception.code,400)


if __name__ == '__main__':
    unittest.main()
