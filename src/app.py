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
from functools import wraps
from datetime import date, timedelta
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from src import db, extension, finance, request_ctx, auth, profiles, read_cache, quality, reportes, recurrentes

LOG_DIR=db.db_path().parent / 'logs'
logger=logging.getLogger('finanzas')
logger.setLevel(logging.ERROR)
if not logger.handlers:
    try:
        LOG_DIR.mkdir(parents=True,exist_ok=True)
        log_handler=RotatingFileHandler(LOG_DIR/'errores.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8')
    except OSError:
        log_handler=logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(log_handler)

def error_page(title, message):
    return layout('<section class="panel denied" role="alert"><div class="denied-icon" aria-hidden="true">!</div><h2>'+e(title)+'</h2><p>'+e(message)+'</p><p class="help">Si el problema continúa, contacte al administrador. Los detalles técnicos quedaron registrados para su revisión.</p><a class="denied-btn primary" href="/">Volver al inicio</a></section>').encode('utf-8')


def controlled_request(method):
    """Una sola frontera de errores, incluida la autenticación que consulta SQLite."""
    @wraps(method)
    def handle(self):
        request_ctx.set_admin(False)
        request_ctx.set_user_id(1)
        request_ctx.set_identity()
        try:
            self.connection.settimeout(10)
            return method(self)
        except (BrokenPipeError, ConnectionResetError):
            logger.info('Cliente desconectado durante %s', self.command)
            return
        except profiles.AccessDenied:
            status, title, message = 403, 'Acceso restringido', 'No tiene permiso para esta operación en el perfil seleccionado.'
        except sqlite3.IntegrityError as exc:
            logger.exception('Restricción SQLite durante %s', self.command)
            status, title = 409, 'No se pudo realizar el cambio'
            code = getattr(exc, 'sqlite_errorname', '')
            if code in ('SQLITE_CONSTRAINT_UNIQUE', 'SQLITE_CONSTRAINT_PRIMARYKEY'):
                message = 'Ya existe un registro con esos datos. Revise la información antes de guardar.'
            elif code == 'SQLITE_CONSTRAINT_FOREIGNKEY':
                message = 'El registro está relacionado con otros datos o una referencia ya no está disponible. Revise sus relaciones antes de cambiarlo.'
            else:
                message = 'Los datos no cumplen las reglas del registro. Revise los campos e intente nuevamente.'
        except sqlite3.Error as exc:
            logger.exception('Error SQLite durante %s', self.command)
            status, title = 503, 'Base de datos no disponible'
            code = getattr(exc, 'sqlite_errorcode', 0) or 0
            if (code & 255) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                message = 'La base de datos está ocupada. Espere unos segundos y vuelva a intentarlo.'
            elif (code & 255) == sqlite3.SQLITE_INTERRUPT:
                message = 'La consulta superó el tiempo permitido y se detuvo. Intente una operación más pequeña.'
            else:
                message = 'No fue posible acceder a los datos en este momento.'
            if self.command == 'POST':
                message += ' Compruebe si el cambio se guardó antes de volver a enviarlo.'
        except (OSError, TimeoutError):
            logger.exception('Error de almacenamiento o espera durante %s', self.command)
            status, title = 503, 'No se pudo completar la operación'
            message = 'El almacenamiento no está disponible o la espera terminó. Compruebe el resultado antes de volver a intentarlo.'
        except ValueError:
            logger.exception('Solicitud inválida durante %s', self.command)
            status, title, message = 400, 'Revise los datos', 'Hay un campo con formato incorrecto. Revise la información ingresada.'
        except Exception:
            logger.exception('Error inesperado durante %s', self.command)
            status, title, message = 500, 'No se pudo completar la operación', 'Ocurrió un problema inesperado. Compruebe el resultado antes de volver a intentarlo.'
        try:
            if status == 503 and self.command == 'GET' and self.serve_stale():
                return
            return self.respond(status, error_page(title, message))
        except (OSError, TimeoutError):
            logger.info('No se pudo entregar la respuesta de error al cliente')
    return handle

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
# La persistencia de autenticacion vive en SQLite.
hash_password = auth.hash_password
credentials = auth.credentials
save_users = auth.save_users


def user_by_name(name):
    return next((u for u in credentials() if u['username']==name),None)

def users_page(message='',error=False,editing=''):
    users=credentials()
    selected=next((u for u in users if u['username']==editing),None)
    notice=('<p role="alert" style="color:'+('#b91c1c' if error else '#166534')+'">'+e(message)+'</p>') if message else ''
    rows=''.join('<tr><td>'+e(u['username'])+'</td><td>'+e(u['name'])+'</td><td>'+e(u['role_name'])+'</td><td>'+('Activo' if u['active'] else 'Inactivo')+'</td><td><a class="btn btn-neutral btn-sm" href="/admin/usuarios?editar='+e(u['username'])+'">Editar</a></td></tr>' for u in users)
    role_options = ''.join(f'<option value="{value}" {"selected" if (selected and selected["role_name"]==value) or (not selected and value=="usuario") else ""}>{label}</option>' for value,label in (('administrador','Administrador'),('usuario','Usuario')))
    form=f"""<form method="post" action="/admin/usuarios/guardar" class="form-grid">
    <label>Usuario<input name="username" maxlength="40" pattern="[A-Za-z0-9_.-]+" value="{e(selected['username']) if selected else ''}" {'readonly' if selected else 'required'}></label>
    <label>Nombre completo<input name="name" maxlength="100" value="{e(selected['name']) if selected else ''}" required></label>
    <label>Rol<select name="role">{role_options}</select></label>
    <label>Estado<select name="active"><option value="1" {'selected' if not selected or selected['active'] else ''}>Activo</option><option value="0" {'selected' if selected and not selected['active'] else ''}>Inactivo</option></select></label>
    <label>{'Nueva contraseña (dejar vacío para conservar)' if selected else 'Contraseña inicial'}<input name="password" type="password" minlength="8" maxlength="128" {'required' if not selected else ''}></label>
    <button class="primary" type="submit">Guardar usuario</button><a href="/admin/usuarios">Cancelar</a></form>"""
    return layout('<section class="panel"><h2>Mantenimiento de usuarios</h2><p>Solo administradores pueden crear y modificar usuarios. Las contraseñas se almacenan con hash.</p>'+notice+'<table><thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acción</th></tr></thead><tbody>'+rows+'</tbody></table><h3>'+('Editar usuario' if selected else 'Nuevo usuario')+'</h3>'+form+'</section>')

def change_password_page(message='',error=False):
    notice=('<p role="alert" style="color:'+('#b91c1c' if error else '#166534')+'">'+e(message)+'</p>') if message else ''
    return layout('<section class="panel"><h2>Cambiar mi contraseña</h2><p>Escriba su nueva contraseña y confírmela. Por seguridad, el sistema no genera ni muestra contraseñas nuevas: la nueva será exactamente la que usted introduzca. Después deberá iniciar sesión de nuevo.</p>'+notice+'<form method="post" action="/admin/cambiar-clave" class="form-grid"><label>Contraseña actual<input type="password" name="actual" required></label><label>Nueva contraseña<input type="password" name="nueva" minlength="8" required></label><label>Confirmar contraseña<input type="password" name="confirmar" minlength="8" required></label><button class="primary">Cambiar contraseña</button></form></section>')

def login_page(error='',message=''):
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ingresar - MisFinanzas</title><link rel="icon" type="image/png" href="/static/logo.png"><link rel="stylesheet" href="/static/styles.css"></head>'
            '<body class="login-body"><div class="lg-bg" aria-hidden="true"><span class="lg-orb lg-orb-1"></span><span class="lg-orb lg-orb-2"></span><span class="lg-orb lg-orb-3"></span><span class="lg-orb lg-orb-4"></span></div>'
            '<main class="lg-wrap"><section class="lg-card" aria-labelledby="lg-title"><div class="lg-brand"><img class="app-logo app-logo-login" src="/static/logo.png" alt="Logo de MisFinanzas" width="72" height="72"><span>MisFinanzas</span></div>'
            '<h1 id="lg-title">Iniciar sesión</h1><p class="lg-sub">Ingrese sus credenciales para acceder al sistema.</p>'
            +('<p class="lg-alert" role="alert">'+e(error)+'</p>' if error else '')
            +('<p class="lg-success" role="status">'+e(message)+'</p>' if message else '')+
            '<form method="post" action="/login" class="lg-form"><label>Usuario<input class="lg-input" name="usuario" required autocomplete="username" autofocus></label>'
            '<label>Contraseña<input class="lg-input" name="contrasena" type="password" required autocomplete="current-password"></label>'
            '<button class="lg-btn" type="submit">Ingresar</button></form><p class="lg-create">¿No tienes una cuenta? <a href="/registro">Crear cuenta</a></p><p class="lg-forgot"><a href="/olvide-clave">¿Olvidó su contraseña?</a></p></section></main></body></html>')


