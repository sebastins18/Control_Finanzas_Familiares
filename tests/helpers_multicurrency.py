"""Base compartida de pruebas multimoneda; usada por test_multicurrency_v7 y test_lazy_fx_v8."""
import logging
import os
import tempfile
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
from src import db


def close_app_log_handlers():
    """Libera el archivo errores.log antes de borrar el directorio temporal (requerido en Windows)."""
    logger = logging.getLogger('finanzas')
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


class MulticurrencyBase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ, {'DB_PATH':str(Path(self.tmp.name)/'test.sqlite')})
        self.env.start()
        db.init_db()
        with db.connect() as c:
            self.crc=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            self.usd=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='USD'").fetchone()[0]
            self.cat=c.execute("SELECT id_categoria FROM categorias WHERE tipo='gasto' LIMIT 1").fetchone()[0]
            self.crc_account=c.execute("SELECT id_cuenta FROM cuentas LIMIT 1").fetchone()[0]
            c.execute("INSERT INTO cuentas(id_perfil,nombre,id_moneda,saldo_inicial_centimos) VALUES(1,'USD test',?,100000)",(self.usd,))
            self.usd_account=c.execute("SELECT id_cuenta FROM cuentas WHERE nombre='USD test'").fetchone()[0]
        self.today=date.today().isoformat()
    def tearDown(self):
        close_app_log_handlers()
        self.env.stop()
        self.tmp.cleanup()
