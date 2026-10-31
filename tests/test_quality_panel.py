"""Panel de calidad (/admin/calidad): acceso solo para administradores y ejecucion segura.

Comprueba: 403 para usuarios normales, redireccion sin sesion, token CSRF obligatorio, un solo
trabajo a la vez, proceso hijo sin la base real, escape de HTML y el resumen JSON de la suite.
Todo usa carpetas temporales (portable a Linux); no se lanzan pruebas reales desde el navegador.
"""
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from scripts import run_quality_suite
from src import app, auth, db, quality, read_cache, request_ctx
from tests.helpers_multicurrency import close_app_log_handlers
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class QualityPanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'DB_PATH': str(root / 'test.sqlite3'), 'APP_BASE_PATH': '',
                                           'QUALITY_DIR': str(root / 'quality'),
                                           'FINANZAS_INITIAL_ADMIN_PASSWORD': TEST_ADMIN_PASSWORD})
        self.env.start()
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        read_cache.clear()
        db.init_db()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.SESSIONS.clear()
        read_cache.clear()
        close_app_log_handlers()
        self.env.stop()
        self.tmp.cleanup()

    def login(self, user='admin', password=TEST_ADMIN_PASSWORD):
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        opener.open(Request(self.base + '/login', data=urlencode({'usuario': user, 'contrasena': password}).encode()), timeout=5).read()
        with db.connect() as c:
            pid = c.execute('SELECT id_perfil FROM perfiles_financieros WHERE id_propietario=? ORDER BY id_perfil LIMIT 1',
                            (app.user_by_name(user)['id_usuario'],)).fetchone()[0]
        opener.open(Request(self.base + '/perfiles/seleccionar', data=urlencode({'id_perfil': pid}).encode()), timeout=5).read()
        return opener

    def get(self, opener, route):
        with opener.open(self.base + route, timeout=5) as r:
            return r.status, r.url, r.read().decode()

    def post(self, opener, route, fields):
        return opener.open(Request(self.base + route, data=urlencode(fields).encode()), timeout=5)

    def test_admin_sees_panel_and_menu_link(self):
        status, _, html = self.get(self.login(), '/admin/calidad')
        self.assertEqual(status, 200)
        self.assertIn('Ejecutar: Suite de pruebas', html)
        self.assertIn('Ejecutar: Mediciones de SQLite', html)
        self.assertIn('href="/admin/calidad"', html)
        self.assertRegex(html, r'name="csrf" value="[0-9a-f]{64}"')
        self.assertNotIn(self.tmp.name, html)

    def test_regular_user_and_anonymous_are_denied(self):
        auth.register({'username': 'Ana', 'name': 'Ana', 'password': 'Clave123!', 'confirm_password': 'Clave123!'})
        user = self.login('Ana', 'Clave123!')
        with self.assertRaises(HTTPError) as denied:
            self.get(user, '/admin/calidad')
        self.assertEqual(denied.exception.code, 403)
        self.assertNotIn('href="/admin/calidad"', self.get(user, '/')[2])
        with patch.object(quality, 'start') as start, self.assertRaises(HTTPError) as post_denied:
            self.post(user, '/admin/calidad/ejecutar', {'job': 'suite', 'csrf': 'x'})
        self.assertEqual(post_denied.exception.code, 403)
        start.assert_not_called()
        _, final_url, _ = self.get(build_opener(HTTPCookieProcessor(CookieJar())), '/admin/calidad')
        self.assertTrue(final_url.endswith('/login'))

    def test_run_requires_valid_csrf_and_known_job(self):
        admin = self.login()
        with patch.object(quality, 'start') as start:
            for fields in ({'job': 'suite'}, {'job': 'suite', 'csrf': 'falso'}):
                with self.assertRaises(HTTPError) as bad:
                    self.post(admin, '/admin/calidad/ejecutar', fields)
                self.assertEqual(bad.exception.code, 403)
            start.assert_not_called()
        token = re.search(r'name="csrf" value="([0-9a-f]+)"', self.get(admin, '/admin/calidad')[2]).group(1)
        with self.post(admin, '/admin/calidad/ejecutar', {'job': 'rm -rf /', 'csrf': token}) as r:
            self.assertIn('aviso=error', r.url)

    def test_only_one_job_at_a_time_and_stale_lock_expires(self):
        self.assertTrue(quality._acquire('suite'))
        self.assertEqual(quality.running_job()[0], 'suite')
        self.assertEqual(quality.start('bench'), 'busy')
        old = time.time() - quality.LOCK_TTL - 5
        os.utime(quality._lock_path(), (old, old))
        self.assertIsNone(quality.running_job())
        self.assertTrue(quality._acquire('bench'))
        quality._release()

    def test_child_process_is_isolated_from_the_real_database(self):
        real = str(Path(self.tmp.name) / 'real.sqlite3')
        fake = MagicMock()
        fake.wait.return_value = 0
        with patch.dict(os.environ, {'DB_PATH': real, 'FINANZAS_INITIAL_ADMIN_PASSWORD': 'secreta', 'APP_BASE_PATH': '/f'}), \
                patch.object(quality.subprocess, 'Popen', return_value=fake) as popen:
            self.assertEqual(quality.start('suite'), 'started')
            for _ in range(100):
                if quality.running_job() is None:
                    break
                time.sleep(0.05)
        command = popen.call_args.args[0]
        env = popen.call_args.kwargs['env']
        self.assertEqual(command[1:3], ['-m', 'scripts.run_quality_suite'])
        self.assertNotEqual(env['DB_PATH'], real)
        self.assertIn('sandbox', env['DB_PATH'])
        self.assertNotIn('FINANZAS_INITIAL_ADMIN_PASSWORD', env)
        self.assertNotIn('APP_BASE_PATH', env)
        self.assertIsNone(quality.running_job())
        # El proceso simulado no produjo resultados: no se da por bueno.
        self.assertEqual(quality.read_status()['suite']['estado'], 'error')

    def test_stored_results_are_escaped(self):
        folder = quality.results_dir()
        folder.mkdir(parents=True)
        payload = {'generado': 'hoy', 'segundos': 1, 'total': 1, 'entorno': {}, 'archivos': [
            {'archivo': '<script>alert(1)</script>', 'descripcion': '<img src=x onerror=1>', 'tests': 1,
             'fallos': 0, 'errores': 0, 'segundos': 0.1, 'problemas': []}]}
        (folder / 'suite.json').write_text(json.dumps(payload), encoding='utf-8')
        html = quality.content('t' * 64)
        self.assertNotIn('<script>alert(1)', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)

    def test_corrupt_results_do_not_break_the_page(self):
        folder = quality.results_dir()
        folder.mkdir(parents=True)
        (folder / 'suite.json').write_text('{no es json', encoding='utf-8')
        (folder / 'status.json').write_text('[]', encoding='utf-8')
        self.assertIn('Aún no hay resultados', quality.content('t' * 64))