def registration_page(error='',form=None):
    form=form or {}
    html=login_page().replace('<title>Ingresar -','<title>Crear cuenta -')
    start=html.index('<h1 id="lg-title">')
    end=html.index('</section>',start)
    notice=f'<p class="lg-alert" role="alert">{e(error)}</p>' if error else ''
    content=f'''<h1 id="lg-title">Crear cuenta</h1><p class="lg-sub">Regístrate para comenzar a organizar tus finanzas.</p>{notice}
        <form method="post" action="/registro" class="lg-form">
        <label>Nombre completo<input class="lg-input" name="name" autocomplete="name" maxlength="100" value="{e(form.get('name',''))}" required></label>
        <label>Usuario<input class="lg-input" name="username" autocomplete="username" pattern="[A-Za-z0-9_.-]+" maxlength="40" value="{e(form.get('username',''))}" required></label>
        <p class="help">El usuario debe ser único. Usa letras, números, puntos o guiones, sin espacios.</p>
        <label>Contraseña<input class="lg-input" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required></label>
        <label>Confirmar contraseña<input class="lg-input" name="confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required></label>
        <button class="lg-btn" type="submit">Crear cuenta</button></form>
        <p class="lg-create">¿Ya tienes cuenta? <a href="/login">Iniciar sesión</a></p>'''
    return html[:start]+content+html[end:]

def forgot_password_page():
    """Recuperación sin correo: la contraseña solo la restablece un administrador."""
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Recuperar contraseña - MisFinanzas</title><link rel="icon" type="image/png" href="/static/logo.png"><link rel="stylesheet" href="/static/styles.css"></head>'
            '<body class="login-body"><div class="lg-bg" aria-hidden="true"><span class="lg-orb lg-orb-1"></span><span class="lg-orb lg-orb-2"></span><span class="lg-orb lg-orb-3"></span><span class="lg-orb lg-orb-4"></span></div>'
            '<main class="lg-wrap"><section class="lg-card" aria-labelledby="lg-title"><div class="lg-brand"><img class="app-logo app-logo-login" src="/static/logo.png" alt="Logo de MisFinanzas" width="72" height="72"><span>MisFinanzas</span></div>'
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


# CSRF: cada formulario POST de una página con sesión lleva un token oculto (HMAC de la sesión, ver quality.csrf_token).
# Se inyecta en la respuesta, así que no hay que editar cada plantilla. No depende de cabeceras Host/Origin,
# por lo que funciona igual detrás del proxy de Apache/Virtualmin.
CSRF_FIELD = 'csrf'
_POST_FORM_RE = re.compile(r'<form\b[^>]*\bmethod=(["\']?)post\1[^>]*>', re.I)


def inject_csrf(body: bytes, token: str) -> bytes:
    if not token or b'<form' not in body:
        return body
    field = f'<input type="hidden" name="{CSRF_FIELD}" value="{e(token)}">'
    return _POST_FORM_RE.sub(lambda match: match.group(0) + field, body.decode('utf-8')).encode('utf-8')


def submitted_csrf(payload: bytes, content_type: str) -> str:
    """Token enviado en un formulario urlencoded o multipart (subida de comprobantes)."""
    try:
        if content_type.lower().startswith('multipart/form-data'):
            message = BytesParser(policy=default).parsebytes(
                b'Content-Type: ' + content_type.encode('latin-1') + b'\r\nMIME-Version: 1.0\r\n\r\n' + payload)
            for part in message.iter_parts() if message.is_multipart() else ():
                if part.get_param('name', header='content-disposition') == CSRF_FIELD:
                    return str(part.get_content()).strip()
            return ''
        return parse_qs(payload.decode('utf-8', 'replace'), keep_blank_values=True).get(CSRF_FIELD, [''])[0]
    except Exception:
        return ''


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


def layout(content: str, *, subtitle: str = '', selection: bool = False, compact_hero: bool = False) -> str:
    # Opciones de administración visibles solo para administradores (las rutas se protegen aparte).
    security_links = ('<a href="/admin/usuarios">Mantenimiento de usuarios</a>'
                      if request_is_admin() and not auth.STANDARD_USER_MODE else '')
    if request_ctx.is_quality_admin():
        security_links += '<a href="/admin/calidad">Calidad y pruebas</a>'
    name, role = request_ctx.identity()
    identity = (f'<div class="session-identity" aria-label="Usuario conectado"><span class="session-name">{e(name)}</span><form method="post" action="/logout" class="session-logout"><button type="submit">Cerrar sesión</button></form></div>' if name else '')
    selected_profile=request_ctx.profile()
    guest=bool(selected_profile and not selected_profile['es_propietario'])
    profiles_label='Mis perfiles' if guest else 'Administrar perfiles / integrantes'
    profile_bar=(f'<section class="notice-strip profile-strip"><span>Perfil financiero: <strong>{e(selected_profile["nombre"])}</strong> · {"Propietario" if selected_profile["es_propietario"] else "Invitado"}</span><a href="/perfiles/elegir">Cambiar perfil</a><a href="/perfiles">{profiles_label}</a></section>' if selected_profile and not selection else '')
    html = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MisFinanzas · Grupo 5</title><link rel="icon" type="image/png" href="/static/logo.png"><link rel="stylesheet" href="/static/styles.css"></head>
<body><header class="topbar"><div class="shell top-inner"><div class="brand"><img class="app-logo" src="/static/logo.png" alt="Logo de MisFinanzas" width="64" height="64"><span><strong>MisFinanzas</strong><small>Proyecto open source · Grupo 5</small></span></div>{identity}</div></header>
<main class="shell"><nav class="main-nav" aria-label="Menú principal"><a class="nav-home" href="/">⌂ Resumen</a><details class="nav-group"><summary>Operaciones</summary><div class="nav-drop"><a href="/">Ingresos y gastos</a><a href="/historial">Historial y búsqueda</a><a href="/admin/movimientos_recurrentes">Movimientos recurrentes</a><a href="/admin/transferencias">Transferencias</a><a href="/admin/movimientos_ahorro">Movimientos de ahorro</a><a href="/comprobantes">Comprobantes</a></div></details><details class="nav-group"><summary>Planificación</summary><div class="nav-drop"><a href="/admin/presupuestos">Presupuestos</a><a href="/admin/metas_ahorro">Metas de ahorro</a><a href="/admin/alertas">Alertas</a><a href="/reportes/anual">Reporte anual</a></div></details><details class="nav-group"><summary>Catálogos</summary><div class="nav-drop"><a href="/admin/cuentas">Cuentas</a><a href="/admin/categorias">Categorías</a><a href="/admin/monedas">Monedas</a></div></details><details class="nav-group"><summary>Seguridad</summary><div class="nav-drop">{security_links}<a href="/admin/cambiar-clave">Cambiar contraseña</a></div></details></nav>{profile_bar}<section class="hero{' hero-compact' if compact_hero else ''}"><div><p class="eyebrow">PANEL FINANCIERO</p><h1>Un panorama claro de tu dinero.</h1><p>Movimientos, presupuestos y alertas en una sola página. {e(subtitle)}</p></div><span class="hero-art" aria-hidden="true">↗</span></section>{content}</main>
<footer class="shell footer">Datos de demostración ficticios · Sin cuentas reales · UNA · II-2026</footer>
<script>
// Categorías según el tipo elegido (botones Gasto / Ingreso del formulario de movimiento).
const tipos=[...document.querySelectorAll('input[name="tipo"][data-filtra-categoria]')]; const categoria = document.getElementById('id_categoria');
function filtrar(){{const elegido=tipos.find(t=>t.checked); if(elegido&&elegido.form)elegido.form.dataset.tipo=elegido.value; if(!elegido||!categoria)return; const all=[...categoria.options];
 let visible=all.filter(o=>o.dataset.tipo===elegido.value); for(const o of all)o.hidden=o.dataset.tipo!==elegido.value;
 if(!visible.includes(categoria.selectedOptions[0])&&visible.length)categoria.value=visible[0].value;}}
for(const t of tipos){{t.addEventListener('change',filtrar);t.form.addEventListener('reset',()=>setTimeout(filtrar));}}
filtrar();
// Indicador deslizante en selectores segmentados y pestañas. Solo presentación: no cambia qué se envía.
for(const g of document.querySelectorAll('.segmented,.profile-tabs')){{
  const thumb=document.createElement('span');thumb.className='seg-thumb';thumb.setAttribute('aria-hidden','true');
  g.prepend(thumb);g.classList.add('con-indicador');
  const activo=()=>g.classList.contains('segmented')?g.querySelector('input:checked+label'):g.querySelector('[aria-selected="true"]');
  const mover=animar=>{{const a=activo();if(!a||!a.offsetWidth){{thumb.style.opacity='0';return;}}
    if(!animar)thumb.classList.add('sin-transicion');
    thumb.style.opacity='1';thumb.style.width=a.offsetWidth+'px';thumb.style.height=a.offsetHeight+'px';
    thumb.style.transform='translate('+a.offsetLeft+'px,'+a.offsetTop+'px)';
    const entrada=a.previousElementSibling;thumb.dataset.valor=(entrada&&entrada.tagName==='INPUT'?entrada.value:a.dataset.group)||'';
    if(!animar){{void thumb.offsetWidth;thumb.classList.remove('sin-transicion');}}}};
  g.addEventListener('change',()=>mover(true));
  new MutationObserver(()=>mover(true)).observe(g,{{subtree:true,attributes:true,attributeFilter:['aria-selected']}});
  const f=g.closest('form');if(f)f.addEventListener('reset',()=>setTimeout(()=>mover(true)));
  if(window.ResizeObserver)new ResizeObserver(()=>mover(false)).observe(g);
  mover(false);
}}
// Atajos de fecha: solo rellenan el campo; el servidor valida la fecha igual que antes.
const isoLocal=d=>{{const c=new Date(d);c.setMinutes(c.getMinutes()-c.getTimezoneOffset());return c.toISOString().slice(0,10);}};
for(const b of document.querySelectorAll('[data-fecha][data-objetivo]'))b.addEventListener('click',()=>{{const d=new Date();
 if(b.dataset.fecha==='ayer')d.setDate(d.getDate()-1); if(b.dataset.fecha==='inicio')d.setDate(1);
 const campo=document.getElementById(b.dataset.objetivo); if(campo){{campo.value=isoLocal(d);campo.dispatchEvent(new Event('input',{{bubbles:true}}));}}}});
