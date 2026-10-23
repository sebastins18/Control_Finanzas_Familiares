"""Mantenimientos adicionales del prototipo local (sin sesiones)."""
from __future__ import annotations
import sqlite3
import os
import uuid
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from datetime import date
from html import escape
from src import db

SCHEMA = '''
CREATE TABLE IF NOT EXISTS monedas (id_moneda INTEGER PRIMARY KEY, codigo_iso TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, simbolo TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tipos_cambio (id_tipo_cambio INTEGER PRIMARY KEY, id_moneda_origen INTEGER NOT NULL REFERENCES monedas(id_moneda), id_moneda_destino INTEGER NOT NULL REFERENCES monedas(id_moneda), fecha TEXT NOT NULL, valor TEXT NOT NULL, CHECK(id_moneda_origen <> id_moneda_destino), UNIQUE(id_moneda_origen,id_moneda_destino,fecha));
CREATE TABLE IF NOT EXISTS metas_ahorro (id_meta INTEGER PRIMARY KEY, id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario), id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda), nombre TEXT NOT NULL, monto_objetivo_centimos INTEGER NOT NULL CHECK(monto_objetivo_centimos>0), fecha_objetivo TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transferencias (id_transferencia INTEGER PRIMARY KEY, id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario), id_cuenta_origen INTEGER NOT NULL REFERENCES cuentas(id_cuenta), id_cuenta_destino INTEGER NOT NULL REFERENCES cuentas(id_cuenta), monto_origen_centimos INTEGER NOT NULL CHECK(monto_origen_centimos>0), monto_destino_centimos INTEGER NOT NULL CHECK(monto_destino_centimos>0), id_tipo_cambio INTEGER REFERENCES tipos_cambio(id_tipo_cambio), fecha TEXT NOT NULL, descripcion TEXT NOT NULL DEFAULT '', CHECK(id_cuenta_origen <> id_cuenta_destino));
CREATE TABLE IF NOT EXISTS movimientos_ahorro (id_movimiento_ahorro INTEGER PRIMARY KEY, id_meta INTEGER NOT NULL REFERENCES metas_ahorro(id_meta), id_cuenta INTEGER NOT NULL REFERENCES cuentas(id_cuenta), tipo TEXT NOT NULL CHECK(tipo IN ('aporte','retiro')), monto_centimos INTEGER NOT NULL CHECK(monto_centimos>0), fecha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alertas (id_alerta INTEGER PRIMARY KEY, id_presupuesto INTEGER NOT NULL REFERENCES presupuestos(id_presupuesto) ON DELETE CASCADE, id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario), umbral INTEGER NOT NULL, fecha TEXT NOT NULL, leida INTEGER NOT NULL DEFAULT 0, UNIQUE(id_presupuesto,umbral));
CREATE TABLE IF NOT EXISTS comprobantes (id_comprobante INTEGER PRIMARY KEY, id_movimiento INTEGER NOT NULL REFERENCES movimientos(id_movimiento), ruta_archivo TEXT NOT NULL, tipo_mime TEXT NOT NULL, fecha_subida TEXT NOT NULL DEFAULT (datetime('now')));
'''

