"""Consultas de lectura: historial filtrable y paginado, reporte anual y exportación CSV.

Todo es de solo lectura y está acotado al perfil financiero activo (current_profile_id()).
Los filtros llegan como parámetros SQL; ningún identificador SQL proviene de la solicitud.
Los montos nunca se suman entre monedas distintas.
"""
from __future__ import annotations

import csv
import io
from datetime import date
from html import escape
from urllib.parse import urlencode

from src import db

PAGE_SIZE = 25
MONTHS = ('Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic')
FILTER_KEYS = ('q', 'tipo', 'id_categoria', 'id_cuenta', 'desde', 'hasta')
# Fórmulas en hojas de cálculo: un texto que empieza así se neutraliza al exportar (OWASP CSV injection).
FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

BASE_FROM = '''FROM movimientos m
    JOIN categorias c ON c.id_categoria = m.id_categoria
    JOIN cuentas a ON a.id_cuenta = m.id_cuenta
    JOIN monedas mo ON mo.id_moneda = a.id_moneda'''


def h(value) -> str:
    return escape(str(value if value is not None else ''), quote=True)


def amount(cents: int) -> str:
    return f'{cents / 100:,.2f}'


# ---------------------------------------------------------------- filtros
def parse_filters(query: dict) -> dict:
    """Normaliza los parámetros GET. Lanza ValueError con un mensaje legible si son inválidos."""
    def first(key):
        return str(query.get(key, [''])[0]).strip()

    filters = {'q': first('q')[:80], 'tipo': first('tipo'), 'id_categoria': None, 'id_cuenta': None,
               'desde': first('desde'), 'hasta': first('hasta'), 'pagina': 1}
    if filters['tipo'] not in ('', 'ingreso', 'gasto'):
        raise ValueError('Tipo de movimiento no válido.')
    for key in ('id_categoria', 'id_cuenta'):
        raw = first(key)
        if raw:
            try:
                filters[key] = int(raw)
            except ValueError:
                raise ValueError('Filtro de categoría o cuenta no válido.') from None
    for key in ('desde', 'hasta'):
        if filters[key]:
            filters[key] = db.validate_date(filters[key])
    if filters['desde'] and filters['hasta'] and filters['desde'] > filters['hasta']:
        raise ValueError('La fecha inicial no puede ser posterior a la final.')
    try:
        filters['pagina'] = max(1, min(int(first('pagina') or 1), 100_000))
    except ValueError:
        filters['pagina'] = 1
    return filters


def _where(filters: dict) -> tuple[str, list]:
    clauses, params = ['m.id_perfil = current_profile_id()'], []
    if filters['q']:
        pattern = '%' + filters['q'].replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        clauses.append("(m.descripcion LIKE ? ESCAPE '\\' OR c.nombre LIKE ? ESCAPE '\\')")
        params += [pattern, pattern]
    if filters['tipo']:
        clauses.append('m.tipo = ?')
        params.append(filters['tipo'])
    if filters['id_categoria'] is not None:
        clauses.append('m.id_categoria = ?')
        params.append(filters['id_categoria'])
    if filters['id_cuenta'] is not None:
        clauses.append('m.id_cuenta = ?')
        params.append(filters['id_cuenta'])
    if filters['desde']:
        clauses.append('m.fecha >= ?')
        params.append(filters['desde'])
    if filters['hasta']:
        clauses.append('m.fecha <= ?')
        params.append(filters['hasta'])
    return ' WHERE ' + ' AND '.join(clauses), params


def query_string(filters: dict, **changes) -> str:
    values = {k: filters.get(k) for k in FILTER_KEYS}
    values.update(changes)
    return urlencode({k: v for k, v in values.items() if v not in (None, '')})


