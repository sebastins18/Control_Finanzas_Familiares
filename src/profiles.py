"""Perfiles financieros, integrantes y permisos independientes del rol de acceso."""
import re
import sqlite3
import time
from contextlib import closing
from html import escape

from src import db, request_ctx

TABLES = ('categorias', 'cuentas', 'movimientos', 'presupuestos',
          'metas_ahorro', 'transferencias', 'alertas')
SCHEMA = '''
CREATE TABLE IF NOT EXISTS perfiles_financieros (
    id_perfil INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL CHECK(length(trim(nombre)) BETWEEN 1 AND 100),
    id_propietario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS integrantes_perfil (
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil) ON DELETE CASCADE,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    PRIMARY KEY(id_perfil,id_usuario)
);
'''


class AccessDenied(Exception):
    pass


def init():
    # Reconstrucción transaccional estándar de SQLite para cambiar las FK sin
    # renombrar las tablas originales ni alterar las referencias de sus hijas.
    with closing(sqlite3.connect(db.db_path(), timeout=3)) as c:
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=OFF')
        deadline=time.monotonic()+db.OPERATION_TIMEOUT_SECONDS
        c.set_progress_handler(lambda: int(time.monotonic()>=deadline),1000)
        try:
            c.execute('BEGIN IMMEDIATE')
            for statement in SCHEMA.split(';'):
                if statement.strip(): c.execute(statement)
            old = [t for t in TABLES if 'id_usuario' in {r['name'] for r in c.execute(f'PRAGMA table_info({t})')}]
            if old:
                for user in c.execute('SELECT id_usuario,nombre FROM usuarios').fetchall():
                    c.execute('INSERT OR IGNORE INTO perfiles_financieros(id_perfil,nombre,id_propietario) VALUES(?,?,?)',
                              (user['id_usuario'], 'Finanzas de '+user['nombre'], user['id_usuario']))
                for table in old:
                    original=c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()[0]
                    indexes=[r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",(table,))]
                    columns=[r['name'] for r in c.execute(f'PRAGMA table_info({table})')]
                    sql=re.sub(r'\bid_usuario\b','id_perfil',original)
                    sql=sql.replace('REFERENCES usuarios(id_perfil)','REFERENCES perfiles_financieros(id_perfil)')
                    sql=re.sub(r'(?i)(CREATE TABLE\s+(?:IF NOT EXISTS\s+)?)["`\[]?'+table+r'["`\]]?',r'\1'+table+'_migracion',sql,count=1)
                    c.execute(sql)
                    target=','.join('id_perfil' if n=='id_usuario' else n for n in columns)
                    c.execute(f'INSERT INTO {table}_migracion ({target}) SELECT '+','.join(columns)+f' FROM {table}')
                    c.execute(f'DROP TABLE {table}')
                    c.execute(f'ALTER TABLE {table}_migracion RENAME TO {table}')
                    for index in indexes:
                        c.execute(re.sub(r'\bid_usuario\b','id_perfil',index))
            rate_columns={r['name'] for r in c.execute('PRAGMA table_info(tipos_cambio)')}
            if rate_columns and 'id_perfil' not in rate_columns:
                rates=c.execute('SELECT * FROM tipos_cambio ORDER BY id_tipo_cambio').fetchall()
                transfers=c.execute('SELECT id_transferencia,id_perfil,id_tipo_cambio FROM transferencias WHERE id_tipo_cambio IS NOT NULL').fetchall()
                rate_ids={}
                c.execute('''CREATE TABLE tipos_cambio_migracion (
                    id_tipo_cambio INTEGER PRIMARY KEY,
                    id_perfil INTEGER NOT NULL DEFAULT 1 REFERENCES perfiles_financieros(id_perfil),
                    id_moneda_origen INTEGER NOT NULL REFERENCES monedas(id_moneda),
                    id_moneda_destino INTEGER NOT NULL REFERENCES monedas(id_moneda),
                    fecha TEXT NOT NULL,valor TEXT NOT NULL,
                    CHECK(id_moneda_origen<>id_moneda_destino),
                    UNIQUE(id_perfil,id_moneda_origen,id_moneda_destino,fecha))''')
                for profile in c.execute('SELECT id_perfil FROM perfiles_financieros ORDER BY id_perfil').fetchall():
                    for rate in rates:
                        new_id=c.execute('''INSERT INTO tipos_cambio_migracion
                            (id_perfil,id_moneda_origen,id_moneda_destino,fecha,valor) VALUES(?,?,?,?,?)''',
                            (profile[0],rate['id_moneda_origen'],rate['id_moneda_destino'],rate['fecha'],rate['valor'])).lastrowid
                        rate_ids[(profile[0],rate['id_tipo_cambio'])]=new_id
                for transfer in transfers:
                    c.execute('UPDATE transferencias SET id_tipo_cambio=? WHERE id_transferencia=?',
                              (rate_ids[(transfer['id_perfil'],transfer['id_tipo_cambio'])],transfer['id_transferencia']))
                c.execute('DROP TABLE tipos_cambio')
                c.execute('ALTER TABLE tipos_cambio_migracion RENAME TO tipos_cambio')
            if c.execute('PRAGMA foreign_key_check').fetchone():
                raise sqlite3.IntegrityError('La migración contiene referencias inválidas')
            c.commit()
        except Exception:
            c.set_progress_handler(None,0)
            c.rollback()
            raise
    with db.connect() as c:
        for user in c.execute('SELECT id_usuario FROM usuarios').fetchall():
            ensure_default(c, user['id_usuario'])


def seed(c, profile_id):
    for name, kind in [('Salario','ingreso'),('Otros ingresos','ingreso'),
                       ('Alimentación','gasto'),('Transporte','gasto'),('Vivienda','gasto'),
                       ('Servicios','gasto'),('Entretenimiento','gasto'),('Salud','gasto')]:
        c.execute('INSERT OR IGNORE INTO categorias(id_perfil,nombre,tipo) VALUES(?,?,?)',(profile_id,name,kind))
    for name in ('Cuenta principal','Efectivo'):
        c.execute("INSERT OR IGNORE INTO cuentas(id_perfil,nombre,id_moneda) VALUES(?,?,(SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'))",(profile_id,name))


def ensure_default(c, user_id):
    row=c.execute('SELECT id_perfil FROM perfiles_financieros WHERE id_propietario=? ORDER BY id_perfil LIMIT 1',(user_id,)).fetchone()
    if not row:
        name=c.execute('SELECT nombre FROM usuarios WHERE id_usuario=?',(user_id,)).fetchone()[0]
        profile=c.execute('INSERT INTO perfiles_financieros(nombre,id_propietario) VALUES(?,?)',('Finanzas de '+name,user_id)).lastrowid
        seed(c,profile)
    else:
        profile=row[0]
        # Solo prepara un perfil recién migrado y vacío; no recrea catálogos borrados.
        if not c.execute('SELECT 1 FROM cuentas WHERE id_perfil=?',(profile,)).fetchone(): seed(c,profile)
    return profile


def available(c=None):
    if c is None:
        with db.connect() as connection: return available(connection)
    return c.execute('''SELECT p.*,u.nombre AS propietario,
        CASE WHEN p.id_propietario=? THEN 1 ELSE 0 END AS es_propietario
        FROM perfiles_financieros p JOIN usuarios u ON u.id_usuario=p.id_propietario
        WHERE p.id_propietario=? OR EXISTS(SELECT 1 FROM integrantes_perfil i
            WHERE i.id_perfil=p.id_perfil AND i.id_usuario=?) ORDER BY p.id_perfil''',
        (request_ctx.user_id(),)*3).fetchall()


def access(c, profile_id=None, owner=False):
    pid=profile_id if profile_id is not None else request_ctx.profile_id()
    row=next((r for r in available(c) if r['id_perfil']==int(pid)),None)
    if row is None or (owner and not row['es_propietario']):
        raise AccessDenied('No tiene permiso para administrar este perfil.' if owner else 'No tiene acceso a este perfil.')
    return row


def can_write(c,table,editing=False):
    if table=='monedas':
        from src.auth import STANDARD_USER_MODE
        if STANDARD_USER_MODE: return False
        user=c.execute('SELECT rol FROM usuarios WHERE id_usuario=?',(request_ctx.user_id(),)).fetchone()
        return bool(user and user[0]=='administrador')
    profile=access(c)
    return bool(profile['es_propietario'] or (table in ('movimientos','transferencias','movimientos_ahorro','comprobantes') and not editing))


def require_write(c,table,editing=False):
    if not can_write(c,table,editing):
        raise AccessDenied('Solo el propietario puede modificar la estructura y los registros existentes del perfil.')


def resolve(selected=None):
    with db.connect() as c:
        rows=available(c)
        if not rows: raise AccessDenied('No hay perfiles disponibles para esta cuenta.')
        return next((r for r in rows if r['id_perfil']==selected),rows[0])


def create(name):
    name=str(name).strip()
    if not 1<=len(name)<=100: raise ValueError('El nombre debe tener entre 1 y 100 caracteres.')
    with db.connect() as c:
        pid=c.execute('INSERT INTO perfiles_financieros(nombre,id_propietario) VALUES(?,?)',(name,request_ctx.user_id())).lastrowid
        seed(c,pid)
        return pid


def rename(pid,name):
    name=str(name).strip()
    if not 1<=len(name)<=100: raise ValueError('El nombre debe tener entre 1 y 100 caracteres.')
    with db.connect() as c:
        access(c,pid,owner=True)
        c.execute('UPDATE perfiles_financieros SET nombre=? WHERE id_perfil=?',(name,pid))


def delete(pid):
    with db.connect() as c:
        access(c,pid,owner=True)
        if c.execute('SELECT COUNT(*) FROM perfiles_financieros WHERE id_propietario=?',(request_ctx.user_id(),)).fetchone()[0]<=1:
            raise ValueError('Conserve al menos un perfil propio.')
        # Los perfiles se eliminan solo si no tienen información financiera.
        if any(c.execute(f'SELECT 1 FROM {t} WHERE id_perfil=? LIMIT 1',(pid,)).fetchone()
               for t in ('movimientos','presupuestos','metas_ahorro','transferencias','alertas')):
            raise ValueError('No puede eliminar un perfil que contiene información financiera.')
        if c.execute('SELECT 1 FROM cuentas WHERE id_perfil=? AND saldo_inicial_centimos<>0',(pid,)).fetchone():
            raise ValueError('No puede eliminar un perfil con saldos iniciales.')
        c.execute('DELETE FROM categorias WHERE id_perfil=?',(pid,))
        c.execute('DELETE FROM cuentas WHERE id_perfil=?',(pid,))
        c.execute('DELETE FROM perfiles_financieros WHERE id_perfil=?',(pid,))


def invite(pid,username):
    with db.connect() as c:
        profile=access(c,pid,owner=True)
        user=c.execute('SELECT id_usuario FROM usuarios WHERE username=? AND activo=1',(str(username).strip(),)).fetchone()
        if not user: raise ValueError('No existe un usuario activo con ese nombre de acceso.')
        if user[0]==profile['id_propietario']: raise ValueError('El propietario ya tiene acceso al perfil.')
        c.execute('INSERT OR IGNORE INTO integrantes_perfil(id_perfil,id_usuario) VALUES(?,?)',(pid,user[0]))


def remove_member(pid,uid):
    with db.connect() as c:
        profile=access(c,pid,owner=True)
        if uid==profile['id_propietario']: raise ValueError('No puede quitar al propietario.')
        c.execute('DELETE FROM integrantes_perfil WHERE id_perfil=? AND id_usuario=?',(pid,uid))


def selection_page():
    from src.app import layout
    h=lambda value: escape(str(value),quote=True)
    groups={'own':[],'guest':[]}
    active=request_ctx.profile()
    with db.connect() as c:
        for row in available(c):
            pid=row['id_perfil']
            count=c.execute('SELECT COUNT(*)+1 FROM integrantes_perfil WHERE id_perfil=?',(pid,)).fetchone()[0]
            group='own' if row['es_propietario'] else 'guest'
            subtitle=('Solo tú' if count==1 else f'{count} integrantes') if group=='own' else 'Propietario: '+row['propietario']
            checked=' checked' if active and active['id_perfil']==pid else ''
            groups[group].append(f'<label class="profile-option"><input type="radio" name="id_perfil" value="{pid}" required{checked}><span class="profile-option-icon" aria-hidden="true">⌂</span><span class="profile-option-copy"><strong>{h(row["nombre"])}</strong><small>{h(subtitle)}</small></span><span class="profile-option-arrow" aria-hidden="true">›</span></label>')
    start_group='guest' if active and not active['es_propietario'] else 'own'
    panels=''
    for group,cards in groups.items():
        cards_html=''.join(cards) if cards else '<p class="profile-empty">No hay perfiles disponibles en esta sección.</p>'
        panels+=f'<section id="profiles-{group}" class="profile-group" data-group="{group}" role="tabpanel" aria-labelledby="tab-{group}">{cards_html}</section>'
    content=f'''<section class="panel profile-picker" aria-labelledby="picker-title">
        <h1 id="picker-title">Seleccionar perfil financiero</h1>
        <p class="muted">Elige el perfil con el que deseas trabajar.</p>
        <div class="profile-tabs" role="tablist" aria-label="Tipo de perfil">
          <button type="button" id="tab-own" role="tab" aria-controls="profiles-own" aria-selected="true" data-group="own">Mis perfiles</button>
          <button type="button" id="tab-guest" role="tab" aria-controls="profiles-guest" aria-selected="false" data-group="guest">Invitado</button>
        </div>
        <form method="post" action="/perfiles/seleccionar" id="profile-selection">{panels}
          <button class="primary profile-enter" type="submit" id="enter-profile">Ingresar al perfil <span aria-hidden="true">→</span></button>
        </form>
        <div class="profile-picker-footer"><form method="post" action="/logout"><button class="secondary">Cerrar sesión</button></form></div>
        </section>
        <script>
        (()=>{{
          const form=document.getElementById('profile-selection'), enter=document.getElementById('enter-profile');
          const tabs=[...document.querySelectorAll('.profile-tabs [role="tab"]')];
          function update(){{enter.disabled=!form.querySelector('input[name="id_perfil"]:checked');}}
          function select(group){{
            tabs.forEach(tab=>tab.setAttribute('aria-selected',String(tab.dataset.group===group)));
            form.querySelectorAll('.profile-group').forEach(panel=>{{
              panel.hidden=panel.dataset.group!==group;
              panel.querySelectorAll('input').forEach(input=>{{input.disabled=panel.hidden;if(panel.hidden)input.checked=false;}});
            }});
            update();
          }}
          tabs.forEach((tab,index)=>{{tab.addEventListener('click',()=>select(tab.dataset.group));
            tab.addEventListener('keydown',event=>{{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){{event.preventDefault();const other=tabs[1-index];other.focus();select(other.dataset.group);}}}});}});
          form.addEventListener('change',update);select('{start_group}');
        }})();
        </script>'''
    return layout(content,selection=True)


def page():
    from src.app import layout
    h=lambda value: escape(str(value),quote=True)
    sections=[]
    with db.connect() as c:
        for row in available(c):
            pid=row['id_perfil']
            state='Propietario' if row['es_propietario'] else 'Invitado'
            content=f'<section class="panel"><h2>{h(row["nombre"])}</h2><p>{state} · Propietario: {h(row["propietario"])}</p>'
            content+=f'<form method="post" action="/perfiles/seleccionar"><input type="hidden" name="id_perfil" value="{pid}"><button class="primary">Usar este perfil</button></form>'
            if row['es_propietario']:
                members=c.execute('''SELECT u.id_usuario,u.nombre,u.username FROM integrantes_perfil i
                    JOIN usuarios u ON u.id_usuario=i.id_usuario WHERE i.id_perfil=? ORDER BY u.nombre''',(pid,)).fetchall()
                content+=f'<h3>Nombre del perfil</h3><form method="post" action="/perfiles/{pid}/guardar" class="form-grid"><label>Nombre<input name="nombre" maxlength="100" value="{h(row["nombre"])}" required></label><button>Guardar nombre</button></form>'
                content+='<h3>Invitados</h3><p class="help">Pueden consultar y registrar operaciones. Las cuentas, categorías, presupuestos e integrantes los administra el propietario.</p>'
                for member in members:
                    content+=f'<p>{h(member["nombre"])} ({h(member["username"])})</p><form method="post" action="/perfiles/{pid}/integrantes/{member["id_usuario"]}/eliminar"><button>Quitar acceso</button></form>'
                if not members: content+='<p class="muted">Todavía no hay invitados.</p>'
                content+=f'<form method="post" action="/perfiles/{pid}/invitar" class="form-grid"><label>Usuario de acceso<input name="username" maxlength="40" required></label><button>Agregar invitado</button></form>'
                content+=f'<form method="post" action="/perfiles/{pid}/eliminar"><button onclick="return confirm(\'¿Eliminar este perfil vacío?\')">Eliminar perfil vacío</button></form>'
            sections.append(content+'</section>')
    form='<section class="panel"><h2>Crear perfil financiero</h2><form method="post" action="/perfiles/crear" class="form-grid"><label>Nombre<input name="nombre" maxlength="100" required></label><button class="primary">Crear perfil</button></form></section>'
    return layout('<section class="panel"><h2>Mis perfiles financieros</h2><p>Puedes administrar tus perfiles propios. En los perfiles compartidos contigo puedes consultar y registrar operaciones; su propietario administra la estructura y los integrantes.</p><p>Seleccionar un perfil solo cambia esta sesión.</p></section>'+form+''.join(sections))