def init():
    with db.connect() as c:
        c.executescript(SCHEMA)
        c.execute('CREATE TABLE IF NOT EXISTS app_config (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)')
        c.execute("INSERT OR IGNORE INTO app_config(clave,valor) VALUES('perfil_activo','1')")
        for code, name, symbol in [('CRC','Colón costarricense','₡'),('USD','Dólar estadounidense','$'),('EUR','Euro','€')]:
            c.execute('INSERT OR IGNORE INTO monedas(codigo_iso,nombre,simbolo) VALUES(?,?,?)',(code,name,symbol))
        cols={r['name'] for r in c.execute('PRAGMA table_info(cuentas)')}
        if 'id_moneda' not in cols:
            c.execute('ALTER TABLE cuentas ADD COLUMN id_moneda INTEGER REFERENCES monedas(id_moneda)')
        c.execute("UPDATE cuentas SET id_moneda=(SELECT id_moneda FROM monedas WHERE codigo_iso='CRC') WHERE id_moneda IS NULL")
        cols={r['name'] for r in c.execute('PRAGMA table_info(movimientos)')}
        # Migración de bases V10: el tipo de cambio pertenece exclusivamente a transferencias.
        if 'id_tipo_cambio' in cols:
            c.execute('ALTER TABLE movimientos DROP COLUMN id_tipo_cambio')
        cols={r['name'] for r in c.execute('PRAGMA table_info(movimientos)')}
        if 'monto_acreditado_centimos' not in cols: c.execute('ALTER TABLE movimientos ADD COLUMN monto_acreditado_centimos INTEGER')
        cols={r['name'] for r in c.execute('PRAGMA table_info(presupuestos)')}
        if 'id_moneda' not in cols:
            c.execute('ALTER TABLE presupuestos ADD COLUMN id_moneda INTEGER REFERENCES monedas(id_moneda)')
        c.execute("UPDATE presupuestos SET id_moneda=(SELECT id_moneda FROM monedas WHERE codigo_iso='CRC') WHERE id_moneda IS NULL")

# Each maintenance is explicitly allowlisted; SQL identifiers never come from the request.
CONFIG = {
 'usuarios': ('Usuarios locales','usuarios','id_usuario',[('nombre','Nombre','text')]),
 'categorias': ('Categorías','categorias','id_categoria',[('nombre','Nombre','text'),('tipo','Tipo','choice:ingreso,gasto')]),
 'cuentas': ('Cuentas','cuentas','id_cuenta',[('nombre','Nombre','text'),('saldo_inicial_centimos','Saldo inicial','money'),('id_moneda','Moneda','ref:monedas')]),
 'monedas': ('Monedas','monedas','id_moneda',[('codigo_iso','Código ISO','text'),('nombre','Nombre','text'),('simbolo','Símbolo','text')]),
 'presupuestos': ('Presupuestos','presupuestos','id_presupuesto',[('id_categoria','Categoría','ref:categorias'),('id_moneda','Moneda','ref:monedas'),('anio','Año','integer'),('mes','Mes','integer'),('monto_limite_centimos','Límite','money')]),
 'metas_ahorro': ('Metas de ahorro','metas_ahorro','id_meta',[('nombre','Nombre','text'),('id_moneda','Moneda','ref:monedas'),('monto_objetivo_centimos','Monto objetivo','money'),('fecha_objetivo','Fecha objetivo','date')]),
 'transferencias': ('Transferencias','transferencias','id_transferencia',[('id_cuenta_origen','Cuenta origen','ref:cuentas'),('id_cuenta_destino','Cuenta destino','ref:cuentas'),('monto_origen_centimos','Monto origen','money'),('monto_destino_centimos','Monto destino','money'),('id_tipo_cambio','Tipo de cambio (opcional)','optional:tipos_cambio'),('fecha','Fecha','date'),('descripcion','Descripción','text')]),
 'alertas': ('Alertas','alertas','id_alerta',[('id_presupuesto','Presupuesto','ref:presupuestos'),('umbral','Umbral (%)','integer'),('fecha','Fecha','date'),('leida','Leída (0/1)','integer')]),
 'movimientos_ahorro': ('Movimientos de ahorro','movimientos_ahorro','id_movimiento_ahorro',[('id_meta','Meta','ref:metas_ahorro'),('id_cuenta','Cuenta','ref:cuentas'),('tipo','Tipo','choice:aporte,retiro'),('monto_centimos','Monto','money'),('fecha','Fecha','date')]),
}

