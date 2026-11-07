"""E2E real y grabación local. Nunca acepta URL ni DB externas como destino de escritura."""
from __future__ import annotations

import argparse
import csv
import html
import importlib.metadata
import io
import json
import logging
import os
from pathlib import Path
import platform
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TZ = timezone(timedelta(hours=-6), 'America/Costa_Rica')
EXPECTED_SHOTS = ['01_login', '02_dashboard', '03_crear_ingreso', '04_crear_gasto',
                  '05_editar_movimiento', '06_eliminar_movimiento', '07_presupuestos',
                  '08_alerta_80', '09_alerta_100', '10_historial', '11_reporte_anual',
                  '12_validacion_error']
CASES = [
 ('E01', 'Ruta protegida sin sesión redirige al login', 'S3,S4'),
 ('E02', 'Login, selección de perfil y redirecciones', 'S2,S4'),
 ('E03', 'Dashboard inicial sin movimientos', 'S1,S4'),
 ('E04', 'Navegación por menú y consulta de cuentas', 'S2,S4'),
 ('E05', 'Crear categoría desde formulario', 'S2'),
 ('E06', 'Editar categoría y verificar SQLite', 'S2,S3'),
 ('E07', 'Eliminar categoría sin referencias', 'S2,S3'),
 ('E08', 'Crear categoría exclusiva de presupuesto', 'S2'),
 ('E09', 'Crear ingreso: interfaz y SQLite', 'S2,S3'),
 ('E10', 'Crear gasto: interfaz y SQLite', 'S2,S3'),
 ('E11', 'Editar gasto: interfaz y SQLite', 'S2,S3'),
 ('E12', 'Eliminar gasto y comprobar ausencia', 'S2,S3'),
 ('E13', 'Crear presupuesto CRC 100.00', 'S2,S4'),
 ('E14', 'Alerta al 80 %: importe, estado y SQLite', 'S2,S3,S4'),
 ('E15', 'Alerta al 100 %: importe, estado y SQLite', 'S2,S3,S4'),
 ('E16', 'Consultar alertas persistidas desde menú', 'S2,S4'),
 ('E17', 'Historial sin filtros y totales', 'S2,S3'),
 ('E18', 'Filtrar descripción, tipo, categoría, cuenta y fechas', 'S2,S3'),
 ('E19', 'Descargar CSV filtrado y contrastar con SQLite', 'S3,S4'),
 ('E20', 'Reporte anual y totales por categoría', 'S3,S4'),
 ('E21', 'Descargar CSV anual y contrastar con SQLite', 'S3,S4'),
 ('E22', 'Monto negativo bloqueado por validación HTML', 'S3'),
 ('E23', 'Monto negativo: respuesta 400 sin escritura', 'S3'),
 ('E24', 'Filtro de fechas inválido: respuesta 400', 'S3'),
 ('E25', 'Usuario estándar: administración y calidad devuelven 403', 'S3,S4'),
 ('E26', 'Cerrar sesión e impedir volver a ruta protegida', 'S3,S4'),
 ('E27', 'SQLite final: integridad, FK, WAL y totales', 'S1,S3,S4'),
]


def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                                    *args], cwd=ROOT, text=True).strip()


