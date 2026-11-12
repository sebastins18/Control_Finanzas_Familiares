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
from tests.csrf_util import csrf_opener, opener_csrf
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
        opener = csrf_opener()
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
        """El administrador ve el panel de calidad y su enlace en el menú."""
        status, _, html = self.get(self.login(), '/admin/calidad')
        self.assertEqual(status, 200)
        self.assertIn('Ejecutar: Suite de pruebas', html)
        self.assertIn('Ejecutar: Mediciones de SQLite', html)
        self.assertIn('href="/admin/calidad"', html)
        self.assertRegex(html, r'name="csrf" value="[0-9a-f]{64}"')
        self.assertNotIn(self.tmp.name, html)

    def test_regular_user_and_anonymous_are_denied(self):
        """Un usuario normal o sin sesión no puede ver el panel de calidad."""
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
        _, final_url, _ = self.get(csrf_opener(), '/admin/calidad')
        self.assertTrue(final_url.endswith('/login'))

    def test_run_requires_valid_csrf_and_known_job(self):
        """Ejecutar un trabajo exige token CSRF válido y solo acepta trabajos conocidos."""
        admin = self.login()
        with patch.object(quality, 'start') as start:
            # csrf vacío = formulario sin token (el cliente de prueba solo agrega el token si el campo falta).
            for fields in ({'job': 'suite', 'csrf': ''}, {'job': 'suite', 'csrf': 'falso'}):
                with self.assertRaises(HTTPError) as bad:
                    self.post(admin, '/admin/calidad/ejecutar', fields)
                self.assertEqual(bad.exception.code, 403)
            start.assert_not_called()
        token = re.search(r'name="csrf" value="([0-9a-f]+)"', self.get(admin, '/admin/calidad')[2]).group(1)
        with self.post(admin, '/admin/calidad/ejecutar', {'job': 'rm -rf /', 'csrf': token}) as r:
            self.assertIn('aviso=error', r.url)

    def test_only_one_job_at_a_time_and_stale_lock_expires(self):
        """Solo corre un trabajo a la vez y un bloqueo abandonado caduca solo."""
        self.assertTrue(quality._acquire('suite'))
        self.assertEqual(quality.running_job()[0], 'suite')
        self.assertEqual(quality.start('bench'), 'busy')
        old = time.time() - quality.LOCK_TTL - 5
        os.utime(quality._lock_path(), (old, old))
        self.assertIsNone(quality.running_job())
        self.assertTrue(quality._acquire('bench'))
        quality._release()

    def test_child_process_is_isolated_from_the_real_database(self):
        """Los trabajos del panel corren en un proceso aparte con base temporal, nunca con la base real."""
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
        """Los resultados guardados se muestran escapados (no se puede inyectar HTML)."""
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
        """Un archivo de resultados dañado no rompe la página del panel."""
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
        """El resumen JSON de una suite exitosa cuenta pruebas y resultados por archivo."""
        payload, saved = self.run_in('"""Prueba de ejemplo."""\nimport unittest\n'
                                     'class T(unittest.TestCase):\n    def test_a(self): pass\n    def test_b(self): pass\n')
        self.assertTrue(payload['exito'])
        self.assertEqual(saved['total'], 2)
        self.assertEqual(saved['archivos'][0]['descripcion'], 'Prueba de ejemplo.')

    def test_summary_reports_failures_without_internal_paths(self):
        """El resumen de una suite con fallos los informa sin exponer rutas internas."""
        payload, saved = self.run_in('import unittest\nclass T(unittest.TestCase):\n'
                                     '    def test_ok(self): pass\n    def test_bad(self): self.assertEqual(1, 2)\n')
        self.assertFalse(payload['exito'])
        row = saved['archivos'][0]
        self.assertEqual((row['ok'], row['fallos']), (1, 1))
        self.assertEqual(row['problemas'][0]['prueba'], 'test_bad')
        self.assertNotIn(str(run_quality_suite.ROOT), json.dumps(saved))

    def test_each_test_reports_meaning_and_functions_used(self):
        """Cada prueba informa qué significa (docstring) y con qué funciones o rutas de la app se logró."""
        source = ('import unittest\nfrom src import finance\n'
                  'class T(unittest.TestCase):\n'
                  '    def helper(self, route="/historial"):\n        return route\n'
                  '    def test_formato(self):\n        """El formato de montos usa símbolo y decimales."""\n'
                  '        self.assertEqual(finance.format_amount(100, "$"), "$1.00")\n'
                  '    def test_ruta(self):\n        self.helper()\n        self.assertTrue(len("/movimientos/1/eliminar".split("/")))\n'
                  '        self.assertEqual(str("/movimientos/5/eliminar"), "/movimientos/5/eliminar")\n'
                  '    def test_mal(self):\n        """Debe fallar."""\n        self.assertEqual(1, 2)\n')
        _, saved = self.run_in(source)
        tests = {t['prueba']: t for t in saved['archivos'][0]['pruebas']}
        self.assertEqual(set(tests), {'test_formato', 'test_ruta', 'test_mal'})
        ok = tests['test_formato']
        self.assertEqual((ok['clase'], ok['resultado']), ('T', 'ok'))
        self.assertEqual(ok['significado'], 'El formato de montos usa símbolo y decimales.')
        self.assertEqual(ok['funciones'], ['finance.format_amount()'])
        route = tests['test_ruta']['funciones']
        self.assertIn('Ruta /historial → reportes.history_page()', route)          # valor por defecto del ayudante
        self.assertIn('Ruta /movimientos/5/eliminar → db.remove_movement()', route)
        self.assertEqual(tests['test_mal']['resultado'], 'fallo')
        self.assertIn('AssertionError', tests['test_mal']['detalle'])

    def test_panel_shows_detail_escaped_and_tolerates_old_results(self):
        """El panel muestra el detalle por prueba escapado y avisa si el JSON es de una versión anterior."""
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'DB_PATH': str(Path(folder) / 'x.sqlite3')}):
            results = quality.results_dir()
            results.mkdir(parents=True)
            row = {'archivo': 'test_x', 'descripcion': 'd', 'tests': 1, 'fallos': 1, 'errores': 0, 'segundos': 0.1, 'problemas': [],
                   'pruebas': [{'clase': 'T', 'prueba': 'test_<b>', 'significado': '<script>x</script>', 'resultado': 'fallo',
                                'funciones': ['db.save_movement()', '<img src=x>'], 'segundos': 0.25, 'detalle': 'AssertionError: 1 != 2'}]}
            payload = {'generado': 'hoy', 'segundos': 1, 'total': 1, 'entorno': {}, 'archivos': [row]}
            (results / 'suite.json').write_text(json.dumps(payload), encoding='utf-8')
            html = quality.content('t' * 64)
            self.assertIn('Cómo leer estos resultados', html)
            self.assertIn('<details class="subform quality-tests" open>', html)   # con fallos: abierto
            self.assertIn('<code>db.save_movement()</code>', html)
            self.assertIn('FALLO', html)
            self.assertIn('250 ms', html)
            self.assertNotIn('<script>x', html)
            self.assertNotIn('<img src=x', html)
            del row['pruebas']
            (results / 'suite.json').write_text(json.dumps(payload), encoding='utf-8')
            self.assertIn('Vuelve a ejecutar la suite para ver el detalle por prueba', quality.content('t' * 64))


if __name__ == '__main__':
    unittest.main()

