"""Formularios rediseñados: se envían como lo haría un navegador y se verifica lo guardado en SQLite.

Un analizador HTML recorre el formulario real que genera la app y arma los datos en el orden del
documento: radios y casillas solo si están marcados, selects con su opción elegida y campos ocultos.
Así se comprueba que los controles nuevos (selector segmentado, interruptor, campo con − y +)
envían exactamente los nombres y valores que el servidor ya esperaba.
"""
import unittest
from html.parser import HTMLParser
from urllib.parse import urlencode

from src import db
from tests.test_historial_reportes import HttpMixin
from tests.test_s3_normal import S3HttpBase


class FormParser(HTMLParser):
    def __init__(self, action):
        super().__init__(convert_charrefs=True)
        self.action, self.inside, self.controls, self.select, self.options = action, False, [], None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form' and a.get('action') == self.action:
            self.inside = True
        if not self.inside:
            return
        if tag == 'input' and a.get('name'):
            kind = a.get('type', 'text')
            self.controls.append({'tag': 'input', 'type': kind, 'name': a['name'], 'value': a.get('value', 'on' if kind in ('checkbox', 'radio') else ''),
                                  'checked': 'checked' in a, 'attrs': a})
        elif tag == 'select' and a.get('name'):
            self.select = {'tag': 'select', 'name': a['name'], 'options': [], 'attrs': a}
            self.controls.append(self.select)
        elif tag == 'option' and self.select is not None:
            self.select['options'].append({'value': a.get('value', ''), 'selected': 'selected' in a, 'attrs': a})

    def handle_endtag(self, tag):
        if tag == 'select':
            self.select = None
        if tag == 'form' and self.inside:
            self.inside = False

    def find(self, name, **match):
        return [c for c in self.controls if c['name'] == name and all(c.get(k) == v for k, v in match.items())]

    def payload(self):
        """Pares (nombre, valor) en orden de documento, como serializa un navegador."""
        pairs = []
        for c in self.controls:
            if c['tag'] == 'select':
                chosen = next((o for o in c['options'] if o['selected']), c['options'][0] if c['options'] else None)
                if chosen is not None:
                    pairs.append((c['name'], chosen['value']))
            elif c['type'] in ('checkbox', 'radio'):
                if c['checked']:
                    pairs.append((c['name'], c['value']))
            else:
                pairs.append((c['name'], c['value']))
        return pairs

    # Acciones de la persona sobre el formulario
    def set(self, name, value):
        for c in self.find(name):
            if c['tag'] == 'select':
                for o in c['options']:
                    o['selected'] = o['value'] == str(value)
            elif c['type'] not in ('checkbox', 'radio', 'hidden'):
                c['value'] = str(value)

    def choose(self, name, value):
        for c in self.find(name, type='radio'):
            c['checked'] = c['value'] == value

    def tick(self, name, on):
        for c in self.find(name, type='checkbox'):
            c['checked'] = on