class SuiteRunnerTests(unittest.TestCase):
    def run_in(self, source):
        with tempfile.TemporaryDirectory() as folder:
            name = f'test_tmp_{time.time_ns()}'
            (Path(folder) / f'{name}.py').write_text(source, encoding='utf-8')
            output = Path(folder) / 'out' / 'suite.json'
            try:
                payload = run_quality_suite.run(folder, output)
                return payload, json.loads(output.read_text(encoding='utf-8'))
            finally:
                sys.modules.pop(name, None)
                if folder in sys.path:
                    sys.path.remove(folder)

    def test_summary_for_passing_suite(self):
        payload, saved = self.run_in('"""Prueba de ejemplo."""\nimport unittest\n'
                                     'class T(unittest.TestCase):\n    def test_a(self): pass\n    def test_b(self): pass\n')
        self.assertTrue(payload['exito'])
        self.assertEqual(saved['total'], 2)
        self.assertEqual(saved['archivos'][0]['descripcion'], 'Prueba de ejemplo.')

    def test_summary_reports_failures_without_internal_paths(self):
        payload, saved = self.run_in('import unittest\nclass T(unittest.TestCase):\n'
                                     '    def test_ok(self): pass\n    def test_bad(self): self.assertEqual(1, 2)\n')
        self.assertFalse(payload['exito'])
        row = saved['archivos'][0]
        self.assertEqual((row['ok'], row['fallos']), (1, 1))
        self.assertEqual(row['problemas'][0]['prueba'], 'test_bad')
        self.assertNotIn(str(run_quality_suite.ROOT), json.dumps(saved))


if __name__ == '__main__':
    unittest.main()

