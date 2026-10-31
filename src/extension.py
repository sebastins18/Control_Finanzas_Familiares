"""Mantenimientos adicionales del prototipo local (sin sesiones)."""
from __future__ import annotations
import sqlite3
import os
import uuid
import json
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from datetime import date
from html import escape
from src import db, finance

SCHEMA = '''
CREATE TABLE IF NOT EXISTS monedas (id_moneda INTEGER PRIMARY KEY, codigo_iso TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, simbolo TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS metas_ahorro (id_meta INTEGER PRIMARY KEY, id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil), id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda), nombre TEXT NOT NULL, monto_objetivo_centimos INTEGER NOT NULL CHECK(monto_objetivo_centimos>0), fecha_objetivo TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transferencias (id_transferencia INTEGER PRIMARY KEY, id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil), id_cuenta_origen INTEGER NOT NULL REFERENCES cuentas(id_cuenta), id_cuenta_destino INTEGER NOT NULL REFERENCES cuentas(id_cuenta), monto_origen_centimos INTEGER NOT NULL CHECK(monto_origen_centimos>0), monto_destino_centimos INTEGER NOT NULL CHECK(monto_destino_centimos>0), id_tipo_cambio INTEGER REFERENCES tipos_cambio(id_tipo_cambio), fecha TEXT NOT NULL, descripcion TEXT NOT NULL DEFAULT '', CHECK(id_cuenta_origen <> id_cuenta_destino));
CREATE TABLE IF NOT EXISTS movimientos_ahorro (id_movimiento_ahorro INTEGER PRIMARY KEY, id_meta INTEGER NOT NULL REFERENCES metas_ahorro(id_meta), id_cuenta INTEGER NOT NULL REFERENCES cuentas(id_cuenta), tipo TEXT NOT NULL CHECK(tipo IN ('aporte','retiro')), monto_centimos INTEGER NOT NULL CHECK(monto_centimos>0), fecha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alertas (id_alerta INTEGER PRIMARY KEY, id_presupuesto INTEGER NOT NULL REFERENCES presupuestos(id_presupuesto) ON DELETE CASCADE, id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil), umbral INTEGER NOT NULL, fecha TEXT NOT NULL, leida INTEGER NOT NULL DEFAULT 0, UNIQUE(id_presupuesto,umbral));
CREATE TABLE IF NOT EXISTS comprobantes (id_comprobante INTEGER PRIMARY KEY, id_movimiento INTEGER NOT NULL REFERENCES movimientos(id_movimiento), ruta_archivo TEXT NOT NULL, tipo_mime TEXT NOT NULL, fecha_subida TEXT NOT NULL DEFAULT (datetime('now')));
'''

SCHEMA = finance.QUOTE_SCHEMA + ';\n' + SCHEMA


