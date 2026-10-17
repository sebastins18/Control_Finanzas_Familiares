"""Aplicación web mínima, construida solo con Python estándar y SQLite.

Uso local: python -m src.app
No se proporciona autenticación: NO desplegar en Internet sin añadirla.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from src import db

CSS_PATH = Path(__file__).with_name('static') / 'styles.css'


def currency(cents: int) -> str:
    amount = abs(int(cents))
    thousands, decimals = divmod(amount, 100)
    whole = f'{thousands:,}'.replace(',', '.')
    return f"{'−' if cents < 0 else ''}₡{whole},{decimals:02d}"


def e(value: object) -> str:
    return escape(str(value), quote=True)


def option_rows(rows, selected: int | None, kind: str | None = None) -> str:
    result = []
    for row in rows:
        if kind is not None and row['tipo'] != kind:
            continue
        selected_attr = ' selected' if selected == row[0] else ''
        class_attr = f' data-tipo="{e(row["tipo"])}"' if 'tipo' in row.keys() else ''
        result.append(f'<option value="{row[0]}"{class_attr}{selected_attr}>{e(row["nombre"])}</option>')
    return ''.join(result)


def layout(content: str, *, subtitle: str = '') -> str:
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finanzas Familiares · Grupo 5</title><link rel="stylesheet" href="/static/styles.css"></head>
<body><header class="topbar"><div class="shell top-inner"><div class="brand"><span class="brand-icon">₡</span><span><strong>Finanzas Familiares</strong><small>Proyecto open source · Grupo 5</small></span></div><span class="top-badge">SQLite · MVP local</span></div></header>
<main class="shell"><section class="hero"><div><p class="eyebrow">PANEL FINANCIERO</p><h1>Un panorama claro de tu dinero.</h1><p>Movimientos, presupuestos y alertas en una sola página. {e(subtitle)}</p></div><span class="hero-art" aria-hidden="true">↗</span></section>{content}</main>
<footer class="shell footer">Datos de demostración ficticios · Sin cuentas reales · UNA · II-2026</footer>
<script>
const tipo = document.getElementById('tipo'); const categoria = document.getElementById('id_categoria');
function filtrar(){{if(!tipo||!categoria)return; const all=[...categoria.options];
 let visible=all.filter(o=>o.dataset.tipo===tipo.value); for(const o of all)o.hidden=o.dataset.tipo!==tipo.value;
 if(!visible.includes(categoria.selectedOptions[0])&&visible.length)categoria.value=visible[0].value;}}
if(tipo){{tipo.addEventListener('change',filtrar);filtrar();}}
for(const b of document.querySelectorAll('[data-confirm]'))b.addEventListener('click',ev=>{{if(!confirm('¿Eliminar este movimiento?'))ev.preventDefault();}});
</script></body></html>'''


def dashboard_page(query: dict) -> str:
    today = date.today()
    try:
        year = int(query.get('anio', [today.year])[0]); month = int(query.get('mes', [today.month])[0])
        if not (2020 <= year <= 2100 and 1 <= month <= 12): raise ValueError
    except ValueError:
        year, month = today.year, today.month
    data = db.dashboard(year, month)
    movement_edit = None
    try:
        movement_edit = db.get_movement(int(query.get('editar', ['0'])[0]))
    except ValueError:
        pass
    categories, accounts = data['categories'], data['accounts']
    kind = movement_edit['tipo'] if movement_edit else 'gasto'
    cat_selected = movement_edit['id_categoria'] if movement_edit else None
    acc_selected = movement_edit['id_cuenta'] if movement_edit else accounts[0]['id_cuenta']
    amount = f"{movement_edit['monto_centimos']/100:.2f}" if movement_edit else ''
    tx_date = movement_edit['fecha'] if movement_edit else today.isoformat()
    description = movement_edit['descripcion'] if movement_edit else ''
    action = f'/movimientos/{movement_edit["id_movimiento"]}/actualizar' if movement_edit else '/movimientos'
    budget_html = ''
    for p in data['budgets']:
        pct = round(p['gastado'] / p['limite'] * 100) if p['limite'] else 0
        status = 'Excedido' if pct >= 100 else ('Cerca del límite' if pct >= 80 else 'Bajo control')
        status_class = 'danger' if pct >= 100 else ('warning' if pct >= 80 else 'ok')
        budget_html += f'''<div class="budget-line"><div class="budget-head"><strong>{e(p['categoria'])}</strong><span class="pill {status_class}">{status}</span></div>
        <div class="budget-values"><span>{currency(p['gastado'])} utilizados</span><span>de {currency(p['limite'])}</span></div>
        <div class="track"><div class="fill {status_class}" style="width:{min(pct,100)}%"></div></div></div>'''
    if not budget_html:
        budget_html = '<p class="muted">Todavía no se han definido presupuestos para este mes.</p>'
    rows = ''
    for tx in data['movements']:
        symbol = '+' if tx['tipo'] == 'ingreso' else '−'
        css_class = 'income' if tx['tipo'] == 'ingreso' else 'expense'
        desc = tx['descripcion'] or tx['categoria']
        rows += f'''<tr><td><strong>{e(desc)}</strong><small>{e(tx['categoria'])} · {e(tx['cuenta'])}</small></td>
        <td>{e(tx['fecha'])}</td><td class="amount {css_class}">{symbol}{currency(tx['monto_centimos'])}</td>
        <td class="actions"><a href="/?editar={tx['id_movimiento']}&anio={year}&mes={month}">Editar</a>
        <form method="post" action="/movimientos/{tx['id_movimiento']}/eliminar"><button class="link-danger" data-confirm="true" type="submit">Eliminar</button></form></td></tr>'''
    if not rows:
        rows = '<tr><td colspan="4" class="empty">Aún no hay movimientos en el período seleccionado.</td></tr>'
    balance = data['income'] - data['expense']
    content = f'''
    <form class="period" method="get"><label>Período <input type="month" name="periodo" value="{year:04d}-{month:02d}" aria-label="Mes de consulta" onchange="const a=this.value.split('-');document.getElementById('anio').value=a[0];document.getElementById('mes').value=Number(a[1]);this.form.submit()"></label>
    <input type="hidden" id="anio" name="anio" value="{year}"><input type="hidden" id="mes" name="mes" value="{month}"><button class="secondary" type="submit">Actualizar</button></form>
    <section class="metrics"><article class="metric"><span>Ingresos del mes</span><strong class="income">{currency(data['income'])}</strong><small>Movimientos registrados</small></article>
    <article class="metric"><span>Gastos del mes</span><strong class="expense">{currency(data['expense'])}</strong><small>Movimientos registrados</small></article>
    <article class="metric emphasized"><span>Balance del mes</span><strong>{currency(balance)}</strong><small>Ingresos menos gastos</small></article></section>
    <section class="columns"><article class="panel"><div class="panel-title"><div><p class="eyebrow">REGISTRO</p><h2>{'Editar movimiento' if movement_edit else 'Nuevo movimiento'}</h2></div>{'<a href="/">Cancelar</a>' if movement_edit else ''}</div>
    <form action="{action}" method="post" class="form-grid"><label>Tipo<select name="tipo" id="tipo"><option value="gasto" {'selected' if kind=='gasto' else ''}>Gasto</option><option value="ingreso" {'selected' if kind=='ingreso' else ''}>Ingreso</option></select></label>
    <label>Monto (CRC)<input name="monto" type="number" min="0.01" step="0.01" required value="{e(amount)}" placeholder="25000.00"></label>
    <label>Categoría<select name="id_categoria" id="id_categoria" required>{option_rows(categories, cat_selected)}</select></label>
    <label>Cuenta<select name="id_cuenta" required>{option_rows(accounts, acc_selected)}</select></label>
    <label>Fecha<input name="fecha" type="date" required value="{e(tx_date)}"></label>
    <label>Descripción<input name="descripcion" maxlength="160" value="{e(description)}" placeholder="Ej. Compras del supermercado"></label>
    <button type="submit" class="primary span2">{'Guardar cambios' if movement_edit else 'Agregar movimiento'}</button></form></article>
    <article class="panel"><div class="panel-title"><div><p class="eyebrow">CONTROL MENSUAL</p><h2>Presupuestos y alertas</h2></div></div>{budget_html}
    <div class="subform"><h3>Crear o actualizar límite</h3><form method="post" action="/presupuestos" class="form-grid"><label class="span2">Categoría<select name="id_categoria" required>{option_rows(categories, None, 'gasto')}</select></label>
    <label>Monto máximo (CRC)<input name="monto_limite" type="number" min="0.01" step="0.01" placeholder="50000.00" required></label>
    <input type="hidden" name="anio" value="{year}"><input type="hidden" name="mes" value="{month}"><button class="primary" type="submit">Guardar límite</button></form>
    <p class="help">Una alerta aparece al alcanzar el 80 % del presupuesto de una categoría.</p></div></article></section>
    <section class="panel table-panel"><div class="panel-title"><div><p class="eyebrow">HISTORIAL</p><h2>Movimientos del período</h2></div><span class="pill neutral">Últimos 100</span></div>
    <div class="table-scroll"><table><thead><tr><th>Descripción / categoría</th><th>Fecha</th><th>Monto</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="foot-note">Versión de seguimiento 1 · Prototipo local, con usuario de demostración y moneda CRC. No incluye autenticación, conversión de monedas ni metas de ahorro.</section>
    '''
    return layout(content, subtitle='Datos sintéticos para la demostración del curso.')


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, body: bytes, content_type: str = 'text/html; charset=utf-8') -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def redirect(self) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', '/')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path)
        try:
            if path.path == '/static/styles.css':
                return self.respond(200, CSS_PATH.read_bytes(), 'text/css; charset=utf-8')
            if path.path == '/health':
                with db.connect() as connection:
                    ver = connection.execute('SELECT sqlite_version()').fetchone()[0]
                    tables = connection.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"').fetchone()[0]
                return self.respond(200, json.dumps({'status':'ok','motor':'SQLite','version':ver,'tablas':tables}).encode(), 'application/json')
            if path.path in ('/', '/index.html'):
                query = parse_qs(path.query)
                return self.respond(200, dashboard_page(query).encode('utf-8'))
            return self.respond(404, layout('<section class="panel"><h2>Página no encontrada</h2><a href="/">Volver al inicio</a></section>').encode())
        except Exception as exc:
            print(f'GET error: {exc}')
            return self.respond(500, layout('<section class="panel"><h2>Error de lectura</h2><p>Verifique la conexión con SQLite.</p></section>').encode())

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        length = int(self.headers.get('Content-Length','0'))
        if length < 0 or length > 16_384:
            return self.respond(413, b'Formulario demasiado grande', 'text/plain; charset=utf-8')
        try:
            posted = parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=True)
            form = {key: vals[0] for key, vals in posted.items()}
            if path == '/movimientos':
                db.save_movement(form)
            elif path == '/presupuestos':
                db.save_budget(form)
            elif m := re.fullmatch(r'/movimientos/(\d+)/(actualizar|eliminar)', path):
                movement_id = int(m.group(1))
                if m.group(2) == 'actualizar': db.save_movement(form, movement_id)
                else: db.remove_movement(movement_id)
            else:
                return self.respond(404, b'Ruta no encontrada', 'text/plain; charset=utf-8')
            self.redirect()
        except (ValueError, UnicodeDecodeError) as exc:
            self.respond(400, layout(f'<section class="panel"><h2>Revise los datos</h2><p>{e(exc)}</p><p><a href="/">Volver al inicio</a></p></section>').encode('utf-8'))
        except Exception as exc:
            print(f'POST error: {exc}')
            self.respond(500, layout('<section class="panel"><h2>No se pudo guardar</h2><p>Ocurrió un error de base de datos.</p></section>').encode('utf-8'))


def main() -> None:
    parser = argparse.ArgumentParser(description='Finanzas Familiares - Grupo 5')
    parser.add_argument('--host', default='127.0.0.1', help='Escuchar solo en localhost por defecto')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    db.init_db()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Aplicación local: http://{args.host}:{args.port}/')
    print(f'Conexión SQLite: {db.db_path()}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nDeteniendo servidor...')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
