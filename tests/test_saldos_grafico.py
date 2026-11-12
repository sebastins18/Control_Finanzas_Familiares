"""Módulo «Evolución de saldos» del Resumen: historial diario por cuenta y rangos 1 semana / 1 mes / 3 meses."""
import json
import re
import unittest
from datetime import date, timedelta

from src import db, finance, request_ctx
from src.app import months_back
from tests.test_historial_reportes import HttpMixin
from tests.test_s3_normal import S3HttpBase


class MonthsBackTests(unittest.TestCase):
    def test_clamps_to_last_day_and_crosses_years(self):
        """Restar meses a una fecha ajusta al último día del mes y cruza de año correctamente."""
        self.assertEqual(months_back(date(2026, 3, 31), 1), date(2026, 2, 28))
        self.assertEqual(months_back(date(2024, 5, 31), 3), date(2024, 2, 29))
        self.assertEqual(months_back(date(2026, 1, 15), 1), date(2025, 12, 15))
        self.assertEqual(months_back(date(2026, 2, 10), 3), date(2025, 11, 10))
        self.assertEqual(months_back(date(2026, 11, 11), 3), date(2026, 8, 11))


class BalanceHistoryTests(HttpMixin, S3HttpBase):
    def setUp(self):
        super().setUp()
        request_ctx.set_profile(None)
        request_ctx.set_user_id(1)
        with db.connect() as c:
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=100000 WHERE id_cuenta=?', (self.account,))
            crc = c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            self.second = c.execute("INSERT INTO cuentas(id_perfil,nombre,saldo_inicial_centimos,id_moneda) VALUES(1,'Segunda',0,?)",
                                    (crc,)).lastrowid
            meta = c.execute("INSERT INTO metas_ahorro(id_perfil,id_moneda,nombre,monto_objetivo_centimos,fecha_objetivo) VALUES(1,?,'Meta',100000,'2030-01-01')",
                             (crc,)).lastrowid
            self.meta = meta

    def test_series_follow_movements_transfers_and_savings(self):
        """El historial diario de saldos incluye movimientos, transferencias y ahorros en el día correcto."""
        end = date(2026, 6, 30)
        start = end - timedelta(days=9)
        self.add('2026-06-01', 5000, 'Antes del rango')                            # entra en el saldo base
        self.add('2026-06-23', 20000, 'Salario', tipo='ingreso')
        self.add('2026-06-25', 3000, 'Compra')
        self.add('2026-07-02', 99999, 'Futuro')                                    # después del rango: no cuenta
        with db.connect() as c:
            c.execute('''INSERT INTO transferencias(id_perfil,id_cuenta_origen,id_cuenta_destino,monto_origen_centimos,monto_destino_centimos,fecha)
                VALUES(1,?,?,7000,7000,'2026-06-27')''', (self.account, self.second))
            c.execute("INSERT INTO movimientos_ahorro(id_meta,id_cuenta,tipo,monto_centimos,fecha) VALUES(?,?,'aporte',1000,'2026-06-28')",
                      (self.meta, self.account))
        history = finance.balance_history(start, end)
        self.assertEqual(history['fechas'][0], '2026-06-21')
        self.assertEqual(history['fechas'][-1], '2026-06-30')
        self.assertEqual(len(history['fechas']), 10)
        series = {a['id']: a['serie'] for a in history['cuentas']}
        main, second = series[self.account], series[self.second]
        self.assertEqual(main[0], 95000)                                             # 1000.00 inicial − 50.00 previo
        self.assertEqual(main[2], 115000)                                            # 23/6: +200.00
        self.assertEqual(main[4], 112000)                                            # 25/6: −30.00
        self.assertEqual(main[6], 105000)                                            # 27/6: transferencia −70.00
        self.assertEqual(main[7], 104000)                                            # 28/6: aporte de ahorro −10.00
        self.assertEqual(main[-1], 104000)
        self.assertEqual(second, [0] * 6 + [7000] * 4)
        self.assertNotIn('Futuro', json.dumps(history))

    def test_last_point_matches_current_balance(self):
        """El último punto del gráfico de saldos coincide con el saldo actual de cada cuenta."""
        today = date.today()
        self.add((today - timedelta(days=3)).isoformat(), 12345, 'Reciente')
        history = finance.balance_history(today - timedelta(days=7), today)
        with db.connect() as c:
            for account in history['cuentas']:
                self.assertEqual(account['serie'][-1], finance.account_balance(c, account['id']))

    def test_dashboard_panel_scoped_to_profile_and_escaped(self):
        """El gráfico de saldos solo usa cuentas del perfil activo y escapa los nombres."""
        self.other_profile()
        with db.connect() as c:
            c.execute("UPDATE cuentas SET nombre='Caja </script><b>x' WHERE id_cuenta=?", (self.second,))
        page = self.get('/')
        self.assertIn('Evolución de saldos', page)
        for value, label in (('1s', '1 semana'), ('1m', '1 mes'), ('3m', '3 meses')):
            self.assertIn(f'value="{value}"', page)
            self.assertIn(f'>{label}</label>', page)
        raw = re.search(r'<script type="application/json" id="saldos-datos">(.*?)</script>', page, re.S).group(1)
        self.assertNotIn('</script>', raw)
        data = json.loads(raw)
        today = date.today()
        self.assertEqual(data['fechas'][-1], today.isoformat())
        self.assertEqual(data['rangos'], {'1s': (today - timedelta(days=7)).isoformat(),
                                          '1m': months_back(today, 1).isoformat(),
                                          '3m': months_back(today, 3).isoformat()})
        self.assertEqual(data['fechas'][0], data['rangos']['3m'])
        names = [a['nombre'] for a in data['cuentas']]
        self.assertIn('Caja </script><b>x', names)
        self.assertNotIn('Ajena', names)


if __name__ == '__main__':
    unittest.main()
