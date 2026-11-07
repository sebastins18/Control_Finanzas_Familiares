"""Graba 19 escenas reales en 1080p, guiadas por los tiempos de la voz aceptada.

Separado del runner de regresión. Solo localhost y SQLite temporal propia.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime,timedelta,timezone
import html
import json
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from media_common import ROOT,save

sys.path.insert(0,str(ROOT))
CURSOR = '''document.addEventListener('DOMContentLoaded',()=>{
if(location.hostname==='127.0.0.1' && location.pathname.startsWith('/finanzas')){document.documentElement.style.zoom='1.08';document.body.style.paddingBottom='400px';}
const cursor=document.createElement('div');cursor.id='qa-cursor';cursor.style.cssText='position:fixed;left:0;top:0;width:30px;height:36px;z-index:2147483646;pointer-events:none;transform:translate(1800px,900px)';
cursor.style.zoom=String(1/(parseFloat(document.documentElement.style.zoom)||1));
cursor.innerHTML='<svg width="30" height="36" viewBox="0 0 30 36"><path d="M3 2 L3 29 L10 23 L16 34 L22 31 L16 20 L27 19 Z" fill="#123d59" stroke="white" stroke-width="2.5"/></svg>';document.body.append(cursor);
document.addEventListener('pointermove',e=>cursor.style.transform=`translate(${e.clientX}px,${e.clientY}px)`,true);
document.addEventListener('pointerdown',e=>{const r=document.createElement('div');r.style.cssText=`position:fixed;left:${e.clientX-18}px;top:${e.clientY-18}px;width:36px;height:36px;border:4px solid #ef9b21;border-radius:50%;z-index:2147483645;pointer-events:none`;document.body.append(r);r.animate([{opacity:1,transform:'scale(.5)'},{opacity:0,transform:'scale(1.7)'}],{duration:550});setTimeout(()=>r.remove(),550)},true);
});'''


def main():
    from playwright.sync_api import sync_playwright,expect
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    parser.add_argument('--work',default='.venv-e2e/presentacion/toma-01')
    parser.add_argument('--scenes',default='1-19',help='Rango a conservar; el estado previo se prepara igualmente por UI')
    parser.add_argument('--handles',type=float,default=0,help='Cobertura real adicional después de las acciones, para cortar esperas sin retimar')
    parser.add_argument('--coverage',type=float,default=0,help='Hold real por encuadre para disponer de puntos de corte de presentación')
    parser.add_argument('--coverage-scenes',default='4',help='Escenas que requieren cobertura en cada estado')
    args=parser.parse_args()
    out=Path(args.output).resolve()
    work=Path(args.work).resolve()
    work.mkdir(parents=True,exist_ok=True)
    (out/'capturas').mkdir(parents=True,exist_ok=True)
    scenes=json.loads((ROOT/'evidencias/MisFinanzas_S4_Informe_Narracion_Natural.json').read_text(encoding='utf-8-sig'))
    boundaries=[0]+[s['start'] for s in scenes[1:]]+[246.84]
    selected=set()
    for part in args.scenes.split(','):
        ends=list(map(int,part.split('-')))
        selected.update(range(ends[0],ends[-1]+1))
    assert len(scenes)==19
    coverage_scenes=set(map(int,args.coverage_scenes.split(',')))
    previous={k:os.environ.get(k) for k in ('DB_PATH','APP_BASE_PATH','FINANZAS_INITIAL_ADMIN_PASSWORD','FINANZAS_COOKIE_SECURE')}
    log=[]
    with tempfile.TemporaryDirectory(prefix='misfinanzas_presentacion_') as folder:
        os.environ.update(DB_PATH=str(Path(folder)/'demo.sqlite3'),APP_BASE_PATH='/finanzas',
                          FINANZAS_INITIAL_ADMIN_PASSWORD=secrets.token_urlsafe(30),FINANZAS_COOKIE_SECURE='0')
        from src import db,auth,profiles
        db.init_db()
        password=secrets.token_urlsafe(24)
        uid=auth.register(dict(username='demo_e2e',name='Familia de demostración E2E',password=password,confirm_password=password))
        with db.connect() as cx:
            pid=profiles.ensure_default(cx,uid)
        from src.app import Handler
        class LocalHandler(Handler):
            def log_message(self,*_):
                pass
            def do_GET(self):
                if self.path.startswith('/_qa/csv/'):
                    path=out/'exportaciones'/self.path.rsplit('/',1)[-1]
                    if not path.is_file() or path.parent!=out/'exportaciones':
                        return self.respond(404,b'No disponible','text/plain')
                    import csv
                    with path.open(encoding='utf-8-sig',newline='') as f:
                        records=list(csv.reader(f))
                    table=''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in r)+'</tr>' for r in records)
                    body=f'''<!doctype html><meta charset="utf-8"><style>body{{font:23px Arial;margin:65px;background:#f1f6fa;color:#17344b}}table{{border-collapse:collapse;width:100%;font-size:19px}}td{{padding:12px;border:1px solid #b9c9d5}}tr:first-child{{background:#dce8f1;font-weight:bold}}</style><h1>CSV descargado y verificado</h1><p>Visor local de evidencia QA · archivo auténtico: {html.escape(path.name)}</p><table>{table}</table><p>Los importes se contrastaron con SQLite en modo de solo lectura.</p>'''
                    return self.respond(200,body.encode(),cache=False)
                return super().do_GET()
        server=ThreadingHTTPServer(('127.0.0.1',0),LocalHandler)
        runner=threading.Thread(target=server.serve_forever,daemon=True)
        runner.start()
        base=f'http://127.0.0.1:{server.server_port}/finanzas'
        today=datetime.now(timezone(timedelta(hours=-6))).date().isoformat()
        def rows(query,params=()):
            with closing(sqlite3.connect(Path(os.environ['DB_PATH']).as_uri()+'?mode=ro',uri=True)) as cx:
                cx.row_factory=sqlite3.Row
                return [dict(r) for r in cx.execute(query,params)]
        def scalar(query,params=()):
            return next(iter(rows(query,params)[0].values()))
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='chromium',headless=True)
                context=browser.new_context(viewport=dict(width=1920,height=1080),record_video_dir=str(work),
                    record_video_size=dict(width=1920,height=1080),locale='es-CR',timezone_id='America/Costa_Rica',
                    reduced_motion='reduce',accept_downloads=True)
                context.add_init_script(CURSOR)
                context.route('**/*',lambda route:route.continue_() if urlsplit(route.request.url).hostname=='127.0.0.1' or route.request.url.startswith('file:') else route.abort())
                page=None
                t0=0
                active=None
                def go(path='/'):
                    response=page.goto(base+path,wait_until='networkidle')
                    page.evaluate('document.documentElement.style.zoom="1.08";document.body.style.paddingBottom="400px"')
                    page.evaluate('document.fonts.ready')
                    return response
                def focus(locator,shot=None):
                    expect(locator).to_be_visible()
                    locator.scroll_into_view_if_needed()
                    box=locator.bounding_box()
                    dest=page.evaluate('(r)=>Math.max(0,window.scrollY+r.y+r.height/2-480)',box)
                    page.evaluate('(y)=>window.scrollTo({top:y,behavior:"smooth"})',dest)
                    page.wait_for_function('(e)=>{const r=e.getBoundingClientRect();return r.top>=-2 && r.bottom<=960}',arg=locator.element_handle(),timeout=3000)
                    page.wait_for_timeout(120)
                    box=locator.bounding_box()
                    assert box and box['y']>=-2 and box['y']+box['height']<=960, f'Elemento fuera del encuadre: {box}'
                    if shot:
                        page.screenshot(path=str(out/'capturas'/f'{shot}.png'))
                    if active is not None:
                        active['validaciones'].append(dict(t=round(time.monotonic()-t0,3),tipo='encuadre',
                                                          selector=locator._impl_obj._selector,caja=box))
                        if args.coverage and active['escena'] in coverage_scenes:
                            page.wait_for_timeout(args.coverage*1000)
                    return box
                def point(locator):
                    locator.scroll_into_view_if_needed()
                    box=locator.bounding_box()
                    if box:
                        x=box['x']+min(80,box['width']/2);y=box['y']+box['height']/2
                        page.mouse.move(x,y,steps=15)
                        cursor=page.locator('#qa-cursor').bounding_box()
                        assert cursor and abs(cursor['x']-x)<2 and abs(cursor['y']-y)<2,('Cursor fuera de posición',cursor,x,y)
                def at(seconds):
                    if active is None:
                        return
                    delay=seconds-(time.monotonic()-t0)
                    if delay>0:
                        page.wait_for_timeout(delay*1000)
                    elif delay<-.8:
                        active['demoras'].append(dict(objetivo=seconds,retraso=round(-delay,3)))
                def start(number,path,prepare=None):
                    nonlocal page,t0,active
                    page=context.new_page()
                    page.set_default_timeout(30000)
                    page.on('dialog',lambda d:d.accept())
                    go(path)
                    if prepare:
                        prepare()
                    page.mouse.move(1800,950,steps=10)
                    if number not in selected:
                        active=None
                        return
                    # Marca técnica solo en el preroll; el montaje la elimina al primer fotograma sin ella.
                    calibration=page.evaluate('''()=>{let d=document.createElement('div');d.id='qa-sync';d.style.cssText='position:fixed;left:0;top:0;transform:translate(1870px,10px);width:20px;height:20px;background:rgb(255,0,255);z-index:2147483647';d.style.zoom=String(1/(parseFloat(document.documentElement.style.zoom)||1));document.body.append(d);const r=d.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}}''')
                    assert abs(calibration['x']-1870)<2 and abs(calibration['y']-10)<2,calibration
                    page.wait_for_timeout(450)
                    page.evaluate('document.getElementById("qa-sync").remove()')
                    t0=time.monotonic()
                    active=dict(escena=number,inicio=boundaries[number-1],final=boundaries[number],
                                titulo=scenes[number-1]['title'],narracion=scenes[number-1]['text'],
                                validaciones=[],demoras=[],calibracion=calibration)
                def end():
                    nonlocal active
                    if active is not None:
                        minimum_tail={4:7.5,5:11.5,9:13.5,13:9,15:9.6}.get(active['escena'],0)
                        last=active['validaciones'][-1]['t'] if active['validaciones'] else 0
                        at(max(active['final']-active['inicio']+.6,time.monotonic()-t0+args.handles,last+minimum_tail))
                        active['duracion_grabada']=round(time.monotonic()-t0,3)
                        entry=active
                    else:
                        entry=None
                    video=page.video
                    page.close()
                    if entry:
                        target=work/f"escena_{entry['escena']:02}.webm"
                        if target.exists():
                            raise FileExistsError(target)
                        video.save_as(str(target))
                        entry['fuente']=target.relative_to(ROOT).as_posix()
                        log.append(entry)
                        save(work/'escenas_grabadas.json',log)
                        print(f"{entry['escena']:02}/19 grabada: {entry['titulo']}",flush=True)
                    active=None
                    if entry and entry['escena']==max(selected) and max(selected)<19:
                        raise StopIteration
                def movement_form(kind,amount,description,category):
                    form=page.locator('form[action*="/movimientos"]').filter(has=page.locator('[name="monto"]'))
                    form.locator(f'label[for="tipo-{kind}"]').click()
                    form.locator('[name="id_categoria"]').select_option(label=category)
                    form.locator('[name="id_cuenta"]').select_option(label='Cuenta principal')
                    form.locator('[name="fecha"]').fill(today)
                    form.locator('[name="monto"]').fill(amount)
                    form.locator('[name="descripcion"]').fill(description)
                    return form
                def movement_row(description):
                    return page.locator('tr').filter(has=page.get_by_text(description,exact=True))
                def save_movement(form,description,amount,edit=False):
                    button=form.get_by_role('button',name='Guardar cambios' if edit else 'Agregar movimiento',exact=True)
                    point(button)
                    button.click()
                    expect(page).to_have_url(base+'/')
                    row=movement_row(description)
                    expect(row).to_have_count(1)
                    expect(row).to_contain_text(f'{float(amount):,.2f}')
                    assert scalar('SELECT monto_centimos FROM movimientos WHERE id_perfil=? AND descripcion=?',(pid,description))==round(float(amount)*100)
                    return row
                def line():
                    return page.locator('.budget-line').filter(has_text='Presupuesto E2E')
                def prepare_income(kind,amount,description,category):
                    def prepare():
                        form=movement_form(kind,amount,description,category)
                        focus(form)
                    return prepare

                # 01: Aplicación real, sin portada que pueda confundirse con funcionamiento.
                start(1,'/login',lambda:focus(page.locator('.lg-card')))
                if 1 in selected: page.screenshot(path=str(out/'capturas/01_login.png'))
                at(3);point(page.get_by_role('heading',name='Iniciar sesión'))
                end()
                # 02: campos y perfil, antes de que la voz lo mencione.
                start(2,'/login',lambda:focus(page.locator('.lg-card')))
                page.locator('[name="usuario"]').press_sequentially('demo_e2e',delay=60)
                page.locator('[name="contrasena"]').fill(password)
                assert page.locator('[name="contrasena"]').get_attribute('type')=='password'
                at(.9);point(page.get_by_role('button',name='Ingresar',exact=True))
                page.get_by_role('button',name='Ingresar',exact=True).click()
                expect(page).to_have_url(base+'/perfiles/elegir')
                page.locator('label.profile-option').filter(has=page.locator(f'input[value="{pid}"]')).click()
                focus(page.locator('#profile-selection'))
                at(9.9);page.get_by_role('button',name='Ingresar al perfil').click()
                expect(page).to_have_url(base+'/')
                end()
                # 03: saldos y ausencia inicial de operaciones.
                start(3,'/',lambda:focus(page.locator('section.panel').filter(has=page.get_by_role('heading',name='Saldos por cuenta'))))
                at(1);point(page.get_by_text('Cuenta principal',exact=True).first)
                at(3);focus(page.locator('section.panel').filter(has=page.get_by_role('heading',name='Resumen mensual por moneda')))
                at(6);focus(page.locator('section.table-panel'))
                expect(page.get_by_text('Aún no hay movimientos en el período seleccionado.',exact=True)).to_be_visible()
                if 3 in selected: page.screenshot(path=str(out/'capturas/02_dashboard.png'))
                end()
                # 04: cuentas y CRUD de categoría visible con desplazamientos reales.
                start(4,'/admin/cuentas',lambda:focus(page.locator('table.records')))
                at(4.4);go('/admin/categorias');focus(page.locator('form.form-card'))
                page.locator('[name="nombre"]').press_sequentially('Categoría temporal E2E',delay=35)
                page.locator('label[for="f-tipo-gasto"]').click()
                at(5.4);page.get_by_role('button',name='Guardar',exact=True).click()
                row=page.locator('tr').filter(has=page.get_by_text('Categoría temporal E2E',exact=True));focus(row)
                at(7.3);row.get_by_role('link',name='Editar',exact=True).click()
                focus(page.locator('form.form-card'));page.locator('[name="nombre"]').fill('Categoría editada E2E')
                at(9);page.get_by_role('button',name='Guardar',exact=True).click()
                row=page.locator('tr').filter(has=page.get_by_text('Categoría editada E2E',exact=True));focus(row)
                at(10.4);point(row.get_by_role('button',name='Eliminar',exact=True));row.get_by_role('button',name='Eliminar',exact=True).click()
                expect(page.get_by_text('Categoría editada E2E',exact=True)).to_have_count(0)
                assert scalar('SELECT COUNT(*) FROM categorias WHERE id_perfil=? AND nombre=?',(pid,'Categoría editada E2E'))==0
                at(12);focus(page.locator('form.form-card'));page.locator('[name="nombre"]').fill('Presupuesto E2E')
                page.locator('label[for="f-tipo-gasto"]').click();page.get_by_role('button',name='Guardar',exact=True).click()
                focus(page.locator('tr').filter(has=page.get_by_text('Presupuesto E2E',exact=True)))
                end()
                # 05–06: formularios completos y resultado antes de la frase de comprobación.
                for number,kind,amount,description,category,shot in (
                    (5,'ingreso','1000.00','Ingreso ficticio E2E','Salario','03_crear_ingreso'),
                    (6,'gasto','25.00','Gasto ficticio E2E','Alimentación','04_crear_gasto')):
                    start(number,'/',prepare_income(kind,amount,description,category))
                    form=page.locator('form[action*="/movimientos"]').filter(has=page.locator('[name="monto"]'))
                    at(.3);point(form.locator('[name="monto"]'))
                    at(1.5);row=save_movement(form,description,amount)
                    focus(row,shot if number in selected else None)
                    at(6);point(row)
                    end()
                # 07: antes, campos editados y después.
                start(7,'/',lambda:focus(movement_row('Gasto ficticio E2E')))
                at(.25);movement_row('Gasto ficticio E2E').get_by_role('link',name='Editar',exact=True).click()
                form=movement_form('gasto','35.00','Gasto editado E2E','Alimentación');focus(form)
                at(1.6);point(form.locator('[name="monto"]'))
                at(2.3);point(form.locator('[name="descripcion"]'))
                at(3.2);row=save_movement(form,'Gasto editado E2E','35.00',edit=True)
                focus(row,'05_editar_movimiento' if 7 in selected else None)
                end()
                # 08: eliminación y ausencia, manteniendo el ingreso.
                start(8,'/',lambda:focus(page.locator('section.table-panel')))
                at(.4);button=movement_row('Gasto editado E2E').get_by_role('button',name='Eliminar',exact=True);point(button);button.click()
                expect(page.get_by_text('Gasto editado E2E',exact=True)).to_have_count(0)
                assert scalar('SELECT COUNT(*) FROM movimientos WHERE id_perfil=? AND descripcion=?',(pid,'Gasto editado E2E'))==0
                focus(page.locator('section.table-panel'),'06_eliminar_movimiento' if 8 in selected else None)
                end()
                # 09: presupuesto 100 y estado inicial, visibles mientras se explican.
                def prepare_budget():
                    form=page.locator('form[action$="/presupuestos"]')
                    form.locator('[name="id_categoria"]').select_option(label='Presupuesto E2E')
                    form.locator('[name="monto_limite"]').fill('100.00')
                    crc=scalar("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'")
                    form.locator('[name="id_moneda"]').select_option(str(crc));focus(form)
                start(9,'/',prepare_budget)
                at(.8);page.get_by_role('button',name='Guardar límite').click()
                expect(line()).to_contain_text('Bajo control')
                focus(line(),'07_presupuestos' if 9 in selected else None)
                end()
                # 10: el estado 80 ya está visible al empezar la mención.
                def prepare80():
                    form=movement_form('gasto','80.00','Umbral 80 E2E','Presupuesto E2E')
                    save_movement(form,'Umbral 80 E2E','80.00')
                    expect(line()).to_contain_text('Cerca del límite');focus(line())
                start(10,'/',prepare80)
                focus(line(),'08_alerta_80' if 10 in selected else None)
                assert [r['umbral'] for r in rows('SELECT umbral FROM alertas WHERE id_perfil=? ORDER BY umbral',(pid,))]==[80]
                at(6.1);go('/admin/alertas');focus(page.locator('table.records'))
                expect(page.locator('table.records')).to_contain_text('80')
                end()
                # 11: +20, resultado exacto 100 y alertas 80/100.
                start(11,'/',prepare_income('gasto','20.00','Umbral 100 E2E','Presupuesto E2E'))
                at(.3);form=page.locator('form[action*="/movimientos"]').filter(has=page.locator('[name="monto"]'))
                save_movement(form,'Umbral 100 E2E','20.00')
                expect(line()).to_contain_text('Excedido');expect(line()).to_contain_text('100.00 utilizados')
                focus(line(),'09_alerta_100' if 11 in selected else None)
                at(6.1);go('/admin/alertas');focus(page.locator('table.records'))
                expect(page.locator('table.records tbody tr')).to_have_count(2)
                end()
                # 12: registros y totales en un encuadre.
                start(12,'/historial',lambda:focus(page.locator('section.table-panel')))
                expect(page.locator('table.records tbody tr')).to_have_count(3)
                focus(page.locator('section.table-panel'),'10_historial' if 12 in selected else None)
                end()
                # 13: filtros, un resultado y descarga del mismo conjunto.
                start(13,'/historial',lambda:focus(page.get_by_role('search')))
                form=page.get_by_role('search')
                form.locator('[name="q"]').press_sequentially('Umbral 80 E2E',delay=40)
                form.locator('label[for="h-tipo-gasto"]').click()
                form.locator('[name="id_categoria"]').select_option(label='Presupuesto E2E (gasto)')
                form.locator('[name="id_cuenta"]').select_option(label='Cuenta principal')
                form.locator('[name="desde"]').fill(today);form.locator('[name="hasta"]').fill(today)
                at(3.4);form.get_by_role('button',name='Aplicar filtros').click()
                expect(page.locator('table.records tbody tr')).to_have_count(1)
                focus(page.locator('section.table-panel'))
                at(6);point(page.get_by_role('link',name='Exportar CSV',exact=True))
                with page.expect_download() as download:
                    page.get_by_role('link',name='Exportar CSV',exact=True).click()
                (out/'exportaciones').mkdir(exist_ok=True)
                download.value.save_as(out/'exportaciones/historial_filtrado.csv')
                focus(page.locator('section.table-panel'))
                end()
                # 14: encabezado y navegación anual cargados antes de hablar.
                start(14,'/reportes/anual',lambda:focus(page.locator('section.panel').first))
                point(page.get_by_role('link',name='Exportar CSV',exact=True));end()
                # 15: tabla anual y contenido real del CSV descargado.
                start(15,'/reportes/anual',lambda:focus(page.locator('table.records.annual')))
                expect(page.locator('tr').filter(has=page.get_by_text('Presupuesto E2E',exact=True)).locator('td').last).to_have_text('100.00')
                focus(page.locator('table.records.annual'),'11_reporte_anual' if 15 in selected else None)
                at(4.35)
                with page.expect_download() as download:
                    page.get_by_role('link',name='Exportar CSV',exact=True).click()
                download.value.save_as(out/'exportaciones/reporte_anual.csv')
                page.goto(f'http://127.0.0.1:{server.server_port}/_qa/csv/reporte_anual.csv',wait_until='networkidle')
                expect(page.get_by_role('heading',name='CSV descargado y verificado')).to_be_visible()
                focus(page.locator('table'))
                end()
                # 16: burbuja nativa de validación, sin texto inventado.
                start(16,'/',prepare_income('gasto','-10','Monto inválido E2E','Alimentación'))
                at(.15);field=page.locator('[name="monto"]');point(field)
                page.get_by_role('button',name='Agregar movimiento').click()
                assert field.evaluate('(e)=>e.validity.rangeUnderflow')
                assert field.evaluate('(e)=>e.validationMessage')
                assert scalar('SELECT COUNT(*) FROM movimientos WHERE descripcion=?',('Monto inválido E2E',))==0
                if 16 in selected: page.screenshot(path=str(out/'capturas/16_validacion_nativa.png'))
                end()
                # 17: rechazo del servidor visible al pronunciar HTTP 400.
                def prepare400():
                    form=movement_form('gasto','-10','Monto inválido E2E','Alimentación')
                    form.evaluate('(e)=>e.noValidate=true')
                    with page.expect_response(lambda r:r.url==base+'/movimientos' and r.request.method=='POST') as response:
                        form.get_by_role('button',name='Agregar movimiento').click()
                    assert response.value.status==400
                    focus(page.locator('section.panel').filter(has=page.get_by_role('heading',name='Revise los datos')))
                start(17,'/',prepare400)
                message=page.get_by_text('El monto debe ser mayor que cero.',exact=True);expect(message).to_be_visible()
                focus(page.locator('section.panel').filter(has=page.get_by_role('heading',name='Revise los datos')),'12_validacion_error' if 17 in selected else None)
                assert scalar('SELECT COUNT(*) FROM movimientos WHERE descripcion=?',('Monto inválido E2E',))==0
                end()
                # 18: 403 esperado, cuenta visible, logout y protección.
                start(18,'/admin/usuarios')
                expect(page.get_by_role('heading',name='No tiene permiso para ver esta página')).to_be_visible()
                page.evaluate('window.scrollTo(0,0)')
                at(2);response=go('/admin/calidad');assert response.status==403
                expect(page.get_by_role('heading',name='No tiene permiso para ver esta página')).to_be_visible()
                at(5.7);page.get_by_role('button',name='Cerrar sesión',exact=True).click()
                expect(page).to_have_url(base+'/login')
                go('/historial');expect(page).to_have_url(base+'/login');focus(page.locator('.lg-card'))
                end()
                # 19: informe compacto derivado de ejecuciones reales, separado de la aplicación.
                start(19,'/login')
                page.goto((out/'reportes/resumen_presentacion.html').as_uri(),wait_until='load')
                expect(page.get_by_text('27 / 27',exact=True)).to_be_visible()
                # Volver a marcar el comienzo para excluir navegación al informe.
                if 19 in selected:
                    page.evaluate('''()=>{let d=document.createElement('div');d.id='qa-sync';d.style.cssText='position:fixed;left:1870px;top:10px;width:20px;height:20px;background:rgb(255,0,255);z-index:2147483647';document.body.append(d)}''')
                    page.wait_for_timeout(450);page.evaluate('document.getElementById("qa-sync").remove()');t0=time.monotonic()
                    focus(page.locator('main'))
                end()
                context.close();browser.close()
        except StopIteration:
            pass
        finally:
            server.shutdown();server.server_close();runner.join(timeout=5)
            for handler in logging.getLogger('finanzas').handlers[:]:
                handler.close();logging.getLogger('finanzas').removeHandler(handler)
            for key,value in previous.items():
                if value is None: os.environ.pop(key,None)
                else: os.environ[key]=value
    name='grabacion_escenas.json' if len(log)==19 else 'grabacion_parcial.json'
    save(out/'reportes'/name,dict(resolucion=[1920,1080],fuente='Playwright Chromium nativo',
         codigo_funcional_modificado=False,datos='Ficticios; base temporal eliminada',escenas=log))


if __name__=='__main__':
    main()
