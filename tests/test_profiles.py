"""Perfiles compartidos: aislamiento, sesiones e invitados por HTTP y SQLite."""
import os
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import date
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from src import app, auth, db, extension, profiles, request_ctx, finance


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.sqlite3'
        self.env=patch.dict(os.environ,{'DB_PATH':str(self.path),'APP_BASE_PATH':'',
                                      'FINANZAS_INITIAL_ADMIN_PASSWORD':''})
        self.env.start()
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        db.init_db()
        users=auth.credentials()
        for name in ('Miriam','OtraPersona'):
            salt='ac'*16
            users.append(dict(username=name,name=name,role='usuario',active=True,
                              salt=salt,hash=auth.hash_password('Clave123!',salt)))
        auth.save_users(users)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.owner=self.client('admin','admin123!')
        self.guest=self.client('Miriam','Clave123!')
        self.outsider=self.client('OtraPersona','Clave123!')

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
        request_ctx.set_user_id(1)
        app.SESSIONS.clear()
        self.env.stop();self.tmp.cleanup()

    def client(self,name,password):
        client=build_opener(HTTPCookieProcessor(CookieJar()))
        self.post(client,'/login',dict(usuario=name,contrasena=password))
        uid=app.user_by_name(name)['id_usuario']
        with db.connect() as c:pid=c.execute('SELECT id_perfil FROM perfiles_financieros WHERE id_propietario=? ORDER BY id_perfil LIMIT 1',(uid,)).fetchone()[0]
        self.post(client,'/perfiles/seleccionar',{'id_perfil':pid})
        return client

    def post(self,client,path,fields):
        with client.open(Request(self.base+path,data=urlencode(fields).encode()),timeout=5) as r:
            return r.read().decode()

    def get(self,client,path='/'):
        with client.open(self.base+path,timeout=5) as r:return r.read().decode()

    def denied(self,client,path,fields=None,status=403):
        with self.assertRaises(HTTPError) as caught:
            client.open(Request(self.base+path,data=urlencode(fields).encode() if fields is not None else None),timeout=5)
        self.assertEqual(caught.exception.code,status)
        caught.exception.close()

    def shared(self):
        self.post(self.owner,'/perfiles/crear',{'nombre':'Hogar compartido'})
        with db.connect() as c:
            pid=c.execute("SELECT id_perfil FROM perfiles_financieros WHERE nombre='Hogar compartido'").fetchone()[0]
        self.post(self.owner,f'/perfiles/{pid}/invitar',{'username':'Miriam'})
        self.post(self.guest,'/perfiles/seleccionar',{'id_perfil':pid})
        return pid

    def movement_form(self,pid,description='Gasto compartido',kind='gasto',amount='100'):
        with db.connect() as c:
            category=c.execute('SELECT id_categoria FROM categorias WHERE id_perfil=? AND tipo=? LIMIT 1',(pid,kind)).fetchone()[0]
            account=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=? LIMIT 1',(pid,)).fetchone()[0]
        return dict(tipo=kind,monto=amount,fecha=date.today().isoformat(),
                    id_categoria=category,id_cuenta=account,descripcion=description)

    def test_shared_ledger_and_independent_session_selection(self):
        pid=self.shared()
        self.post(self.guest,'/movimientos',self.movement_form(pid))
        self.assertIn('Gasto compartido',self.get(self.owner))
        self.assertIn('Gasto compartido',self.get(self.guest))
        self.assertNotIn('Gasto compartido',self.get(self.outsider))
        self.post(self.owner,'/perfiles/seleccionar',{'id_perfil':1})
        self.assertNotIn('Gasto compartido',self.get(self.owner))
        self.assertIn('Gasto compartido',self.get(self.guest))
        self.denied(self.outsider,'/perfiles/seleccionar',{'id_perfil':pid})
        self.denied(self.guest,'/movimientos',self.movement_form(1),status=400)
        self.assertNotIn('Guardar límite',self.get(self.guest))
        self.assertNotIn('Editar',self.get(self.guest,'/admin/cuentas'))
        self.assertNotIn('id_cuenta"',self.get(self.guest,'/admin/cuentas'))

    def test_two_sessions_of_same_account_keep_independent_profiles(self):
        pid=self.shared()
        second_session=self.client('admin','admin123!')
        self.assertNotIn('Perfil financiero: <strong>Hogar compartido',self.get(second_session))
        self.assertIn('Perfil financiero: <strong>Hogar compartido',self.get(self.owner))
        self.post(second_session,'/perfiles/seleccionar',{'id_perfil':pid})
        self.post(self.owner,'/perfiles/seleccionar',{'id_perfil':1})
        self.assertIn('Perfil financiero: <strong>Hogar compartido',self.get(second_session))
        self.assertNotIn('Perfil financiero: <strong>Hogar compartido',self.get(self.owner))

    def test_login_requires_selection_before_entering_financial_information(self):
        pid=self.shared()
        pending=build_opener(HTTPCookieProcessor(CookieJar()))
        with pending.open(Request(self.base+'/login',data=urlencode({'usuario':'Miriam','contrasena':'Clave123!'}).encode()),timeout=5) as r:
            self.assertEqual(r.url,self.base+'/perfiles/elegir')
            html=r.read().decode()
            for expected in ('Seleccionar perfil financiero','Mis perfiles','Invitado','Hogar compartido','Ingresar al perfil'):
                self.assertIn(expected,html)
            self.assertNotIn('class="main-nav"',html)
            self.assertNotIn('class="hero"',html)
            self.assertNotIn('Finanzas de OtraPersona',html)
        for entry in app.SESSIONS.values():
            if entry[0]=='Miriam' and len(entry)==2:
                break
        else:self.fail('La sesión nueva no debe tener un perfil elegido automáticamente')
        self.post(pending,'/movimientos',self.movement_form(pid))
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0],0)
        with pending.open(self.base+'/',timeout=5) as r:
            self.assertEqual(r.url,self.base+'/perfiles/elegir')
        self.post(pending,'/perfiles/seleccionar',{'id_perfil':pid})
        self.assertIn('Perfil financiero: <strong>Hogar compartido',self.get(pending))
        self.post(pending,'/movimientos',self.movement_form(pid))
        self.assertIn('Gasto compartido',self.get(self.owner))

    def test_guest_cannot_change_structure_or_members_even_with_direct_posts(self):
        pid=self.shared()
        form=self.movement_form(pid)
        guest_panel=self.get(self.guest)
        self.assertIn('href="/perfiles">Mis perfiles</a>',guest_panel)
        self.assertNotIn('Administrar perfiles / integrantes',guest_panel)
        self.assertIn('<summary>Consultas</summary>',guest_panel)
        for route,label in (('presupuestos','Presupuestos'),('metas_ahorro','Metas de ahorro'),
                            ('cuentas','Cuentas'),('categorias','Categorías'),('monedas','Monedas')):
            self.assertIn(f'{label} · Consulta',guest_panel)
            html=self.get(self.guest,f'/admin/{route}')
            self.assertNotIn(f'action="/admin/{route}/guardar"',html)
            self.assertNotIn('<th>Acciones</th>',html)
            self.assertIn('Consulta de ',html)
        shared_profiles=self.get(self.guest,'/perfiles')
        self.assertNotIn(f'action="/perfiles/{pid}/guardar"',shared_profiles)
        self.assertNotIn(f'action="/perfiles/{pid}/invitar"',shared_profiles)
        self.assertNotIn(f'action="/perfiles/{pid}/eliminar"',shared_profiles)
        self.assertIn('Administrar perfiles / integrantes',self.get(self.owner))
        with db.connect() as c:
            category=form['id_categoria']
            account=form['id_cuenta']
        for route,fields in [('/admin/categorias/guardar',{'nombre':'Intruso','tipo':'gasto'}),
            (f'/admin/cuentas/{account}/eliminar',{}),
            ('/admin/cuentas/guardar',{'nombre':'Cuenta intrusa','saldo_inicial_centimos':'0','id_moneda':'1'}),
            ('/presupuestos',{'id_categoria':category,'anio':'2026','mes':'10','monto_limite':'100'}),
            (f'/perfiles/{pid}/guardar',{'nombre':'Renombrado'}),
            (f'/perfiles/{pid}/invitar',{'username':'OtraPersona'}),
            (f'/perfiles/{pid}/integrantes/1/eliminar',{}),
            (f'/perfiles/{pid}/eliminar',{})]:
            self.denied(self.guest,route,fields)
        self.denied(self.guest,f'/admin/cuentas?editar={account}')
        self.post(self.owner,'/movimientos',form)
        with db.connect() as c:mid=c.execute('SELECT id_movimiento FROM movimientos WHERE id_perfil=?',(pid,)).fetchone()[0]
        self.denied(self.guest,f'/movimientos/{mid}/eliminar',{})
        self.denied(self.guest,f'/movimientos/{mid}/actualizar',form)
        self.denied(self.guest,'/admin/usuarios')

    def test_revoking_guest_access_keeps_records_and_takes_effect_next_request(self):
        pid=self.shared()
        self.post(self.guest,'/movimientos',self.movement_form(pid))
        self.post(self.owner,f'/perfiles/{pid}/integrantes/2/eliminar',{})
        self.assertNotIn('Gasto compartido',self.get(self.guest))
        self.assertIn('Gasto compartido',self.get(self.owner))
        self.denied(self.guest,'/perfiles/seleccionar',{'id_perfil':pid})
        self.denied(self.guest,f'/perfiles/{pid}/invitar',{'username':'OtraPersona'})

    def test_multiple_profiles_edit_and_delete_only_empty_profiles(self):
        self.post(self.owner,'/perfiles/crear',{'nombre':'Segundo hogar'})
        with db.connect() as c:pid=c.execute("SELECT id_perfil FROM perfiles_financieros WHERE nombre='Segundo hogar'").fetchone()[0]
        self.post(self.owner,f'/perfiles/{pid}/guardar',{'nombre':'Hogar renombrado'})
        self.assertIn('Hogar renombrado',self.get(self.owner,'/perfiles'))
        self.post(self.owner,f'/perfiles/{pid}/eliminar',{})
        with db.connect() as c:
            self.assertIsNone(c.execute('SELECT 1 FROM perfiles_financieros WHERE id_perfil=?',(pid,)).fetchone())
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.denied(self.owner,'/perfiles/1/eliminar',{},status=400)
        pid=self.shared()
        self.post(self.guest,'/movimientos',self.movement_form(pid))
        self.denied(self.owner,f'/perfiles/{pid}/eliminar',{},status=400)

    def test_guest_can_register_transfers_and_savings_and_read_alerts(self):
        pid=self.shared()
        self.post(self.owner,'/movimientos',self.movement_form(pid,kind='ingreso',amount='1000'))
        with db.connect() as c:
            accounts=c.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=? ORDER BY id_cuenta',(pid,)).fetchall()
        self.post(self.guest,'/admin/transferencias/guardar',dict(id_cuenta_origen=accounts[0][0],
            id_cuenta_destino=accounts[1][0],monto_origen_centimos='10',fecha=date.today().isoformat(),descripcion='Transferencia invitada'))
        self.post(self.owner,'/admin/metas_ahorro/guardar',dict(nombre='Meta familiar',id_moneda='1',
            monto_objetivo_centimos='200',fecha_objetivo='2027-01-01'))
        with db.connect() as c:meta=c.execute('SELECT id_meta FROM metas_ahorro WHERE id_perfil=?',(pid,)).fetchone()[0]
        self.post(self.guest,'/admin/movimientos_ahorro/guardar',dict(id_meta=meta,id_cuenta=accounts[0][0],
            tipo='aporte',monto_centimos='10',fecha=date.today().isoformat()))
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM transferencias WHERE id_perfil=?',(pid,)).fetchone()[0],1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM movimientos_ahorro WHERE id_meta=?',(meta,)).fetchone()[0],1)

    def test_exchange_rates_do_not_change_another_profiles_conversions(self):
        first=profiles.create('Primer perfil')
        second=profiles.create('Segundo perfil')
        with db.connect() as c:
            for pid,rate in ((first,'0.002'),(second,'0.003')):
                c.execute('INSERT INTO tipos_cambio(id_perfil,id_moneda_base,id_moneda_cotizada,fecha,cotizacion) VALUES(?,1,2,?,?)',
                          (pid,date.today().isoformat(),rate))
            request_ctx.set_profile(profiles.access(c,first))
            self.assertEqual(finance.historical_conversion(c,1,2,100000,date.today().isoformat()),200)
            request_ctx.set_profile(profiles.access(c,second))
            self.assertEqual(finance.historical_conversion(c,1,2,100000,date.today().isoformat()),300)

    def test_guest_receipts_are_shared_but_outsiders_cannot_read_them(self):
        pid=self.shared()
        self.post(self.guest,'/movimientos',self.movement_form(pid))
        with db.connect() as c:mid=c.execute('SELECT id_movimiento FROM movimientos WHERE id_perfil=?',(pid,)).fetchone()[0]
        boundary='MisFinanzasTest'
        data=(f'--{boundary}\r\nContent-Disposition: form-data; name="id_movimiento"\r\n\r\n{mid}\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="archivo"; filename="prueba.png"\r\nContent-Type: image/png\r\n\r\n').encode()+b'\x89PNG\r\n\x1a\n'+f'\r\n--{boundary}--\r\n'.encode()
        with self.guest.open(Request(self.base+'/comprobantes/subir',data=data,
            headers={'Content-Type':f'multipart/form-data; boundary={boundary}'}),timeout=5) as r:self.assertEqual(r.status,200)
        with db.connect() as c:receipt=c.execute('SELECT id_comprobante FROM comprobantes WHERE id_movimiento=?',(mid,)).fetchone()[0]
        with self.owner.open(self.base+f'/comprobantes/{receipt}/archivo',timeout=5) as r:
            self.assertEqual(r.headers['Content-Type'],'image/png')
        self.denied(self.outsider,f'/comprobantes/{receipt}/archivo',status=404)
        self.denied(self.guest,f'/comprobantes/{receipt}/eliminar',{})
        self.assertNotIn(f'/comprobantes/{receipt}/eliminar',self.get(self.guest,'/comprobantes'))