def init():
    with db.connect() as c:
        c.executescript(SCHEMA)
        alert_columns={r['name'] for r in c.execute('PRAGMA table_info(alertas)')}
        if 'origen' not in alert_columns:
            c.execute("ALTER TABLE alertas ADD COLUMN origen TEXT NOT NULL DEFAULT 'automatica' CHECK(origen IN ('automatica','manual'))")
        c.execute('CREATE TABLE IF NOT EXISTS app_config (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)')

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
 'categorias': ('Categorías','categorias','id_categoria',[('nombre','Nombre','text'),('tipo','Tipo','choice:ingreso,gasto')]),
 'cuentas': ('Cuentas','cuentas','id_cuenta',[('nombre','Nombre','text'),('saldo_inicial_centimos','Saldo inicial','money'),('id_moneda','Moneda','ref:monedas')]),
 'monedas': ('Monedas','monedas','id_moneda',[('codigo_iso','Código ISO','text'),('nombre','Nombre','text'),('simbolo','Símbolo','text')]),
 'presupuestos': ('Presupuestos','presupuestos','id_presupuesto',[('id_categoria','Categoría','ref:categorias'),('id_moneda','Moneda','ref:monedas'),('anio','Año','integer'),('mes','Mes','integer'),('monto_limite_centimos','Límite','money')]),
 'metas_ahorro': ('Metas de ahorro','metas_ahorro','id_meta',[('nombre','Nombre','text'),('id_moneda','Moneda','ref:monedas'),('monto_objetivo_centimos','Monto objetivo','money'),('fecha_objetivo','Fecha objetivo','date')]),
 'transferencias': ('Transferencias','transferencias','id_transferencia',[('id_cuenta_origen','Cuenta origen','ref:cuentas'),('id_cuenta_destino','Cuenta destino','ref:cuentas'),('monto_origen_centimos','Monto origen','money'),('monto_destino_centimos','Monto destino','money'),('id_tipo_cambio','Tipo de cambio (opcional)','optional:tipos_cambio'),('fecha','Fecha','date'),('descripcion','Descripción','text')]),
 'alertas': ('Alertas','alertas','id_alerta',[('id_presupuesto','Presupuesto','ref:presupuestos'),('umbral','Umbral (%)','integer'),('fecha','Fecha','date'),('leida','Leída','boolean')]),
 'movimientos_ahorro': ('Movimientos de ahorro','movimientos_ahorro','id_movimiento_ahorro',[('id_meta','Meta','ref:metas_ahorro'),('id_cuenta','Cuenta','ref:cuentas'),('tipo','Tipo','choice:aporte,retiro'),('monto_centimos','Monto','money'),('fecha','Fecha','date')]),
}

MONTH_NAMES=('Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre')

def h(v): return escape(str(v if v is not None else ''),quote=True)

def label_for_column(table,key,label):
    """Encabezado de columna: el nombre del campo, con el nombre visible de la cotización."""
    if table=='transferencias' and key=='id_tipo_cambio': return 'Cotización aplicada'
    return label
def label_for(table,row):
    if table=='presupuestos': return f"{row['anio']}/{row['mes']:02d} · {row['categoria_nombre']}"
    if table=='alertas': return f"Presupuesto {row['id_presupuesto']} · {row['umbral']}%"
    if table=='monedas': return f"{row['codigo_iso']} — {row['nombre']}"
    if table=='tipos_cambio': return finance.quote_label(row)
    return str(row['nombre'] if 'nombre' in row.keys() else row[0])

def all_rows(c, table):
    if table not in CONFIG and table not in ('presupuestos','tipos_cambio'): raise ValueError('Tabla desconocida')
    if table=='presupuestos':
        return c.execute('''SELECT p.*,c.nombre AS categoria_nombre FROM presupuestos p
            JOIN categorias c ON c.id_categoria=p.id_categoria AND c.id_perfil=p.id_perfil
            WHERE p.id_perfil=? ORDER BY p.id_presupuesto DESC''',(current_profile_id(c),)).fetchall()
    if table=='tipos_cambio':
        return c.execute('''SELECT q.*,b.codigo_iso AS moneda_base,m.codigo_iso AS moneda_cotizada
            FROM tipos_cambio q JOIN monedas b ON b.id_moneda=q.id_moneda_base
            JOIN monedas m ON m.id_moneda=q.id_moneda_cotizada
            WHERE q.id_perfil=? ORDER BY q.id_tipo_cambio DESC''',(current_profile_id(c),)).fetchall()
    owner=f' WHERE id_perfil={current_profile_id(c)}' if table in ('categorias','cuentas','metas_ahorro','transferencias','presupuestos','alertas','tipos_cambio') else ''
    if table=='movimientos_ahorro':
        owner=f' WHERE id_meta IN (SELECT id_meta FROM metas_ahorro WHERE id_perfil={current_profile_id(c)})'
    return c.execute(f'SELECT * FROM {table}{owner} ORDER BY 1 DESC').fetchall()


def owned_row(c, table, item_id):
    pk=CONFIG[table][2]
    return next((r for r in all_rows(c,table) if r[pk]==item_id),None)

