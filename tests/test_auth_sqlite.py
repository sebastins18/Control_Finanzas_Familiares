"""Autenticación SQLite, migración y permisos mediante solicitudes HTTP reales."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import date
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import app, auth, db, extension, request_ctx
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class AuthSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.env = patch.dict(os.environ, {'DB_PATH': str(self.path),
            'APP_BASE_PATH': '', 'FINANZAS_INITIAL_ADMIN_PASSWORD': TEST_ADMIN_PASSWORD})
        self.env.start()
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()

    def tearDown(self):
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        self.env.stop()
        self.tmp.cleanup()

    def test_defaults_and_idempotence(self):
        db.init_db()
        admin = app.user_by_name('admin')
        self.assertEqual(admin['hash'], auth.hash_password(TEST_ADMIN_PASSWORD, admin['salt']))
        self.assertNotEqual(admin['hash'], TEST_ADMIN_PASSWORD)
        self.assertEqual(admin['role_name'], 'administrador')
        self.assertFalse((self.path.parent / 'login_credentials.json').exists())
        db.init_db()
        self.assertEqual(app.user_by_name('admin')['hash'],admin['hash'])
        with db.connect() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM sqlite_master WHERE name='roles'").fetchone())
            for bad in ('admin','otro',''):
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute('UPDATE usuarios SET rol=? WHERE id_usuario=1',(bad,))

    def run_init_script(self, password=None):
        env = dict(os.environ, DB_PATH=str(self.path))
        env.pop('FINANZAS_INITIAL_ADMIN_PASSWORD', None)
        if password is not None:
            env['FINANZAS_INITIAL_ADMIN_PASSWORD'] = password
        result = subprocess.run([sys.executable, str(db.ROOT / 'scripts' / 'init_db.py')],
                                cwd=db.ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fresh_cli_ignores_json_and_preserves_existing_credentials(self):
        legacy = self.path.parent / 'login_credentials.json'
        salt = 'ab' * 16
        legacy_text = json.dumps({'users': [
            dict(username=name, name=name, role='admin', active=True,
                 salt=salt, hash=auth.hash_password('Anterior123!', salt))
            for name in ('admin', 'Diego')]})
        legacy.write_text(legacy_text, encoding='utf-8')
        self.run_init_script()
        with db.connect() as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            self.assertEqual(len(tables), 17, sorted(tables))
            self.assertEqual([tuple(r) for r in c.execute('SELECT username,rol,activo FROM usuarios')],
                             [('admin', 'administrador', 1)])
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        admin = app.user_by_name('admin')
        self.assertEqual(admin['hash'], auth.hash_password('admin123!', admin['salt']))
        self.assertNotEqual(admin['hash'], 'admin123!')
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = build_opener(HTTPCookieProcessor(CookieJar()))
            with client.open(Request(f'http://127.0.0.1:{server.server_port}/login',
                    data=urlencode({'usuario':'admin', 'contrasena':'admin123!'}).encode()), timeout=5) as r:
                self.assertTrue(r.url.endswith('/perfiles/elegir'))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        # Una contraseña cambiada y otros usuarios deben sobrevivir a la CLI.
        changed_salt = 'cd' * 16
        with db.connect() as c:
            c.execute('UPDATE usuarios SET password_salt=?,password_hash=? WHERE username=?',
                      (changed_salt, auth.hash_password('Cambiada123!', changed_salt), 'admin'))
        auth.register(dict(username='Existente', name='Usuario existente', password='Existente123!',
                           confirm_password='Existente123!'))
        with db.connect() as c:
            before = [tuple(r) for r in c.execute('SELECT * FROM usuarios ORDER BY id_usuario')]
        self.run_init_script('OtraInicial123!')
        with db.connect() as c:
            self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM usuarios ORDER BY id_usuario')], before)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(legacy.read_text(encoding='utf-8'), legacy_text)

    def test_fresh_cli_custom_password_ignores_invalid_json(self):
        legacy = self.path.parent / 'login_credentials.json'
        legacy.write_text('{invalid', encoding='utf-8')
        self.run_init_script(TEST_ADMIN_PASSWORD)
        admin = app.user_by_name('admin')
        self.assertEqual(admin['hash'], auth.hash_password(TEST_ADMIN_PASSWORD, admin['salt']))
        self.assertEqual(len(auth.credentials()), 1)
        self.run_init_script()
        self.assertEqual(app.user_by_name('admin')['hash'], admin['hash'])
        self.assertEqual(legacy.read_text(encoding='utf-8'), '{invalid')

    def test_migrate_json_preserves_users_and_financial_ids(self):
        with closing(sqlite3.connect(self.path)) as c:
            with c:
                c.execute('CREATE TABLE usuarios(id_usuario INTEGER PRIMARY KEY,nombre TEXT NOT NULL)')
                legacy_schema=db.SCHEMA.read_text(encoding='utf-8').split('CREATE TABLE IF NOT EXISTS categorias',1)[1]
                legacy_schema='CREATE TABLE IF NOT EXISTS categorias'+legacy_schema
                c.executescript(legacy_schema.replace('id_perfil','id_usuario').replace('REFERENCES perfiles_financieros(id_usuario)','REFERENCES usuarios(id_usuario)'))
                c.execute("INSERT INTO usuarios VALUES(1,'Familia de demostración')")
                c.execute("INSERT INTO cuentas(id_usuario,nombre) VALUES(1,'Cuenta existente')")
        salt = 'ab' * 16
        users = [{'username': name, 'name': name, 'role': role, 'active': True,
                  'salt': salt, 'hash': auth.hash_password('ClaveAnterior!', salt)}
                 for name, role in [('admin','admin'), ('Diego','usuario')]]
        legacy = self.path.parent / 'login_credentials.json'
        legacy.write_text(json.dumps({'users':users}), encoding='utf-8')
        db.init_db()
        db.init_db()
        self.assertEqual(len(auth.credentials()), 2)
        self.assertEqual(len(list(self.path.parent.glob('*.antes-usuarios-*.sqlite3'))), 1)
        for name in ('admin', 'Diego'):
            self.assertEqual(app.user_by_name(name)['hash'], auth.hash_password('ClaveAnterior!', salt))
        with db.connect() as c:
            self.assertEqual(c.execute("SELECT id_perfil FROM cuentas WHERE nombre='Cuenta existente'").fetchone()[0], 1)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        legacy.write_text('{invalid}', encoding='utf-8')
        self.assertIsNotNone(app.user_by_name('Diego'))  # SQLite es la fuente de verdad.

    def test_migrate_role_table_to_fixed_user_field(self):
        salt='ab'*16
        password=auth.hash_password('Anterior123!',salt)
        with closing(sqlite3.connect(self.path)) as c:
            c.executescript('''CREATE TABLE roles(id_rol INTEGER PRIMARY KEY,nombre TEXT,es_administrador INTEGER);
                INSERT INTO roles VALUES(5,'Administrador personalizado',1),(8,'Operador',0);
                CREATE TABLE usuarios(id_usuario INTEGER PRIMARY KEY,nombre TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,id_rol INTEGER NOT NULL REFERENCES roles(id_rol),
                    activo INTEGER NOT NULL,password_salt TEXT NOT NULL,password_hash TEXT NOT NULL);''')
            with c:
                c.executemany('INSERT INTO usuarios VALUES(?,?,?,?,?,?,?)',
                    [(1,'Luis','admin',5,1,salt,password),(2,'Miriam','Miriam',8,1,salt,password)])
        db.init_db()
        db.init_db()
        with db.connect() as c:
            self.assertEqual([tuple(r) for r in c.execute('SELECT id_usuario,rol FROM usuarios ORDER BY 1')],
                             [(1,'administrador'),(2,'usuario')])
            self.assertNotIn('id_rol',{r['name'] for r in c.execute('PRAGMA table_info(usuarios)')})
            self.assertIsNone(c.execute("SELECT 1 FROM sqlite_master WHERE name='roles'").fetchone())
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(app.user_by_name('admin')['hash'],password)
        self.assertEqual(app.user_by_name('Miriam')['hash'],password)

    def test_http_users_roles_and_permissions(self):
        db.init_db()
        server = ThreadingHTTPServer(('127.0.0.1',0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        opener = build_opener(HTTPCookieProcessor(CookieJar()))

        def post(path, data):
            with opener.open(Request(base+path, data=urlencode(data).encode()), timeout=5) as r:
                return r.read().decode()

        def login(name='admin', password=TEST_ADMIN_PASSWORD):
            post('/login', {'usuario':name, 'contrasena':password})
            uid=app.user_by_name(name)['id_usuario']
            with db.connect() as c:pid=c.execute('SELECT id_perfil FROM perfiles_financieros WHERE id_propietario=? ORDER BY id_perfil LIMIT 1',(uid,)).fetchone()[0]
            return post('/perfiles/seleccionar', {'id_perfil':pid})

        try:
            admin_html = login()
            self.assertIn('/perfiles', admin_html)
            self.assertIn('Mantenimiento de usuarios', admin_html)
            with opener.open(base+'/admin/usuarios') as r:
                html=r.read().decode()
                self.assertIn('value="administrador"',html)
                self.assertIn('value="usuario"',html)
                self.assertNotIn('Mantenimiento de roles',html)
            post('/admin/usuarios/guardar', {'username':'Diego','name':'Diego', 'role':'usuario',
                                            'active':'1','password':'Diego123!'})
            self.assertEqual(app.user_by_name('Diego')['role_name'], 'usuario')
            login()
            with app.AUTH_LOCK:
                admin_sessions = {token: session for token, session in app.SESSIONS.items() if session[0] == 'admin'}
                app.SESSIONS['edited-user-session'] = ('Diego', 9999999999)
            saved_html = post('/admin/usuarios/guardar', {'username':'Diego','name':'Diego actualizado','role':'usuario',
                                            'active':'1','password':''})
            self.assertIn('Mantenimiento de usuarios', saved_html)
            self.assertNotIn('action="/login"', saved_html)
            self.assertTrue(admin_sessions)
            self.assertTrue(all(token in app.SESSIONS and app.SESSIONS[token][0] == session[0]
                                for token, session in admin_sessions.items()))
            self.assertNotIn('edited-user-session', app.SESSIONS)
            self.assertEqual(app.user_by_name('Diego')['name'], 'Diego actualizado')
            login()
            post('/admin/usuarios/guardar', {'username':'Diego','name':'Diego actualizado','role':'administrador',
                                            'active':'1','password':''})
            self.assertEqual(app.user_by_name('Diego')['role_name'],'administrador')
            login('Diego','Diego123!')
            with opener.open(base+'/admin/usuarios') as r:
                self.assertEqual(r.status,200)
            post('/admin/usuarios/guardar', {'username':'Diego','name':'Diego actualizado','role':'usuario',
                                            'active':'1','password':''})
            login()
            with self.assertRaises(HTTPError) as caught:
                post('/admin/usuarios/guardar', {'username':'Diego','name':'Diego','role':'otro',
                                                'active':'1','password':''})
            self.assertEqual(caught.exception.code,400)
            caught.exception.close()
            with self.assertRaises(HTTPError) as caught:
                login('Diego', 'Incorrecta')
            self.assertEqual(caught.exception.code, 401)
            caught.exception.close()
            html = login('Diego', 'Diego123!')
            self.assertNotIn('Mantenimiento de usuarios', html)
            self.assertNotIn('Mantenimiento de roles', html)
            with db.connect() as c:
                uid=app.user_by_name('Diego')['id_usuario']
                category=c.execute("SELECT id_categoria FROM categorias WHERE id_perfil=? AND tipo='gasto' LIMIT 1",(uid,)).fetchone()[0]
                account=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=?',(uid,)).fetchone()[0]
                admin_category=c.execute("SELECT id_categoria FROM categorias WHERE id_perfil=1 AND tipo='gasto' LIMIT 1").fetchone()[0]
            post('/movimientos', {'tipo':'gasto','monto':'10','fecha':date.today().isoformat(),
                                 'id_categoria':category,'id_cuenta':account,'descripcion':'Solo Diego'})
            with db.connect() as c:
                self.assertEqual(c.execute('SELECT id_perfil FROM movimientos').fetchone()[0],uid)
            with self.assertRaises(HTTPError) as caught:
                post('/movimientos', {'tipo':'gasto','monto':'10','fecha':date.today().isoformat(),
                                     'id_categoria':admin_category,'id_cuenta':account})
            self.assertEqual(caught.exception.code,400)
            caught.exception.close()
            with self.assertRaises(HTTPError) as caught:
                opener.open(base+'/admin/usuarios')
            self.assertEqual(caught.exception.code,403)
            caught.exception.close()
            with self.assertRaises(HTTPError) as caught:
                post('/admin/usuarios/guardar', {'username':'admin','name':'Intruso','role':'administrador','active':'1','password':''})
            self.assertEqual(caught.exception.code,403)
            caught.exception.close()
            for route,data in [('/admin/roles',None),('/admin/roles/guardar',b'nombre=Intruso')]:
                with self.assertRaises(HTTPError) as caught:
                    opener.open(Request(base+route,data=data))
                self.assertEqual(caught.exception.code,404)
                caught.exception.close()
            post('/admin/cambiar-clave', {'actual':'Diego123!','nueva':'Nueva123!','confirmar':'Nueva123!'})
            login('Diego','Nueva123!')
            login()
            with opener.open(base+'/perfiles') as r:
                self.assertEqual(r.status,200)
            with self.assertRaises(HTTPError) as caught:
                post('/admin/usuarios/guardar', {'username':'admin','name':'Admin','role':'usuario','active':'1','password':''})
            self.assertEqual(caught.exception.code,400)
            caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