class ProfileMigrationTests(unittest.TestCase):
    def test_existing_financial_tables_and_children_keep_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite3'
            with patch.dict(os.environ,{'DB_PATH':str(path)}):
                request_ctx.set_user_id(1)
                # Emula la versión previa, con datos que pertenecían al usuario.
                schema=db.SCHEMA.read_text(encoding='utf-8')
                prefix=schema.split('CREATE TABLE IF NOT EXISTS perfiles_financieros',1)[0]
                finances='CREATE TABLE IF NOT EXISTS categorias'+schema.split('CREATE TABLE IF NOT EXISTS categorias',1)[1]
                finances=finances.replace('id_perfil','id_usuario').replace('REFERENCES perfiles_financieros(id_usuario)','REFERENCES usuarios(id_usuario)')
                legacy_rates='''CREATE TABLE tipos_cambio(id_tipo_cambio INTEGER PRIMARY KEY,id_moneda_origen INTEGER NOT NULL REFERENCES monedas(id_moneda),id_moneda_destino INTEGER NOT NULL REFERENCES monedas(id_moneda),fecha TEXT NOT NULL,valor TEXT NOT NULL,UNIQUE(id_moneda_origen,id_moneda_destino,fecha));'''
                old_extension=legacy_rates+extension.SCHEMA.removeprefix(finance.QUOTE_SCHEMA+';\n').replace('id_perfil','id_usuario').replace('REFERENCES perfiles_financieros(id_usuario)','REFERENCES usuarios(id_usuario)')
                with closing(sqlite3.connect(path)) as c:
                    c.executescript(prefix+finances+old_extension)
                    c.execute('ALTER TABLE cuentas ADD COLUMN id_moneda INTEGER REFERENCES monedas(id_moneda)')
                    with c:
                        c.execute("INSERT INTO usuarios VALUES(1,'Luis','admin','administrador',1,'salt','hash')")
                        c.execute("INSERT INTO usuarios VALUES(2,'Miriam','Miriam','usuario',1,'salt','hash')")
                        c.execute("INSERT INTO monedas VALUES(1,'CRC','Colón','₡'),(2,'USD','Dólar','$')")
                        c.execute("INSERT INTO categorias VALUES(20,1,'Comida rápida','gasto')")
                        c.execute("INSERT INTO cuentas(id_cuenta,id_usuario,nombre) VALUES(30,1,'Cuenta anterior')")
                        c.execute("INSERT INTO movimientos(id_movimiento,id_usuario,id_cuenta,id_categoria,tipo,monto_centimos,fecha) VALUES(40,1,30,20,'gasto',5000,'2026-10-29')")
                        c.execute("INSERT INTO presupuestos(id_presupuesto,id_usuario,id_categoria,anio,mes,monto_limite_centimos) VALUES(50,1,20,2026,10,10000)")
                        c.execute("INSERT INTO alertas(id_alerta,id_presupuesto,id_usuario,umbral,fecha,leida) VALUES(60,50,1,80,'2026-10-29',1)")
                        c.execute("INSERT INTO comprobantes(id_comprobante,id_movimiento,ruta_archivo,tipo_mime) VALUES(70,40,'anterior.pdf','application/pdf')")
                        c.execute("UPDATE cuentas SET id_moneda=1 WHERE id_cuenta=30")
                        c.execute("INSERT INTO cuentas(id_cuenta,id_usuario,nombre,id_moneda) VALUES(31,1,'Dólares',2),(130,2,'Colones Miriam',1),(131,2,'Dólares Miriam',2)")
                        for rate_id,day,rate in ((1,'2026-10-25','0.001'),(4,'2026-10-26','0.002'),(5,'2026-10-27','0.003')):
                            c.execute('INSERT INTO tipos_cambio VALUES(?,1,2,?,?)',(rate_id,day,rate))
                            c.execute('''INSERT INTO transferencias(id_transferencia,id_usuario,id_cuenta_origen,id_cuenta_destino,
                                monto_origen_centimos,monto_destino_centimos,id_tipo_cambio,fecha)
                                VALUES(?,2,130,131,10000,20,?,'2026-10-29')''',(180+rate_id,rate_id))
                db.init_db();db.init_db()
                with db.connect() as c:
                    self.assertEqual(c.execute('SELECT id_perfil FROM movimientos WHERE id_movimiento=40').fetchone()[0],1)
                    self.assertEqual(c.execute('SELECT nombre FROM categorias WHERE id_categoria=20').fetchone()[0],'Comida rápida')
                    self.assertEqual(c.execute('SELECT leida FROM alertas WHERE id_alerta=60').fetchone()[0],1)
                    self.assertEqual(c.execute('SELECT id_movimiento FROM comprobantes WHERE id_comprobante=70').fetchone()[0],40)
                    self.assertEqual([tuple(r) for r in c.execute('''SELECT t.id_transferencia,r.cotizacion,r.id_perfil
                        FROM transferencias t JOIN tipos_cambio r ON r.id_tipo_cambio=t.id_tipo_cambio
                        ORDER BY t.id_transferencia''')],[(181,'0.001',2),(184,'0.002',2),(185,'0.003',2)])
                    self.assertEqual(c.execute('SELECT COUNT(*) FROM tipos_cambio').fetchone()[0],6)
                    self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
                    self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(len(list(Path(tmp).glob('*.antes-usuarios-*.sqlite3'))),1)