def save(table, form, item_id=None):
    if table not in CONFIG: raise ValueError('Mantenimiento no disponible')
    from src.profiles import require_write
    with db.connect() as permission_db: require_write(permission_db,table,editing=item_id is not None)
    _,_,pk,fields=CONFIG[table]
    values={}
    for key,label,kind in fields:
        raw=str(form.get(key,'')).strip()
        if table=='transferencias' and key in ('monto_destino_centimos','id_tipo_cambio'):
            values[key]=None
            continue
        if kind=='checkbox':
            if raw not in ('','0','1'): raise ValueError(f'{label} inválido')
            values[key]=int(raw or '0')
            continue
        if kind=='boolean':
            if raw not in ('0','1'): raise ValueError(f'{label}: seleccione Sí o No.')
            values[key]=int(raw)
            continue
        if kind.startswith('optional:') and not raw: values[key]=None; continue
        if not raw: raise ValueError(f'El campo {label} es obligatorio.')
        if kind=='integer':
            try: values[key]=int(raw)
            except ValueError: raise ValueError(f'{label} inválido')
        elif kind=='money': values[key]=0 if kind=='money' and key=='saldo_inicial_centimos' and raw in ('0','0.0','0.00') else db.parse_money(raw)
        elif kind=='date': values[key]=db.validate_date(raw)
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
    if table=='transferencias':
        if values['id_cuenta_origen']==values['id_cuenta_destino']: raise ValueError('Las cuentas deben ser distintas')
    with db.connect() as c:
        if item_id is not None and owned_row(c,table,item_id) is None:
            raise ValueError('Registro no encontrado')
        for key,_,kind in fields:
            if kind.startswith('ref:'):
                referenced=kind.split(':',1)[1]
                if not any(r[CONFIG[referenced][2]]==values[key] for r in all_rows(c,referenced)):
                    raise ValueError('Referencia no válida para este usuario')
        if table=='presupuestos':
            cat=c.execute("SELECT 1 FROM categorias WHERE id_categoria=? AND tipo='gasto'",(values['id_categoria'],)).fetchone()
            if not cat: raise ValueError('La categoría debe ser de gasto')
        if table=='movimientos_ahorro' and values['tipo']=='retiro':
            balance=c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='aporte' THEN monto_centimos ELSE -monto_centimos END),0) FROM movimientos_ahorro WHERE id_meta=? AND id_movimiento_ahorro != ?",(values['id_meta'],item_id or -1)).fetchone()[0]
            if values['monto_centimos']>balance: raise ValueError('El retiro supera el ahorro disponible')
        if table=='transferencias':
            user=current_profile_id(c)
            src=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_perfil=?',(values['id_cuenta_origen'],user)).fetchone()
            dst=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_perfil=?',(values['id_cuenta_destino'],user)).fetchone()
            if not src or not dst: raise ValueError('Cuenta no válida para este usuario')
            if src[0]==dst[0]:
                values['id_tipo_cambio']=None
                values['monto_destino_centimos']=values['monto_origen_centimos']
            else:
                quote_value=finance.parse_quote(form.get('cotizacion',''))
                base,quoted=finance.quote_pair(c,src[0],dst[0])
                quote={'id_moneda_base':base,'id_moneda_cotizada':quoted,'cotizacion':quote_value}
                destination_cents=finance.apply_quote(quote,src[0],dst[0],values['monto_origen_centimos'])
                if not 1<=destination_cents<=999_999_999_999:
                    raise ValueError('El monto convertido debe ser al menos 0,01 y no superar el m?ximo permitido.')
                rate_id=c.execute('''INSERT INTO tipos_cambio
                    (id_perfil,id_moneda_base,id_moneda_cotizada,fecha,cotizacion)
                    VALUES(current_profile_id(),?,?,?,?)''',(base,quoted,values['fecha'],quote_value)).lastrowid
                values['id_tipo_cambio']=rate_id
                values['monto_destino_centimos']=destination_cents
        if table=='movimientos_ahorro':
            meta=c.execute('SELECT id_moneda FROM metas_ahorro WHERE id_meta=? AND id_perfil=current_profile_id()',(values['id_meta'],)).fetchone()
            acc=c.execute('SELECT id_moneda FROM cuentas WHERE id_cuenta=? AND id_perfil=current_profile_id()',(values['id_cuenta'],)).fetchone()
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
        if table in ('categorias','cuentas','metas_ahorro','transferencias','presupuestos','alertas'): values['id_perfil']=current_profile_id(c)
        if table=='alertas' and item_id is None:
            values['origen']='manual'
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
    with db.connect() as c:
        from src.profiles import require_write
        require_write(c,table,editing=True)
        if owned_row(c,table,item_id) is None: raise ValueError('Registro no encontrado')
        cur=c.execute(f'DELETE FROM {table} WHERE {pk}=?',(item_id,))
        if not cur.rowcount: raise ValueError('Registro no encontrado')