# ---------------------------------------------------------------- historial
def history(filters: dict) -> dict:
    where, params = _where(filters)
    with db.connect() as c:
        total = c.execute(f'SELECT COUNT(*) {BASE_FROM}{where}', params).fetchone()[0]
        pages = max(1, -(-total // PAGE_SIZE))
        page = min(filters['pagina'], pages)
        rows = c.execute(f'''SELECT m.id_movimiento, m.fecha, m.tipo, m.monto_centimos, m.descripcion,
                c.nombre AS categoria, a.nombre AS cuenta, mo.codigo_iso AS moneda
            {BASE_FROM}{where}
            ORDER BY m.fecha DESC, m.id_movimiento DESC LIMIT ? OFFSET ?''',
            [*params, PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
        sums = c.execute(f'''SELECT mo.codigo_iso AS moneda, m.tipo, SUM(m.monto_centimos) AS total
            {BASE_FROM}{where} GROUP BY mo.codigo_iso, m.tipo ORDER BY mo.codigo_iso''', params).fetchall()
        categories = c.execute('SELECT id_categoria, nombre, tipo FROM categorias WHERE id_perfil = current_profile_id() ORDER BY tipo, nombre').fetchall()
        accounts = c.execute('SELECT id_cuenta, nombre FROM cuentas WHERE id_perfil = current_profile_id() ORDER BY nombre').fetchall()
    totals = {}
    for r in sums:
        totals.setdefault(r['moneda'], {'ingreso': 0, 'gasto': 0})[r['tipo']] = r['total']
    return dict(rows=rows, total=total, page=page, pages=pages, totals=totals,
                categories=categories, accounts=accounts)


def _options(rows, key, selected, placeholder):
    html = f'<option value="">{h(placeholder)}</option>'
    for r in rows:
        label = f"{r['nombre']} ({r['tipo']})" if 'tipo' in r.keys() else r['nombre']
        html += f'<option value="{r[key]}"{" selected" if r[key] == selected else ""}>{h(label)}</option>'
    return html


def _active_filters(filters: dict, data: dict) -> str:
    """Etiquetas de los filtros aplicados; cada una es un enlace que quita solo ese filtro (solo lectura)."""
    names = {'ingreso': 'Ingresos', 'gasto': 'Gastos'}
    category = next((r['nombre'] for r in data['categories'] if r['id_categoria'] == filters['id_categoria']), None)
    account = next((r['nombre'] for r in data['accounts'] if r['id_cuenta'] == filters['id_cuenta']), None)
    chips = []
    if filters['q']:
        chips.append((f'“{filters["q"]}”', query_string(filters, q='')))
    if filters['tipo']:
        chips.append((names[filters['tipo']], query_string(filters, tipo='')))
    if category:
        chips.append((category, query_string(filters, id_categoria='')))
    if account:
        chips.append((account, query_string(filters, id_cuenta='')))
    if filters['desde'] or filters['hasta']:
        chips.append((f'{filters["desde"] or "…"} → {filters["hasta"] or "…"}', query_string(filters, desde='', hasta='')))
    if not chips:
        return ''
    close = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
             'stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"></path></svg>')
    links = ''.join(f'<a class="chip" href="/historial?{h(qs)}" aria-label="Quitar filtro: {h(text)}">{h(text)}{close}</a>' for text, qs in chips)
    return f'<div class="active-filters"><span>Filtros activos:</span>{links}</div>'


def history_page(query: dict, notice: str = '') -> str:
    filters = parse_filters(query)
    data = history(filters)
    kinds = ''.join(f'<input type="radio" id="h-tipo-{v or "todos"}" name="tipo" value="{v}"{" checked" if filters["tipo"] == v else ""}>'
                    f'<label for="h-tipo-{v or "todos"}">{n}</label>'
                    for v, n in (('', 'Todos'), ('ingreso', 'Ingresos'), ('gasto', 'Gastos')))
    search_icon = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5b6b82" stroke-width="2" '
                   'stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>')
    form = f'''<form class="form-card" method="get" action="/historial" role="search"><div class="filters-grid">
      <div class="field field-search"><label for="h-q">Buscar</label><div class="input-icon">{search_icon}<input id="h-q" type="search" name="q" maxlength="80" value="{h(filters['q'])}" placeholder="Descripción o categoría"></div></div>
      <fieldset class="field"><legend class="field-label">Tipo</legend><div class="segmented">{kinds}</div></fieldset>
      <div class="field"><label for="h-cat">Categoría</label><select id="h-cat" name="id_categoria">{_options(data['categories'], 'id_categoria', filters['id_categoria'], 'Todas')}</select></div>
      <div class="field"><label for="h-cta">Cuenta</label><select id="h-cta" name="id_cuenta">{_options(data['accounts'], 'id_cuenta', filters['id_cuenta'], 'Todas')}</select></div>
      <fieldset class="field"><legend class="field-label">Período</legend><div class="input-group range"><input type="date" name="desde" aria-label="Desde" value="{h(filters['desde'])}"><span class="sep" aria-hidden="true">→</span><input type="date" name="hasta" aria-label="Hasta" value="{h(filters['hasta'])}"></div></fieldset>
      </div>{_active_filters(filters, data)}
      <div class="form-actions"><p class="lead"><strong>{data['total']} movimiento{'s' if data['total'] != 1 else ''}</strong> con estos filtros</p>
      <a class="btn btn-ghost" href="/historial">Limpiar filtros</a><button class="btn btn-primary" type="submit">Aplicar filtros</button></div></form>'''
    rows = ''
    for r in data['rows']:
        sign, css = ('+', 'income') if r['tipo'] == 'ingreso' else ('−', 'expense')
        rows += (f'<tr><td data-label="Fecha">{h(r["fecha"])}</td>'
                 f'<td data-label="Descripción"><strong>{h(r["descripcion"] or r["categoria"])}</strong></td>'
                 f'<td data-label="Categoría">{h(r["categoria"])}</td><td data-label="Cuenta">{h(r["cuenta"])}</td>'
                 f'<td data-label="Monto" class="amount num {css}">{sign}{amount(r["monto_centimos"])} {h(r["moneda"])}</td></tr>')
    if not rows:
        rows = '<tr><td colspan="5" class="empty">No hay movimientos con estos filtros.</td></tr>'
    totals = ''.join(
        f'<tr><td>{h(code)}</td><td class="num">{amount(t["ingreso"])}</td><td class="num">{amount(t["gasto"])}</td>'
        f'<td class="num">{amount(t["ingreso"] - t["gasto"])}</td></tr>' for code, t in sorted(data['totals'].items()))
    totals_html = (f'<div class="table-scroll"><table><thead><tr><th>Moneda</th><th>Ingresos</th><th>Gastos</th><th>Balance</th></tr></thead><tbody>{totals}</tbody></table></div>'
                   if totals else '')
    pager = ''
    if data['pages'] > 1:
        prev_link = (f'<a class="btn btn-neutral btn-sm" href="/historial?{h(query_string(filters, pagina=data["page"] - 1))}">← Anterior</a>'
                     if data['page'] > 1 else '<span class="btn btn-ghost btn-sm" aria-disabled="true">← Anterior</span>')
        next_link = (f'<a class="btn btn-neutral btn-sm" href="/historial?{h(query_string(filters, pagina=data["page"] + 1))}">Siguiente →</a>'
                     if data['page'] < data['pages'] else '<span class="btn btn-ghost btn-sm" aria-disabled="true">Siguiente →</span>')
        pager = f'<nav class="pager" aria-label="Paginación">{prev_link}<span>Página {data["page"]} de {data["pages"]}</span>{next_link}</nav>'
    notice_html = f'<section class="notice-strip" role="status">{h(notice)}</section>' if notice else ''
    body = f'''{notice_html}<section class="panel"><p><a href="/">← Panel principal</a></p><div class="panel-title"><div><p class="eyebrow">CONSULTA</p><h2>Historial de movimientos</h2></div><a class="btn btn-neutral" href="/historial.csv?{h(query_string(filters))}">Exportar CSV</a></div>{form}</section>
    <section class="panel table-panel"><div class="panel-title"><div><p class="eyebrow">RESULTADOS</p><h2>{data['total']} movimiento{'s' if data['total'] != 1 else ''}</h2></div></div>
    {totals_html}
    <div class="table-scroll"><table class="records"><thead><tr><th>Fecha</th><th>Descripción</th><th>Categoría</th><th>Cuenta</th><th class="num">Monto</th></tr></thead><tbody>{rows}</tbody></table></div>{pager}</section>'''
    from src.app import layout
    return layout(body)


def _safe_cell(value) -> str:
    text = str(value if value is not None else '')
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def _csv_bytes(header, rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\r\n')
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe_cell(v) for v in row])
    # BOM UTF-8 para que Excel muestre bien las tildes; el resto de programas lo ignora.
    return buffer.getvalue().encode('utf-8-sig')


def history_csv(query: dict) -> bytes:
    filters = parse_filters(query)
    where, params = _where(filters)
    with db.connect() as c:
        rows = c.execute(f'''SELECT m.fecha, m.tipo, c.nombre, a.nombre, mo.codigo_iso,
                m.monto_centimos, m.descripcion
            {BASE_FROM}{where} ORDER BY m.fecha DESC, m.id_movimiento DESC''', params).fetchall()
    return _csv_bytes(('fecha', 'tipo', 'categoria', 'cuenta', 'moneda', 'monto', 'descripcion'),
                      ((r[0], r[1], r[2], r[3], r[4], f'{r[5] / 100:.2f}', r[6]) for r in rows))


# ---------------------------------------------------------------- reporte anual
def parse_year(query: dict) -> int:
    raw = str(query.get('anio', [''])[0]).strip()
    try:
        year = int(raw) if raw else date.today().year
    except ValueError:
        raise ValueError('Año no válido.') from None
    if not 2000 <= year <= 2100:
        raise ValueError('El año debe estar entre 2000 y 2100.')
    return year


def annual(year: int) -> dict:
    """{moneda: {tipo: {categoria: [12 montos]}}}. Usa el índice por fecha con un rango cerrado-abierto."""
    with db.connect() as c:
        rows = c.execute(f'''SELECT mo.codigo_iso AS moneda, m.tipo, c.nombre AS categoria,
                CAST(substr(m.fecha, 6, 2) AS INTEGER) AS mes, SUM(m.monto_centimos) AS total
            {BASE_FROM}
            WHERE m.id_perfil = current_profile_id() AND m.fecha >= ? AND m.fecha < ?
            GROUP BY mo.codigo_iso, m.tipo, c.nombre, mes''',
            (f'{year:04d}-01-01', f'{year + 1:04d}-01-01')).fetchall()
    report = {}
    for r in rows:
        months = report.setdefault(r['moneda'], {'ingreso': {}, 'gasto': {}})[r['tipo']].setdefault(r['categoria'], [0] * 12)
        months[r['mes'] - 1] += r['total']
    return report


def _sum_columns(groups) -> list:
    return [sum(values[i] for values in groups) for i in range(12)]


def annual_page(query: dict) -> str:
    year = parse_year(query)
    report = annual(year)
    head = '<th>Categoría</th>' + ''.join(f'<th class="num">{m}</th>' for m in MONTHS) + '<th class="num">Total</th>'

    def line(label, values, css=''):
        cells = ''.join(f'<td class="num">{amount(v) if v else "—"}</td>' for v in values)
        return f'<tr class="{css}"><td>{h(label)}</td>{cells}<td class="num"><strong>{amount(sum(values))}</strong></td></tr>'

    sections = ''
    for code in sorted(report):
        body = ''
        subtotals = {}
        for kind, title in (('ingreso', 'Ingresos'), ('gasto', 'Gastos')):
            categories = report[code][kind]
            if not categories:
                subtotals[kind] = [0] * 12
                continue
            body += f'<tr class="group-row"><th colspan="14">{title}</th></tr>'
            for name in sorted(categories):
                body += line(name, categories[name])
            subtotals[kind] = _sum_columns(categories.values())
            body += line(f'Total {title.lower()}', subtotals[kind], 'subtotal-row')
        balance = [i - g for i, g in zip(subtotals['ingreso'], subtotals['gasto'])]
        body += line('Balance', balance, 'subtotal-row')
        sections += (f'<section class="panel table-panel"><h2>{h(code)}</h2>'
                     f'<div class="table-scroll"><table class="records annual"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>')
    if not sections:
        sections = f'<section class="panel table-panel"><p class="empty">No hay movimientos registrados en {year}.</p></section>'
    nav = (f'<a class="btn btn-neutral btn-sm" href="/reportes/anual?anio={year - 1}">← {year - 1}</a>'
           f'<a class="btn btn-neutral btn-sm" href="/reportes/anual?anio={year + 1}">{year + 1} →</a>'
           f'<a class="btn btn-neutral btn-sm" href="/reportes/anual.csv?anio={year}">Exportar CSV</a>')
    body = f'''<section class="panel"><p><a href="/">← Panel principal</a></p><div class="panel-title"><div><p class="eyebrow">REPORTE</p><h2>Reporte anual por categoría · {year}</h2></div><div class="row-actions">{nav}</div></div>
    <p class="help">Totales mensuales por categoría, separados por moneda: los montos de monedas distintas no se suman.</p></section>{sections}'''
    from src.app import layout
    return layout(body)


def annual_csv(query: dict) -> bytes:
    year = parse_year(query)
    report = annual(year)
    rows = []
    for code in sorted(report):
        for kind in ('ingreso', 'gasto'):
            for name in sorted(report[code][kind]):
                values = report[code][kind][name]
                rows.append((year, code, kind, name, *(f'{v / 100:.2f}' for v in values), f'{sum(values) / 100:.2f}'))
    header = ('anio', 'moneda', 'tipo', 'categoria', *(m.lower() for m in MONTHS), 'total')
    return _csv_bytes(header, rows)