class Run:
    def __init__(self, out, pace):
        self.out, self.pace = out, pace
        self.results, self.scenes = [], []
        self.started = time.monotonic()
        self.page = None
        self.password = ''

    def safe(self, value):
        text = str(value).replace(self.password, '[REDACTADO]') if self.password else str(value)
        return text.replace(str(ROOT), '<repositorio>')

    def step(self, case, action):
        ident, title, req = case
        start = time.monotonic()
        try:
            detail = action() or 'Comprobaciones completadas.'
        except Exception as exc:
            self.results.append(dict(id=ident, prueba=title, requisitos=req, estado='FALLIDA',
                                     detalle=self.safe(exc), segundos=round(time.monotonic()-start, 3)))
            print(f'{ident} FALLIDA: {self.safe(exc)}', flush=True)
            raise
        self.results.append(dict(id=ident, prueba=title, requisitos=req, estado='APROBADA',
                                 detalle=detail, segundos=round(time.monotonic()-start, 3)))
        print(f'{ident} APROBADA: {title}', flush=True)

    def scene(self, title, target=None, shot=None, seconds=None):
        if target is not None:
            target.scroll_into_view_if_needed()
        self.page.wait_for_timeout(250)
        if shot:
            self.page.screenshot(path=str(self.out/'capturas'/f'{shot}.png'), full_page=True)
        self.scenes.append(dict(inicio=round(time.monotonic()-self.started, 2), escena=title))
        self.page.wait_for_timeout(1000 * (self.pace if seconds is None else seconds))

    def reports(self, metadata):
        counts = {s: sum(r['estado'] == s for r in self.results)
                  for s in ('APROBADA', 'FALLIDA', 'OMITIDA')}
        payload = dict(entorno=metadata, conteo=counts, pruebas=self.results, escenas=self.scenes)
        report = self.out/'reportes'
        (report/'resultados.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        summary = ', '.join(f'{v} {k.lower()}s' for k,v in counts.items())
        rows = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in
                       ('id','prueba','estado','requisitos','detalle')) + '</tr>' for r in self.results)
        doc = f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>MisFinanzas · Informe E2E Playwright Python</title>