def page(table, edit_id=None):
    if table not in CONFIG: raise ValueError('Mantenimiento no disponible')
    title,_,pk,fields=CONFIG[table]
    with db.connect() as c:
        from src.profiles import can_write
        allow_create=can_write(c,table)
        allow_edit=can_write(c,table,editing=True)
        if edit_id and not allow_edit:
            from src.profiles import AccessDenied
            raise AccessDenied('No tiene permiso para editar este registro.')
        rows=all_rows(c,table)
        item=owned_row(c,table,edit_id) if edit_id else None
        if edit_id and not item: raise ValueError('Registro no encontrado')
        refs={t:all_rows(c,t) for _,_,kind in fields if (kind.startswith('ref:') or kind.startswith('optional:')) for t in [kind.split(':',1)[1]]}
    from src.app import layout
    inputs=''
    for key,label,kind in fields:
        if table=='transferencias' and key in ('monto_destino_centimos','id_tipo_cambio'):
            continue
        value=item[key] if item else ''
        if kind=='boolean':
            selected_value=int(value) if item else 0
            options=''.join(f'<option value="{number}" {"selected" if number==selected_value else ""}>{name}</option>' for number,name in ((0,'No'),(1,'Sí')))
            inputs+=f'<label>{h(label)}<select name="{key}" required>{options}</select></label>'
            continue
        if table=='presupuestos' and key=='mes':
            months=('Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre')
            selected_month=int(value) if item else date.today().month
            options=''.join(f'<option value="{number}" {"selected" if number==selected_month else ""}>{name}</option>' for number,name in enumerate(months,1))
            inputs+=f'<label>{h(label)}<select name="mes" required>{options}</select></label>'
            continue
        if kind=='checkbox':
            checked=' checked' if value else ''
            inputs+=f'<label style="display:flex;align-items:center;gap:10px"><input style="width:auto" type="checkbox" name="{key}" value="1"{checked}>{h(label)}</label>'
            continue
        if kind=='money' and item: value=f'{value/100:.2f}'
        if kind.startswith(('ref:','optional:','choice:')):
            if kind.startswith('choice:'): options=[(v,v) for v in kind[7:].split(',')]
            else:
                t=kind.split(':',1)[1]; options=[(r[CONFIG[t][2]],label_for(t,r)) for r in refs[t]]
            opt='<option value="">Seleccionar</option>' if kind.startswith('optional:') else ''
            opt+=''.join(f'<option value="{h(v)}" {"selected" if str(v)==str(value) else ""}>{h(n)}</option>' for v,n in options)
            field=f'<select name="{key}" {"" if kind.startswith("optional:") else "required"}>{opt}</select>'
        else:
            typ='date' if kind=='date' else 'number' if kind in ('money','integer') else 'text'
            step=' step="0.01"' if kind=='money' else ''
            default=date.today().isoformat() if kind=='date' and not item else value
            field=f'<input name="{key}" type="{typ}"{step} value="{h(default)}" required>'
        inputs+=f'<label>{h(label)}{field}</label>'
    action=f'/admin/{table}/{edit_id}/guardar' if item else f'/admin/{table}/guardar'
    headers=''.join(f'<th>{h(label_for_column(table,key,label))}</th>' for key,label,kind in fields)
    trs=''
    for r in rows:
        rid=r[pk]
        cells=[]
        for key,label,kind in fields:
            value=r[key]
            if table=='alertas' and key=='id_presupuesto':
                budget=next((b for b in refs['presupuestos'] if b['id_presupuesto']==value),None)
                value=label_for('presupuestos',budget) if budget else 'Presupuesto no disponible'
            elif table=='presupuestos' and key=='mes':
                value=MONTH_NAMES[int(value)-1] if value else ''
            elif kind.startswith('ref:'):
                ref_table=kind.split(':',1)[1]
                target=next((x for x in refs[ref_table] if x[CONFIG[ref_table][2]]==value),None)
                if target is None: value='No disponible'
                elif ref_table=='monedas': value=target['nombre']
                else: value=label_for(ref_table,target)
            elif table=='transferencias' and key=='id_tipo_cambio':
                label='Cotización aplicada'
                quote=next((q for q in refs['tipos_cambio'] if q['id_tipo_cambio']==value),None)
                value=finance.quote_label(quote) if quote else 'Misma moneda'
            elif kind=='money': value=f'{value/100:.2f}'
            elif kind in ('checkbox','boolean'): value='Sí' if value else 'No'
            cells.append(f'<td data-label="{h(label)}">{h(value)}</td>')
        actions=(f'<a class="btn btn-neutral btn-sm" href="/admin/{table}?editar={rid}">Editar</a><form method="post" action="/admin/{table}/{rid}/eliminar"><button class="btn btn-danger btn-sm" type="submit" onclick="return confirm(\'¿Eliminar registro?\')">Eliminar</button></form>' if allow_edit else '')
        if table=='alertas' and not r['leida']:
            actions+=f'<form method="post" action="/alertas/{rid}/leida"><button class="btn btn-neutral btn-sm" type="submit">Marcar como leída</button></form>'
        actions=f'<div class="row-actions">{actions}</div>' if actions else ''
        trs+=f'<tr>{"".join(cells)}<td class="row-actions-cell">{actions}</td></tr>'
    if table=='transferencias':
        with db.connect() as fxdb:
            account_info={str(r['id_cuenta']):{'currency':r['codigo_iso'],'id':r['id_moneda']} for r in fxdb.execute('SELECT a.id_cuenta,a.id_moneda,m.codigo_iso FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda WHERE a.id_perfil=?',(current_profile_id(fxdb),))}
        inputs += '''<div class="span2" id="fx-panel" style="padding:14px;border:1px solid #cbd5e1;border-radius:10px" aria-live="polite"><strong>Cotización de la transferencia</strong><p id="fx-status">Seleccione las cuentas.</p><div id="fx-quote-panel" hidden><label><span id="fx-quote-label">Cotización</span><input type="number" name="cotizacion" id="fx-quote" min="0.01" max="1000000000" step="0.01" disabled></label><p class="help">Por ejemplo: si 1 USD equivale a 460 CRC, ingresa 460. La conversión se calcula automáticamente según las cuentas.</p></div><p id="fx-preview"></p></div>'''
        inputs += '<script>'+r'''const accounts=ACCOUNT_DATA,
            origin=document.querySelector('[name="id_cuenta_origen"]'),dest=document.querySelector('[name="id_cuenta_destino"]'),
            amount=document.querySelector('[name="monto_origen_centimos"]'),quote=document.getElementById('fx-quote'),
            panel=document.getElementById('fx-quote-panel'),quoteLabel=document.getElementById('fx-quote-label'),
            status=document.getElementById('fx-status'),preview=document.getElementById('fx-preview');
        let lastPair='';
        function asCents(raw){
            if(raw.length>32||!/^\d+(?:\.\d{1,2})?$/.test(raw))return null;
            const parts=raw.split('.');return BigInt(parts[0])*100n+BigInt((parts[1]||'').padEnd(2,'0'));
        }
        function update(){
            const a=accounts[origin.value],b=accounts[dest.value],different=!!(a&&b&&a.id!==b.id);
            let base,quoted;
            if(different){
                [base,quoted]=a.currency==='CRC'?[b,a]:b.currency==='CRC'?[a,b]:a.currency<b.currency?[a,b]:[b,a];
                const pair=base.id+'>'+quoted.id;
                if(pair!==lastPair)quote.value='';
                lastPair=pair;quoteLabel.textContent='1 '+base.currency+' equivale a ('+quoted.currency+')';
            }
            panel.hidden=!different;quote.disabled=!different;quote.required=different;
            status.textContent=!a||!b?'Seleccione las cuentas.':different?'Indica la cotización para calcular el monto a recibir.':'Misma moneda: no se requiere cotización.';
            const cents=asCents(amount.value),quoteCents=asCents(quote.value);
            preview.textContent='';
            if(different&&cents!==null&&quoteCents!==null&&cents>0n&&quoteCents>0n){
                const numerator=a.id===base.id?cents*quoteCents:cents*100n,denominator=a.id===base.id?100n:quoteCents;
                const received=(numerator*2n+denominator)/(denominator*2n);
                preview.textContent=received>0n&&received<=999999999999n?'Monto a recibir: '+(received/100n).toString()+'.'+(received%100n).toString().padStart(2,'0')+' '+b.currency:'El monto convertido queda fuera del rango permitido.';
            }
        }
        [origin,dest,amount,quote].forEach(x=>x.addEventListener('input',update));update();''' .replace('ACCOUNT_DATA',json.dumps(account_info))+'</script>'

    form_section=(f'<h3>{"Editar" if item else "Nuevo"} registro</h3><form class="form-grid" method="post" action="{action}">{inputs}<button class="primary" type="submit">Guardar</button></form>' if allow_create else '<p class="muted">Consulta del perfil. Su propietario administra estos registros.</p>')
    if not allow_edit:
        if allow_create:
            form_section='<p class="muted">Puedes consultar y registrar nuevas operaciones. El propietario puede editar o eliminar registros existentes.</p>'+form_section
        else:
            title='Consulta de '+title.lower()
    body=f'<section class="panel"><p><a href="/">← Panel principal</a></p><h2>{h(title)}</h2>{form_section}</section><section class="panel table-panel"><h2>Registros</h2><div class="table-scroll"><table class="records"><thead><tr>{headers}<th class="row-actions-head">Acciones</th></tr></thead><tbody>{trs or f'<tr><td colspan="{len(fields)+1}" class="empty">No hay registros</td></tr>'}</tbody></table></div></section>'
    if not allow_edit and table!='alertas':
        body=body.replace('<th class="row-actions-head">Acciones</th>','').replace('<td class="row-actions-cell"></td>','')
    return layout(body)