// Campo numérico con − y +: respeta min y max del propio campo.
for(const s of document.querySelectorAll('[data-stepper]')){{const campo=s.querySelector('input');
 for(const b of s.querySelectorAll('button[data-paso]'))b.addEventListener('click',()=>{{const min=Number(campo.min||-Infinity),max=Number(campo.max||Infinity);
  const v=Math.min(max,Math.max(min,(Number(campo.value)||0)+Number(b.dataset.paso)));campo.value=v;campo.dispatchEvent(new Event('input',{{bubbles:true}}));}});}}
// Contador de caracteres.
for(const c of document.querySelectorAll('[data-contador]')){{const out=document.getElementById(c.dataset.contador);const max=c.maxLength;
 const upd=()=>{{if(out)out.textContent=c.value.length+' / '+max;}};c.addEventListener('input',upd);if(c.form)c.form.addEventListener('reset',()=>setTimeout(upd));}}
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
// Confirmación antes de borrar: el texto viene en data-confirm (valor "true" heredado = movimiento).
for(const b of document.querySelectorAll('[data-confirm]'))b.addEventListener('click',ev=>{{const t=b.dataset.confirm;if(!confirm(t&&t!=='true'?t:'¿Eliminar este movimiento?'))ev.preventDefault();}});
// Menú principal: se abre al pasar el cursor (hover) y se cierra al salir; un solo desplegable abierto a la vez.
// Teclado y pantallas táctiles siguen funcionando con clic/Enter gracias al <summary> nativo.
const grupos=[...document.querySelectorAll('.main-nav details.nav-group')];
const finHover=window.matchMedia('(hover:hover) and (pointer:fine)');
for(const g of grupos){{
  g.addEventListener('toggle',()=>{{if(g.open)for(const o of grupos)if(o!==g)o.open=false;}});
  if(finHover.matches){{
    g.addEventListener('mouseenter',()=>{{clearTimeout(g._cierre);g.open=true;}});
    g.addEventListener('mouseleave',()=>{{g._cierre=setTimeout(()=>{{g.open=false;}},120);}});
    g.querySelector('summary').addEventListener('click',ev=>ev.preventDefault());
  }}
}}
document.addEventListener('click',ev=>{{for(const g of grupos)if(g.open&&!g.contains(ev.target))g.open=false;}});
document.addEventListener('keydown',ev=>{{if(ev.key==='Escape')for(const g of grupos)g.open=false;}});
// Iluminación que sigue al puntero: paneles, tarjetas y botones. Un solo listener delegado, a lo sumo una vez por cuadro.
// Se excluyen los botones de controles compuestos y todo lo del menú desplegable (posición absoluta).
if(finHover.matches&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){{
  const brillo='.main-nav,.panel,.metric,.hero,.lg-card,.table-panel,.btn,.primary,.secondary,.quick-dates button,.form-actions button';
  for(const s of document.querySelectorAll(brillo)){{
    if(s.closest('.nav-drop,.stepper,.session-logout'))continue;
    s.classList.add('glow-track');
  }}
  let ultimo=null,pendiente=false;
  document.addEventListener('pointermove',ev=>{{ultimo=ev;if(pendiente)return;pendiente=true;
    requestAnimationFrame(()=>{{pendiente=false;const t=ultimo.target;let el=t&&t.closest?t.closest('.glow-track'):null;
      while(el){{const r=el.getBoundingClientRect();el.style.setProperty('--gx',(ultimo.clientX-r.left)+'px');el.style.setProperty('--gy',(ultimo.clientY-r.top)+'px');
        el=el.parentElement?el.parentElement.closest('.glow-track'):null;}}}});}},{{passive:true}});
}}
</script></body></html>'''
    if guest:
        for route,label in (('presupuestos','Presupuestos'),('metas_ahorro','Metas de ahorro'),('cuentas','Cuentas'),('categorias','Categorías'),('monedas','Monedas')):
            html=html.replace(f'href="/admin/{route}">{label}</a>',f'href="/admin/{route}">{label} · Consulta</a>')
        html=html.replace('<summary>Catálogos</summary>','<summary>Consultas</summary>')
    if selection:
        html=re.sub(r'<nav class="main-nav".*?</nav>','',html,flags=re.S)
        html=re.sub(r'<section class="hero[^"]*">.*?</section>','',html,flags=re.S)
        html=html.replace('Proyecto open source · Grupo 5','Bienvenido, '+e(name))
    return html


def months_back(day: date, months: int) -> date:
    """Misma fecha N meses antes; si el día no existe en ese mes, usa el último día del mes."""
    index = day.year * 12 + day.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(day.day, last))


BALANCE_RANGES = (('1s', '1 semana'), ('1m', '1 mes'), ('3m', '3 meses'))

# Gráfico de evolución de saldos: se dibuja en el navegador a partir del JSON embebido (sin dependencias).
# Los nombres de cuenta se insertan siempre con textContent, nunca como HTML.
BALANCE_CHART_JS = r'''<script>(()=>{
const fuente=document.getElementById('saldos-datos'),caja=document.getElementById('saldos-grafico');
if(!fuente||!caja)return;
const datos=JSON.parse(fuente.textContent),fechas=datos.fechas;
const resumen=document.getElementById('saldos-resumen'),leyenda=document.getElementById('saldos-leyenda');
const COLORES=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300','#6250d6','#e34948'],OTRAS='#7b8494';
const NS='http://www.w3.org/2000/svg',TEXTOS={'1s':'última semana','1m':'último mes','3m':'últimos 3 meses'};
// Series por moneda: color fijo por cuenta (orden por nombre); más de 8 cuentas se agrupan en «Otras cuentas».
const grupos={};
for(const c of datos.cuentas)(grupos[c.moneda]=grupos[c.moneda]||[]).push(c);
for(const k of Object.keys(grupos)){const l=grupos[k];
  if(l.length>8){const resto=l.slice(7);grupos[k]=l.slice(0,7).concat([{nombre:'Otras cuentas ('+resto.length+')',simbolo:l[0].simbolo,otras:true,
    serie:fechas.map((_,i)=>resto.reduce((s,c)=>s+c.serie[i],0))}]);}
  grupos[k].forEach((c,i)=>{c.color=c.otras?OTRAS:COLORES[i];});}
const monedas=Object.keys(grupos);
const leer=k=>{try{return localStorage.getItem(k);}catch(_){return null;}},guardar=(k,v)=>{try{localStorage.setItem(k,v);}catch(_){}};
const marcada=document.querySelector('input[name="moneda-saldos"]:checked');
let rango=TEXTOS[leer('saldos-rango')]?leer('saldos-rango'):'1m';
let moneda=monedas.includes(leer('saldos-moneda'))?leer('saldos-moneda'):(marcada&&monedas.includes(marcada.value)?marcada.value:monedas[0]);
for(const r of document.querySelectorAll('input[name="rango-saldos"]')){r.checked=r.value===rango;
  r.addEventListener('change',()=>{rango=r.value;guardar('saldos-rango',rango);dibujar();});}
for(const r of document.querySelectorAll('input[name="moneda-saldos"]')){r.checked=r.value===moneda;
  r.addEventListener('change',()=>{moneda=r.value;guardar('saldos-moneda',moneda);dibujar();});}
const dinero=(c,s)=>(c<0?'−':'')+s+(Math.abs(c)/100).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
// Etiquetas del eje: la forma más corta que siga distinguiendo cada marca (compacta, entera o con céntimos).
const FORMATOS=[{notation:'compact',maximumFractionDigits:1},{notation:'compact',maximumFractionDigits:2},{maximumFractionDigits:0},{minimumFractionDigits:2,maximumFractionDigits:2}].map(o=>new Intl.NumberFormat('en-US',o));
const etiquetasEje=(ticks,s)=>{for(const f of FORMATOS){const l=ticks.map(c=>(c<0?'−':'')+s+f.format(Math.abs(c)/100));if(new Set(l).size===l.length)return l;}return ticks.map(c=>dinero(c,s));};
const aFecha=iso=>{const[y,m,d]=iso.split('-').map(Number);return new Date(y,m-1,d);};
const fCorta=iso=>aFecha(iso).toLocaleDateString('es-CR',{day:'numeric',month:'short'});
const fLarga=iso=>{const t=aFecha(iso).toLocaleDateString('es-CR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});return t.charAt(0).toUpperCase()+t.slice(1);};
const el=(tag,attrs,padre,texto)=>{const n=document.createElementNS(NS,tag);for(const k in attrs)n.setAttribute(k,attrs[k]);if(texto!=null)n.textContent=texto;if(padre)padre.appendChild(n);return n;};
const html=(tag,clase,padre,texto)=>{const n=document.createElement(tag);if(clase)n.className=clase;if(texto!=null)n.textContent=texto;if(padre)padre.appendChild(n);return n;};
function marcas(min,max){if(min===max){const p=Math.max(Math.abs(min)*.1,10000);min-=p;max+=p;}
  const bruto=(max-min)/4,mag=10**Math.floor(Math.log10(bruto)),paso=[1,2,2.5,5,10].map(k=>k*mag).find(p=>p>=bruto);
  const t=[];for(let v=Math.floor(min/paso)*paso;v<=Math.ceil(max/paso)*paso+paso/2;v+=paso)t.push(Math.round(v));return t;}
function dibujar(){
  const lista=grupos[moneda]||[],simbolo=lista.length?lista[0].simbolo:'';
  let desde=fechas.indexOf(datos.rangos[rango]);if(desde<0)desde=0;
  const dias=fechas.slice(desde),n=dias.length,series=lista.map(c=>({...c,valores:c.serie.slice(desde)}));
  caja.replaceChildren();resumen.replaceChildren();leyenda.replaceChildren();
  if(!series.length||n<2){html('p','chart-empty',caja,'Aún no hay cuentas para graficar en este perfil.');return;}
  // Resumen: total de la moneda al final del rango y variación (signo y flecha, no solo color).
  const total=i=>series.reduce((s,c)=>s+c.valores[i],0),fin=total(n-1),ini=total(0),dif=fin-ini;
  const kpi=html('div','chart-kpi',resumen);html('span','chart-kpi-label',kpi,'Saldo total · '+moneda);html('strong','',kpi,dinero(fin,simbolo));
  const delta=html('div','chart-delta '+(dif>0?'up':dif<0?'down':'flat'),resumen);
  html('span','',delta,dif>0?'▲ ':dif<0?'▼ ':'● ').setAttribute('aria-hidden','true');
  const pct=ini>0&&dif?' ('+(dif>0?'+':'−')+Math.abs(dif/ini*100).toFixed(1)+' %)':'';
  delta.appendChild(document.createTextNode((dif>0?'+':'')+dinero(dif,simbolo)+pct));
  html('small','',delta,'desde el '+fCorta(dias[0]));
  // Geometría
  const W=Math.max(caja.clientWidth,280),H=W<560?220:280,todos=series.flatMap(s=>s.valores);
  const ticks=marcas(Math.min(...todos),Math.max(...todos)),yMin=ticks[0],yMax=ticks[ticks.length-1],eje=etiquetasEje(ticks,simbolo);
  const directas=series.length<=4&&W>=560;
  // Leyenda siempre con 2+ series; con una sola basta la etiqueta directa (si cabe).
  if(series.length>1||!directas)for(const s of series){const it=html('span','legend-item',leyenda);html('span','legend-key',it).style.background=s.color;html('span','',it,s.nombre);}
  const m={t:12,r:directas?128:14,b:30,l:Math.max(...eje.map(t=>t.length))*7+14};
  const pw=W-m.l-m.r,ph=H-m.t-m.b,x=i=>m.l+i/(n-1)*pw,y=v=>m.t+(yMax-v)/((yMax-yMin)||1)*ph;
  const etiqueta=series.map(s=>s.nombre+': de '+dinero(s.valores[0],simbolo)+' a '+dinero(s.valores[n-1],simbolo)).join('; ');
  const svg=el('svg',{viewBox:'0 0 '+W+' '+H,width:W,height:H,role:'img',tabindex:'0',
    'aria-label':'Evolución de saldos en '+moneda+', '+TEXTOS[rango]+'. '+etiqueta+'. Use las flechas para recorrer los días.'},caja);
  const rejilla=el('g',{},svg);
  ticks.forEach((t,i)=>{el('line',{x1:m.l,x2:W-m.r,y1:y(t),y2:y(t),stroke:t===0&&yMin<0?'#9aa6b8':'#e6ebf2','stroke-width':1},rejilla);
    el('text',{x:m.l-10,y:y(t)+4,'text-anchor':'end',class:'chart-axis'},rejilla,eje[i]);});
  const k=n<=8&&W>=560?n:(W<560?3:5);
  for(let j=0;j<k;j++){const i=Math.round(j*(n-1)/(k-1));
    el('text',{x:x(i),y:H-8,'text-anchor':j===0?'start':j===k-1?'end':'middle',class:'chart-axis'},rejilla,fCorta(dias[i]));}
  for(const s of series){
    el('path',{d:s.valores.map((v,i)=>(i?'L':'M')+x(i).toFixed(1)+' '+y(v).toFixed(1)).join(''),fill:'none',stroke:s.color,'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'},svg);
    el('circle',{cx:x(n-1),cy:y(s.valores[n-1]),r:4,fill:s.color,stroke:'#fff','stroke-width':2},svg);}
  if(directas){const pos=series.map(s=>({s,y:y(s.valores[n-1])})).sort((a,b)=>a.y-b.y);
    for(let i=1;i<pos.length;i++)pos[i].y=Math.max(pos[i].y,pos[i-1].y+15);
    const exceso=pos.length?pos[pos.length-1].y-(m.t+ph):0;if(exceso>0)for(const p of pos)p.y-=exceso;
    for(const p of pos){const nombre=p.s.nombre.length>16?p.s.nombre.slice(0,15)+'…':p.s.nombre;
      el('text',{x:W-m.r+10,y:p.y+4,class:'chart-direct'},svg,nombre);}}
  // Capa de lectura: cruz vertical que se ajusta al día más cercano y un tooltip con todas las cuentas.
  const cruz=el('line',{y1:m.t,y2:m.t+ph,stroke:'#5b6b82','stroke-width':1,'stroke-dasharray':'3 3',visibility:'hidden'},svg);
  const puntos=series.map(s=>el('circle',{r:4.5,fill:s.color,stroke:'#fff','stroke-width':2,visibility:'hidden'},svg));
  const zona=el('rect',{x:m.l,y:m.t,width:pw,height:ph,fill:'transparent'},svg);
  const tip=html('div','chart-tip',caja);tip.hidden=true;let actual=n-1;
  const mostrar=i=>{actual=Math.max(0,Math.min(n-1,i));const cx=x(actual);
    cruz.setAttribute('x1',cx);cruz.setAttribute('x2',cx);cruz.setAttribute('visibility','visible');
    puntos.forEach((p,j)=>{p.setAttribute('cx',cx);p.setAttribute('cy',y(series[j].valores[actual]));p.setAttribute('visibility','visible');});
    tip.replaceChildren();html('div','chart-tip-fecha',tip,fLarga(dias[actual]));
    for(const s of series){const f=html('div','chart-tip-fila',tip);html('span','legend-key',f).style.background=s.color;
      html('strong','',f,dinero(s.valores[actual],simbolo));html('span','',f,s.nombre);}
    if(series.length>1){const f=html('div','chart-tip-fila chart-tip-total',tip);html('strong','',f,dinero(total(actual),simbolo));html('span','',f,'Total');}
    tip.hidden=false;const ancho=tip.offsetWidth,izq=cx+14+ancho>W?cx-14-ancho:cx+14;
    tip.style.left=Math.max(0,Math.min(W-ancho,izq))+'px';tip.style.top=m.t+'px';};
  const ocultar=()=>{tip.hidden=true;cruz.setAttribute('visibility','hidden');for(const p of puntos)p.setAttribute('visibility','hidden');};
  zona.addEventListener('pointermove',ev=>{const r=svg.getBoundingClientRect();mostrar(Math.round((ev.clientX-r.left-m.l)/pw*(n-1)));});
  zona.addEventListener('pointerleave',ocultar);
  svg.addEventListener('focus',()=>mostrar(actual));svg.addEventListener('blur',ocultar);
  svg.addEventListener('keydown',ev=>{const mov={ArrowLeft:-1,ArrowRight:1}[ev.key];
    if(mov){ev.preventDefault();mostrar(actual+mov);}else if(ev.key==='Home'){ev.preventDefault();mostrar(0);}else if(ev.key==='End'){ev.preventDefault();mostrar(n-1);}else if(ev.key==='Escape')ocultar();});
}
dibujar();
let ancho=caja.clientWidth,pend=false;
if(window.ResizeObserver)new ResizeObserver(()=>{if(pend||caja.clientWidth===ancho)return;pend=true;requestAnimationFrame(()=>{pend=false;ancho=caja.clientWidth;dibujar();});}).observe(caja);
})();</script>'''


def balance_chart_panel(today: date) -> str:
    """Módulo del Resumen: evolución diaria del saldo de cada cuenta (1 semana, 1 mes, 3 meses)."""
    starts = {'1s': today - timedelta(days=7), '1m': months_back(today, 1), '3m': months_back(today, 3)}
    history = finance.balance_history(min(starts.values()), today)
    history['rangos'] = {key: day.isoformat() for key, day in starts.items()}
    data_json = json.dumps(history, ensure_ascii=False).replace('</', '<\\/')
    # Moneda inicial: la que tiene más cuentas (empate: orden alfabético).
    counts = {}
    for account in history['cuentas']:
        counts[account['moneda']] = counts.get(account['moneda'], 0) + 1
    currencies = sorted(counts, key=lambda code: (-counts[code], code))
    ranges = ''.join(f'<input type="radio" name="rango-saldos" id="rango-{key}" value="{key}"{" checked" if key == "1m" else ""}>'
                     f'<label for="rango-{key}">{label}</label>' for key, label in BALANCE_RANGES)
    currency_control = ''
    if len(currencies) > 1:
        currency_control = ('<div class="segmented chart-currency" role="radiogroup" aria-label="Moneda del gráfico">' + ''.join(
            f'<input type="radio" name="moneda-saldos" id="moneda-saldos-{e(code)}" value="{e(code)}"{" checked" if i == 0 else ""}>'
            f'<label for="moneda-saldos-{e(code)}">{e(code)}</label>' for i, code in enumerate(currencies)) + '</div>')
    return f'''<section class="panel balance-chart" id="evolucion-saldos" aria-labelledby="titulo-evolucion">
    <div class="panel-title"><div><p class="eyebrow">SALDOS</p><h2 id="titulo-evolucion">Evolución de saldos</h2></div>
    <div class="chart-controls">{currency_control}<div class="segmented chart-range" role="radiogroup" aria-label="Rango de tiempo">{ranges}</div></div></div>
    <div class="chart-summary" id="saldos-resumen" aria-live="polite"></div>
    <div class="chart-legend" id="saldos-leyenda"></div>
    <div class="chart-wrap" id="saldos-grafico"><p class="chart-empty">Cargando gráfico…</p></div>
    <p class="help">Saldo al cierre de cada día en la moneda de cada cuenta; no se suman monedas distintas. Los valores actuales exactos están en «Saldos por cuenta».</p>
    <script type="application/json" id="saldos-datos">{data_json}</script>{BALANCE_CHART_JS}</section>'''


MONTHS_ES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def variation_html(current: int, previous: int, previous_label: str) -> str:
    """Variación frente al mes anterior con flecha y signo (no depende solo del color)."""
    if not previous:
        return f'<small class="variation">Sin registros en {e(previous_label)}</small>' if current else ''
    pct = round((current - previous) / previous * 100)
    if pct == 0:
        return f'<small class="variation">= igual que {e(previous_label)}</small>'
    arrow = '▲' if pct > 0 else '▼'
    return f'<small class="variation"><span aria-hidden="true">{arrow}</span> {"+" if pct > 0 else "−"}{abs(pct)} % vs. {e(previous_label)}</small>'


def summary_cards(totals: dict, balances: list, symbols: dict, month_label: str) -> str:
    """Tarjetas superiores: saldo total, ingresos, gastos y neto del mes. Una moneda principal; las demás, aparte."""
    balance_by_code, account_count = {}, {}
    for _, code, amount in balances:
        balance_by_code[code] = balance_by_code.get(code, 0) + amount
        account_count[code] = account_count.get(code, 0) + 1
    codes = sorted(set(balance_by_code) | set(totals), key=lambda c: (-account_count.get(c, 0), c != 'CRC', c))
    if not codes:
        codes = ['CRC']
    primary, others = codes[0], codes[1:]

    def values(getter):
        return {code: getter(code) for code in codes}

    cards = (('Saldo total', 'Todas las cuentas', values(lambda c: balance_by_code.get(c, 0)), ''),
             ('Ingresos', month_label, values(lambda c: totals.get(c, {}).get('ingreso', 0)), 'income'),
             ('Gastos', month_label, values(lambda c: totals.get(c, {}).get('gasto', 0)), 'expense'),
             ('Neto del mes', month_label, values(lambda c: totals.get(c, {}).get('ingreso', 0) - totals.get(c, {}).get('gasto', 0)), 'net'))
    html = ''
    for title, context, amounts, kind in cards:
        main = amounts[primary]
        css = {'income': 'income', 'expense': 'expense'}.get(kind, '')
        if kind == 'net':
            css = 'income' if main > 0 else ('expense' if main < 0 else '')
        extra = ''.join(f'<small class="metric-other">{e(code)} {e(finance.format_amount(amounts[code], symbols.get(code, "")))}</small>'
                        for code in others if amounts[code])
        html += (f'<article class="metric"><span>{e(title)} · {e(primary)}</span><strong class="{css}">{e(finance.format_amount(main, symbols.get(primary, "")))}</strong>'
                 f'<small>{e(context)}</small>{extra}</article>')
    return f'<section class="metrics metrics-4" aria-label="Resumen del período">{html}</section>'


def category_panel(groups: dict, month_label: str, start_day: str, end_day: str) -> str:
    """Gastos del mes por categoría: barras horizontales por moneda (sin conversión). HTML puro, sin JavaScript."""
    body = ''
    for code in sorted(groups):
        symbol, items = groups[code]['simbolo'], groups[code]['categorias']
        total = sum(amount for _, amount in items)
        shown = items[:6]
        if len(items) > 6:
            shown = shown + [(f'Otras ({len(items) - 6})', sum(amount for _, amount in items[6:]))]
        top = max(amount for _, amount in shown) or 1
        heading = f'<h3 class="cat-currency">{e(code)} · total {e(finance.format_amount(total, symbol))}</h3>' if len(groups) > 1 else ''
        rows = ''.join(f'<li class="cat-row"><span class="cat-name">{e(name)}</span>'
                       f'<span class="cat-bar" aria-hidden="true"><span style="width:{max(2, round(amount / top * 100))}%"></span></span>'
                       f'<span class="cat-value">{e(finance.format_amount(amount, symbol))}<small>{round(amount / total * 100) if total else 0} %</small></span></li>'
                       for name, amount in shown)
        body += f'{heading}<ul class="cat-list">{rows}</ul>'
    if not body:
        body = (f'<p class="empty-state">Sin gastos registrados en {e(month_label)}. '
                '<a href="#monto-movimiento">Registrar un gasto →</a></p>')
    return (f'<article class="panel"><div class="panel-title"><div><p class="eyebrow">¿EN QUÉ SE VA EL DINERO?</p><h2>Gastos por categoría</h2></div>'
            f'<a href="/historial?tipo=gasto&amp;desde={start_day}&amp;hasta={end_day}">Ver gastos →</a></div>'
            f'<p class="help">{e(month_label.capitalize())}. Cada moneda se muestra por separado.</p>{body}</article>')


def goals_panel(goals: list, today: date, can_manage: bool) -> str:
    """Progreso de metas de ahorro (aportes − retiros frente al objetivo). Solo lectura."""
    items = ''
    for goal in goals[:4]:
        target, saved, symbol = goal['objetivo'], goal['ahorrado'], goal['simbolo']
        pct = round(saved / target * 100) if target else 0
        remaining = max(target - saved, 0)
        try:
            days_left = (date.fromisoformat(goal['fecha_objetivo']) - today).days
        except ValueError:
            days_left = None
        if saved >= target:
            status, css = 'Completada', 'ok'
        elif days_left is not None and days_left < 0:
            status, css = 'Fecha vencida', 'warning'
        elif days_left is not None:
            status, css = ('Vence hoy' if days_left == 0 else f'Faltan {days_left} días'), 'neutral'
        else:
            status, css = 'En curso', 'neutral'
        detail = 'Objetivo alcanzado' if not remaining else f'Faltan {finance.format_amount(remaining, symbol)}'
        items += (f'<div class="budget-line goal-line"><div class="budget-head"><strong>{e(goal["nombre"])}</strong><span class="pill {css}">{e(status)}</span></div>'
                  f'<div class="budget-values"><span>{e(finance.format_amount(saved, symbol))} de {e(finance.format_amount(target, symbol))}</span><span>{pct} % · {e(detail)}</span></div>'
                  f'<div class="track" role="progressbar" aria-label="Progreso de {e(goal["nombre"])}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{min(max(pct, 0), 100)}">'
                  f'<div class="fill goal" style="width:{min(max(pct, 0), 100)}%"></div></div></div>')
    if not items:
        action = '<a href="/admin/metas_ahorro">Crear una meta →</a>' if can_manage else ''
        items = f'<p class="empty-state">Aún no hay metas de ahorro en este perfil. {action}</p>'
    more = f'<p class="help">Se muestran 4 de {len(goals)} metas.</p>' if len(goals) > 4 else ''
    return (f'<article class="panel"><div class="panel-title"><div><p class="eyebrow">AHORRO</p><h2>Metas de ahorro</h2></div>'
            f'<a href="/admin/metas_ahorro">Ver todas →</a></div>{items}{more}'
            '<p class="help">Lo ahorrado son los aportes menos los retiros registrados en «Movimientos de ahorro».</p></article>')


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
        can_manage=bool(profiles.access(c)['es_propietario'])
        account_rows = c.execute('SELECT a.id_cuenta,m.codigo_iso,m.simbolo FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda WHERE a.id_perfil=current_profile_id()').fetchall()
        account_currency = {str(r['id_cuenta']): r['codigo_iso'] for r in account_rows}
        # Solo lectura: moneda y saldo de cada cuenta para el prefijo del monto y la ayuda del formulario.
        account_info = {str(r['id_cuenta']): {'codigo': r['codigo_iso'], 'simbolo': r['simbolo'],
                                              'saldo': finance.format_amount(finance.account_balance(c, r['id_cuenta']), r['simbolo'])}
                        for r in account_rows}
    if movement_edit and not can_manage:
        raise profiles.AccessDenied('Solo el propietario puede editar movimientos existentes.')

    kind = movement_edit['tipo'] if movement_edit else 'gasto'
    cat_selected = movement_edit['id_categoria'] if movement_edit else None
    acc_selected = movement_edit['id_cuenta'] if movement_edit else (accounts[0]['id_cuenta'] if accounts else None)
    amount = f"{movement_edit['monto_centimos']/100:.2f}" if movement_edit else ''
    tx_date = movement_edit['fecha'] if movement_edit else today.isoformat()
    currency_selected = account_currency.get(str(acc_selected), 'CRC')
    selected_info = account_info.get(str(acc_selected), {'simbolo': '', 'saldo': '—'})
    account_json = json.dumps(account_info).replace('</', '<\\/')
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
        budget_html = ('<p class="empty-state">Todavía no se han definido presupuestos para este mes.'
                       + (' <a href="#nuevo-limite">Crear el primero ↓</a>' if can_manage else '') + '</p>')
    symbols = finance.currency_symbols()
    account_symbol = {r['id_cuenta']: r['simbolo'] for r in account_rows}
    rows = ''
    for tx in data['movements']:
        sign = '+' if tx['tipo'] == 'ingreso' else '−'
        css_class = 'income' if tx['tipo'] == 'ingreso' else 'expense'
        desc = tx['descripcion'] or tx['categoria']
        shown_amount = sign + finance.format_amount(tx['monto_centimos'], account_symbol.get(tx['id_cuenta'], ''))
        rows += f'''<tr><td><strong>{e(desc)}</strong><small>{e(tx['categoria'])} · {e(tx['cuenta'])}</small></td>
        <td>{e(tx['fecha'])}</td><td class="amount {css_class}" title="{e(account_currency.get(str(tx['id_cuenta']), ''))}">{e(shown_amount)}</td>
        <td class="actions"><a class="btn btn-neutral btn-sm" href="/?editar={tx['id_movimiento']}&anio={year}&mes={month}">Editar</a>
        <form method="post" action="/movimientos/{tx['id_movimiento']}/eliminar"><button class="btn btn-danger btn-sm" data-confirm="¿Eliminar este movimiento?" type="submit">Eliminar</button></form></td></tr>'''
    if not rows:
        rows = ('<tr><td colspan="4" class="empty"><span>Aún no hay movimientos en el período seleccionado.</span> '
                '<a href="#monto-movimiento">Registrar el primero ↑</a></td></tr>')
    prev_year, prev_month_number = previous_month(year, month)
    previous_label = MONTHS_ES[prev_month_number - 1]
    previous_totals = finance.month_totals(prev_year, prev_month_number)
    metric_rows = []
    for code, amounts in sorted(data['totals_by_currency'].items()):
        inc, exp = amounts['ingreso'], amounts['gasto']
        before = previous_totals.get(code, {'ingreso': 0, 'gasto': 0})
        sym = symbols.get(code, '')
        metric_rows.append(f'<tr><td>{e(code)}</td><td class="num">{e(finance.format_amount(inc, sym))}{variation_html(inc, before["ingreso"], previous_label)}</td>'
                           f'<td class="num">{e(finance.format_amount(exp, sym))}{variation_html(exp, before["gasto"], previous_label)}</td>'
                           f'<td class="num">{e(finance.format_amount(inc - exp, sym))}</td></tr>')
    metrics_html = ('<section class="panel"><h2>Resumen mensual por moneda</h2><p>Los montos no se suman entre monedas diferentes. '
                    f'La variación compara con {e(previous_label)}.</p><div class="table-scroll"><table><thead><tr><th>Moneda</th><th class="num">Ingresos</th><th class="num">Gastos</th><th class="num">Balance</th></tr></thead><tbody>'
                    + (''.join(metric_rows) or '<tr><td colspan="4">Sin movimientos este mes</td></tr>') + '</tbody></table></div></section>')
    with db.connect() as c:
        active=extension.current_profile_id(c)
        alert_count=c.execute('SELECT COUNT(*) FROM alertas WHERE id_perfil=? AND leida=0',(active,)).fetchone()[0]
        recurring_count=len(recurrentes.pending(c))
    start_day=f'{year:04d}-{month:02d}-01'
    end_day=(date(year+(month==12),month%12+1,1)-timedelta(days=1)).isoformat()
    recurring_strip=(f'<section class="notice-strip"><span>🔁 <strong>{recurring_count}</strong> movimientos recurrentes pendientes</span><a href="/admin/movimientos_recurrentes">Revisar y generar →</a></section>' if recurring_count else '')
    all_balances = finance.all_balances()
    balances = ''.join(f'<tr><td>{e(name)}</td><td>{e(code)}</td><td class="num">{e(finance.format_amount(amount, symbols.get(code, "")))}</td></tr>'
                       for name, code, amount in all_balances)
    if not balances:
        balances = '<tr><td colspan="3" class="empty"><span>Aún no hay cuentas en este perfil.</span>' + (' <a href="/admin/cuentas">Crear una cuenta →</a>' if can_manage else '') + '</td></tr>'
    month_label = f'{MONTHS_ES[month - 1]} {year}'
    content = f'''
    <section class="notice-strip"><span>🔔 <strong>{alert_count}</strong> alertas pendientes</span><a href="/admin/alertas">Ver alertas →</a></section>{recurring_strip}
    <form class="period" method="get"><label>Período <input type="month" name="periodo" value="{year:04d}-{month:02d}" aria-label="Mes de consulta" onchange="const a=this.value.split('-');document.getElementById('anio').value=a[0];document.getElementById('mes').value=Number(a[1]);this.form.submit()"></label>
    <input type="hidden" id="anio" name="anio" value="{year}"><input type="hidden" id="mes" name="mes" value="{month}"><button class="secondary" type="submit">Actualizar</button></form>
    {summary_cards(data['totals_by_currency'], all_balances, symbols, month_label)}
    {balance_chart_panel(today)}
    <section class="panel"><h2>Saldos por cuenta</h2><p>Incluye ingresos, gastos, transferencias y ahorros. Cada saldo está en su propia moneda.</p><div class="table-scroll"><table class="table-fit"><tr><th>Cuenta</th><th>Moneda</th><th class="num">Saldo</th></tr>{balances}</table></div></section>
    {metrics_html}
    <section class="columns">{category_panel(finance.month_expenses_by_category(year, month), month_label, start_day, end_day)}{goals_panel(finance.savings_goals(), today, can_manage)}</section>
    <section class="columns"><article class="panel"><div class="panel-title"><div><p class="eyebrow">REGISTRO</p><h2>{'Editar movimiento' if movement_edit else 'Nuevo movimiento'}</h2></div><a href="/historial">Ver historial</a></div>
    <form action="{action}" method="post" class="form-card"><div class="form-grid">
    <fieldset class="field span2"><legend class="field-label">Tipo de movimiento</legend><div class="segmented">
      <input type="radio" name="tipo" id="tipo-gasto" value="gasto" data-filtra-categoria {'checked' if kind=='gasto' else ''}><label for="tipo-gasto">− Gasto</label>
      <input type="radio" name="tipo" id="tipo-ingreso" value="ingreso" data-filtra-categoria {'checked' if kind=='ingreso' else ''}><label for="tipo-ingreso">+ Ingreso</label></div></fieldset>
    <div class="field span2"><label for="monto-movimiento">Monto</label>
      <div class="input-group input-money lg"><span class="addon prefix" id="simbolo-monto" aria-hidden="true">{e(selected_info['simbolo'])}</span><input id="monto-movimiento" name="monto" type="number" inputmode="decimal" min="0.01" step="0.01" required value="{e(amount)}" placeholder="0.00" aria-describedby="monto-ayuda"><span class="addon suffix" id="moneda-monto">{e(currency_selected)}</span></div>
      <p class="field-hint" id="monto-ayuda">Se registra en la moneda de la cuenta, sin conversión. Máximo dos decimales.</p></div>
    <div class="field"><label for="id_categoria">Categoría</label><select name="id_categoria" id="id_categoria" required>{option_rows(categories, cat_selected)}</select></div>
    <div class="field"><label for="cuenta-movimiento">Cuenta</label><select name="id_cuenta" id="cuenta-movimiento" required aria-describedby="saldo-cuenta">{option_rows(accounts, acc_selected)}</select>
      <p class="field-hint" id="saldo-cuenta">Saldo disponible: <span id="saldo-valor">{e(selected_info['saldo'])}</span></p></div>
    <div class="field"><label for="fecha-movimiento">Fecha</label><input id="fecha-movimiento" name="fecha" type="date" required value="{e(tx_date)}"></div>
    <div class="field"><span class="field-label" id="atajos-fecha">Atajos de fecha</span><div class="quick-dates" role="group" aria-labelledby="atajos-fecha"><button type="button" data-fecha="hoy" data-objetivo="fecha-movimiento">Hoy</button><button type="button" data-fecha="ayer" data-objetivo="fecha-movimiento">Ayer</button><button type="button" data-fecha="inicio" data-objetivo="fecha-movimiento">Inicio de mes</button></div></div>
    <div class="field span2"><label for="descripcion-movimiento">Descripción <span class="optional">· Opcional</span></label><input id="descripcion-movimiento" name="descripcion" maxlength="160" value="{e(description)}" placeholder="Ej. Compras del supermercado" data-contador="contador-descripcion">
      <p class="field-hint"><span>Si queda vacía, se muestra la categoría.</span><span id="contador-descripcion" aria-live="polite">{len(description)} / 160</span></p></div>
    </div>
    <div class="form-actions">{'<a class="btn btn-neutral" href="/">Cancelar</a>' if movement_edit else '<button class="btn btn-ghost" type="reset">Limpiar</button>'}<button type="submit" class="btn btn-primary">{'Guardar cambios' if movement_edit else 'Agregar movimiento'}</button></div>
    <script>const cuentasInfo={account_json};const cuentaMov=document.getElementById('cuenta-movimiento');const cambiarMoneda=()=>{{const i=cuentasInfo[cuentaMov.value]||{{}};document.getElementById('moneda-monto').textContent=i.codigo||'—';document.getElementById('simbolo-monto').textContent=i.simbolo||'';document.getElementById('saldo-valor').textContent=i.saldo||'—';}};cuentaMov.addEventListener('change',cambiarMoneda);cuentaMov.form.addEventListener('reset',()=>setTimeout(cambiarMoneda));cambiarMoneda();</script>
    </form></article>
    <article class="panel"><div class="panel-title"><div><p class="eyebrow">CONTROL MENSUAL</p><h2>Presupuestos y alertas</h2></div></div>{budget_html}
    <div class="subform"><h3 id="nuevo-limite">Crear o actualizar límite</h3><form method="post" action="/presupuestos" class="form-grid"><label class="span2">Categoría<select name="id_categoria" required>{option_rows(categories, None, 'gasto')}</select></label>
    <label>Monto máximo (moneda elegida)<input name="monto_limite" type="number" min="0.01" step="0.01" placeholder="50000.00" required></label>
    <label>Moneda del presupuesto<select name="id_moneda">{extension.currency_options()}</select></label><input type="hidden" name="anio" value="{year}"><input type="hidden" name="mes" value="{month}"><button class="primary" type="submit">Guardar límite</button></form>
    <p class="help">Una alerta aparece al alcanzar el 80 % del presupuesto de una categoría.</p></div></article></section>
    <section class="panel table-panel"><div class="panel-title"><div><p class="eyebrow">HISTORIAL</p><h2>Movimientos del período</h2></div><div class="row-actions"><span class="pill neutral">Últimos 100</span><a class="btn btn-neutral btn-sm" href="/historial?desde={start_day}&amp;hasta={end_day}">Ver historial completo →</a></div></div>
    <div class="table-scroll"><table><thead><tr><th>Descripción / categoría</th><th>Fecha</th><th>Monto</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="foot-note">Prototipo académico local · No exponer a Internet.</section>
    '''
    if not can_manage:
        content=re.sub(r'<div class="subform">.*?</div>','<p class="help">El propietario administra los presupuestos.</p>',content,flags=re.S)
        content=re.sub(r'<td class="actions">.*?</td>','<td>Consulta</td>',content,flags=re.S)
    return layout(content, subtitle='', compact_hero=True)


class Handler(BaseHTTPRequestHandler):
    CACHEABLE_ROUTES = ('/admin/cuentas', '/admin/categorias', '/admin/monedas', '/admin/presupuestos', '/admin/metas_ahorro')

    def read_cache_key(self):
        """Clave por sesión y perfil para páginas de catálogo sin parámetros; None si no es cacheable."""
        if self.command != 'GET':
            return None
        parsed = urlsplit(self.path)
        route = internal_path(parsed.path)
        if parsed.query or route not in self.CACHEABLE_ROUTES:
            return None
        token = self.session_token()
        with AUTH_LOCK:
            entry = SESSIONS.get(token)
        if not entry or entry[1] <= time.time():
            return None
        return (token, entry[2] if len(entry) > 2 else None, route)

    def serve_stale(self) -> bool:
        """Con SQLite caído, sirve la última copia de un catálogo con aviso visible. Nunca escribe."""
        key = self.read_cache_key()
        hit = read_cache.fetch(key) if key else None
        if not hit:
            return False
        body, age = hit
        body = body.replace(b'<main class="shell">', b'<main class="shell">' + read_cache.stale_banner(age), 1)
        self.respond(200, body, headers={'X-Datos-Desactualizados': str(age)}, cache=False)
        return True

    def respond(self, status: int, body: bytes, content_type: str = 'text/html; charset=utf-8',
                headers=None, cache: bool = True) -> None:
        if content_type.startswith('text/html'):
            if cache and status == 200:
                key = self.read_cache_key()
                if key:
                    read_cache.store(key, body)
            # Después de guardar en caché: la copia guardada nunca lleva token y se vuelve a firmar al servirse.
            # Sin tomar AUTH_LOCK: respond() también se llama con ese lock tomado (p. ej. al guardar usuarios).
            # Un token de una cookie vencida es inofensivo: ese POST igual exige sesión válida.
            token = self.session_token()
            if token:
                body = inject_csrf(body, quality.csrf_token(token))
            body = prefix_html(body)
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store' if status >= 400 else 'private, no-cache')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        if status >= 500:
            self.send_header('Retry-After', '30')
        self.end_headers()
        self.wfile.write(body)

    def serve_report(self, route, query):
        """Historial, reporte anual y sus CSV. Un filtro inválido muestra su motivo (400)."""
        try:
            if route == '/historial.csv':
                return self.respond(200, reportes.history_csv(query), 'text/csv; charset=utf-8',
                                    headers={'Content-Disposition': 'attachment; filename="movimientos.csv"'})
            if route == '/reportes/anual.csv':
                year = reportes.parse_year(query)
                return self.respond(200, reportes.annual_csv(query), 'text/csv; charset=utf-8',
                                    headers={'Content-Disposition': f'attachment; filename="reporte_anual_{year}.csv"'})
            if route == '/reportes/anual':
                return self.respond(200, reportes.annual_page(query).encode('utf-8'))
            notice = ''
            if 'generados' in query:
                try: created, remaining = int(query['generados'][0]), int(query.get('restantes', ['0'])[0])
                except ValueError: created, remaining = 0, 0
                notice = f'Se generaron {created} movimientos recurrentes.' + (f' Quedan {remaining} pendientes: vuelva a generar.' if remaining else '')
                query = {}
            return self.respond(200, reportes.history_page(query, notice).encode('utf-8'))
        except ValueError as exc:
            back = '/reportes/anual' if route.startswith('/reportes') else '/historial'
            return self.respond(400, layout(f'<section class="panel"><h2>Revise los filtros</h2><p>{e(exc)}</p><p><a href="{back}">Volver</a></p></section>').encode('utf-8'))

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

    @staticmethod
    def csrf_rejected() -> bytes:
        return error_page('Solicitud no válida', 'El formulario caducó o no proviene de esta aplicación. Recargue la página e intente de nuevo.')

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
                    SESSIONS[token]=(entry[0],time.time()+8*3600,*entry[2:])
                    return True
            SESSIONS.pop(token,None)
        return False

    def current_user(self):
        entry=SESSIONS.get(self.session_token())
        return user_by_name(entry[0]) if entry else None

    def is_admin(self):
        user=self.current_user()
        return auth.is_system_admin(user)

    def is_quality_admin(self):
        """Panel de calidad: administrador activo, independiente del modo temporal de usuarios."""
        user=self.current_user()
        return bool(user and user['role']=='admin' and user['active'])

    def auth_redirect(self):
        self.redirect_to('/login')

    def prepare_request(self):
        """Fija el rol de esta solicitud para que layout() oculte las opciones de administración."""
        request_ctx.set_user_id(1)
        authenticated = self.authenticated()
        user = self.current_user() if authenticated else None
        request_ctx.set_user_id(user['id_usuario'] if user else 1)
        request_ctx.set_admin(auth.is_system_admin(user))
        request_ctx.set_quality_admin(bool(user and user['role']=='admin' and user['active']))
        request_ctx.set_identity(user['name'] if user else '', user['role_name'] if user else '')
        if user:
            token=self.session_token()
            with AUTH_LOCK:
                entry=SESSIONS.get(token)
                selected=entry[2] if entry and len(entry)>2 else None
            if selected is not None:
                with db.connect() as c:
                    try: selected_profile=profiles.access(c,selected)
                    except profiles.AccessDenied: selected_profile=None
                request_ctx.set_profile(selected_profile)
                if selected_profile is None:
                    with AUTH_LOCK:
                        if token in SESSIONS: SESSIONS[token]=SESSIONS[token][:2]

    @controlled_request
    def do_GET(self) -> None:
        self.prepare_request()
        path = urlsplit(self.path)
        route = internal_path(path.path)
        if route == '/login':
            message='Cuenta creada correctamente. Ya puedes iniciar sesión.' if parse_qs(path.query).get('registro')==['ok'] else ''
            return self.redirect_to('/') if self.authenticated() else self.respond(200,login_page(message=message).encode('utf-8'))
        if route == '/registro':
            return self.redirect_to('/perfiles/elegir') if self.authenticated() else self.respond(200,registration_page().encode('utf-8'))
        if route == '/olvide-clave':
            return self.respond(200,forgot_password_page().encode('utf-8'))
        if route not in ('/static/styles.css', '/static/logo.png') and not self.authenticated(): return self.auth_redirect()
        if route == '/perfiles/elegir':
            return self.respond(200,profiles.selection_page().encode('utf-8'))
        if not request_ctx.profile() and route not in ('/perfiles','/admin/usuarios','/admin/cambiar-clave','/health','/static/styles.css','/static/logo.png'):
            return self.redirect_to('/perfiles/elegir')
        if route == '/perfiles':
            return self.respond(200,profiles.page().encode('utf-8'))
        if route == '/admin/usuarios':
            if not self.is_admin(): return self.respond(403,forbidden_page())
            return self.respond(200,users_page(editing=parse_qs(path.query).get('editar',[''])[0]).encode('utf-8'))
        if route == '/admin/cambiar-clave': return self.respond(200,change_password_page().encode('utf-8'))
        if route == '/admin/calidad':
            if not self.is_quality_admin(): return self.respond(403,forbidden_page())
            notices={'iniciado':'Trabajo iniciado. La página se actualiza sola al terminar.',
                     'ocupado':'Ya hay un trabajo en ejecución. Espere a que termine.',
                     'error':'No se pudo iniciar el trabajo. Revise el registro de errores del servidor.'}
            notice=notices.get(parse_qs(path.query).get('aviso',[''])[0],'')
            body=layout(quality.content(quality.csrf_token(self.session_token()),notice)).encode('utf-8')
            return self.respond(200,body,cache=False)
        if route == '/static/logo.png':
            return self.respond(200, CSS_PATH.with_name('logo.png').read_bytes(), 'image/png')
        if route == '/static/styles.css':
            return self.respond(200, CSS_PATH.read_bytes(), 'text/css; charset=utf-8')
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
        if route in ('/historial', '/historial.csv', '/reportes/anual', '/reportes/anual.csv'):
            return self.serve_report(route, parse_qs(path.query))
        if m := re.fullmatch(r'/admin/([a-z_]+)', route):
            if m.group(1)=='roles': return self.respond(404,error_page('Página no disponible','El rol se administra directamente en cada usuario.'))
            edit_id=int(parse_qs(path.query).get('editar',['0'])[0]) or None
            return self.respond(200, extension.page(m.group(1),edit_id).encode('utf-8'))
        if route in ('/', '/index.html'):
            query = parse_qs(path.query)
            return self.respond(200, dashboard_page(query).encode('utf-8'))
        return self.respond(404, layout('<section class="panel"><h2>Página no encontrada</h2><a href="/">Volver al inicio</a></section>').encode())

    @staticmethod
    def secure_cookie_suffix():
        # El proxy HTTPS termina TLS fuera de Python: activarlo con
        # FINANZAS_COOKIE_SECURE=1 en la configuración del servidor.
        return '; Secure' if os.environ.get('FINANZAS_COOKIE_SECURE') == '1' else ''

    @controlled_request
    def do_POST(self) -> None:
        self.prepare_request()
        path = internal_path(urlsplit(self.path).path)
        length = int(self.headers.get('Content-Length','0'))
        if length < 0 or length > 6_000_000:
            return self.respond(413, b'Formulario demasiado grande', 'text/plain; charset=utf-8')
        try:
            if path == '/logout':
                payload=self.rfile.read(length)
                if self.authenticated() and not quality.csrf_valid(self.session_token(),submitted_csrf(payload,self.headers.get('Content-Type',''))):
                    return self.respond(403,self.csrf_rejected())
                with AUTH_LOCK: SESSIONS.pop(self.session_token(),None)
                self.send_response(303);self.send_header('Location',external_path('/login'));self.send_header('Set-Cookie',f'finanzas_session=; HttpOnly; SameSite=Strict; Path={app_base_path() or chr(47)}; Max-Age=0{self.secure_cookie_suffix()}');self.send_header('Content-Length','0');self.end_headers();return
            payload=self.rfile.read(length)
            if path == '/registro':
                if self.authenticated(): return self.redirect_to('/perfiles/elegir')
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8'),keep_blank_values=True).items()}
                try: auth.register(form)
                except ValueError as exc:
                    return self.respond(400,registration_page(str(exc),form).encode('utf-8'))
                return self.redirect_to('/login?registro=ok')
            if path == '/login':
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8')).items()}
                creds=user_by_name(form.get('usuario',''))
                if creds and creds['active'] and hmac.compare_digest(form.get('usuario',''),creds['username']) and hmac.compare_digest(hash_password(form.get('contrasena',''),creds['salt']),creds['hash']):
                    token=secrets.token_urlsafe(32)
                    with AUTH_LOCK: SESSIONS[token]=(creds["username"],time.time()+8*3600)
                    self.send_response(303);self.send_header('Location',external_path('/perfiles/elegir'));self.send_header('Set-Cookie',f'finanzas_session={token}; HttpOnly; SameSite=Strict; Path={app_base_path() or chr(47)}; Max-Age=28800{self.secure_cookie_suffix()}');self.send_header('Content-Length','0');self.end_headers();return
                return self.respond(401,login_page('Usuario o contraseña incorrectos').encode('utf-8'))
            if not self.authenticated(): return self.auth_redirect()
            # Toda escritura con sesión exige el token CSRF del formulario (login y registro ocurren sin sesión).
            if not quality.csrf_valid(self.session_token(),submitted_csrf(payload,self.headers.get('Content-Type',''))):
                return self.respond(403,self.csrf_rejected())
            if not request_ctx.profile() and not path.startswith('/perfiles/') and path not in ('/admin/usuarios/guardar','/admin/cambiar-clave'):
                return self.redirect_to('/perfiles/elegir')
            if path == '/admin/calidad/ejecutar':
                if not self.is_quality_admin(): return self.respond(403,forbidden_page())
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8'),keep_blank_values=True).items()}
                if not quality.csrf_valid(self.session_token(),form.get('csrf','')):
                    return self.respond(403,error_page('Solicitud no válida','El formulario caducó. Recargue la página e intente de nuevo.'))
                outcome=quality.start(form.get('job',''))
                return self.redirect_to('/admin/calidad?aviso='+{'started':'iniciado','busy':'ocupado'}.get(outcome,'error'))
            if path == '/admin/usuarios/guardar':
                if not self.is_admin(): return self.respond(403,forbidden_page())
                form={k:v[0] for k,v in parse_qs(payload.decode('utf-8'),keep_blank_values=True).items()}
                username=form.get('username','').strip(); name=form.get('name','').strip()
                submitted_role=form.get('role','')
                role='admin' if submitted_role=='administrador' else 'usuario'
                active=form.get('active')=='1'; password=form.get('password','')
                with AUTH_LOCK:
                    users=credentials(); existing=next((u for u in users if u['username']==username),None)
                    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,40}',username) or not 1<=len(name)<=100 or submitted_role not in ('administrador','usuario') or (password and not 8<=len(password)<=128) or (not existing and not password):
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
                    editing_self = SESSIONS[self.session_token()][0] == username
                    for token, session in list(SESSIONS.items()):
                        if session[0] == username:
                            SESSIONS.pop(token, None)
                return self.redirect_to('/login' if editing_self else '/admin/usuarios')
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
            if path=='/perfiles/crear':
                pid=profiles.create(form.get('nombre',''))
                with AUTH_LOCK:
                    entry=SESSIONS[self.session_token()]
                    SESSIONS[self.session_token()]=(entry[0],entry[1],pid)
                return self.redirect_to('/perfiles/elegir')
            if path=='/perfiles/seleccionar':
                pid=int(form.get('id_perfil','0'))
                with db.connect() as c: profiles.access(c,pid)
                with AUTH_LOCK:
                    entry=SESSIONS[self.session_token()]
                    SESSIONS[self.session_token()]=(entry[0],entry[1],pid)
                return self.redirect_to('/')
            if m := re.fullmatch(r'/perfiles/(\d+)/(guardar|invitar|eliminar)',path):
                pid=int(m[1])
                if m[2]=='guardar': profiles.rename(pid,form.get('nombre',''))
                elif m[2]=='invitar': profiles.invite(pid,form.get('username',''))
                else: profiles.delete(pid)
                return self.redirect_to('/perfiles')
            if m := re.fullmatch(r'/perfiles/(\d+)/integrantes/(\d+)/eliminar',path):
                profiles.remove_member(int(m[1]),int(m[2]))
                return self.redirect_to('/perfiles')
            if path == '/recurrentes/generar':
                created, remaining = recurrentes.generate()
                extension.refresh_alerts()
                return self.redirect_to(f'/historial?generados={created}&restantes={remaining}')
            if m := re.fullmatch(r'/alertas/(\d+)/leida',path):
                with db.connect() as c:
                    profiles.access(c)
                    c.execute('UPDATE alertas SET leida=1 WHERE id_alerta=? AND id_perfil=?',(int(m[1]),request_ctx.profile_id()))
                return self.redirect_to('/admin/alertas')
            if m := re.fullmatch(r'/comprobantes/(\d+)/eliminar',path):
                extension.delete_receipt(int(m.group(1)))
                return self.redirect_to('/comprobantes')
            if m := re.fullmatch(r'/admin/([a-z_]+)(?:/(\d+))?/(guardar|eliminar)', path):
                table,item_id,action=m.group(1),int(m.group(2)) if m.group(2) else None,m.group(3)
                if table=='roles': return self.respond(404,error_page('Página no disponible','El rol se administra directamente en cada usuario.'))
                if table in ('usuarios',) and not self.is_admin(): return self.respond(403,forbidden_page())
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
            if isinstance(exc, UnicodeDecodeError) or str(exc).startswith('invalid literal'):
                raise ValueError('Formato incorrecto') from exc
            self.respond(400, layout(f'<section class="panel"><h2>Revise los datos</h2><p>{e(exc)}</p><p><a href="/">Volver al inicio</a></p></section>').encode('utf-8'))


def main() -> None:
    parser = argparse.ArgumentParser(description='MisFinanzas - Grupo 5')
    parser.add_argument('--host', default='127.0.0.1', help='Escuchar solo en localhost por defecto')
    parser.add_argument('--port', default=8000, type=int)
    args = parser.parse_args()
    try:
        db.init_db()
        extension.init()
        credentials()
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except Exception:
        logger.exception('Error al iniciar aplicación')
        parser.exit(1,'No se pudo iniciar la aplicación. Revise la base de datos, el puerto y el registro de errores.\n')
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
