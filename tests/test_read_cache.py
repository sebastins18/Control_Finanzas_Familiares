import os
import sqlite3
import tempfile
import threading
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener

from src import app, db, read_cache, request_ctx
from tests.helpers_multicurrency import close_app_log_handlers
from tests.helpers_admin import TEST_ADMIN_PASSWORD


class ReadCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tmp.name) / 'test.sqlite'
        self.env = patch.dict(os.environ, {'DB_PATH': str(self.db_file),
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
            return r.status, r.headers, r.read().decode()

    def test_catalog_is_served_from_cache_with_notice_when_sqlite_fails(self):
        status, _, fresh = self.get('/admin/cuentas')
        self.assertEqual(status, 200)
        self.assertNotIn('La base de datos no responde', fresh)
        with patch.object(db, 'connect', side_effect=sqlite3.OperationalError('caida')):
            status, headers, stale = self.get('/admin/cuentas')
        self.assertEqual(status, 200)
        self.assertIn('La base de datos no responde', stale)
        self.assertIn('X-Datos-Desactualizados', headers)
        self.assertNotIn('caida', stale)

    def test_non_cacheable_pages_still_return_503(self):
        self.get('/')
        with patch.object(db, 'connect', side_effect=sqlite3.OperationalError('caida')):
            with self.assertRaises(HTTPError) as caught:
                self.get('/')
        self.assertEqual(caught.exception.code, 503)
        caught.exception.close()

    def test_cache_expires_and_is_bounded(self):
        read_cache.store('k', b'x')
        with patch('src.read_cache.time.time', return_value=read_cache._entries['k'][0] + read_cache.MAX_AGE_SECONDS + 1):
            self.assertIsNone(read_cache.fetch('k'))
        for i in range(read_cache.MAX_ENTRIES + 5):
            read_cache.store(i, b'x')
        self.assertLessEqual(len(read_cache._entries), read_cache.MAX_ENTRIES)


if __name__ == '__main__':
    unittest.main()
