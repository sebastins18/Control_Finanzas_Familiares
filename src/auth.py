"""Usuarios en SQLite con dos roles fijos y migraciones de versiones anteriores."""
import hashlib
import json
import os
import secrets
import re
import sqlite3

from src import db

# Modo temporal: todas las sesiones utilizan permisos de usuario normal.
STANDARD_USER_MODE = True


def is_system_admin(user):
    return bool(not STANDARD_USER_MODE and user and user['role']=='admin' and user['active'])


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()


def init(connection):
    columns = {r['name'] for r in connection.execute('PRAGMA table_info(usuarios)')}
    if 'id_rol' in columns:
        if 'rol' not in columns:
            connection.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('administrador','usuario'))")
        connection.execute("""UPDATE usuarios SET rol=CASE WHEN EXISTS
            (SELECT 1 FROM roles r WHERE r.id_rol=usuarios.id_rol AND r.es_administrador=1)
            THEN 'administrador' ELSE 'usuario' END""")
        connection.execute('ALTER TABLE usuarios DROP COLUMN id_rol')
        connection.execute('DROP TABLE roles')
        columns = {r['name'] for r in connection.execute('PRAGMA table_info(usuarios)')}
    if 'username' in columns and connection.execute('SELECT 1 FROM usuarios WHERE username IS NOT NULL').fetchone():
        username_constraints(connection)
        return
    for column, definition in (
            ('username', 'username TEXT'),
            ('rol', "rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('administrador','usuario'))"),
            ('activo', 'activo INTEGER NOT NULL DEFAULT 0 CHECK(activo IN (0,1))'),
            ('password_salt', 'password_salt TEXT'),
            ('password_hash', 'password_hash TEXT')):
        if column not in columns:
            connection.execute('ALTER TABLE usuarios ADD COLUMN ' + definition)
            columns.add(column)
    connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)')
    # Conserva los identificadores y sus relaciones financieras al migrar.
    for row in connection.execute('SELECT id_usuario FROM usuarios').fetchall():
        salt = secrets.token_hex(16)
        connection.execute('''UPDATE usuarios SET username=?, rol='usuario',
            password_salt=?,password_hash=? WHERE id_usuario=?''',
            (f"legacy_{row['id_usuario']}", salt, hash_password(secrets.token_urlsafe(32), salt), row['id_usuario']))
    legacy = db.db_path().parent / 'login_credentials.json'
    users = []
    if legacy.exists():
        data = json.loads(legacy.read_text(encoding='utf-8'))
        users = data.get('users', [dict(data, name='Administrador', role='admin', active=True)]) if isinstance(data, dict) else []
    admin = next((u for u in users if u['username'] == 'admin'), None)
    if admin is None:
        salt = secrets.token_hex(16)
        admin = dict(username='admin', name='Administrador', role='admin', active=True,
                     salt=salt, hash=hash_password(os.environ.get('FINANZAS_INITIAL_ADMIN_PASSWORD') or 'admin123!', salt))
    connection.execute('''INSERT INTO usuarios(id_usuario,username,nombre,rol,activo,password_salt,password_hash)
        VALUES(1,'admin',?,'administrador',1,?,?) ON CONFLICT(id_usuario) DO UPDATE SET
        username='admin',nombre=excluded.nombre,rol='administrador',activo=1,
        password_salt=excluded.password_salt,password_hash=excluded.password_hash''',
        (admin.get('name', 'Administrador'), admin['salt'], admin['hash']))
    for user in users:
        if user['username'] == 'admin':
            continue
        connection.execute('''INSERT INTO usuarios(nombre,username,rol,activo,password_salt,password_hash)
            VALUES(?,?,?,?,?,?)''', (user.get('name', user['username']), user['username'],
            'administrador' if user.get('role') == 'admin' else 'usuario', int(user.get('active', True)), user['salt'], user['hash']))
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_config'").fetchone():
        connection.execute("DELETE FROM app_config WHERE clave='perfil_activo'")
    username_constraints(connection)


