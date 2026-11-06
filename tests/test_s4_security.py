"""S4: políticas de credenciales y cabeceras en una instalación SQLite nueva."""
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from src import app, auth, db


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class ReleaseSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            'DB_PATH': str(Path(self.tmp.name) / 's4.sqlite3'),
            'APP_BASE_PATH': '/finanzas',
            'FINANZAS_INITIAL_ADMIN_PASSWORD': 'SoloPruebaS4Segura2026!',
            'FINANZAS_COOKIE_SECURE': '1',
        })
        self.env.start()
        db.init_db()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_secure_headers_and_login_cookie_with_explicit_tls(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        client = build_opener(_NoRedirect())
        try:
            with client.open(base + '/finanzas/login', timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
                self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
            request = Request(base + '/finanzas/login',
                data=urlencode({'usuario': 'admin',
                                'contrasena': 'SoloPruebaS4Segura2026!'}).encode())
            with self.assertRaises(HTTPError) as context:
                client.open(request, timeout=5)
            response = context.exception
            self.assertEqual(response.code, 303)
            cookie = response.headers['Set-Cookie']
            self.assertIn('HttpOnly', cookie)
            self.assertIn('SameSite=Strict', cookie)
            self.assertIn('Secure', cookie)
            self.assertIn('Path=/finanzas', cookie)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_deployment_requires_strong_initial_admin(self):
        for password in ('', 'admin123!', '12345678901'):
            with self.subTest(length=len(password)):
                with tempfile.TemporaryDirectory() as folder:
                    env = {'DB_PATH': str(Path(folder) / 'fresh.sqlite3'),
                           'APP_BASE_PATH': '/finanzas'}
                    with patch.dict(os.environ, env):
                        with patch.dict(os.environ, {'FINANZAS_INITIAL_ADMIN_PASSWORD': password}):
                            with self.assertRaisesRegex(ValueError, 'FINANZAS_INITIAL_ADMIN_PASSWORD'):
                                db.init_db()
        # Una clave segura permite crear una base nueva bajo el proxy web.
        self.assertEqual(len(auth.credentials()), 1)

    def test_existing_admin_is_not_overwritten_by_new_env_variable(self):
        before = auth.credentials()[0]['hash']
        with patch.dict(os.environ, {'FINANZAS_INITIAL_ADMIN_PASSWORD': 'CambioNoDebeAplicar2026!'}):
            db.init_db()
        self.assertEqual(before, auth.credentials()[0]['hash'])


if __name__ == '__main__':
    unittest.main()
