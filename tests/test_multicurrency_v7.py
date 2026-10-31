from datetime import date
from src import db, extension
from tests.helpers_multicurrency import MulticurrencyBase

class MulticurrencyTests(MulticurrencyBase):
    def test_separate_monthly_totals(self):
        for account, amount in [(self.crc_account,'1000'),(self.usd_account,'25')]:
            db.save_movement({'tipo':'gasto','monto':amount,'fecha':self.today,'id_categoria':str(self.cat),'id_cuenta':str(account)})
        d=db.dashboard(date.today().year,date.today().month)
        self.assertEqual(d['totals_by_currency']['CRC']['gasto'],100000)
        self.assertEqual(d['totals_by_currency']['USD']['gasto'],2500)
    def test_transfer_between_currencies(self):
        with db.connect() as c:
            c.execute('INSERT INTO tipos_cambio(id_moneda_base,id_moneda_cotizada,fecha,cotizacion) VALUES(?,?,?,?)',
                      (self.usd,self.crc,self.today,'500'))
        extension.save('transferencias', {'id_cuenta_origen':str(self.usd_account),
            'id_cuenta_destino':str(self.crc_account),'monto_origen_centimos':'10',
            'fecha':self.today,'descripcion':'Cambio de prueba','cotizacion':'500'})
        with db.connect() as c:
            t=c.execute('SELECT * FROM transferencias').fetchone()
            self.assertEqual(t['monto_origen_centimos'],1000)
            self.assertEqual(t['monto_destino_centimos'],500000)
            self.assertIsNotNone(t['id_tipo_cambio'])
    def test_budget_converts_from_actual_account_currency(self):
        with db.connect() as c:
            c.execute('INSERT INTO tipos_cambio(id_moneda_base,id_moneda_cotizada,fecha,cotizacion) VALUES(?,?,?,?)',
                      (self.usd,self.crc,self.today,'500'))
        db.save_movement({'tipo':'gasto','monto':'10','fecha':self.today,'id_categoria':str(self.cat),'id_cuenta':str(self.usd_account)})
        db.save_budget({'id_categoria':str(self.cat),'anio':str(date.today().year),
                        'mes':str(date.today().month),'monto_limite':'6000','id_moneda':str(self.crc)})
        d=db.dashboard(date.today().year,date.today().month)
        self.assertEqual(d['budgets'][0]['gastado'],500000)
        self.assertEqual(d['budgets'][0]['missing'],0)
