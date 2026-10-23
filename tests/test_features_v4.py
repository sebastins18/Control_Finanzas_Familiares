import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from src import db, extension

class V4Features(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DB_PATH':str(Path(self.temp.name)/'test.db')})
        self.env.start();db.init_db()
    def tearDown(self):
        self.env.stop();self.temp.cleanup()
    def test_profiles_are_separate(self):
        extension.save('usuarios',{'nombre':'Perfil 2'})
        with db.connect() as c:
            uid=c.execute("SELECT id_usuario FROM usuarios WHERE nombre='Perfil 2'").fetchone()[0]
        extension.select_profile({'id_usuario':str(uid)})
        with db.connect() as c:
            self.assertEqual(extension.active_profile(c),uid)
        self.assertEqual(db.dashboard(2026,10)['expense'],0)
        extension.select_profile({'id_usuario':'1'})
    def test_budget_alerts_and_currency(self):
        with db.connect() as c:
            cat=c.execute("SELECT id_categoria FROM categorias WHERE nombre='Alimentación' AND id_usuario=1").fetchone()[0]
            account=c.execute('SELECT id_cuenta FROM cuentas WHERE id_usuario=1 LIMIT 1').fetchone()[0]
            usd=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='USD'").fetchone()[0]
            crc=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
        today=date.today().isoformat()
        # Cotización precargada por el proveedor automático, sin mantenimiento manual.
        with db.connect() as c:
            c.execute('INSERT INTO tipos_cambio(id_moneda_origen,id_moneda_destino,fecha,valor) VALUES(?,?,?,?)',
                      (crc,usd,today,'0.002'))
        db.save_budget({'id_categoria':str(cat),'anio':str(date.today().year),'mes':str(date.today().month),'monto_limite':'10','id_moneda':str(usd)})
        db.save_movement({'tipo':'gasto','id_categoria':str(cat),'id_cuenta':str(account),'fecha':today,'monto':'5000','descripcion':'Test'})
        extension.refresh_alerts()
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alertas').fetchone()[0],2)
        self.assertEqual(db.dashboard(date.today().year,date.today().month)['budgets'][0]['gastado'],1000)
    def test_menus_and_receipt_page(self):
        self.assertIn('multipart/form-data',extension.receipts_page())
        self.assertIn('Perfiles familiares',extension.profiles_page())

if __name__=='__main__':unittest.main()
