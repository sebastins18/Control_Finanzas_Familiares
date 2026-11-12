"""Resumen v2 (tarjetas, gastos por categoría, metas, variación mensual, estados vacíos, formato único)
y protección CSRF en todos los formularios POST con sesión."""
import re
import unittest
from datetime import date
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import db, finance
from src.app import variation_html
from tests.test_historial_reportes import HttpMixin
from tests.test_s3_normal import S3HttpBase


class FormatTests(unittest.TestCase):
    def test_single_money_format(self):
        self.assertEqual(finance.format_amount(572480000, '₡'), '₡5,724,800.00')
        self.assertEqual(finance.format_amount(-23690000, '₡'), '−₡236,900.00')
        self.assertEqual(finance.format_amount(0, '$'), '$0.00')

    def test_variation_text(self):
        self.assertIn('+20 % vs. mayo', variation_html(12000, 10000, 'mayo'))
        self.assertIn('▲', variation_html(12000, 10000, 'mayo'))
        self.assertIn('−50 % vs. mayo', variation_html(5000, 10000, 'mayo'))
        self.assertIn('igual que mayo', variation_html(100, 100, 'mayo'))
        self.assertIn('Sin registros en mayo', variation_html(100, 0, 'mayo'))
        self.assertEqual(variation_html(0, 0, 'mayo'), '')


class DashboardTests(HttpMixin, S3HttpBase):
    def page(self):
        return self.get('/?anio=2026&mes=6')

    def test_empty_states_and_compact_hero(self):
        html = self.page()
        self.assertIn('class="hero hero-compact"', html)
        self.assertIn('Un panorama claro de tu dinero.', html)
        self.assertIn('<span>Aún no hay movimientos en el período seleccionado.</span>', html)
        self.assertIn('Sin gastos registrados en junio 2026', html)
        self.assertIn('Aún no hay metas de ahorro en este perfil.', html)
        self.assertIn('Crear el primero ↓', html)
        self.assertIn('id="nuevo-limite"', html)

    def test_cards_categories_comparison_and_goals(self):
        with db.connect() as c:
            other = c.execute("INSERT INTO categorias(id_perfil,nombre,tipo) VALUES(1,'Taxis de prueba','gasto')").lastrowid
            crc = c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            meta = c.execute("INSERT INTO metas_ahorro(id_perfil,id_moneda,nombre,monto_objetivo_centimos,fecha_objetivo) VALUES(1,?,'Vacaciones',100000,'2030-01-01')",
                             (crc,)).lastrowid
            c.execute("INSERT INTO movimientos_ahorro(id_meta,id_cuenta,tipo,monto_centimos,fecha) VALUES(?,?,'aporte',40000,'2026-06-02')", (meta, self.account))
        self.add('2026-05-10', 10000, 'Gasto mayo')
        self.add('2026-06-10', 15000, 'Gasto junio')
        self.add('2026-06-11', 5000, 'Bus', category=other)
        self.add('2026-06-12', 200000, 'Salario', tipo='ingreso')
        html = self.page()
        self.assertIn('metrics-4', html)
        for label in ('Saldo total · CRC', 'Ingresos · CRC', 'Gastos · CRC', 'Neto del mes · CRC'):
            self.assertIn(label, html)
        self.assertIn('₡1,800.00', html)                  # neto de junio: 2000 − 150 − 50
        self.assertIn('Gastos por categoría', html)
        self.assertIn('Taxis de prueba', html)
        self.assertIn('₡150.00<small>75 %</small>', html)  # categoría principal: 150 de 200
        self.assertIn('+100 % vs. mayo', html)             # gastos: 200 frente a 100
        self.assertIn('Sin registros en mayo', html)       # ingresos: no hubo en mayo
        self.assertIn('Vacaciones', html)
        self.assertIn('₡400.00 de ₡1,000.00', html)
        self.assertIn('40 % · Faltan ₡600.00', html)
        self.assertIn('aria-valuenow="40"', html)
        self.assertIn('−₡150.00', html)                   # montos de la tabla con símbolo y signo
        self.assertIn('data-confirm="¿Eliminar este movimiento?"', html)


class CsrfTests(HttpMixin, S3HttpBase):
    def plain_client(self):
        """Mismo inicio de sesión que self.opener, pero sin agregar el token (como un sitio externo)."""
        jar = next(h.cookiejar for h in self.opener.handlers if isinstance(h, HTTPCookieProcessor))
        return build_opener(HTTPCookieProcessor(jar))

    def form(self):
        return {'tipo': 'gasto', 'id_categoria': str(self.category), 'id_cuenta': str(self.account),
                'monto': '10.00', 'fecha': '2026-06-01', 'descripcion': 'CSRF'}

    def count(self):
        with db.connect() as c:
            return c.execute("SELECT COUNT(*) FROM movimientos WHERE descripcion='CSRF'").fetchone()[0]

    def test_every_post_form_carries_the_token(self):
        html = self.get('/')
        post_forms = re.findall(r'<form\b[^>]*method="post"[^>]*>', html)
        self.assertGreaterEqual(len(post_forms), 3)
        self.assertEqual(html.count('name="csrf"'), len(post_forms))
        login = build_opener().open(self.base + '/login', timeout=5).read().decode('utf-8')
        self.assertNotIn('name="csrf"', login)

    def test_post_without_or_with_wrong_token_is_rejected_and_saves_nothing(self):
        plain = self.plain_client()
        for extra in ({}, {'csrf': 'falso'}):
            with self.assertRaises(HTTPError) as caught:
                plain.open(Request(self.base + '/movimientos', data=urlencode({**self.form(), **extra}).encode()), timeout=5)
            self.assertEqual(caught.exception.code, 403)
        self.assertEqual(self.count(), 0)
        self.post(self.form(), '/movimientos')            # con el token de la página
        self.assertEqual(self.count(), 1)

    def test_logout_requires_token(self):
        with self.assertRaises(HTTPError) as caught:
            self.plain_client().open(Request(self.base + '/logout', data=b''), timeout=5)
        self.assertEqual(caught.exception.code, 403)
        self.assertIn('Evolución de saldos', self.get('/'))  # la sesión sigue activa
        self.post({}, '/logout')
        self.assertIn('lg-form', self.get('/'))              # ahora redirige al login


if __name__ == '__main__':
    unittest.main()
