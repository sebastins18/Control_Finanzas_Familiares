import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from src import db, extension
from tests.helpers_multicurrency import close_app_log_handlers

class V4Features(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DB_PATH':str(Path(self.temp.name)/'test.db')})
        self.env.start();db.init_db()
    def tearDown(self):
        close_app_log_handlers()
        self.env.stop();self.temp.cleanup()
    def test_budget_alerts_and_currency(self):
        with db.connect() as c:
            cat=c.execute("SELECT id_categoria FROM categorias WHERE nombre='Alimentación' AND id_perfil=1").fetchone()[0]
            account=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=1 LIMIT 1').fetchone()[0]
            usd=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='USD'").fetchone()[0]
            crc=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
        today=date.today().isoformat()
        # Cotización precargada por el proveedor automático, sin mantenimiento manual.
        with db.connect() as c:
            c.execute('INSERT INTO tipos_cambio(id_moneda_base,id_moneda_cotizada,fecha,cotizacion) VALUES(?,?,?,?)',
                      (crc,usd,today,'0.002'))
        db.save_budget({'id_categoria':str(cat),'anio':str(date.today().year),'mes':str(date.today().month),'monto_limite':'10','id_moneda':str(usd)})
        db.save_movement({'tipo':'gasto','id_categoria':str(cat),'id_cuenta':str(account),'fecha':today,'monto':'5000','descripcion':'Test'})
        extension.refresh_alerts()
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alertas').fetchone()[0],2)
        self.assertEqual(db.dashboard(date.today().year,date.today().month)['budgets'][0]['gastado'],1000)
    def test_menus_and_receipt_page(self):
        self.assertIn('multipart/form-data',extension.receipts_page())
        with self.assertRaises(ValueError):
            extension.page('roles')

    def test_manual_alert_survives_refresh_while_automatic_alerts_recalculate(self):
        today=date.today()
        with db.connect() as c:
            category=c.execute("SELECT id_categoria FROM categorias WHERE tipo='gasto' AND id_perfil=1 LIMIT 1").fetchone()[0]
            account=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=1 LIMIT 1').fetchone()[0]
        db.save_budget({'id_categoria':str(category),'anio':str(today.year),
                        'mes':str(today.month),'monto_limite':'100'})
        with db.connect() as c:
            budget=c.execute('SELECT id_presupuesto FROM presupuestos').fetchone()[0]
        form={'id_presupuesto':str(budget),'umbral':'80','fecha':today.isoformat(),'leida':'0'}
        extension.save('alertas',form)
        extension.refresh_alerts()
        with db.connect() as c:
            alert=c.execute('SELECT * FROM alertas').fetchone()
            self.assertIsNotNone(alert)
            self.assertEqual(alert['origen'],'manual')
            alert_id=alert['id_alerta']
        extension.save('alertas',dict(form,leida='1'),alert_id)
        db.save_movement({'tipo':'gasto','id_categoria':str(category),'id_cuenta':str(account),
                          'monto':'100','fecha':today.isoformat()})
        extension.refresh_alerts()
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM alertas').fetchone()[0],2)
            movement=c.execute('SELECT id_movimiento FROM movimientos').fetchone()[0]
        db.remove_movement(movement)
        extension.refresh_alerts()
        db.init_db()
        with db.connect() as c:
            remaining=c.execute('SELECT * FROM alertas').fetchall()
            self.assertEqual(len(remaining),1)
            self.assertEqual(remaining[0]['id_alerta'],alert_id)
            self.assertEqual(remaining[0]['leida'],1)

if __name__=='__main__':unittest.main()
