"""Aplicación web mínima, construida solo con Python estándar y SQLite.

Uso local: python -m src.app
Autenticación local incluida; no desplegar directamente en Internet.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import hmac
import threading
import time
from http.cookies import SimpleCookie
import base64
import io
import mimetypes
import secrets
import shutil
from email.parser import BytesParser
from email.policy import default
import json
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import re
from datetime import date
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from src import db, extension, finance, request_ctx

LOG_DIR=db.db_path().parent / 'logs'
LOG_DIR.mkdir(parents=True,exist_ok=True)
logger=logging.getLogger('finanzas')
logger.setLevel(logging.ERROR)
if not logger.handlers:
    log_handler=RotatingFileHandler(LOG_DIR/'errores.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')
    log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(log_handler)

def error_page(title, message):
    return layout('<section class="panel" role="alert"><h2>'+e(title)+'</h2><p>'+e(message)+'</p><p>Intente nuevamente en unos momentos. Si el problema continúa, contacte al administrador.</p><a href="/">Volver al inicio</a></section>').encode('utf-8')

def request_is_admin() -> bool:
    """Rol de la solicitud en curso (False sin sesión). Solo decide qué enlaces muestra la interfaz;
    la autorización real se valida en cada ruta con Handler.is_admin().
    El estado vive en src.request_ctx para que sea único aunque este módulo se cargue dos veces."""
    return request_ctx.is_admin()

def forbidden_page():
    """Página 403 con el diseño de la aplicación (sin cambiar el código de estado)."""
    return layout('<section class="panel denied" role="alert"><div class="denied-icon" aria-hidden="true">🔒</div><p class="eyebrow">ERROR 403 · ACCESO RESTRINGIDO</p><h2>No tiene permiso para ver esta página</h2><p>Esta sección está reservada para administradores. Su cuenta no cuenta con los permisos necesarios para acceder a ella.</p><p class="help">Si considera que debería tener acceso, solicite a un administrador que revise su rol.</p><div class="denied-actions"><a class="denied-btn primary" href="/">← Volver al panel principal</a><a class="denied-btn" href="/admin/cambiar-clave">Cambiar mi contraseña</a></div></section>').encode('utf-8')

AUTH_LOCK=threading.Lock()
SESSIONS={}
def auth_file():
    # Separa credenciales por DB_PATH; evita contaminar datos de prueba.
    return db.db_path().parent / 'login_credentials.json'
def hash_password(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000).hex()
def credentials():
    if not auth_file().exists():
        auth_file().parent.mkdir(parents=True,exist_ok=True)
        initial = os.environ.get('FINANZAS_INITIAL_ADMIN_PASSWORD', '')
        if app_base_path() and len(initial) < 12:
            raise RuntimeError('Configure FINANZAS_INITIAL_ADMIN_PASSWORD (12 caracteres o más) antes de iniciar la instancia web')
        # Contraseña histórica predeterminada solo para el prototipo localhost.
        initial = initial or 'Admin12345!'
        salt=secrets.token_hex(16)
        save_users([{'username':'admin','name':'Administrador','role':'admin','active':True,'salt':salt,'hash':hash_password(initial,salt)}])
    data=json.loads(auth_file().read_text(encoding='utf-8'))
    if isinstance(data,dict) and 'users' not in data:
        data={'users':[{'username':data['username'],'name':'Administrador','role':'admin','active':True,'salt':data['salt'],'hash':data['hash']}]}
        save_users(data['users'])
    return data['users']

def save_users(users):
    temp=auth_file().with_suffix('.tmp')
    temp.write_text(json.dumps({'users':users},ensure_ascii=False,indent=2),encoding='utf-8')
    try: os.chmod(temp,0o600)
    except OSError: pass
    temp.replace(auth_file())

def user_by_name(name):
    return next((u for u in credentials() if u['username']==name),None)

def users_page(message='',error=False,editing=''):
    users=credentials()
    selected=next((u for u in users if u['username']==editing),None)
    notice=('<p role="alert" style="color:'+('#b91c1c' if error else '#166534')+'">'+e(message)+'</p>') if message else ''
    rows=''.join('<tr><td>'+e(u['username'])+'</td><td>'+e(u['name'])+'</td><td>'+e(u['role'])+'</td><td>'+('Activo' if u['active'] else 'Inactivo')+'</td><td><a href="/admin/usuarios?editar='+e(u['username'])+'">Editar</a></td></tr>' for u in users)
    form=f"""<form method="post" action="/admin/usuarios/guardar" class="form-grid">
    <label>Usuario<input name="username" maxlength="40" pattern="[A-Za-z0-9_.-]+" value="{e(selected['username']) if selected else ''}" {'readonly' if selected else 'required'}></label>
    <label>Nombre completo<input name="name" maxlength="100" value="{e(selected['name']) if selected else ''}" required></label>
    <label>Rol<select name="role"><option value="usuario" {'selected' if not selected or selected['role']=='usuario' else ''}>Usuario</option><option value="admin" {'selected' if selected and selected['role']=='admin' else ''}>Administrador</option></select></label>
    <label>Estado<select name="active"><option value="1" {'selected' if not selected or selected['active'] else ''}>Activo</option><option value="0" {'selected' if selected and not selected['active'] else ''}>Inactivo</option></select></label>
    <label>{'Nueva contraseña (dejar vacío para conservar)' if selected else 'Contraseña inicial'}<input name="password" type="password" minlength="8" maxlength="128" {'required' if not selected else ''}></label>
    <button class="primary" type="submit">Guardar usuario</button><a href="/admin/usuarios">Cancelar</a></form>"""
    return layout('<section class="panel"><h2>Mantenimiento de usuarios</h2><p>Solo administradores pueden crear y modificar usuarios. Las contraseñas se almacenan con hash.</p>'+notice+'<table><thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead><tbody>'+rows+'</tbody></table><h3>'+('Editar usuario' if selected else 'Nuevo usuario')+'</h3>'+form+'</section>')

def change_password_page(message='',error=False):
    notice=('<p role="alert" style="color:'+('#b91c1c' if error else '#166534')+'">'+e(message)+'</p>') if message else ''
    return layout('<section class="panel"><h2>Cambiar mi contraseña</h2><p>Escriba su nueva contraseña y confírmela. Por seguridad, el sistema no genera ni muestra contraseñas nuevas: la nueva será exactamente la que usted introduzca. Después deberá iniciar sesión de nuevo.</p>'+notice+'<form method="post" action="/admin/cambiar-clave" class="form-grid"><label>Contraseña actual<input type="password" name="actual" required></label><label>Nueva contraseña<input type="password" name="nueva" minlength="8" required></label><label>Confirmar contraseña<input type="password" name="confirmar" minlength="8" required></label><button class="primary">Cambiar contraseña</button></form></section>')

def login_page(error=''):
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ingresar - Finanzas Familiares</title><link rel="stylesheet" href="/static/styles.css"></head>'
            '<body class="login-body"><div class="lg-bg" aria-hidden="true"><span class="lg-orb lg-orb-1"></span><span class="lg-orb lg-orb-2"></span><span class="lg-orb lg-orb-3"></span><span class="lg-orb lg-orb-4"></span></div>'
            '<main class="lg-wrap"><section class="lg-card" aria-labelledby="lg-title"><div class="lg-brand"><span class="lg-logo" aria-hidden="true">₡</span><span>Finanzas Familiares</span></div>'
            '<h1 id="lg-title">Iniciar sesión</h1><p class="lg-sub">Ingrese sus credenciales para acceder al sistema.</p>'
            +('<p class="lg-alert" role="alert">'+e(error)+'</p>' if error else '')+
            '<form method="post" action="/login" class="lg-form"><label>Usuario<input class="lg-input" name="usuario" required autocomplete="username" autofocus></label>'
            '<label>Contraseña<input class="lg-input" name="contrasena" type="password" required autocomplete="current-password"></label>'
            '<button class="lg-btn" type="submit">Ingresar</button></form><p class="lg-forgot"><a href="/olvide-clave">¿Olvidó su contraseña?</a></p></section></main></body></html>')

def forgot_password_page():
    """Recuperación sin correo: la contraseña solo la restablece un administrador."""
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Recuperar contraseña - Finanzas Familiares</title><link rel="stylesheet" href="/static/styles.css"></head>'
            '<body class="login-body"><div class="lg-bg" aria-hidden="true"><span class="lg-orb lg-orb-1"></span><span class="lg-orb lg-orb-2"></span><span class="lg-orb lg-orb-3"></span><span class="lg-orb lg-orb-4"></span></div>'
            '<main class="lg-wrap"><section class="lg-card" aria-labelledby="lg-title"><div class="lg-brand"><span class="lg-logo" aria-hidden="true">₡</span><span>Finanzas Familiares</span></div>'
            '<h1 id="lg-title">¿Olvidó su contraseña?</h1><p class="lg-sub">Por seguridad, las contraseñas no se pueden consultar ni enviar por correo. Un administrador puede asignarle una nueva.</p>'
            '<ol class="lg-steps"><li>Comuníquese con un administrador del sistema e indíquele su nombre de usuario.</li>'
            '<li>El administrador la restablece en <strong>Seguridad → Mantenimiento de usuarios</strong>.</li>'
            '<li>Ingrese con la contraseña temporal y cámbiela de inmediato en <strong>Seguridad → Cambiar contraseña</strong>.</li></ol>'
            '<p class="lg-note">Si la contraseña olvidada es la de un administrador y no hay otro disponible, la recuperación requiere acceso al servidor donde se ejecuta la aplicación.</p>'
            '<a class="lg-btn lg-btn-link" href="/login">← Volver a iniciar sesión</a></section></main></body></html>')

def app_base_path() -> str:
    """Prefijo público cuando la app vive bajo /finanzas (proxy inverso)."""
    raw = os.environ.get('APP_BASE_PATH', '').strip().rstrip('/')
    if raw and not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)+', raw):
        raise ValueError('APP_BASE_PATH debe ser una ruta como /finanzas')
    return raw


def external_path(path: str) -> str:
    prefix = app_base_path()
    if not prefix or path.startswith(prefix + '/') or path == prefix:
        return path
    return prefix + path if path.startswith('/') else path


def internal_path(path: str) -> str:
    prefix = app_base_path()
    if prefix and (path == prefix or path.startswith(prefix + '/')):
        return path[len(prefix):] or '/'
    return path


def prefix_html(body: bytes) -> bytes:
    prefix = app_base_path()
    if not prefix:
        return body
    html = body.decode('utf-8')
    # Adaptar rutas absolutas de href/action/src sin tocar URLs externas ni datos.
    html = re.sub(r'((?:href|action|src)=")/(?!/)',
                  lambda match: match.group(1) + prefix + '/', html)
    return html.encode('utf-8')


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
    # Opciones de administración visibles solo para administradores (las rutas se protegen aparte).
    security_links = ('<a href="/admin/usuarios">Mantenimiento de usuarios</a><a href="/perfiles">Mantenimiento de perfiles</a>'
                      if request_is_admin() else '')
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finanzas Familiares · Grupo 5</title><link rel="stylesheet" href="/static/styles.css"></head>
<body><header class="topbar"><div class="shell top-inner"><div class="brand"><span class="brand-icon">₡</span><span><strong>Finanzas Familiares</strong><small>Proyecto open source · Grupo 5</small></span></div><span class="top-badge">SQLite · MVP local</span></div></header>
<main class="shell"><nav class="main-nav" aria-label="Menú principal"><a class="nav-home" href="/">⌂ Resumen</a><details class="nav-group"><summary>Operaciones</summary><div class="nav-drop"><a href="/">Ingresos y gastos</a><a href="/admin/transferencias">Transferencias</a><a href="/admin/movimientos_ahorro">Movimientos de ahorro</a><a href="/comprobantes">Comprobantes</a></div></details><details class="nav-group"><summary>Planificación</summary><div class="nav-drop"><a href="/admin/presupuestos">Presupuestos</a><a href="/admin/metas_ahorro">Metas de ahorro</a><a href="/admin/alertas">Alertas</a></div></details><details class="nav-group"><summary>Catálogos</summary><div class="nav-drop"><a href="/admin/cuentas">Cuentas</a><a href="/admin/categorias">Categorías</a><a href="/admin/monedas">Monedas</a></div></details><details class="nav-group"><summary>Seguridad</summary><div class="nav-drop">{security_links}<a href="/admin/cambiar-clave">Cambiar contraseña</a></div></details><form method="post" action="/logout" style="display:inline"><button type="submit">Cerrar sesión</button></form></nav><section class="hero"><div><p class="eyebrow">PANEL FINANCIERO</p><h1>Un panorama claro de tu dinero.</h1><p>Movimientos, presupuestos y alertas en una sola página. {e(subtitle)}</p></div><span class="hero-art" aria-hidden="true">↗</span></section>{content}</main>
<footer class="shell footer">Datos de demostración ficticios · Sin cuentas reales · UNA · II-2026</footer>
<script>
const tipo = document.getElementById('tipo'); const categoria = document.getElementById('id_categoria');
function filtrar(){{if(!tipo||!categoria)return; const all=[...categoria.options];
 let visible=all.filter(o=>o.dataset.tipo===tipo.value); for(const o of all)o.hidden=o.dataset.tipo!==tipo.value;
 if(!visible.includes(categoria.selectedOptions[0])&&visible.length)categoria.value=visible[0].value;}}
if(tipo){{tipo.addEventListener('change',filtrar);filtrar();}}
// Impide dobles envíos por clics repetidos; no realiza reintentos automáticos.
for(const form of document.querySelectorAll('form[method="post"]')){{
  form.addEventListener('submit',ev=>{{
    if(form.dataset.enviando==='1'){{ev.preventDefault();return;}}
    if(ev.defaultPrevented)return;
    form.dataset.enviando='1';
    const submit=form.querySelector('button[type="submit"],button:not([type]),input[type="submit"]');
    if(submit){{submit.setAttribute('aria-disabled','true');submit.dataset.textoOriginal=submit.textContent;submit.textContent='Procesando…';}}
  }});
}}
for(const b of document.querySelectorAll('[data-confirm]'))b.addEventListener('click',ev=>{{if(!confirm('¿Eliminar este movimiento?'))ev.preventDefault();}});
// Menú principal: un solo desplegable abierto a la vez; se cierra al hacer clic fuera o con Escape.
const grupos=[...document.querySelectorAll('.main-nav details.nav-group')];
for(const g of grupos)g.addEventListener('toggle',()=>{{if(g.open)for(const o of grupos)if(o!==g)o.open=false;}});
document.addEventListener('click',ev=>{{for(const g of grupos)if(g.open&&!g.contains(ev.target))g.open=false;}});
document.addEventListener('keydown',ev=>{{if(ev.key==='Escape')for(const g of grupos)g.open=false;}});
</script></body></html>'''


def dashboard_page(query: dict) -> str:
    today = date.today()
    try:
        year = int(query.get('anio', [today.year])[0]); month = int(query.get('mes', [today.month])[0])
        if not (2020 <= year <= 2100 and 1 <= month <= 12): raise ValueError
    except ValueError:
        year, month = today.year, today.month
    extension.refresh_alerts()
    data = db.dashboard(year, month)
    movement_edit = None
    try:
        movement_edit = db.get_movement(int(query.get('editar', ['0'])[0]))
    except ValueError:
        pass
    categories, accounts = data['categories'], data['accounts']
    with db.connect() as c:
        account_currency = {str(r['id_cuenta']): r['codigo_iso'] for r in c.execute('SELECT a.id_cuenta,m.codigo_iso FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda')}

    kind = movement_edit['tipo'] if movement_edit else 'gasto'
    cat_selected = movement_edit['id_categoria'] if movement_edit else None
    acc_selected = movement_edit['id_cuenta'] if movement_edit else accounts[0]['id_cuenta']
    amount = f"{movement_edit['monto_centimos']/100:.2f}" if movement_edit else ''
    tx_date = movement_edit['fecha'] if movement_edit else today.isoformat()
    currency_selected = account_currency.get(str(acc_selected), 'CRC')
    description = movement_edit['descripcion'] if movement_edit else ''
    action = f'/movimientos/{movement_edit["id_movimiento"]}/actualizar' if movement_edit else '/movimientos'
    budget_html = ''
    for p in data['budgets']:
        pct = round(p['gastado'] / p['limite'] * 100) if p['limite'] else 0
        status = 'Excedido' if pct >= 100 else ('Cerca del límite' if pct >= 80 else 'Bajo control')
        status_class = 'danger' if pct >= 100 else ('warning' if pct >= 80 else 'ok')
        budget_html += f'''<div class="budget-line"><div class="budget-head"><strong>{e(p['categoria'])}</strong><span class="pill {status_class}">{status}</span></div>
        <div class="budget-values"><span>{finance.format_amount(p['gastado'],p['simbolo'])} utilizados</span><span>de {finance.format_amount(p['limite'],p['simbolo'])}</span></div>
        <div class="track"><div class="fill {status_class}" style="width:{min(pct,100)}%"></div></div>{f"<small>Faltan tipos de cambio para {p['missing']} gastos; total parcial.</small>" if p['missing'] else ""}</div>'''
    if not budget_html:
        budget_html = '<p class="muted">Todavía no se han definido presupuestos para este mes.</p>'
    rows = ''
    for tx in data['movements']:
        symbol = '+' if tx['tipo'] == 'ingreso' else '−'
        css_class = 'income' if tx['tipo'] == 'ingreso' else 'expense'
        desc = tx['descripcion'] or tx['categoria']
        rows += f'''<tr><td><strong>{e(desc)}</strong><small>{e(tx['categoria'])} · {e(tx['cuenta'])}</small></td>
        <td>{e(tx['fecha'])}</td><td class="amount {css_class}">{symbol}{tx['monto_centimos']/100:,.2f} {e(account_currency.get(str(tx['id_cuenta']), ''))}</td>
        <td class="actions"><a href="/?editar={tx['id_movimiento']}&anio={year}&mes={month}">Editar</a>
        <form method="post" action="/movimientos/{tx['id_movimiento']}/eliminar"><button class="link-danger" data-confirm="true" type="submit">Eliminar</button></form></td></tr>'''
    if not rows:
        rows = '<tr><td colspan="4" class="empty">Aún no hay movimientos en el período seleccionado.</td></tr>'
    metric_rows = []
    for code, amounts in sorted(data['totals_by_currency'].items()):
        inc, exp = amounts['ingreso'], amounts['gasto']
        metric_rows.append(f'<tr><td>{e(code)}</td><td>{inc/100:,.2f}</td><td>{exp/100:,.2f}</td><td>{(inc-exp)/100:,.2f}</td></tr>')
    metrics_html = '<section class="panel"><h2>Resumen mensual por moneda</h2><p>Los montos no se suman entre monedas diferentes.</p><div class="table-scroll"><table><thead><tr><th>Moneda</th><th>Ingresos</th><th>Gastos</th><th>Balance</th></tr></thead><tbody>' + (''.join(metric_rows) or '<tr><td colspan="4">Sin movimientos este mes</td></tr>') + '</tbody></table></div></section>'
    with db.connect() as c:
        active=extension.active_profile(c)
        alert_count=c.execute('SELECT COUNT(*) FROM alertas WHERE id_usuario=? AND leida=0',(active,)).fetchone()[0]
    balances=''.join(f'<tr><td>{e(name)}</td><td>{e(code)}</td><td>{amount/100:,.2f}</td></tr>' for name,code,amount in finance.all_balances())
    content = f'''
    <section class="panel"><h2>Saldos por cuenta</h2><p>Incluye ingresos, gastos, transferencias y ahorros. Cada saldo está en su propia moneda.</p><table><tr><th>Cuenta</th><th>Moneda</th><th>Saldo</th></tr>{balances}</table></section>
    <section class="notice-strip"><span>🔔 <strong>{alert_count}</strong> alertas pendientes</span><a href="/admin/alertas">Ver alertas →</a><span>Perfil activo: <strong>{e(extension.profile_name())}</strong></span>{'<a href="/perfiles">Cambiar perfil</a>' if request_is_admin() else ''}</section>
    <form class="period" method="get"><label>Período <input type="month" name="periodo" value="{year:04d}-{month:02d}" aria-label="Mes de consulta" onchange="const a=this.value.split('-');document.getElementById('anio').value=a[0];document.getElementById('mes').value=Number(a[1]);this.form.submit()"></label>
    <input type="hidden" id="anio" name="anio" value="{year}"><input type="hidden" id="mes" name="mes" value="{month}"><button class="secondary" type="submit">Actualizar</button></form>
    {metrics_html}
    <section class="columns"><article class="panel"><div class="panel-title"><div><p class="eyebrow">REGISTRO</p><h2>{'Editar movimiento' if movement_edit else 'Nuevo movimiento'}</h2></div>{'<a href="/">Cancelar</a>' if movement_edit else ''}</div>
    <form action="{action}" method="post" class="form-grid"><label>Tipo<select name="tipo" id="tipo"><option value="gasto" {'selected' if kind=='gasto' else ''}>Gasto</option><option value="ingreso" {'selected' if kind=='ingreso' else ''}>Ingreso</option></select></label>
    <label>Monto (<span id="moneda-monto">{e(currency_selected)}</span>)<input name="monto" type="number" min="0.01" step="0.01" required value="{e(amount)}" placeholder="25000.00"></label>
    <label>Categoría<select name="id_categoria" id="id_categoria" required>{option_rows(categories, cat_selected)}</select></label>
    <label>Cuenta<select name="id_cuenta" id="cuenta-movimiento" required>{option_rows(accounts, acc_selected)}</select></label>
    <p class="help span2">El ingreso o gasto se registra directamente en la moneda de la cuenta, sin conversión.</p>
    <script>const monedasCuentas={__import__('json').dumps(account_currency)};const cuentaMov=document.getElementById('cuenta-movimiento');const cambiarMoneda=()=>document.getElementById('moneda-monto').textContent=monedasCuentas[cuentaMov.value]||'—';cuentaMov.addEventListener('change',cambiarMoneda);cambiarMoneda();</script>
    <label>Fecha<input name="fecha" type="date" required value="{e(tx_date)}"></label>
    <label>Descripción<input name="descripcion" maxlength="160" value="{e(description)}" placeholder="Ej. Compras del supermercado"></label>
    <button type="submit" class="primary span2">{'Guardar cambios' if movement_edit else 'Agregar movimiento'}</button></form></article>
    <article class="panel"><div class="panel-title"><div><p class="eyebrow">CONTROL MENSUAL</p><h2>Presupuestos y alertas</h2></div></div>{budget_html}
    <div class="subform"><h3>Crear o actualizar límite</h3><form method="post" action="/presupuestos" class="form-grid"><label class="span2">Categoría<select name="id_categoria" required>{option_rows(categories, None, 'gasto')}</select></label>
    <label>Monto máximo (moneda elegida)<input name="monto_limite" type="number" min="0.01" step="0.01" placeholder="50000.00" required></label>
    <label>Moneda del presupuesto<select name="id_moneda">{extension.currency_options()}</select></label><input type="hidden" name="anio" value="{year}"><input type="hidden" name="mes" value="{month}"><button class="primary" type="submit">Guardar límite</button></form>
    <p class="help">Una alerta aparece al alcanzar el 80 % del presupuesto de una categoría.</p></div></article></section>
    <section class="panel table-panel"><div class="panel-title"><div><p class="eyebrow">HISTORIAL</p><h2>Movimientos del período</h2></div><span class="pill neutral">Últimos 100</span></div>
    <div class="table-scroll"><table><thead><tr><th>Descripción / categoría</th><th>Fecha</th><th>Monto</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="foot-note">Prototipo académico local · perfiles sin contraseña ni aislamiento de seguridad · No exponer a Internet.</section>
    '''
    return layout(content, subtitle='Datos sintéticos para la demostración del curso.')


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, body: bytes, content_type: str = 'text/html; charset=utf-8') -> None:
        if content_type.startswith('text/html'):
            body = prefix_html(body)
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store' if status >= 400 else 'private, no-cache')
        if status >= 500:
            self.send_header('Retry-After', '30')
        self.end_headers()
        self.wfile.write(body)

    def redirect(self) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', external_path('/'))
        self.send_header('Content-Length', '0')
        self.end_headers()

    def redirect_to(self, path):
        self.send_response(303)
        self.send_header('Location',external_path(path))
        self.send_header('Content-Length','0')
        self.end_headers()

    def session_token(self):
        try:
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
            return cookie['finanzas_session'].value if 'finanzas_session' in cookie else ''
        except Exception: return ''

    def authenticated(self):
        token=self.session_token()
        with AUTH_LOCK:
            entry=SESSIONS.get(token)
            if entry and entry[1]>time.time():
                user=user_by_name(entry[0])
                if user and user["active"]:
                    SESSIONS[token]=(entry[0],time.time()+8*3600)
                    return True
            SESSIONS.pop(token,None)
        return False

    def current_user(self):
        entry=SESSIONS.get(self.session_token())
        return user_by_name(entry[0]) if entry else None

    def is_admin(self):
        user=self.current_user()
        return bool(user and user['role']=='admin' and user['active'])

    def auth_redirect(self):
        self.redirect_to('/login')

    def prepare_request(self):
        """Fija el rol de esta solicitud para que layout() oculte las opciones de administración."""
        request_ctx.set_admin(self.authenticated() and self.is_admin())

    def do_GET(self) -> None:
        self.prepare_request()
        path = urlsplit(self.path)
        route = internal_path(path.path)
        try:
            if route == '/login':
                return self.redirect_to('/') if self.authenticated() else self.respond(200,login_page().encode('utf-8'))
            if route == '/olvide-clave':
                return self.respond(200,forgot_password_page().encode('utf-8'))
            if route != '/static/styles.css' and not self.authenticated(): return self.auth_redirect()
            if route == '/admin/usuarios':
                if not self.is_admin(): return self.respond(403,forbidden_page())
                return self.respond(200,users_page(editing=parse_qs(path.query).get('editar',[''])[0]).encode('utf-8'))
            if route == '/admin/cambiar-clave': return self.respond(200,change_password_page().encode('utf-8'))
            if route == '/static/styles.css':
                return self.respond(200, CSS_PATH.read_bytes(), 'text/css; charset=utf-8')
            if route == '/perfiles':
                if not self.is_admin(): return self.respond(403,forbidden_page())
                return self.respond(200, extension.profiles_page().encode('utf-8'))
            if route == '/comprobantes':
                return self.respond(200, extension.receipts_page().encode('utf-8'))
            if m := re.fullmatch(r'/comprobantes/(\d+)/archivo',route):
                receipt=extension.receipt_file(int(m.group(1)))
                if receipt is None: return self.respond(404,b'Archivo no encontrado','text/plain')
                data,mime=receipt
                return self.respond(200,data,mime)
            if route == '/health':
                with db.connect() as connection:
                    ver = connection.execute('SELECT sqlite_version()').fetchone()[0]
                    tables = connection.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"').fetchone()[0]
                return self.respond(200, json.dumps({'status':'ok','motor':'SQLite','version':ver,'tablas':tables}).encode(), 'application/json')
            if m := re.fullmatch(r'/admin/([a-z_]+)', route):
                edit_id=int(parse_qs(path.query).get('editar',['0'])[0]) or None
                return self.respond(200, extension.page(m.group(1),edit_id).encode('utf-8'))
            if route in ('/', '/index.html'):
                query = parse_qs(path.query)
                return self.respond(200, dashboard_page(query).encode('utf-8'))
            return self.respond(404, layout('<section class="panel"><h2>Página no encontrada</h2><a href="/">Volver al inicio</a></section>').encode())
        except sqlite3.Error:
            logger.exception('Error SQLite durante GET %s',route)
            return self.respond(503,error_page('Base de datos no disponible','No se pudo consultar la información en este momento.'))
        except Exception:
            logger.exception('Error inesperado durante GET %s',route)
            return self.respond(500,error_page('Error temporal','No fue posible completar la solicitud.'))

    def do_POST(self) -> None:
        self.prepare_request()
        path = internal_path(urlsplit(self.path).path)
        length = int(self.headers.get('Content-Length','0'))
        if length < 0 or length > 6_000_000:
            return self.respond(413, b'Formulario demasiado grande', 'text/plain; charset=utf-8')
        try:
            if path == '/logout':
                with AUTH_LOCK: SESSIONS.pop(self.session_token(),None)
                self.send_response(303);self.send_header('Location',external_path('/login'));self.send_header('Set-Cookie',f'finanzas_session=; HttpOnly; SameSite=Strict; Path={app_base_path() or chr(47)}; Max-Age=0');self.send_header('Content-Length','0');self.end_headers();return
            payload=self.rfile.read(length)
            if path == '/login':
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8')).items()}
                creds=user_by_name(form.get('usuario',''))
                if creds and creds['active'] and hmac.compare_digest(form.get('usuario',''),creds['username']) and hmac.compare_digest(hash_password(form.get('contrasena',''),creds['salt']),creds['hash']):
                    token=secrets.token_urlsafe(32)
                    with AUTH_LOCK: SESSIONS[token]=(creds["username"],time.time()+8*3600)
                    self.send_response(303);self.send_header('Location',external_path('/'));self.send_header('Set-Cookie',f'finanzas_session={token}; HttpOnly; SameSite=Strict; Path={app_base_path() or chr(47)}; Max-Age=28800');self.send_header('Content-Length','0');self.end_headers();return
                return self.respond(401,login_page('Usuario o contraseña incorrectos').encode('utf-8'))
            if not self.authenticated(): return self.auth_redirect()
            if path == '/admin/usuarios/guardar':
                if not self.is_admin(): return self.respond(403,forbidden_page())
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8'),keep_blank_values=True).items()}
                username=form.get('username','').strip(); name=form.get('name','').strip()
                role=form.get('role'); active=form.get('active')=='1'; password=form.get('password','')
                with AUTH_LOCK:
                    users=credentials(); existing=next((u for u in users if u['username']==username),None)
                    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,40}',username) or not 1<=len(name)<=100 or role not in ('admin','usuario') or (password and not 8<=len(password)<=128) or (not existing and not password):
                        return self.respond(400,users_page('Revise los datos y la contraseña (mínimo 8 caracteres).',True).encode())
                    if existing and existing['role']=='admin' and existing['active'] and (role!='admin' or not active) and sum(u['role']=='admin' and u['active'] for u in users)<=1:
                        return self.respond(400,users_page('Debe existir al menos un administrador activo.',True).encode())
                    if existing:
                        existing.update(name=name,role=role,active=active)
                        target=existing
                    else:
                        target={'username':username,'name':name,'role':role,'active':active}
                        users.append(target)
                    if password:
                        salt=secrets.token_hex(16);target.update(salt=salt,hash=hash_password(password,salt))
                    save_users(users)
                    SESSIONS.clear()
                return self.redirect_to('/login')
            if path == '/admin/cambiar-clave':
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8'),keep_blank_values=True).items()}
                current=self.current_user()
                if not current or not hmac.compare_digest(hash_password(form.get('actual',''),current['salt']),current['hash']):
                    return self.respond(400,change_password_page('La contraseña actual es incorrecta.',True).encode())
                new=form.get('nueva','')
                if not 8<=len(new)<=128 or new!=form.get('confirmar',''):
                    return self.respond(400,change_password_page('La nueva contraseña debe coincidir y tener entre 8 y 128 caracteres.',True).encode())
                with AUTH_LOCK:
                    users=credentials(); target=next(u for u in users if u['username']==current['username'])
                    salt=secrets.token_hex(16);target.update(salt=salt,hash=hash_password(new,salt))
                    save_users(users);SESSIONS.clear()
                return self.redirect_to('/login')
            if path == '/comprobantes/subir':
                extension.upload_receipt(payload,self.headers.get('Content-Type',''))
                return self.redirect_to('/comprobantes')
            posted = parse_qs(payload.decode('utf-8'), keep_blank_values=True)
            form = {key: vals[0] for key, vals in posted.items()}
            if path == '/perfiles/seleccionar':
                if not self.is_admin(): return self.respond(403,forbidden_page())
                extension.select_profile(form)
                return self.redirect_to('/perfiles')
            if m := re.fullmatch(r'/comprobantes/(\d+)/eliminar',path):
                extension.delete_receipt(int(m.group(1)))
                return self.redirect_to('/comprobantes')
            if m := re.fullmatch(r'/admin/([a-z_]+)(?:/(\d+))?/(guardar|eliminar)', path):
                table,item_id,action=m.group(1),int(m.group(2)) if m.group(2) else None,m.group(3)
                if table=='usuarios' and not self.is_admin(): return self.respond(403,forbidden_page())
                if action=='eliminar':
                    if item_id is None: raise ValueError('Falta el identificador')
                    extension.delete(table,item_id)
                else: extension.save(table,form,item_id)
                extension.refresh_alerts()
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header('Location',external_path(f'/admin/{table}'))
                self.send_header('Content-Length','0')
                self.end_headers()
                return
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
            extension.refresh_alerts()
            self.redirect()
        except (ValueError, UnicodeDecodeError) as exc:
            self.respond(400, layout(f'<section class="panel"><h2>Revise los datos</h2><p>{e(exc)}</p><p><a href="/">Volver al inicio</a></p></section>').encode('utf-8'))
        except sqlite3.Error:
            logger.exception('Error SQLite durante POST %s',path)
            self.respond(503,error_page('No se pudo guardar','La base de datos no está disponible. No se confirmó el registro; compruebe los datos antes de reintentar.'))
        except Exception:
            logger.exception('Error inesperado durante POST %s',path)
            self.respond(500,error_page('No se pudo completar la operación','Ocurrió un problema inesperado.'))


def main() -> None:
    parser = argparse.ArgumentParser(description='Finanzas Familiares - Grupo 5')
    parser.add_argument('--host', default='127.0.0.1', help='Escuchar solo en localhost por defecto')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    try:
        db.init_db()
        extension.init()
        credentials()
    except (sqlite3.Error, OSError) as exc:
        logger.exception('Error al iniciar aplicación')
        parser.exit(1,'No se pudo iniciar: revise el acceso a SQLite y el archivo logs/errores.log.\n')
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
