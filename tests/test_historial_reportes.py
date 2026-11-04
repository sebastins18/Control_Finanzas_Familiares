"""Historial filtrable y paginado, reporte anual, exportación CSV y movimientos recurrentes.

Servidor HTTP real con sesión de propietario sobre una base temporal (reutiliza S3HttpBase).
"""
import unittest
from datetime import date
from urllib.error import HTTPError

from src import db, recurrentes, request_ctx
from tests.test_s3_normal import S3HttpBase


class HttpMixin:
    def get(self, path):
        with self.opener.open(self.base + path, timeout=5) as r:
            return r.read().decode('utf-8-sig')

    def get_raw(self, path):
        with self.opener.open(self.base + path, timeout=5) as r:
            return r.headers, r.read()

    def status(self, path):
        try:
            with self.opener.open(self.base + path, timeout=5) as r:
                return r.status
        except HTTPError as exc:
            return exc.code

    def add(self, fecha, monto_centimos, descripcion, tipo='gasto', category=None, account=None):
        with db.connect() as c:
            if category is None:
                category = c.execute('SELECT id_categoria FROM categorias WHERE id_perfil=1 AND tipo=? ORDER BY id_categoria LIMIT 1', (tipo,)).fetchone()[0]
            c.execute('''INSERT INTO movimientos(id_perfil,id_cuenta,id_categoria,tipo,monto_centimos,fecha,descripcion)
                VALUES(1,?,?,?,?,?,?)''', (account or self.account, category, tipo, monto_centimos, fecha, descripcion))

    def other_profile(self):
        """Usuario ajeno con su propio perfil y un movimiento que nunca debe aparecer."""
        with db.connect() as c:
            uid = c.execute("INSERT INTO usuarios(nombre,username,rol,activo,password_salt,password_hash) VALUES('Otro','otro','usuario',1,'00','00')").lastrowid
            pid = c.execute('INSERT INTO perfiles_financieros(nombre,id_propietario) VALUES(?,?)', ('Ajeno', uid)).lastrowid
            cat = c.execute("INSERT INTO categorias(id_perfil,nombre,tipo) VALUES(?,'Secreta','gasto')", (pid,)).lastrowid
            acc = c.execute("INSERT INTO cuentas(id_perfil,nombre,id_moneda) VALUES(?,'Ajena',(SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'))", (pid,)).lastrowid
            c.execute('''INSERT INTO movimientos(id_perfil,id_cuenta,id_categoria,tipo,monto_centimos,fecha,descripcion)
                VALUES(?,?,?,'gasto',99900,'2026-03-10','SECRETO ajeno')''', (pid, acc, cat))