class FormsV2Tests(HttpMixin, S3HttpBase):
    def form(self, page, action):
        parser = FormParser(action)
        parser.feed(self.get(page))
        self.assertTrue(parser.controls, f'No se encontró el formulario {action} en {page}')
        return parser

    def send(self, parser, action):
        return self.post(parser.payload(), action)

    def test_movement_form_segmented_type_and_amount(self):
        f = self.form('/', '/movimientos')
        self.assertEqual({c['value'] for c in f.find('tipo', type='radio')}, {'gasto', 'ingreso'})
        self.assertEqual([c['value'] for c in f.find('tipo', type='radio') if c['checked']], ['gasto'])
        ingreso_cat = next(o['value'] for o in f.find('id_categoria')[0]['options'] if o['attrs'].get('data-tipo') == 'ingreso')
        f.choose('tipo', 'ingreso')
        f.set('id_categoria', ingreso_cat)
        f.set('monto', '1234.50')
        f.set('fecha', '2026-10-15')
        f.set('descripcion', 'Venta formulario v2')
        self.send(f, '/movimientos')
        with db.connect() as c:
            row = c.execute("SELECT tipo, monto_centimos, id_categoria, fecha FROM movimientos WHERE descripcion='Venta formulario v2'").fetchone()
        self.assertEqual(tuple(row), ('ingreso', 123450, int(ingreso_cat), '2026-10-15'))

    def test_movement_edit_round_trip_keeps_values(self):
        self.add('2026-10-10', 98765, 'Para editar')
        with db.connect() as c:
            mid = c.execute("SELECT id_movimiento FROM movimientos WHERE descripcion='Para editar'").fetchone()[0]
        f = self.form(f'/?editar={mid}&anio=2026&mes=10', f'/movimientos/{mid}/actualizar')
        self.assertEqual(dict(f.payload())['monto'], '987.65')
        self.send(f, f'/movimientos/{mid}/actualizar')
        with db.connect() as c:
            row = c.execute('SELECT tipo, monto_centimos, fecha, descripcion FROM movimientos WHERE id_movimiento=?', (mid,)).fetchone()
        self.assertEqual(tuple(row), ('gasto', 98765, '2026-10-10', 'Para editar'))

    def test_recurring_form_switch_and_stepper(self):
        f = self.form('/admin/movimientos_recurrentes', '/admin/movimientos_recurrentes/guardar')
        self.assertEqual(f.find('dia_mes')[0]['attrs'].get('max'), '28')
        f.set('descripcion', 'Plantilla activa v2')
        f.choose('tipo', 'gasto')
        f.set('id_categoria', self.category)
        f.set('id_cuenta', self.account)
        f.set('monto_centimos', '350.25')
        f.set('dia_mes', '7')
        self.send(f, '/admin/movimientos_recurrentes/guardar')    # interruptor encendido por defecto
        f = self.form('/admin/movimientos_recurrentes', '/admin/movimientos_recurrentes/guardar')
        f.set('descripcion', 'Plantilla pausada v2')
        f.choose('tipo', 'gasto')
        f.set('id_categoria', self.category)
        f.set('id_cuenta', self.account)
        f.set('monto_centimos', '10')
        f.tick('activo', False)
        self.assertIn(('activo', '0'), f.payload())
        self.assertNotIn(('activo', '1'), f.payload())
        self.send(f, '/admin/movimientos_recurrentes/guardar')
        with db.connect() as c:
            rows = {r['descripcion']: (r['tipo'], r['monto_centimos'], r['dia_mes'], r['activo'])
                    for r in c.execute('SELECT * FROM movimientos_recurrentes')}
        self.assertEqual(rows['Plantilla activa v2'], ('gasto', 35025, 7, 1))
        self.assertEqual(rows['Plantilla pausada v2'], ('gasto', 1000, 1, 0))

    def test_recurring_edit_round_trip_and_switch_off(self):
        f = self.form('/admin/movimientos_recurrentes', '/admin/movimientos_recurrentes/guardar')
        f.set('descripcion', 'Alquiler v2')
        f.choose('tipo', 'gasto')
        f.set('id_categoria', self.category)
        f.set('id_cuenta', self.account)
        f.set('monto_centimos', '280000.00')
        f.set('dia_mes', '5')
        f.set('fecha_inicio', '2026-01-01')
        self.send(f, '/admin/movimientos_recurrentes/guardar')
        with db.connect() as c:
            before = dict(c.execute("SELECT * FROM movimientos_recurrentes WHERE descripcion='Alquiler v2'").fetchone())
        rid = before['id_recurrente']
        f = self.form(f'/admin/movimientos_recurrentes?editar={rid}', f'/admin/movimientos_recurrentes/{rid}/guardar')
        self.send(f, f'/admin/movimientos_recurrentes/{rid}/guardar')          # sin cambios: idéntico
        with db.connect() as c:
            self.assertEqual(dict(c.execute('SELECT * FROM movimientos_recurrentes WHERE id_recurrente=?', (rid,)).fetchone()), before)
        f = self.form(f'/admin/movimientos_recurrentes?editar={rid}', f'/admin/movimientos_recurrentes/{rid}/guardar')
        f.tick('activo', False)
        self.send(f, f'/admin/movimientos_recurrentes/{rid}/guardar')
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT activo FROM movimientos_recurrentes WHERE id_recurrente=?', (rid,)).fetchone()[0], 0)

    def test_savings_movement_segmented_aporte_retiro(self):
        with db.connect() as c:
            crc = c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            c.execute('UPDATE cuentas SET saldo_inicial_centimos=1000000 WHERE id_cuenta=?', (self.account,))
            meta = c.execute("INSERT INTO metas_ahorro(id_perfil,id_moneda,nombre,monto_objetivo_centimos,fecha_objetivo) VALUES(1,?,'Meta v2',500000,'2027-01-01')", (crc,)).lastrowid
        f = self.form('/admin/movimientos_ahorro', '/admin/movimientos_ahorro/guardar')
        self.assertEqual({c['value'] for c in f.find('tipo', type='radio')}, {'aporte', 'retiro'})
        f.set('id_meta', meta)
        f.set('id_cuenta', self.account)
        f.set('monto_centimos', '150.00')
        self.send(f, '/admin/movimientos_ahorro/guardar')
        with db.connect() as c:
            self.assertEqual(tuple(c.execute('SELECT tipo, monto_centimos FROM movimientos_ahorro WHERE id_meta=?', (meta,)).fetchone()), ('aporte', 15000))

    def test_history_filter_form_round_trip(self):
        self.add('2026-02-03', 5000, 'Supermercado v2')
        self.add('2026-02-04', 7000, 'Otra cosa')
        f = self.form('/historial', '/historial')
        f.set('q', 'Supermercado v2')
        f.choose('tipo', 'gasto')
        f.set('desde', '2026-02-01')
        f.set('hasta', '2026-02-28')
        html = self.get('/historial?' + urlencode(f.payload()))
        self.assertIn('1 movimiento<', html)
        self.assertIn('Quitar filtro: “Supermercado v2”', html)
        # Quitar una etiqueta conserva los demás filtros.
        self.assertIn('href="/historial?tipo=gasto&amp;desde=2026-02-01&amp;hasta=2026-02-28"', html)

    def test_alert_switch_marks_read(self):
        with db.connect() as c:
            crc = c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            budget = c.execute('INSERT INTO presupuestos(id_perfil,id_categoria,anio,mes,monto_limite_centimos,id_moneda) VALUES(1,?,2026,10,100000,?)', (self.category, crc)).lastrowid
        f = self.form('/admin/alertas', '/admin/alertas/guardar')
        f.set('id_presupuesto', budget)
        f.set('umbral', '80')
        f.tick('leida', True)
        self.send(f, '/admin/alertas/guardar')
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT leida FROM alertas WHERE id_presupuesto=? AND umbral=80', (budget,)).fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
