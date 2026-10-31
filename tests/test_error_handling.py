"""Fallos reales de SQLite y errores durante autenticación: siempre una respuesta."""
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import date
from contextlib import closing
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import app, db, request_ctx
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class ErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.env = patch.dict(os.environ, {'DB_PATH':str(self.path), 'APP_BASE_PATH':'',
            'FINANZAS_INITIAL_ADMIN_PASSWORD': TEST_ADMIN_PASSWORD})
        self.env.start()
        request_ctx.set_user_id(1)
        db.init_db()
        self.server = ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.post('/login', {'usuario':'admin','contrasena':TEST_ADMIN_PASSWORD})
        self.post('/perfiles/seleccionar',{'id_perfil':1})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        app.SESSIONS.clear()
        self.env.stop()
        self.tmp.cleanup()

    def post(self, route, fields):
        with self.opener.open(Request(self.base+route,data=urlencode(fields).encode()), timeout=5) as r:
            return r.read().decode()

    def expect_error(self, request, status, text):
        with self.assertRaises(HTTPError) as caught:
            self.opener.open(request, timeout=5)
        with caught.exception as response:
            self.assertEqual(response.code,status)
            body=response.read().decode()
            self.assertIn(text,body)
            for private in ('Traceback','sensitive path','sqlite3.OperationalError','UNIQUE constraint failed'):
                self.assertNotIn(private,body)
            return body

    def test_authentication_failure_get_and_post_are_controlled(self):
        with patch.object(db,'connect',side_effect=sqlite3.OperationalError('sensitive path')):
            self.expect_error(self.base+'/',503,'Base de datos no disponible')
            self.expect_error(Request(self.base+'/login',data=b'usuario=admin'),503,'Base de datos no disponible')
        with self.opener.open(self.base+'/health',timeout=5) as r:
            self.assertEqual(r.status,200)

    def test_constraint_and_validation_have_friendly_responses(self):
        self.expect_error(Request(self.base+'/admin/categorias/guardar',
            data=urlencode({'nombre':'Salario','tipo':'ingreso'}).encode()),409,'Ya existe un registro')
        with db.connect() as c:
            c.execute('INSERT INTO presupuestos(id_perfil,id_categoria,anio,mes,monto_limite_centimos,id_moneda) VALUES(1,3,2026,10,10000,1)')
        self.expect_error(Request(self.base+'/admin/categorias/3/eliminar',data=b''),409,'relacionado con otros datos')
        self.expect_error(self.base+'/admin/cuentas?editar=incorrecto',400,'formato incorrecto')
        with self.opener.open(self.base+'/health',timeout=5) as r:
            self.assertEqual(r.status,200)

    def test_locked_database_returns_without_retry_loop(self):
        with closing(sqlite3.connect(self.path)) as blocker:
            blocker.execute('BEGIN IMMEDIATE')
            try:
                with patch.object(db,'BUSY_TIMEOUT_MS',50):
                    start=time.monotonic()
                    self.expect_error(Request(self.base+'/admin/categorias/guardar',
                        data=b'nombre=Nuevo&tipo=gasto'),503,'base de datos está ocupada')
                    self.assertLess(time.monotonic()-start,3)
            finally:
                blocker.rollback()
        with db.connect() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM categorias WHERE nombre='Nuevo'").fetchone())
        self.post('/admin/categorias/guardar',{'nombre':'Nuevo','tipo':'gasto'})

    def test_transaction_rolls_back_and_closes_after_failure(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.connect() as c:
                c.execute("INSERT INTO categorias(id_perfil,nombre,tipo) VALUES(1,'Temporal','gasto')")
                c.execute("UPDATE usuarios SET rol='invalido' WHERE id_usuario=1")
        with self.assertRaises(sqlite3.ProgrammingError):
            c.execute('SELECT 1')
        with db.connect() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM categorias WHERE nombre='Temporal'").fetchone())

    def test_expensive_query_is_interrupted_and_next_connection_works(self):
        with patch.object(db,'OPERATION_TIMEOUT_SECONDS',0):
            with self.assertRaises(sqlite3.OperationalError) as caught:
                with db.connect() as c:
                    c.execute('''WITH RECURSIVE numbers(n) AS
                        (SELECT 1 UNION ALL SELECT n+1 FROM numbers WHERE n<1000000000)
                        SELECT SUM(n) FROM numbers''').fetchone()
            self.assertEqual(caught.exception.sqlite_errorcode,sqlite3.SQLITE_INTERRUPT)
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)

    def test_storage_and_unexpected_errors_do_not_break_response(self):
        with patch.object(app,'dashboard_page',side_effect=PermissionError('sensitive path')):
            self.expect_error(self.base+'/',503,'almacenamiento')
        with patch.object(app,'dashboard_page',side_effect=RuntimeError('sensitive path')):
            self.expect_error(self.base+'/',500,'problema inesperado')

    def test_cli_failure_has_no_unhandled_traceback(self):
        environment=dict(os.environ, DB_PATH=self.tmp.name)
        result=subprocess.run([sys.executable,'scripts/init_db.py'],env=environment,
                              capture_output=True,text=True,timeout=5,cwd=db.ROOT)
        self.assertEqual(result.returncode,1)
        self.assertIn('No se pudo completar',result.stderr)
        self.assertNotIn('Traceback',result.stderr)
        self.assertNotIn(self.tmp.name,result.stderr)

    def test_quote_transfer_errors_are_controlled_and_rollback_all_changes(self):
        with db.connect() as c:
            origin=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=1 LIMIT 1').fetchone()[0]
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=10000000 WHERE id_cuenta=?',(origin,))
            target=c.execute("INSERT INTO cuentas(id_perfil,nombre,id_moneda) VALUES(1,'Cuenta USD',2)").lastrowid
        form=dict(id_cuenta_origen=origin,id_cuenta_destino=target,monto_origen_centimos='100000',
                  fecha=date.today().isoformat(),descripcion='Prueba cotización',cotizacion='460')
        self.expect_error(Request(self.base+'/admin/transferencias/guardar',
            data=urlencode(dict(form,cotizacion='NaN')).encode()),400,'cotización')
        with db.connect() as c:
            c.execute("CREATE TRIGGER fallo_transferencia BEFORE INSERT ON transferencias BEGIN SELECT RAISE(ABORT,'sensitive path'); END")
        self.expect_error(Request(self.base+'/admin/transferencias/guardar',
            data=urlencode(form).encode()),409,'No se pudo realizar el cambio')
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tipos_cambio').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM transferencias').fetchone()[0],0)
            c.execute('DROP TRIGGER fallo_transferencia')
        self.assertIn('1 USD = 460,00 CRC',self.post('/admin/transferencias/guardar',form))