def current_profile_id(c=None):
    from src.request_ctx import profile_id
    return profile_id()


def currency_options():
    with db.connect() as c:
        rows=c.execute('SELECT id_moneda,codigo_iso,nombre FROM monedas ORDER BY codigo_iso').fetchall()
    return ''.join(f'<option value="{r[0]}" {"selected" if r[1]=="CRC" else ""}>{h(r[1])} — {h(r[2])}</option>' for r in rows)

def refresh_alerts():
    # Recompute thresholds from current expenses. Idempotent: one alert per budget and threshold.
    with db.connect() as c:
        user=current_profile_id(c)
        budgets=c.execute('SELECT * FROM presupuestos WHERE id_perfil=?',(user,)).fetchall()
        for b in budgets:
            start=f"{b['anio']:04d}-{b['mes']:02d}-01"
            end=f"{b['anio']+1:04d}-01-01" if b['mes']==12 else f"{b['anio']:04d}-{b['mes']+1:02d}-01"
            moves=c.execute("SELECT m.monto_centimos,m.fecha,a.id_moneda FROM movimientos m JOIN cuentas a ON a.id_cuenta=m.id_cuenta WHERE m.id_perfil=? AND m.id_categoria=? AND m.tipo='gasto' AND m.fecha>=? AND m.fecha<?",(user,b['id_categoria'],start,end)).fetchall()
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
                    c.execute('INSERT OR IGNORE INTO alertas(id_presupuesto,id_perfil,umbral,fecha,leida) VALUES(?,?,?,?,0)',(b['id_presupuesto'],user,threshold,date.today().isoformat()))
                else:
                    c.execute("DELETE FROM alertas WHERE id_presupuesto=? AND umbral=? AND origen='automatica'",(b['id_presupuesto'],threshold))

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
        from src.profiles import require_write
        require_write(c,'comprobantes')
        if not c.execute("SELECT 1 FROM movimientos WHERE id_movimiento=? AND id_perfil=? AND tipo='gasto'",(movement,current_profile_id(c))).fetchone(): raise ValueError('Gasto no válido para el usuario')
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
        r=c.execute('SELECT co.* FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE co.id_comprobante=? AND m.id_perfil=?',(receipt_id,current_profile_id(c))).fetchone()
    if not r: return None
    path=receipts_dir()/Path(r['ruta_archivo']).name
    if not path.is_file(): return None
    return path.read_bytes(),r['tipo_mime']