<style>body{{font:18px system-ui;background:#eef3f8;color:#18304c;margin:40px}}main{{background:white;padding:30px;border-radius:18px}}h1{{color:#135d4d}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border:1px solid #cad5df;padding:9px;text-align:left}}.big{{font-size:28px;color:#14634c}}small{{color:#526174}}</style>
<main><small>INFORME DE QA · ejecución local real · Grupo 5</small><h1>MisFinanzas — resultados E2E</h1><p class="big">{summary}</p>
<p>{html.escape(metadata['fecha'])} · {html.escape(metadata['sistema'])} · Git {metadata['commit'][:7]}</p>
<p>Python {metadata['python']} · SQLite {metadata['sqlite']} · Chromium {metadata.get('chromium','')} · Playwright {metadata['playwright']}</p>
<p>CRUD, alertas 80 % y 100 %, historial, CSV y controles de acceso. Base temporal, datos ficticios.</p>
<p>Este informe acredita la ejecución técnica; quedan pendientes la instalación independiente, la revisión del grupo y la evaluación docente.</p>
<table><thead><tr><th>ID</th><th>Prueba</th><th>Estado</th><th>Requisito</th><th>Resultado observado</th></tr></thead><tbody>{rows}</tbody></table>
<p>Informe generado por la suite Python que controla Playwright; no usa el reporter HTML de Playwright Test para Node.</p></main></html>'''
        (report/'playwright.html').write_text(doc, encoding='utf-8')
        lines = ['# Resultado real E2E — MisFinanzas', '', f'**{summary}.**', '',
                 *[f'- {k}: {v}' for k,v in metadata.items()], '',
                 '| ID | Prueba | Estado | S1–S4 | Resultado observado |', '|---|---|---|---|---|']
        lines += [f"| {r['id']} | {r['prueba']} | {r['estado']} | {r['requisitos']} | {str(r['detalle']).replace('|','/').replace(chr(10),' ')} |" for r in self.results]
        lines += ['', 'Las operaciones se realizaron desde formularios reales, excepto la preparación de la cuenta ficticia y las consultas SQLite de contraste.',
                  'E23 desactiva únicamente la validación HTML del formulario en el navegador para comprobar la validación del servidor. No altera código de la aplicación.',
                  'Se detiene la cadena si falla un paso; los pasos dependientes restantes se registran como omitidos.',
                  'No se grabaron trazas HAR, cookies ni cuerpos de autenticación. La contraseña aleatoria solo vive en memoria y aparece enmascarada en la interfaz.',
                  'No se probaron todos los módulos ni toda la seguridad del sistema. No acredita instalación por otro integrante, autoría, asistencia, notas, tags ni publicación del video.', '']
        (report/'RESUMEN.md').write_text('\n'.join(lines), encoding='utf-8')
        errors = [f"- {r['id']}: {r['detalle']}" for r in self.results if r['estado'] != 'APROBADA']
        (report/'ERRORES.md').write_text('# Errores y pendientes\n\n' + ('\n'.join(errors) if errors else 'No se detectaron defectos funcionales en los casos ejecutados.') +
            '\n\nPendientes: instalación por otra persona; acta y evaluación docente; revisión del grupo; tags; publicar el video y comprobar el acceso del profesor.\n'
            'Seguridad pendiente ya documentada en S4: CSRF integral, fuerza bruta y sesiones persistentes. Esta suite no es una auditoría de seguridad.\n', encoding='utf-8')
        return counts


def execute(args):
    from playwright.sync_api import sync_playwright, expect
    out = Path(args.output).resolve()
    # No borrar ni sobrescribir evidencias previas accidentalmente.
    if out.exists() and any(out.iterdir()):
        raise SystemExit('El destino contiene archivos. Use una carpeta nueva para conservar las evidencias anteriores.')
    for part in ('capturas','reportes','video','exportaciones'):
        (out/part).mkdir(parents=True, exist_ok=True)
    run = Run(out, args.pace)
    metadata = dict(fecha=datetime.now(TZ).isoformat(timespec='seconds'), sistema=platform.platform(),
                    python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                    playwright=importlib.metadata.version('playwright'), commit=git('rev-parse','HEAD'),
                    rama=git('branch','--show-current'), entorno='local aislado; DB temporal eliminada al terminar',
                    base_path='/finanzas', resolucion='1280x720', codigo_funcional_modificado=False)
    previous_env = {k: os.environ.get(k) for k in ('DB_PATH','APP_BASE_PATH','FINANZAS_INITIAL_ADMIN_PASSWORD','FINANZAS_COOKIE_SECURE')}
    tmp = tempfile.TemporaryDirectory(prefix='misfinanzas_e2e_')
    server = thread = browser = context = None
    video_path = None
    failure = None
    try:
        dbfile = Path(tmp.name)/'aislada.sqlite3'
        os.environ.update(DB_PATH=str(dbfile), APP_BASE_PATH='/finanzas',
                          FINANZAS_INITIAL_ADMIN_PASSWORD=secrets.token_urlsafe(30), FINANZAS_COOKIE_SECURE='0')
        assert dbfile.parent.resolve() == Path(tmp.name).resolve() and not dbfile.exists()
        from src import db, auth, profiles
        db.init_db()
        run.password = secrets.token_urlsafe(24)
        uid = auth.register(dict(username='demo_e2e', name='Familia de demostración E2E',
                                 password=run.password, confirm_password=run.password))
        with db.connect() as c:
            pid = profiles.ensure_default(c, uid)
        from src.app import Handler
        class QuietHandler(Handler):
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        base = f'http://127.0.0.1:{server.server_port}/finanzas'
        metadata['url_local'] = base
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        today = datetime.now(TZ).date()

        def sql(query, params=()):
            # Solo lectura: todas las operaciones de negocio pasan por el navegador.
            with closing(sqlite3.connect(dbfile.as_uri()+'?mode=ro', uri=True)) as c:
                c.row_factory = sqlite3.Row
                return [dict(row) for row in c.execute(query, params)]

        def one(query, params=()):
            return next(iter(sql(query, params)))

        def check(condition, message):
            if not condition:
                raise AssertionError(message)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chromium', headless=True)
            metadata['chromium'] = browser.version
            options = dict(viewport=dict(width=1280,height=720), locale='es-CR', timezone_id='America/Costa_Rica',
                           accept_downloads=True, reduced_motion='reduce')
            if args.record:
                options.update(record_video_dir=str(out/'video'), record_video_size=dict(width=1280,height=720))
            context = browser.new_context(**options)
            # Evita cualquier conexión del navegador a un destino externo.
            context.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' or route.request.url.startswith('file:') else route.abort())
            page = context.new_page()
            run.page = page
            run.started = time.monotonic()
            page.set_default_timeout(30000)
            page.set_default_navigation_timeout(30000)
            page.on('dialog', lambda dialog: dialog.accept())

            def go(path='/'):
                return page.goto(base+path, wait_until='networkidle')

            def nav(group, label, path):
                page.get_by_text(group, exact=True).hover()
                page.get_by_role('link', name=label, exact=True).click()
                expect(page).to_have_url(base+path)

            def movement(kind, amount, desc, category=None, edit=False):
                if not edit:
                    go()
                form = page.locator('form[action*="/movimientos"]').filter(has=page.locator('[name="monto"]'))
                form.locator(f'label[for="tipo-{kind}"]').click()
                form.locator('[name="monto"]').fill(amount)
                form.locator('[name="fecha"]').fill(today.isoformat())
                form.locator('[name="id_cuenta"]').select_option(label='Cuenta principal')
                if category:
                    form.locator('[name="id_categoria"]').select_option(label=category)
                form.locator('[name="descripcion"]').fill(desc)
                if args.record:
                    form.locator('[name="monto"]').scroll_into_view_if_needed()
                    page.wait_for_timeout(1500)
                form.get_by_role('button', name='Guardar cambios' if edit else 'Agregar movimiento', exact=True).click()
                expect(page).to_have_url(base+'/')
                row = page.locator('tr').filter(has=page.get_by_text(desc, exact=True))
                expect(row).to_have_count(1)
                expect(row).to_contain_text(f'{float(amount):,.2f}')
                saved = one('SELECT * FROM movimientos WHERE id_perfil=? AND descripcion=?', (pid,desc))
                check(saved['monto_centimos'] == round(float(amount)*100), 'Monto SQLite diferente de la entrada')
                return row

            def first():
                responses = []
                page.on('response', lambda r: responses.append((r.url,r.status)))
                go('/historial')
                expect(page).to_have_url(base+'/login')
                check((base+'/historial',303) in responses, 'Falta redirección HTTP 303 sin sesión')
                run.scene('Presentación: MisFinanzas, Python, SQLite y navegador real', shot='01_login', seconds=args.pace*1.4)
                return 'GET protegido: 303 al login; formulario real visible.'

            def login():
                page.locator('[name="usuario"]').fill('demo_e2e')
                page.locator('[name="contrasena"]').fill(run.password)
                expect(page.locator('[name="contrasena"]')).to_have_attribute('type','password')
                page.get_by_role('button',name='Ingresar',exact=True).click()
                expect(page).to_have_url(base+'/perfiles/elegir')
                page.locator('label.profile-option').filter(has=page.locator(f'input[value="{pid}"]')).click()
                run.scene('Sesión iniciada; selección del perfil ficticio')
                page.get_by_role('button',name='Ingresar al perfil').click()
                expect(page).to_have_url(base+'/')
                return 'Login → /perfiles/elegir → /finanzas/. Usuario estándar propietario de su perfil.'

            def dashboard():
                expect(page.get_by_role('heading',name='Un panorama claro de tu dinero.')).to_be_visible()
                expect(page.get_by_text('Aún no hay movimientos en el período seleccionado.', exact=True)).to_have_count(1)
                check(not sql('SELECT * FROM movimientos WHERE id_perfil=?',(pid,)), 'Perfil no vacío')
                run.scene('Dashboard y perfil financiero', shot='02_dashboard')

            def accounts():
                nav('Catálogos','Cuentas','/admin/cuentas')
                expect(page.locator('table.records')).to_contain_text('Cuenta principal')
                expect(page.locator('table.records')).to_contain_text('Efectivo')
                run.scene('Cuentas en colones; navegación del menú', page.get_by_role('heading',name='Cuentas',exact=True))

            def category_create():
                nav('Catálogos','Categorías','/admin/categorias')
                page.locator('[name="nombre"]').fill('Categoría temporal E2E')
                page.get_by_role('button',name='Guardar',exact=True).click()
                expect(page.locator('table.records')).to_contain_text('Categoría temporal E2E')

            def category_edit():
                row = page.locator('tr').filter(has=page.get_by_text('Categoría temporal E2E',exact=True))
                row.get_by_role('link',name='Editar',exact=True).click()
                page.locator('[name="nombre"]').fill('Categoría editada E2E')
                page.get_by_role('button',name='Guardar',exact=True).click()
                expect(page.locator('table.records')).to_contain_text('Categoría editada E2E')
                check(len(sql('SELECT * FROM categorias WHERE id_perfil=? AND nombre=?',(pid,'Categoría editada E2E')))==1,'No se editó la categoría')

            def category_delete():
                page.locator('tr').filter(has=page.get_by_text('Categoría editada E2E',exact=True)).get_by_role('button',name='Eliminar',exact=True).click()
                expect(page.get_by_text('Categoría editada E2E',exact=True)).to_have_count(0)
                check(not sql('SELECT * FROM categorias WHERE id_perfil=? AND nombre=?',(pid,'Categoría editada E2E')), 'Categoría aún presente')

            def budget_category():
                page.locator('[name="nombre"]').fill('Presupuesto E2E')
                radio_id = page.locator('input[name="tipo"][value="gasto"]').get_attribute('id')
                page.locator(f'label[for="{radio_id}"]').click()
                page.get_by_role('button',name='Guardar',exact=True).click()
                check(one('SELECT tipo FROM categorias WHERE id_perfil=? AND nombre=?',(pid,'Presupuesto E2E'))['tipo']=='gasto','Categoría incorrecta')

            def income():
                row = movement('ingreso','1000.00','Ingreso ficticio E2E','Salario')
                run.scene('Ingreso registrado: CRC 1,000.00',row,'03_crear_ingreso')

            def expense():
                row = movement('gasto','25.00','Gasto ficticio E2E','Alimentación')
                run.scene('Gasto registrado: CRC 25.00',row,'04_crear_gasto')

            def edit():
                page.locator('tr').filter(has=page.get_by_text('Gasto ficticio E2E',exact=True)).get_by_role('link',name='Editar',exact=True).click()
                row = movement('gasto','35.00','Gasto editado E2E','Alimentación',edit=True)
                check(not sql('SELECT * FROM movimientos WHERE descripcion=?',('Gasto ficticio E2E',)), 'Descripción previa persiste')
                run.scene('Gasto editado: CRC 35.00, contrastado con SQLite',row,'05_editar_movimiento')

            def delete():
                page.locator('tr').filter(has=page.get_by_text('Gasto editado E2E',exact=True)).get_by_role('button',name='Eliminar',exact=True).click()
                expect(page.get_by_text('Gasto editado E2E',exact=True)).to_have_count(0)
                check(not sql('SELECT * FROM movimientos WHERE id_perfil=? AND descripcion=?',(pid,'Gasto editado E2E')), 'Movimiento no eliminado en SQLite')
                run.scene('Gasto eliminado; permanece el ingreso ficticio',page.get_by_role('heading',name='Movimientos del período'),'06_eliminar_movimiento')

            def budget():
                go()
                form = page.locator('form[action$="/presupuestos"]')
                form.locator('[name="id_categoria"]').select_option(label='Presupuesto E2E')
                form.locator('[name="monto_limite"]').fill('100.00')
                crc = one("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'")['id_moneda']
                form.locator('[name="id_moneda"]').select_option(str(crc))
                form.get_by_role('button',name='Guardar límite').click()
                line = page.locator('.budget-line').filter(has_text='Presupuesto E2E')
                expect(line).to_contain_text('Bajo control')
                check(one('SELECT monto_limite_centimos FROM presupuestos WHERE id_perfil=?',(pid,))['monto_limite_centimos']==10000,'Presupuesto distinto de CRC 100')
                run.scene('Presupuesto exclusivo: CRC 100.00',line,'07_presupuestos')

            def threshold(amount, desc, status, threshold, shot):
                movement('gasto',amount,desc,'Presupuesto E2E')
                line = page.locator('.budget-line').filter(has_text='Presupuesto E2E')
                expect(line).to_contain_text(status)
                expect(line).to_contain_text(f'{threshold}.00 utilizados')
                category = one('SELECT id_categoria FROM categorias WHERE id_perfil=? AND nombre=?',(pid,'Presupuesto E2E'))['id_categoria']
                total = one("SELECT SUM(monto_centimos) AS total FROM movimientos WHERE id_perfil=? AND id_categoria=? AND tipo='gasto'",(pid,category))['total']
                check(total==threshold*100, 'El gasto no coincide con el umbral exacto')
                alerts = sql('SELECT umbral FROM alertas WHERE id_perfil=? ORDER BY umbral',(pid,))
                check([r['umbral'] for r in alerts]==([80] if threshold==80 else [80,100]),'Alertas persistidas incorrectas')
                run.scene(f'Umbral exacto {threshold} %: {status}',line,shot)
                return f'CRC {threshold}.00 / CRC 100.00; {status}; alertas SQLite: {alerts}.'

            def alerts():
                nav('Planificación','Alertas','/admin/alertas')
                expect(page.locator('table.records tbody tr')).to_have_count(2)
                expect(page.locator('table.records')).to_contain_text('80')
                expect(page.locator('table.records')).to_contain_text('100')

            def history():
                nav('Operaciones','Historial y búsqueda','/historial')
                expect(page.locator('table.records tbody tr')).to_have_count(3)
                expect(page.locator('.table-panel')).to_contain_text('1,000.00')
                expect(page.locator('.table-panel')).to_contain_text('100.00')
                run.scene('Historial real: un ingreso y dos gastos de presupuesto',page.locator('table.records'),'10_historial')

            def filters():
                form = page.get_by_role('search')
                form.locator('[name="q"]').fill('Umbral 80 E2E')
                form.locator('label[for="h-tipo-gasto"]').click()
                form.locator('[name="id_categoria"]').select_option(label='Presupuesto E2E (gasto)')
                form.locator('[name="id_cuenta"]').select_option(label='Cuenta principal')
                form.locator('[name="desde"]').fill(today.isoformat())
                form.locator('[name="hasta"]').fill(today.isoformat())
                form.get_by_role('button',name='Aplicar filtros').click()
                expect(page.locator('table.records tbody tr')).to_have_count(1)
                expect(page.locator('table.records')).to_contain_text('Umbral 80 E2E')
                expect(page.locator('table.records')).not_to_contain_text('Umbral 100 E2E')
                run.scene('Filtros combinados: un único movimiento de CRC 80.00',page.get_by_role('search'), '13_historial_filtrado')

            def history_csv():
                with page.expect_download() as pending:
                    page.get_by_role('link',name='Exportar CSV',exact=True).click()
                dest = out/'exportaciones'/'historial_filtrado.csv'
                pending.value.save_as(dest)
                records = list(csv.DictReader(io.StringIO(dest.read_text(encoding='utf-8-sig'))))
                check(len(records)==1 and records[0]['descripcion']=='Umbral 80 E2E' and records[0]['monto']=='80.00','CSV no coincide con el filtro')
                actual = one('SELECT monto_centimos FROM movimientos WHERE id_perfil=? AND descripcion=?',(pid,'Umbral 80 E2E'))
                check(actual['monto_centimos']==8000 and records[0]['moneda']=='CRC','CSV difiere de SQLite')
                return 'Descarga real del navegador; 1 fila, CRC 80.00; columnas y datos contrastados con SQLite.'

            def annual():
                nav('Planificación','Reporte anual','/reportes/anual')
                expect(page.get_by_role('heading',name=f'Reporte anual por categoría · {today.year}',exact=True)).to_be_visible()
                row = page.locator('tr').filter(has=page.get_by_text('Presupuesto E2E',exact=True))
                expect(row.locator('td').last).to_have_text('100.00')
                salary = page.locator('tr').filter(has=page.get_by_text('Salario',exact=True))
                expect(salary.locator('td').last).to_have_text('1,000.00')
                run.scene('Reporte anual por categoría: encabezado y exportación',page.get_by_role('heading',name=f'Reporte anual por categoría · {today.year}'),'17_reporte_anual_encabezado',seconds=args.pace/2)
                run.scene('Reporte anual: CRC 1,000.00 de ingreso y CRC 100.00 de gasto',row.locator('td').last,'11_reporte_anual')

            def annual_csv():
                with page.expect_download() as pending:
                    page.get_by_role('link',name='Exportar CSV',exact=True).click()
                dest = out/'exportaciones'/'reporte_anual.csv'
                pending.value.save_as(dest)
                records = list(csv.DictReader(io.StringIO(dest.read_text(encoding='utf-8-sig'))))
                check(len(records)==2,'CSV anual con filas inesperadas')
                actual = sql('SELECT c.nombre AS categoria,m.tipo,SUM(m.monto_centimos) AS total FROM movimientos m JOIN categorias c USING(id_categoria) WHERE m.id_perfil=? GROUP BY c.nombre,m.tipo',(pid,))
                expected = {(r['categoria'],r['tipo']):f"{r['total']/100:.2f}" for r in actual}
                check({(r['categoria'],r['tipo']):r['total'] for r in records}==expected,'Totales CSV anual distintos de SQLite')
                month_key = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][today.month-1]
                check(all(r[month_key]==r['total'] and r['anio']==str(today.year) and r['moneda']=='CRC' for r in records),'Período o moneda CSV incorrectos')
                return 'Descarga CSV anual: 2 filas, CRC 1,000.00 y CRC 100.00; mes, año y totales coinciden con SQLite.'

            def invalid_client():
                go()
                page.locator('[name="monto"]').fill('-10')
                page.locator('[name="descripcion"]').fill('Monto inválido E2E')
                field = page.locator('[name="monto"]')
                page.get_by_role('button',name='Agregar movimiento').click()
                check(field.evaluate('(e)=>e.validity.rangeUnderflow'),'No se activó el mínimo HTML')
                message = field.evaluate('(e)=>e.validationMessage')
                check(bool(message),'Falta mensaje nativo de validación')
                check(not sql('SELECT * FROM movimientos WHERE descripcion=?',('Monto inválido E2E',)),'Se persistió monto inválido')
                run.scene('Validación nativa del monto negativo',field,'14_validacion_html')
                return f'Validación HTML rangeUnderflow; mensaje real de Chromium: {message}'

            def invalid_server():
                # Prueba negativa deliberada: se omite validación cliente para ejercitar backend.
                field = page.locator('[name="monto"]')
                field.evaluate('(e)=>e.form.noValidate=true')
                with page.expect_response(lambda r: r.url==base+'/movimientos' and r.request.method=='POST') as response:
                    page.get_by_role('button',name='Agregar movimiento').click()
                check(response.value.status==400,'El servidor no rechazó con HTTP 400')
                message = page.get_by_text('El monto debe ser mayor que cero.',exact=True)
                expect(message).to_be_visible()
                check(not sql('SELECT * FROM movimientos WHERE descripcion=?',('Monto inválido E2E',)),'Escritura inválida aceptada')
                run.scene('Error controlado HTTP 400: monto debe ser mayor que cero',message,'12_validacion_error')

            def invalid_filter():
                response = go('/historial?desde=2026-12-31&hasta=2026-01-01')
                check(response.status==400,'Filtro inválido no devuelve 400')
                expect(page.get_by_text('La fecha inicial no puede ser posterior a la final.',exact=True)).to_be_visible()

            def permissions():
                for path in ('/admin/usuarios','/admin/calidad'):
                    response = go(path)
                    check(response.status==403,f'Usuario estándar accedió a {path}')
                    expect(page.get_by_role('heading',name='No tiene permiso para ver esta página',exact=True)).to_be_visible()
                run.scene('Usuario estándar: acceso administrativo restringido',shot='15_acceso_restringido')
                return 'GET /admin/usuarios y /admin/calidad: ambos HTTP 403.'

            def logout():
                go()
                page.get_by_role('button',name='Cerrar sesión',exact=True).click()
                expect(page).to_have_url(base+'/login')
                go('/historial')
                expect(page).to_have_url(base+'/login')

            def integrity():
                check(one('PRAGMA integrity_check')['integrity_check']=='ok','Integridad SQLite incorrecta')
                check(not sql('PRAGMA foreign_key_check'),'Claves foráneas incorrectas')
                check(one('PRAGMA journal_mode')['journal_mode']=='wal','Modo WAL no activo')
                tables = len(sql("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                check(tables==17,f'Se esperaban 17 tablas de aplicación, se obtuvieron {tables}')
                check(one('SELECT COUNT(*) AS n FROM movimientos WHERE id_perfil=?',(pid,))['n']==3,'Conteo final distinto de tres')
                return f'integrity_check=ok; foreign_key_check=0 filas; journal_mode=wal; {tables} tablas; 3 movimientos ficticios.'

            actions = [first,login,dashboard,accounts,category_create,category_edit,category_delete,budget_category,
                       income,expense,edit,delete,budget,
                       lambda:threshold('80.00','Umbral 80 E2E','Cerca del límite',80,'08_alerta_80'),
                       lambda:threshold('20.00','Umbral 100 E2E','Excedido',100,'09_alerta_100'),
                       alerts,history,filters,history_csv,annual,annual_csv,invalid_client,invalid_server,
                       invalid_filter,permissions,logout,integrity]
            try:
                for case, action in zip(CASES, actions):
                    run.step(case, action)
                    run.reports(metadata)
            except Exception as exc:
                failure = run.safe(exc)
                done = {r['id'] for r in run.results}
                for ident,title,req in CASES:
                    if ident not in done:
                        run.results.append(dict(id=ident,prueba=title,requisitos=req,estado='OMITIDA',
                                                detalle='Dependencia de un paso anterior fallido; no ejecutada.',segundos=0))
                run.reports(metadata)
                try:
                    page.screenshot(path=str(out/'capturas'/'fallo_real.png'),timeout=10000)
                except Exception:
                    metadata['captura_fallo']='No disponible: el navegador no respondió; se conserva el resultado fallido.'
            counts = run.reports(metadata)
            try:
                page.goto((out/'reportes'/'playwright.html').as_uri(),timeout=10000)
                run.scene('Resultados reales y conclusiones; pendientes académicos visibles',shot='16_resultados',seconds=args.pace*1.6)
            except Exception:
                if not failure:
                    raise
            if args.record:
                video = page.video
            context.close()
            context = None
            if args.record:
                video_path = Path(video.path())
            browser.close()
            browser = None
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass  # Playwright ya cerró el transporte al salir de su contexto.
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        for handler in logging.getLogger('finanzas').handlers[:]:
            handler.close()
            logging.getLogger('finanzas').removeHandler(handler)
        for key,value in previous_env.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value
        tmp.cleanup()
    if video_path:
        target = out/'video'/'MisFinanzas_S4.webm'
        video_path.replace(target)
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        mp4 = out/'video'/'MisFinanzas_S4.mp4'
        subprocess.run([ffmpeg,'-v','error','-i',str(target),'-c:v','libx264','-preset','fast','-crf','21',
                        '-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True,timeout=180)
        run.video_metadata = imageio_ffmpeg.read_frames(str(mp4))
        info = next(run.video_metadata)
        run.video_metadata.close()
        (out/'reportes'/'video.json').write_text(json.dumps({k:info[k] for k in ('codec','size','fps','duration')}, indent=2),encoding='utf-8')
    run.reports(metadata)
    (out/'reportes'/'escenas.json').write_text(json.dumps(run.scenes,ensure_ascii=False,indent=2),encoding='utf-8')
    missing = [f'{s}.png' for s in EXPECTED_SHOTS if not (out/'capturas'/f'{s}.png').exists()]
    (out/'reportes'/'capturas.json').write_text(json.dumps(dict(requeridas=12,faltantes=missing),indent=2),encoding='utf-8')
    print(json.dumps(dict(resultado=counts, salida=str(out), capturas_faltantes=missing),ensure_ascii=False),flush=True)
    return 1 if failure else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='evidencias/s4')
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--pace', type=float, default=11, help='Segundos de lectura por escena; 0 para diagnóstico rápido')
    arguments = parser.parse_args()
    if arguments.pace < 0:
        parser.error('--pace debe ser >= 0')
    raise SystemExit(execute(arguments))
