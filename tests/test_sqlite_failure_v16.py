import sqlite3
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from src import app

class SQLiteFailureTests(unittest.TestCase):
    def test_get_failure_is_controlled(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.object(app.Handler,'authenticated',return_value=True), patch.object(app.db,'connect',side_effect=sqlite3.OperationalError('sensitive db path')):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(f'http://127.0.0.1:{server.server_port}/health',timeout=3)
                self.assertEqual(caught.exception.code,503)
                body=caught.exception.read().decode()
                self.assertIn('Base de datos no disponible',body)
                self.assertNotIn('sensitive db path',body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