def delete_receipt(receipt_id):
    with db.connect() as c:
        from src.profiles import require_write
        require_write(c,'comprobantes',editing=True)
        r=c.execute('SELECT co.ruta_archivo FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE co.id_comprobante=? AND m.id_perfil=?',(receipt_id,current_profile_id(c))).fetchone()
        if not r: raise ValueError('Comprobante inexistente')
        c.execute('DELETE FROM comprobantes WHERE id_comprobante=?',(receipt_id,))
    (receipts_dir()/Path(r[0]).name).unlink(missing_ok=True)

def receipts_page():
    from src.app import layout
    with db.connect() as c:
        from src.profiles import can_write
        allow_delete=can_write(c,'comprobantes',editing=True)
        user=current_profile_id(c)
        expenses=c.execute("SELECT id_movimiento,fecha,descripcion,monto_centimos FROM movimientos WHERE id_perfil=? AND tipo='gasto' ORDER BY fecha DESC LIMIT 250",(user,)).fetchall()
        files=c.execute('SELECT co.id_comprobante,co.tipo_mime,co.fecha_subida,m.descripcion FROM comprobantes co JOIN movimientos m ON m.id_movimiento=co.id_movimiento WHERE m.id_perfil=? ORDER BY co.id_comprobante DESC',(user,)).fetchall()
    options=''.join(f'<option value="{r[0]}">{h(r[1])} · {h(r[2] or "Gasto")} · {r[3]/100:.2f} CRC</option>' for r in expenses)
    trs=''.join(f'<tr><td>{h(r[3])}</td><td>{h(r[1])}</td><td>{h(r[2])}</td><td><a class="btn btn-success btn-sm" target="_blank" rel="noopener" href="/comprobantes/{r[0]}/archivo">Ver</a> <form method="post" action="/comprobantes/{r[0]}/eliminar" style="display:inline"><button class="btn btn-danger btn-sm" onclick="return confirm(\'¿Eliminar comprobante?\')">Eliminar</button></form></td></tr>' for r in files)
    if not allow_delete:
        import re
        trs=re.sub(r'<form method="post".*?</form>','',trs,flags=re.S)
    return layout(f'''<section class="panel"><h2>Comprobantes de gastos</h2><p>Adjunta PDF, JPG, PNG o WebP (máximo 5 MB). Los archivos se almacenan localmente en <code>data/comprobantes</code>.</p><form method="post" enctype="multipart/form-data" action="/comprobantes/subir" class="form-grid"><label>Gasto<select name="id_movimiento" required>{options}</select></label><label>Archivo<input type="file" name="archivo" accept=".pdf,.jpg,.jpeg,.png,.webp" required></label><button class="primary">Adjuntar comprobante</button></form></section><section class="panel table-panel"><h2>Archivos adjuntos</h2><div class="table-scroll"><table><thead><tr><th>Gasto</th><th>Tipo</th><th>Fecha</th><th>Acciones</th></tr></thead><tbody>{trs or '<tr><td colspan="4">No hay comprobantes</td></tr>'}</tbody></table></div></section>''')