def h(v): return escape(str(v if v is not None else ''),quote=True)
def label_for(table,row):
    if table=='presupuestos': return f"{row['anio']}/{row['mes']} · categoría {row['id_categoria']}"
    if table=='alertas': return f"Presupuesto {row['id_presupuesto']} · {row['umbral']}%"
    if table=='monedas': return f"{row['codigo_iso']} — {row['nombre']}"
    if table=='tipos_cambio': return f"{row['fecha']} · {row['id_moneda_origen']} → {row['id_moneda_destino']} · {row['valor']}"
    return str(row['nombre'] if 'nombre' in row.keys() else row[0])

def all_rows(c, table):
    if table not in CONFIG and table not in ('presupuestos','tipos_cambio'): raise ValueError('Tabla desconocida')
    owner=f' WHERE id_usuario={active_profile(c)}' if table in ('categorias','cuentas','metas_ahorro','transferencias','presupuestos','alertas') else ''
    return c.execute(f'SELECT * FROM {table}{owner} ORDER BY 1 DESC').fetchall()

def save(table, form, item_id=None):
    if table not in CONFIG: raise ValueError('Mantenimiento no disponible')
    _,_,pk,fields=CONFIG[table]
    values={}
    for key,label,kind in fields:
        raw=str(form.get(key,'')).strip()
        if table=='transferencias' and key in ('monto_destino_centimos','id_tipo_cambio'):
            values[key]=None
            continue
        if kind.startswith('optional:') and not raw: values[key]=None; continue
        if not raw: raise ValueError(f'El campo {label} es obligatorio.')
        if kind=='integer':
            try: values[key]=int(raw)
            except ValueError: raise ValueError(f'{label} inválido')
        elif kind=='money': values[key]=0 if kind=='money' and key=='saldo_inicial_centimos' and raw in ('0','0.0','0.00') else db.parse_money(raw)
        elif kind=='date': values[key]=db.validate_date(raw)
        elif kind=='rate':
            try: rate=Decimal(raw)
            except InvalidOperation: raise ValueError('Tipo de cambio inválido')
            if not rate.is_finite() or rate<=0: raise ValueError('El tipo de cambio debe ser positivo')
            values[key]=str(rate)
        elif kind.startswith(('ref:','optional:')):
            try: values[key]=int(raw)
            except ValueError: raise ValueError(f'{label} inválido')
        elif kind.startswith('choice:'):
            if raw not in kind[7:].split(','): raise ValueError(f'{label} inválido')
            values[key]=raw
        else: values[key]=raw[:160]
    if table=='presupuestos':
        if not (2020<=values['anio']<=2100 and 1<=values['mes']<=12): raise ValueError('Período inválido')
    if table=='alertas':
        if values['umbral'] not in (80,100) or values['leida'] not in (0,1): raise ValueError('Alerta inválida')
    if table=='cuentas' and values['saldo_inicial_centimos']<0: raise ValueError('Saldo inicial inválido')
    if table=='tipos_cambio' and values['id_moneda_origen']==values['id_moneda_destino']: raise ValueError('Seleccione monedas diferentes')
    if table=='transferencias':
        if values['id_cuenta_origen']==values['id_cuenta_destino']: raise ValueError('Las cuentas deben ser distintas')
    manual_raw=str(form.get('tipo_cambio_manual','')).strip()
    manual_rate=None
    if table=='transferencias':
        with db.connect() as pre:
            user=active_profile(pre)
            origin=pre.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_usuario=?',(values['id_cuenta_origen'],user)).fetchone()
            target=pre.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_usuario=?',(values['id_cuenta_destino'],user)).fetchone()
            if not origin or not target: raise ValueError('Cuenta no válida para este perfil')
            if origin[0]!=target[0]:
                if not manual_raw: raise ValueError('Ingrese el tipo de cambio manual')
                try: manual_rate=Decimal(manual_raw)
                except InvalidOperation: raise ValueError('Tipo de cambio inválido')
                if not manual_rate.is_finite() or manual_rate<=0 or manual_rate>Decimal('1000000000') or manual_rate.as_tuple().exponent < -2:
                    raise ValueError('El tipo de cambio debe ser positivo y tener máximo dos decimales')
    with db.connect() as c:
        if table=='presupuestos':
            cat=c.execute("SELECT 1 FROM categorias WHERE id_categoria=? AND tipo='gasto'",(values['id_categoria'],)).fetchone()
            if not cat: raise ValueError('La categoría debe ser de gasto')
        if table=='movimientos_ahorro' and values['tipo']=='retiro':
            balance=c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='aporte' THEN monto_centimos ELSE -monto_centimos END),0) FROM movimientos_ahorro WHERE id_meta=? AND id_movimiento_ahorro != ?",(values['id_meta'],item_id or -1)).fetchone()[0]
            if values['monto_centimos']>balance: raise ValueError('El retiro supera el ahorro disponible')
        if table=='transferencias':
            user=active_profile(c)
            src=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_usuario=?',(values['id_cuenta_origen'],user)).fetchone()
            dst=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_usuario=?',(values['id_cuenta_destino'],user)).fetchone()
            if not src or not dst: raise ValueError('Cuenta no válida para este perfil')
            if src[0]==dst[0]:
                values['id_tipo_cambio']=None
                values['monto_destino_centimos']=values['monto_origen_centimos']
            else:
                from decimal import ROUND_HALF_UP
                rate_text=format(manual_rate,'.2f')
                c.execute('INSERT INTO tipos_cambio(id_moneda_origen,id_moneda_destino,fecha,valor) VALUES(?,?,?,?) ON CONFLICT(id_moneda_origen,id_moneda_destino,fecha) DO UPDATE SET valor=excluded.valor',(src[0],dst[0],values['fecha'],rate_text))
                rate_id=c.execute('SELECT id_tipo_cambio FROM tipos_cambio WHERE id_moneda_origen=? AND id_moneda_destino=? AND fecha=?',(src[0],dst[0],values['fecha'])).fetchone()[0]
                values['id_tipo_cambio']=rate_id
                values['monto_destino_centimos']=int((Decimal(values['monto_origen_centimos'])*manual_rate).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        if table=='movimientos_ahorro':
            meta=c.execute('SELECT id_moneda FROM metas_ahorro WHERE id_meta=? AND id_usuario=1',(values['id_meta'],)).fetchone()
            acc=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_usuario=1',(values['id_cuenta'],)).fetchone()
            if not meta or not acc or meta[0]!=acc[0]: raise ValueError('La cuenta y meta deben tener la misma moneda')
        if table=='movimientos_ahorro':
            from src.finance import account_balance
            sign=1 if values['tipo']=='retiro' else -1
            old=c.execute('SELECT * FROM movimientos_ahorro WHERE id_movimiento_ahorro=?',(item_id,)).fetchone() if item_id else None
            delta=sign*values['monto_centimos']
            if old and old['id_cuenta']==values['id_cuenta']: delta-= (1 if old['tipo']=='retiro' else -1)*old['monto_centimos']
            if delta<0 and account_balance(c,values['id_cuenta'])+delta<0: raise ValueError('Fondos insuficientes en la cuenta')
        if table=='transferencias':
            from src.finance import account_balance
            old=c.execute('SELECT * FROM transferencias WHERE id_transferencia=?',(item_id,)).fetchone() if item_id else None
            available=account_balance(c,values['id_cuenta_origen'])
            if old and old['id_cuenta_origen']==values['id_cuenta_origen']: available+=old['monto_origen_centimos']
            if available<values['monto_origen_centimos']: raise ValueError('Fondos insuficientes para transferir')
        if table=='categorias':
            old=c.execute('SELECT tipo FROM categorias WHERE id_categoria=?',(item_id,)).fetchone() if item_id else None
            if old and old[0]!=values['tipo'] and c.execute('SELECT 1 FROM movimientos WHERE id_categoria=? LIMIT 1',(item_id,)).fetchone(): raise ValueError('No se puede cambiar el tipo de una categoría utilizada')
        if table in ('categorias','cuentas','metas_ahorro','transferencias','presupuestos','alertas'): values['id_usuario']=active_profile(c)
        cols=list(values)
        if item_id is None:
            c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",tuple(values.values()))
        else:
            old=c.execute(f'SELECT 1 FROM {table} WHERE {pk}=?',(item_id,)).fetchone()
            if not old: raise ValueError('Registro no encontrado')
            c.execute(f"UPDATE {table} SET {','.join(k+'=?' for k in cols)} WHERE {pk}=?",(*values.values(),item_id))

def delete(table,item_id):
    if table not in CONFIG: raise ValueError('Mantenimiento no disponible')
    pk=CONFIG[table][2]
    if table=='usuarios' and item_id==1: raise ValueError('No se puede eliminar el usuario local activo')
    with db.connect() as c:
        cur=c.execute(f'DELETE FROM {table} WHERE {pk}=?',(item_id,))
        if not cur.rowcount: raise ValueError('Registro no encontrado')

def page(table, edit_id=None):
    if table not in CONFIG: raise ValueError('Mantenimiento no disponible')
    title,_,pk,fields=CONFIG[table]
    with db.connect() as c:
        rows=all_rows(c,table)
        item=c.execute(f'SELECT * FROM {table} WHERE {pk}=?',(edit_id,)).fetchone() if edit_id else None
        if edit_id and not item: raise ValueError('Registro no encontrado')
        refs={t:all_rows(c,t) for _,_,kind in fields if (kind.startswith('ref:') or kind.startswith('optional:')) for t in [kind.split(':',1)[1]]}
    from src.app import layout
    inputs=''
    for key,label,kind in fields:
        if table=='transferencias' and key in ('monto_destino_centimos','id_tipo_cambio'):
            continue
        value=item[key] if item else ''
        if kind=='money' and item: value=f'{value/100:.2f}'
        if kind.startswith(('ref:','optional:','choice:')):
            if kind.startswith('choice:'): options=[(v,v) for v in kind[7:].split(',')]
            else:
                t=kind.split(':',1)[1]; options=[(r[CONFIG[t][2]],label_for(t,r)) for r in refs[t]]
            opt='<option value="">Seleccionar</option>' if kind.startswith('optional:') else ''
            opt+=''.join(f'<option value="{h(v)}" {"selected" if str(v)==str(value) else ""}>{h(n)}</option>' for v,n in options)
            field=f'<select name="{key}" {"" if kind.startswith("optional:") else "required"}>{opt}</select>'
        else:
            typ='date' if kind=='date' else 'number' if kind in ('money','rate','integer') else 'text'
            step=' step="0.01"' if kind=='money' else ' step="any"' if kind=='rate' else ''
            default=date.today().isoformat() if kind=='date' and not item else value
            field=f'<input name="{key}" type="{typ}"{step} value="{h(default)}" required>'
        inputs+=f'<label>{h(label)}{field}</label>'
    action=f'/admin/{table}/{edit_id}/guardar' if item else f'/admin/{table}/guardar'
    trs=''
    for r in rows:
        rid=r[pk]
        summary=' · '.join(f'{label}: {h((f"{r[key]/100:.2f}" if kind=="money" else r[key]))}' for key,label,kind in fields)
        trs+=f'<tr><td class="registro-detalle">{summary}</td><td><a href="/admin/{table}?editar={rid}">Editar</a> <form method="post" action="/admin/{table}/{rid}/eliminar" style="display:inline"><button type="submit" onclick="return confirm(\'¿Eliminar registro?\')">Eliminar</button></form></td></tr>'
    nav='' 
    if table=='transferencias':
        with db.connect() as fxdb:
            account_info={str(r['id_cuenta']):{'currency':r['codigo_iso'],'id':r['id_moneda']} for r in fxdb.execute('SELECT a.id_cuenta,a.id_moneda,m.codigo_iso FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda WHERE a.id_usuario=?',(active_profile(fxdb),))}
        inputs += '''<div class="span2" id="fx-panel" style="padding:14px;border:1px solid #cbd5e1;border-radius:10px" aria-live="polite"><strong>Conversión de transferencia</strong><p id="fx-status">Seleccione las cuentas para ingresar el tipo de cambio.</p><label id="fx-manual-label" style="display:none">Tipo de cambio manual (1 unidad de origen equivale a unidades de destino)<input type="number" name="tipo_cambio_manual" id="fx-manual" min="0.01" max="1000000000" step="0.01" disabled></label><p id="fx-preview"></p></div>'''
        inputs += '<script>'+'''const accounts=ACCOUNT_DATA,origin=document.querySelector('[name="id_cuenta_origen"]'),dest=document.querySelector('[name="id_cuenta_destino"]'),amount=document.querySelector('[name="monto_origen_centimos"]'),manual=document.getElementById('fx-manual'),label=document.getElementById('fx-manual-label'),status=document.getElementById('fx-status'),preview=document.getElementById('fx-preview');function update(){const a=accounts[origin.value],b=accounts[dest.value];const different=a&&b&&a.id!==b.id;label.style.display=different?'block':'none';manual.disabled=!different;manual.required=!!different;status.textContent=!a||!b?'Seleccione las cuentas.':different?'Introduzca el tipo de cambio manual de '+a.currency+' a '+b.currency+'.':'Misma moneda: no se requiere conversión.';const rate=Number(manual.value);preview.textContent=different&&rate>0&&Number(amount.value)>0?'Monto estimado a recibir: '+(Number(amount.value)*rate).toFixed(2)+' '+b.currency:'';}[origin,dest,amount,manual].forEach(x=>x.addEventListener('input',update));update();''' .replace('ACCOUNT_DATA',json.dumps(account_info))+'</script>'

    body=f'<section class="panel"><p><a href="/">← Panel principal</a></p><h2>{h(title)}</h2><p class="muted">Administración de {h(title.lower())}. Los cambios se guardan en SQLite.</p><h3>{"Editar" if item else "Nuevo"} registro</h3><form class="form-grid" method="post" action="{action}">{inputs}<button class="primary" type="submit">Guardar</button></form></section><section class="panel table-panel"><h2>Registros</h2><div class="table-scroll"><table><thead><tr><th>Detalle</th><th>Acciones</th></tr></thead><tbody>{trs or "<tr><td>No hay registros</td></tr>"}</tbody></table></div></section>'
    return layout(body)


def active_profile(c):
    try:
        row=c.execute("SELECT valor FROM app_config WHERE clave='perfil_activo'").fetchone()
        return int(row[0]) if row else 1
    except sqlite3.OperationalError:
        return 1

def profile_name():
    with db.connect() as c:
        r=c.execute('SELECT nombre FROM usuarios WHERE id_usuario=?',(active_profile(c),)).fetchone()
        return r[0] if r else 'Familia de demostración'

def profiles_page():
    from src.app import layout
    with db.connect() as c:
        rows=c.execute('SELECT id_usuario,nombre FROM usuarios ORDER BY nombre').fetchall()
        selected=active_profile(c)
    options=''.join(f'<option value="{r[0]}" {"selected" if r[0]==selected else ""}>{h(r[1])}</option>' for r in rows)
    return layout(f'''<section class="panel"><h2>Perfiles familiares</h2><p>Selecciona el perfil con el que se registrarán y consultarán los datos. <strong>El acceso al sistema requiere iniciar sesión.</strong></p><form method="post" action="/perfiles/seleccionar" class="form-grid"><label>Perfil activo<select name="id_usuario">{options}</select></label><button class="primary">Cambiar perfil</button></form><p><a href="/admin/usuarios">Administrar registros de perfiles →</a></p></section>''')

def select_profile(form):
    uid=int(form.get('id_usuario',0))
    with db.connect() as c:
        if not c.execute('SELECT 1 FROM usuarios WHERE id_usuario=?',(uid,)).fetchone(): raise ValueError('Perfil inexistente')
        c.execute("INSERT INTO app_config(clave,valor) VALUES('perfil_activo',?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",(str(uid),))
        for name,kind in [('Salario','ingreso'),('Otros ingresos','ingreso'),('Alimentación','gasto'),('Transporte','gasto'),('Vivienda','gasto')]:
            c.execute('INSERT OR IGNORE INTO categorias(id_usuario,nombre,tipo) VALUES(?,?,?)',(uid,name,kind))
        c.execute("INSERT OR IGNORE INTO cuentas(id_usuario,nombre,id_moneda) VALUES(?,?,(SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'))",(uid,'Cuenta principal'))

def currency_options():
    with db.connect() as c:
        rows=c.execute('SELECT id_moneda,codigo_iso,nombre FROM monedas ORDER BY codigo_iso').fetchall()
    return ''.join(f'<option value="{r[0]}" {"selected" if r[1]=="CRC" else ""}>{h(r[1])} — {h(r[2])}</option>' for r in rows)

def refresh_alerts():
    # Recompute thresholds from current expenses. Idempotent: one alert per budget and threshold.
    with db.connect() as c:
        user=active_profile(c)
        budgets=c.execute('SELECT * FROM presupuestos WHERE id_usuario=?',(user,)).fetchall()
        for b in budgets:
            start=f"{b['anio']:04d}-{b['mes']:02d}-01"
            end=f"{b['anio']+1:04d}-01-01" if b['mes']==12 else f"{b['anio']:04d}-{b['mes']+1:02d}-01"
            moves=c.execute("SELECT m.monto_centimos,m.fecha,a.id_moneda FROM movimientos m JOIN cuentas a ON a.id_cuenta=m.id_cuenta WHERE m.id_usuario=? AND m.id_categoria=? AND m.tipo='gasto' AND m.fecha>=? AND m.fecha<?",(user,b['id_categoria'],start,end)).fetchall()
            crc=c.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
            total=0
            incomplete=False
            from src.finance import historical_conversion
            for m in moves:
                try: total+=historical_conversion(c,m['id_moneda'],b['id_moneda'] or crc,m['monto_centimos'],m['fecha'])
                except ValueError: incomplete=True
            if incomplete: continue
            for threshold in (80,100):
                if total*100>=b['monto_limite_centimos']*threshold:
                    c.execute('INSERT OR IGNORE INTO alertas(id_presupuesto,id_usuario,umbral,fecha,leida) VALUES(?,?,?,?,0)',(b['id_presupuesto'],user,threshold,date.today().isoformat()))
                else:
                    c.execute('DELETE FROM alertas WHERE id_presupuesto=? AND umbral=?',(b['id_presupuesto'],threshold))

def receipts_dir():
    # Adjuntos junto a DB_PATH, fuera de public_html cuando se configura despliegue.
    return db.db_path().parent / 'comprobantes'
ALLOWED={'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}

def upload_receipt(payload,content_type):
    if not content_type.lower().startswith('multipart/form-data'): raise ValueError('El formulario debe adjuntar un archivo')
    message=BytesParser(policy=default).parsebytes(b'Content-Type: '+content_type.encode()+b'\r\nMIME-Version: 1.0\r\n\r\n'+payload)
    if not message.is_multipart(): raise ValueError('Formulario inválido')
    parts={part.get_param('name',header='content-disposition'):part for part in message.iter_parts()}
    if 'archivo' not in parts or 'id_movimiento' not in parts: raise ValueError('Seleccione un gasto y un archivo')
    content=parts['archivo'].get_payload(decode=True)
    if not content or len(content)>5_000_000: raise ValueError('El archivo debe tener entre 1 byte y 5 MB')
    typ=parts['archivo'].get_content_type()
    valid=(typ=='application/pdf' and content.startswith(b'%PDF-')) or (typ=='image/png' and content.startswith(b'\x89PNG\r\n\x1a\n')) or (typ=='image/jpeg' and content.startswith(b'\xff\xd8\xff')) or (typ=='image/webp' and content.startswith(b'RIFF') and content[8:12]==b'WEBP')
    if typ not in ALLOWED or not valid: raise ValueError('Solo se permiten PDF, PNG, JPG o WebP válidos')
    movement=int(parts['id_movimiento'].get_content().strip())
    with db.connect() as c:
        if not c.execute("SELECT 1 FROM movimientos WHERE id_movimiento=? AND id_usuario=? AND tipo='gasto'",(movement,active_profile(c))).fetchone(): raise ValueError('Gasto no válido para el perfil')
        receipts_dir().mkdir(parents=True,exist_ok=True)
        filename=uuid.uuid4().hex+ALLOWED[typ]
        path=receipts_dir()/filename
        try:
            path.write_bytes(content)
            c.execute('INSERT INTO comprobantes(id_movimiento,ruta_archivo,tipo_mime) VALUES(?,?,?)',(movement,filename,typ))
        except Exception:
            path.unlink(missing_ok=True)
            raise

def receipt_file(receipt_id):
    with db.connect() as c:
        r=c.execute('SELECT co.* FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE co.id_comprobante=? AND m.id_usuario=?',(receipt_id,active_profile(c))).fetchone()
    if not r: return None
    path=receipts_dir()/Path(r['ruta_archivo']).name
    if not path.is_file(): return None
    return path.read_bytes(),r['tipo_mime']

def delete_receipt(receipt_id):
    with db.connect() as c:
        r=c.execute('SELECT co.ruta_archivo FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE co.id_comprobante=? AND m.id_usuario=?',(receipt_id,active_profile(c))).fetchone()
        if not r: raise ValueError('Comprobante inexistente')
        c.execute('DELETE FROM comprobantes WHERE id_comprobante=?',(receipt_id,))
    (receipts_dir()/Path(r[0]).name).unlink(missing_ok=True)

def receipts_page():
    from src.app import layout
    with db.connect() as c:
        user=active_profile(c)
        expenses=c.execute("SELECT id_movimiento,fecha,descripcion,monto_centimos FROM movimientos WHERE id_usuario=? AND tipo='gasto' ORDER BY fecha DESC LIMIT 250",(user,)).fetchall()
        files=c.execute('SELECT co.id_comprobante,co.tipo_mime,co.fecha_subida,m.descripcion FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE m.id_usuario=? ORDER BY co.id_comprobante DESC',(user,)).fetchall()
    options=''.join(f'<option value="{r[0]}">{h(r[1])} · {h(r[2] or "Gasto")} · {r[3]/100:.2f} CRC</option>' for r in expenses)
    trs=''.join(f'<tr><td>{h(r[3])}</td><td>{h(r[1])}</td><td>{h(r[2])}</td><td><a target="_blank" rel="noopener" href="/comprobantes/{r[0]}/archivo">Ver</a> <form method="post" action="/comprobantes/{r[0]}/eliminar" style="display:inline"><button onclick="return confirm(\'¿Eliminar comprobante?\')">Eliminar</button></form></td></tr>' for r in files)
    return layout(f'''<section class="panel"><h2>Comprobantes de gastos</h2><p>Adjunta PDF, JPG, PNG o WebP (máximo 5 MB). Los archivos se almacenan localmente en <code>data/comprobantes</code>.</p><form method="post" enctype="multipart/form-data" action="/comprobantes/subir" class="form-grid"><label>Gasto<select name="id_movimiento" required>{options}</select></label><label>Archivo<input type="file" name="archivo" accept=".pdf,.jpg,.jpeg,.png,.webp" required></label><button class="primary">Adjuntar comprobante</button></form></section><section class="panel table-panel"><h2>Archivos adjuntos</h2><div class="table-scroll"><table><thead><tr><th>Gasto</th><th>Tipo</th><th>Fecha</th><th>Acciones</th></tr></thead><tbody>{trs or '<tr><td colspan="4">No hay comprobantes</td></tr>'}</tbody></table></div></section>''')
