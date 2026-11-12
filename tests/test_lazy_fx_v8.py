"""Pruebas actualizadas al modelo V17 de cambio manual sin API de divisas."""
from src import db, extension
from tests.helpers_multicurrency import MulticurrencyBase

class ManualFxTests(MulticurrencyBase):
    def test_same_currency_does_not_require_rate(self):
        """Entre cuentas de la misma moneda no se exige tipo de cambio."""
        with db.connect() as c:
            c.execute('INSERT INTO cuentas(id_perfil,nombre,id_moneda,saldo_inicial_centimos) VALUES(1,?,?,?)',('CRC test',self.crc,0))
            target=c.execute("SELECT id_cuenta FROM cuentas WHERE nombre='CRC test'").fetchone()[0]
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=10000 WHERE id_cuenta=?',(self.crc_account,))
        extension.save('transferencias',{'id_cuenta_origen':str(self.crc_account),
            'id_cuenta_destino':str(target),'monto_origen_centimos':'1',
            'fecha':self.today,'descripcion':'Igual moneda'})

    def test_cached_rate_still_requires_explicit_confirmation(self):
        """Aunque exista una cotización guardada, la transferencia entre monedas exige indicarla explícitamente."""
        with db.connect() as c:
            c.execute('INSERT INTO tipos_cambio(id_moneda_base,id_moneda_cotizada,fecha,cotizacion) VALUES(?,?,?,?)',
                      (self.usd,self.crc,self.today,'500'))
        with self.assertRaisesRegex(ValueError,'cotización'):
            extension.save('transferencias',{'id_cuenta_origen':str(self.usd_account),
                'id_cuenta_destino':str(self.crc_account),'monto_origen_centimos':'1',
                'fecha':self.today,'descripcion':'Requiere tasa explícita'})

    def test_manual_rate_converts_correctly(self):
        """La cotización manual convierte el monto con el redondeo correcto."""
        extension.save('transferencias',{'id_cuenta_origen':str(self.usd_account),
            'id_cuenta_destino':str(self.crc_account),'monto_origen_centimos':'1',
            'fecha':self.today,'descripcion':'Tipo manual','cotizacion':'500'})
        with db.connect() as c:
            row=c.execute('SELECT monto_destino_centimos FROM transferencias ORDER BY id_transferencia DESC LIMIT 1').fetchone()
            self.assertEqual(row[0],50000)
