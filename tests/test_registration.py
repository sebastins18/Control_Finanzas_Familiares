"""Registro público, unicidad y creación transaccional del perfil inicial."""
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import app, auth, db, profiles, request_ctx
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DB_PATH':str(Path(self.tmp.name)/'test.sqlite3'),
                                      'APP_BASE_PATH':'','FINANZAS_INITIAL_ADMIN_PASSWORD':TEST_ADMIN_PASSWORD})
        self.env.start()
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        db.init_db()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.client=build_opener(HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
        app.SESSIONS.clear()
        self.env.stop();self.tmp.cleanup()

    def form(self,**changes):
        return dict(dict(username='Diego',name='Diego Prueba',password='Clave123!',
                         confirm_password='Clave123!'),**changes)

    def post(self,fields,route='/registro'):
        return self.client.open(Request(self.base+route,data=urlencode(fields).encode()),timeout=5)

    def test_public_registration_and_login_with_fixed_user_role(self):
        with self.client.open(self.base+'/login',timeout=5) as r:
            self.assertIn('href="/registro"',r.read().decode())
        with self.client.open(self.base+'/registro',timeout=5) as r:
            html=r.read().decode()
            self.assertIn('action="/registro"',html)
            self.assertNotIn('name="role"',html)
        with self.post(self.form(role='administrador',activo='0')) as r:
            self.assertTrue(r.url.endswith('/login?registro=ok'))
            self.assertIn('Cuenta creada correctamente',r.read().decode())
        user=app.user_by_name('Diego')
        self.assertEqual(user['role_name'],'usuario')
        self.assertTrue(user['active'])
        self.assertNotEqual(user['hash'],'Clave123!')
        with db.connect() as c:
            pid=c.execute('SELECT id_perfil FROM perfiles_financieros WHERE id_propietario=?',(user['id_usuario'],)).fetchone()[0]
            self.assertGreater(c.execute('SELECT COUNT(*) FROM cuentas WHERE id_perfil=?',(pid,)).fetchone()[0],0)
        with self.post({'usuario':'Diego','contrasena':'Clave123!'},'/login') as r:
            self.assertTrue(r.url.endswith('/perfiles/elegir'))
        with self.post({'id_perfil':pid},'/perfiles/seleccionar') as r:
            self.assertIn('Diego Prueba',r.read().decode())

    def test_duplicates_preserve_original_and_case_is_ignored(self):
        with self.post(self.form()) as r:r.read()
        original=app.user_by_name('Diego')
        for username in ('Diego','diego','DIEGO','  Diego  '):
            with self.assertRaises(HTTPError) as caught:
                self.post(self.form(username=username,name='Intento de reemplazo'))
            with caught.exception as r:
                self.assertEqual(r.code,400)
                self.assertIn('ya está registrado',r.read().decode())
        self.assertEqual(app.user_by_name('Diego')['hash'],original['hash'])
        self.assertEqual(app.user_by_name('Diego')['name'],'Diego Prueba')
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0],2)
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("INSERT INTO usuarios(nombre,username,rol,password_salt,password_hash) VALUES('Otro','dIeGo','usuario','salt','hash')")

    def test_validation_and_escaping_without_returning_passwords(self):
        for changes in ({'username':'nombre con espacios'}, {'name':' '}, {'password':'corta'},
                        {'confirm_password':'NoCoincide!'}, {'username':'a'*41}):
            with self.assertRaises(HTTPError) as caught:self.post(self.form(**changes))
            with caught.exception as r:self.assertEqual(r.code,400)
        with self.assertRaises(HTTPError) as caught:
            self.post(self.form(name='<script>alert(1)</script>',confirm_password='Error'))
        with caught.exception as r:
            html=r.read().decode()
            self.assertIn('&lt;script&gt;',html)
            self.assertNotIn('<script>alert(1)</script>',html)
            self.assertNotIn('Clave123!',html)
        with db.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0],1)

    def test_concurrent_signup_only_creates_one_account(self):
        def attempt(username):
            try:return auth.register(self.form(username=username))
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,('Concurrente','concurrente')))
        self.assertEqual(sum(result is not None for result in results),1)
        with db.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM usuarios WHERE lower(username)='concurrente'").fetchone()[0],1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM perfiles_financieros').fetchone()[0],2)

    def test_profile_creation_failure_rolls_back_account(self):
        with patch.object(profiles,'ensure_default',side_effect=sqlite3.OperationalError('sensitive path')):
            with self.assertRaises(HTTPError) as caught:self.post(self.form())
            with caught.exception as r:
                self.assertEqual(r.code,503)
                self.assertNotIn('sensitive path',r.read().decode())
        self.assertIsNone(app.user_by_name('Diego'))

    def test_registration_respects_base_path(self):
        with patch.dict(os.environ,{'APP_BASE_PATH':'/finanzas'}):
            with self.client.open(self.base+'/finanzas/login',timeout=5) as r:
                self.assertIn('href="/finanzas/registro"',r.read().decode())
            with self.client.open(self.base+'/finanzas/registro',timeout=5) as r:
                self.assertIn('action="/finanzas/registro"',r.read().decode())
            with self.post(self.form(),'/finanzas/registro') as r:
                self.assertTrue(r.url.endswith('/finanzas/login?registro=ok'))

    def test_standard_user_mode_hides_roles_and_disables_user_management(self):
        self.assertTrue(auth.STANDARD_USER_MODE)
        with self.post({'usuario':'admin','contrasena':TEST_ADMIN_PASSWORD},'/login') as r:r.read()
        with self.post({'id_perfil':1},'/perfiles/seleccionar') as r:
            html=r.read().decode()
            self.assertIn('session-name',html)
            self.assertNotIn('session-role',html)
            self.assertNotIn('Mantenimiento de usuarios',html)
            self.assertIn('Cambiar contraseña',html)
        with self.assertRaises(HTTPError) as caught:
            self.client.open(self.base+'/admin/usuarios',timeout=5)
        with caught.exception as r:self.assertEqual(r.code,403)
        with self.assertRaises(HTTPError) as caught:
            self.post({'username':'admin','name':'Cambio','role':'administrador','active':'1'},'/admin/usuarios/guardar')
        with caught.exception as r:self.assertEqual(r.code,403)
        with self.client.open(self.base+'/admin/cambiar-clave',timeout=5) as r:
            self.assertIn('Cambiar mi contraseña',r.read().decode())
        with self.post({'actual':TEST_ADMIN_PASSWORD,'nueva':'ClaveNueva123!','confirmar':'ClaveNueva123!'},'/admin/cambiar-clave') as r:r.read()
        with self.post({'usuario':'admin','contrasena':'ClaveNueva123!'},'/login') as r:
            self.assertTrue(r.url.endswith('/perfiles/elegir'))
        with db.connect() as c:
            self.assertEqual(c.execute("SELECT rol FROM usuarios WHERE username='admin'").fetchone()[0],'administrador')