def username_constraints(c):
    # También protege escrituras concurrentes y bases anteriores sin reconstruir usuarios.
    c.execute('''CREATE TRIGGER IF NOT EXISTS usuarios_username_insert
        BEFORE INSERT ON usuarios WHEN EXISTS(SELECT 1 FROM usuarios
            WHERE lower(trim(username))=lower(trim(NEW.username)))
        BEGIN SELECT RAISE(ABORT,'username_exists'); END''')
    c.execute('''CREATE TRIGGER IF NOT EXISTS usuarios_username_update
        BEFORE UPDATE OF username ON usuarios WHEN NEW.username<>OLD.username AND
            EXISTS(SELECT 1 FROM usuarios WHERE id_usuario<>OLD.id_usuario AND
                lower(trim(username))=lower(trim(NEW.username)))
        BEGIN SELECT RAISE(ABORT,'username_exists'); END''')


def register(form):
    username=str(form.get('username','')).strip()
    name=str(form.get('name','')).strip()
    password=str(form.get('password',''))
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,40}',username):
        raise ValueError('El usuario debe tener entre 1 y 40 letras, números, puntos, guiones o guiones bajos, sin espacios.')
    if not 1<=len(name)<=100:
        raise ValueError('Indique un nombre completo de hasta 100 caracteres.')
    if not 8<=len(password)<=128:
        raise ValueError('La contraseña debe tener entre 8 y 128 caracteres.')
    if password!=form.get('confirm_password',''):
        raise ValueError('Las contraseñas no coinciden.')
    with db.connect() as c:
        if c.execute('SELECT 1 FROM usuarios WHERE lower(trim(username))=lower(?)',(username,)).fetchone():
            raise ValueError('Ese nombre de usuario ya está registrado. Elija otro.')
        salt=secrets.token_hex(16)
        try:
            uid=c.execute('''INSERT INTO usuarios(nombre,username,rol,activo,password_salt,password_hash)
                VALUES(?,?,'usuario',1,?,?)''',(name,username,salt,hash_password(password,salt))).lastrowid
        except sqlite3.IntegrityError as exc:
            if 'username_exists' in str(exc) or 'usuarios.username' in str(exc):
                raise ValueError('Ese nombre de usuario ya está registrado. Elija otro.') from None
            raise
        from src.profiles import ensure_default
        ensure_default(c,uid)
        return uid


def credentials():
    with db.connect() as c:
        return [dict(row) for row in c.execute('''SELECT u.id_usuario,u.username,u.nombre AS name,
            u.activo AS active,u.password_salt AS salt,u.password_hash AS hash,
            u.rol AS role_name,
            CASE WHEN u.rol='administrador' THEN 'admin' ELSE 'usuario' END AS role
            FROM usuarios u ORDER BY u.id_usuario''')]


def save_users(users):
    with db.connect() as c:
        for user in users:
            role = user['role']
            if role not in ('admin','usuario'):
                raise ValueError('Rol no permitido')
            role_name = 'administrador' if role == 'admin' else 'usuario'
            existing=c.execute('SELECT id_usuario FROM usuarios WHERE username=?',(user['username'],)).fetchone()
            if existing:
                c.execute('''UPDATE usuarios SET nombre=?,rol=?,activo=?,password_salt=?,password_hash=?
                    WHERE id_usuario=?''',(user['name'],role_name,int(user['active']),user['salt'],user['hash'],existing[0]))
            else:
                c.execute('''INSERT INTO usuarios(nombre,username,rol,activo,password_salt,password_hash)
                    VALUES(?,?,?,?,?,?)''',(user['name'],user['username'],role_name,int(user['active']),user['salt'],user['hash']))
            uid = c.execute('SELECT id_usuario FROM usuarios WHERE username=?', (user['username'],)).fetchone()[0]
            from src.profiles import ensure_default
            ensure_default(c, uid)