class HistoryTests(HttpMixin, S3HttpBase):
    def test_pagination_and_filters(self):
        for i in range(30):
            self.add(f'2026-02-{i % 28 + 1:02d}', 1000 + i, f'Compra {i:02d}')
        self.add('2026-05-01', 500000, 'Salario mayo', tipo='ingreso')
        page1 = self.get('/historial')
        self.assertIn('31 movimientos', page1)
        self.assertIn('Página 1 de 2', page1)
        self.assertIn('Página 2 de 2', self.get('/historial?pagina=2'))
        # Página fuera de rango: se ajusta a la última en vez de fallar.
        self.assertIn('Página 2 de 2', self.get('/historial?pagina=999'))
        only = self.get('/historial?q=Compra+07')
        self.assertIn('1 movimiento<', only)
        self.assertIn('Compra 07', only)
        self.assertIn('1 movimiento<', self.get('/historial?tipo=ingreso'))
        self.assertIn('1 movimiento<', self.get('/historial?desde=2026-05-01&hasta=2026-05-31'))

    def test_like_wildcards_are_literal(self):
        self.add('2026-02-01', 1000, 'Descuento 50%')
        self.add('2026-02-02', 1000, 'Descuento 500')
        self.assertIn('1 movimiento<', self.get('/historial?q=50%25'))

    def test_invalid_filters_return_400_with_reason(self):
        self.assertEqual(self.status('/historial?desde=2026-13-01'), 400)
        self.assertEqual(self.status('/historial?desde=2026-05-01&hasta=2026-01-01'), 400)
        self.assertEqual(self.status('/historial?tipo=otro'), 400)
        self.assertEqual(self.status('/reportes/anual?anio=1999'), 400)

    def test_csv_export_respects_filters_and_neutralizes_formulas(self):
        self.add('2026-02-01', 123456, '=HYPERLINK("http://x")')
        self.add('2026-03-01', 1000, 'Fuera del rango')
        headers, raw = self.get_raw('/historial.csv?desde=2026-02-01&hasta=2026-02-28')
        self.assertTrue(headers['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        text = raw.decode('utf-8-sig')
        self.assertTrue(text.startswith('fecha,tipo,categoria,cuenta,moneda,monto,descripcion'))
        self.assertIn('1234.56', text)
        self.assertIn("'=HYPERLINK", text)
        self.assertNotIn('Fuera del rango', text)

    def test_other_profiles_never_appear(self):
        self.other_profile()
        self.assertIn('0 movimientos', self.get('/historial?q=SECRETO'))
        self.assertNotIn('SECRETO', self.get('/historial.csv'))
        self.assertNotIn('Secreta', self.get('/reportes/anual?anio=2026'))


class AnnualReportTests(HttpMixin, S3HttpBase):
    def test_monthly_totals_by_category_and_currency(self):
        self.add('2026-01-05', 10000, 'Ene a')
        self.add('2026-01-20', 2550, 'Ene b')
        self.add('2026-12-31', 5000, 'Dic')
        self.add('2025-12-31', 777700, 'Año anterior')
        with db.connect() as c:
            usd_account = c.execute("INSERT INTO cuentas(id_perfil,nombre,id_moneda) VALUES(1,'Dólares',(SELECT id_moneda FROM monedas WHERE codigo_iso='USD'))").lastrowid
        self.add('2026-01-10', 4200, 'En dólares', account=usd_account)
        report = self.get('/reportes/anual?anio=2026')
        self.assertIn('Reporte anual por categoría · 2026', report)
        self.assertIn('125.50', report)      # 100.00 + 25.50 en enero
        self.assertIn('175.50', report)      # total anual CRC de la categoría
        self.assertIn('<h2>USD</h2>', report)
        self.assertNotIn('7,777.00', report)  # 2025 queda fuera
        csv_text = self.get('/reportes/anual.csv?anio=2026')
        lines = csv_text.strip().splitlines()
        self.assertTrue(lines[0].startswith('anio,moneda,tipo,categoria,ene,feb'))
        crc = next(line for line in lines if ',CRC,gasto,' in line)
        self.assertTrue(crc.startswith('2026,CRC,gasto,'))
        self.assertTrue(crc.endswith(',175.50'))
        self.assertTrue(any(',USD,gasto,' in line and line.endswith(',42.00') for line in lines))

    def test_empty_year(self):
        self.assertIn('No hay movimientos registrados en 2031', self.get('/reportes/anual?anio=2031'))


class RecurringTests(HttpMixin, S3HttpBase):
    def template(self, **changes):
        form = {'descripcion': 'Alquiler', 'tipo': 'gasto', 'id_categoria': self.category, 'id_cuenta': self.account,
                'monto_centimos': '350000.00', 'dia_mes': '5', 'fecha_inicio': '2026-01-01', 'activo': '1'}
        form.update(changes)
        return form

    def count(self, description='Alquiler'):
        with db.connect() as c:
            return c.execute('SELECT COUNT(*) FROM movimientos WHERE descripcion=?', (description,)).fetchone()[0]

    def test_generation_is_idempotent_and_respects_deleted_movements(self):
        self.post(self.template(), '/admin/movimientos_recurrentes/guardar')
        request_ctx.set_user_id(1)
        self.assertEqual(recurrentes.generate(today=date(2026, 3, 4)), (2, 0))   # ene y feb; el 5 de marzo aún no llega
        self.assertEqual(recurrentes.generate(today=date(2026, 3, 4)), (0, 0))
        self.assertEqual(recurrentes.generate(today=date(2026, 3, 5)), (1, 0))
        with db.connect() as c:
            dates = [r[0] for r in c.execute("SELECT fecha FROM movimientos WHERE descripcion='Alquiler' ORDER BY fecha")]
            self.assertEqual(dates, ['2026-01-05', '2026-02-05', '2026-03-05'])
            c.execute("DELETE FROM movimientos WHERE fecha='2026-02-05' AND descripcion='Alquiler'")
        self.assertEqual(recurrentes.generate(today=date(2026, 3, 5)), (0, 0))
        self.assertEqual(self.count(), 2)

    def test_http_flow_and_inactive_templates(self):
        self.post(self.template(fecha_inicio=date.today().replace(day=1).isoformat(), dia_mes='1'), '/admin/movimientos_recurrentes/guardar')
        self.post(self.template(descripcion='Pausado', activo='0', dia_mes='1'), '/admin/movimientos_recurrentes/guardar')
        self.assertIn('Generar pendientes', self.get('/admin/movimientos_recurrentes'))
        self.assertIn('movimientos recurrentes pendientes', self.get('/'))
        result = self.post({}, '/recurrentes/generar')
        self.assertIn('Se generaron 1 movimientos recurrentes', result)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.count('Pausado'), 0)
        self.post({}, '/recurrentes/generar')
        self.assertEqual(self.count(), 1)

    def test_invalid_templates_are_rejected(self):
        for changes in ({'dia_mes': '31'}, {'tipo': 'ingreso'}, {'fecha_inicio': '1990-01-01'}):
            with self.assertRaises(HTTPError) as ctx:
                self.post(self.template(**changes), '/admin/movimientos_recurrentes/guardar')
            self.assertEqual(ctx.exception.code, 400)
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM movimientos_recurrentes').fetchone()[0], 0)

    def test_database_enforces_one_occurrence_per_period(self):
        self.post(self.template(), '/admin/movimientos_recurrentes/guardar')
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with db.connect() as c:
                rid = c.execute('SELECT id_recurrente FROM movimientos_recurrentes').fetchone()[0]
                c.execute("INSERT INTO recurrentes_generados(id_recurrente,periodo) VALUES(?, '2026-01')", (rid,))
                c.execute("INSERT INTO recurrentes_generados(id_recurrente,periodo) VALUES(?, '2026-01')", (rid,))


if __name__ == '__main__':
    unittest.main()
