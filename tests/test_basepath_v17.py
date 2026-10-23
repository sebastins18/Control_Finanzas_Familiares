"""Cobertura del reverse proxy para /finanzas en CRNube."""
import os
import tempfile
import threading
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor
from src import db
from src.app import Handler

class BasePathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.dict(os.environ, {
            'DB_PATH': str(Path(self.tmp.name) / 'test.sqlite3'),
            'APP_BASE_PATH': '/finanzas',
            'FINANZAS_INITIAL_ADMIN_PASSWORD': 'ClaveDePrueba12345!',
        })
        self.patch.start()
        db.init_db()
        self.server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_address[1])
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.patch.stop()
        self.tmp.cleanup()
    def test_prefixed_login_flow(self):
        opener=build_opener(HTTPCookieProcessor(CookieJar()))
        with opener.open(self.base+'/finanzas/') as response:
            self.assertEqual(response.geturl(),self.base+'/finanzas/login')
            html=response.read().decode()
            self.assertIn('action="/finanzas/login"',html)
            self.assertIn('href="/finanzas/static/styles.css"',html)
        with opener.open(Request(self.base+'/finanzas/login',data=urlencode({'usuario':'admin','contrasena':'ClaveDePrueba12345!'}).encode())) as response:
            self.assertEqual(response.geturl(),self.base+'/finanzas/')
            html=response.read().decode()
            self.assertIn('href="/finanzas/admin/cuentas"',html)
        with opener.open(self.base+'/finanzas/health') as response:
            self.assertIn('"status": "ok"',response.read().decode())
        with opener.open(self.base+'/finanzas/static/styles.css') as response:
            self.assertEqual(response.status,200)
