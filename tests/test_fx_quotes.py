"""Cotización legible, dirección automática e historial inmutable."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src import app, db, extension, finance, request_ctx


class FxQuoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DB_PATH':str(Path(self.tmp.name)/'test.sqlite3')})
        self.env.start();request_ctx.set_user_id(1);db.init_db()
        self.today=date.today().isoformat()
        with db.connect() as c:
            self.crc=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            self.usd=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='USD'").fetchone()[0]
            self.origin=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=1 LIMIT 1').fetchone()[0]
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=100000000 WHERE id_cuenta=?',(self.origin,))
            self.target=c.execute("INSERT INTO cuentas(id_perfil,nombre,id_moneda,saldo_inicial_centimos) VALUES(1,'Dólares',?,100000)",(self.usd,)).lastrowid

    def tearDown(self):
        request_ctx.set_user_id(1);self.env.stop();self.tmp.cleanup()

    def form(self,quote='460',amount='100000'):
        return dict(id_cuenta_origen=str(self.origin),id_cuenta_destino=str(self.target),
                    monto_origen_centimos=amount,fecha=self.today,descripcion='Cotización de prueba',cotizacion=quote)

    def test_100000_colones_to_dollars_stores_the_original_460_quote(self):
        extension.save('transferencias',self.form())
        with db.connect() as c:
            row=c.execute('SELECT * FROM transferencias').fetchone()
            quote=c.execute('SELECT * FROM tipos_cambio').fetchone()
            self.assertEqual(row['monto_destino_centimos'],21739)
            self.assertEqual(quote['cotizacion'],'460.00')
            self.assertEqual((quote['id_moneda_base'],quote['id_moneda_cotizada']),(self.usd,self.crc))
            self.assertEqual(finance.conversion(c,self.crc,self.usd,10000000,self.today,row['id_tipo_cambio']),21739)
            self.assertEqual(finance.historical_conversion(c,self.crc,self.usd,10000000,self.today),21739)
        html=extension.page('transferencias')
        self.assertIn('1 USD = 460,00 CRC',html)

    def test_100_dollars_to_colones_uses_the_same_460_quote(self):
        form=self.form(amount='100')
        form.update(id_cuenta_origen=str(self.target),id_cuenta_destino=str(self.origin))
        extension.save('transferencias',form)
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT monto_destino_centimos FROM transferencias').fetchone()[0],4600000)
            self.assertEqual(c.execute('SELECT cotizacion FROM tipos_cambio').fetchone()[0],'460.00')

    def test_later_quote_does_not_modify_an_existing_transfer(self):
        extension.save('transferencias',self.form())
        extension.save('transferencias',self.form('500',amount='50000'))
        with db.connect() as c:
            quotes=c.execute('SELECT cotizacion FROM tipos_cambio ORDER BY id_tipo_cambio').fetchall()
            self.assertEqual([r[0] for r in quotes],['460.00','500.00'])
            transfers=c.execute('SELECT * FROM transferencias ORDER BY id_transferencia').fetchall()
            self.assertNotEqual(transfers[0]['id_tipo_cambio'],transfers[1]['id_tipo_cambio'])
            self.assertEqual(finance.conversion(c,self.crc,self.usd,10000000,self.today,transfers[0]['id_tipo_cambio']),21739)
            self.assertEqual(finance.historical_conversion(c,self.crc,self.usd,10000000,self.today),20000)

    def test_invalid_quotes_and_unrepresentable_amounts_do_not_write(self):
        forms=[self.form(v) for v in ('','0','-1','NaN','Infinity','0.0021739130434783','460.123','1000000001','abc')]
        forms.append(self.form('1000000000',amount='0.01'))
        for form in forms:
            with self.subTest(form=form):
                with self.assertRaises(ValueError):extension.save('transferencias',form)
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM transferencias').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tipos_cambio').fetchone()[0],0)

    def test_same_currency_needs_no_quote(self):
        with db.connect() as c:
            target=c.execute("SELECT id_cuenta FROM cuentas WHERE nombre='Efectivo' AND id_perfil=1").fetchone()[0]
        form=self.form(amount='100');form.pop('cotizacion');form['id_cuenta_destino']=str(target)
        extension.save('transferencias',form)
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT monto_destino_centimos FROM transferencias').fetchone()[0],10000)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tipos_cambio').fetchone()[0],0)

    def test_insufficient_funds_roll_back_the_quote_too(self):
        with self.assertRaisesRegex(ValueError,'Fondos insuficientes'):
            extension.save('transferencias',self.form(amount='2000000'))
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tipos_cambio').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM transferencias').fetchone()[0],0)

    def test_form_only_asks_for_the_quote_and_schema_has_no_directional_factor(self):
        html=extension.page('transferencias')
        self.assertIn('name="cotizacion"',html)
        for removed in ('operacion_cambio','tipo_cambio_manual','16 decimales','step="any"'):
            self.assertNotIn(removed,html)
        with db.connect() as c:
            columns={r['name'] for r in c.execute('PRAGMA table_info(tipos_cambio)')}
            self.assertEqual(columns,{'id_tipo_cambio','id_perfil','id_moneda_base','id_moneda_cotizada','fecha','cotizacion'})
