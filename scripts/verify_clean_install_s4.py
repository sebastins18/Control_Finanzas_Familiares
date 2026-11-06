"""Valida una instalación LIMPIA de S4 en un SQLite temporal sin tocar la instancia publicada.

Uso: python -m scripts.verify_clean_install_s4 [--report ruta.md]
Requiere únicamente Python 3.11+ y la biblioteca estándar.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def execute(cmd, env):
    result = subprocess.run(
        [sys.executable, *cmd], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise RuntimeError(
            f'Falló {" ".join(cmd)} (código {result.returncode}). '
            'Revise las pruebas en una terminal aislada.'
        )
    return result.stdout.strip()


def run(report=None):
    with tempfile.TemporaryDirectory(prefix='finanzas_s4_clean_') as directory:
        db_file = Path(directory) / 'clean.sqlite3'
        password = secrets.token_urlsafe(24)
        env = dict(os.environ)
        env.update(DB_PATH=str(db_file), APP_BASE_PATH='/finanzas',
                   FINANZAS_INITIAL_ADMIN_PASSWORD=password,
                   FINANZAS_COOKIE_SECURE='1')
        execute(['scripts/init_db.py'], env)
        first_seed = execute(['scripts/seed.py'], env)
        second_seed = execute(['scripts/seed.py'], env)
        execute(['scripts/check_connection.py'], env)
        with sqlite3.connect(db_file) as con:
            integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
            foreign_errors = con.execute('PRAGMA foreign_key_check').fetchall()
            journal = con.execute('PRAGMA journal_mode').fetchone()[0]
            users = con.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
            transactions = con.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]
            tables = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            admin = con.execute("SELECT password_salt, password_hash FROM usuarios WHERE username='admin'").fetchone()
        if integrity != 'ok' or foreign_errors or journal.lower() != 'wal':
            raise RuntimeError('No se cumple integridad, FK o journal WAL')
        if not admin or users < 1 or transactions != 5 or tables < 10:
            raise RuntimeError('No se creó el modelo esperado o hay duplicados del seed')
        # HTTP real sin navegador: inicio de sesión e inicialización de perfil nuevo.
        previous = {key: os.environ.get(key) for key in
                    ('DB_PATH','APP_BASE_PATH','FINANZAS_INITIAL_ADMIN_PASSWORD','FINANZAS_COOKIE_SECURE')}
        try:
            for key in previous:
                os.environ[key] = env[key]
            from src.app import Handler
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            runner = threading.Thread(target=server.serve_forever, daemon=True)
            runner.start()
            base = 'http://127.0.0.1:' + str(server.server_port) + '/finanzas'
            client = build_opener(NoRedirect())
            try:
                with client.open(base+'/login',timeout=6) as response:
                    if response.status!=200 or response.headers.get('X-Frame-Options')!='DENY':
                        raise RuntimeError('No funciona GET /finanzas/login o faltan cabeceras')
                req = Request(base+'/login',data=urlencode({
                    'usuario':'admin','contrasena':password
                }).encode('utf-8'))
                try:
                    client.open(req,timeout=6)
                    raise RuntimeError('El login no emitió redirección')
                except HTTPError as response:
                    if response.code!=303 or 'Secure' not in response.headers.get('Set-Cookie',''):
                        raise RuntimeError('Login/Set-Cookie no cumple la validación de S4')
            finally:
                server.shutdown()
                server.server_close()
                runner.join(timeout=4)
        finally:
            for key,value in previous.items():
                if value is None: os.environ.pop(key,None)
                else: os.environ[key]=value
        record = {
            'integridad':integrity,'journal_mode':journal,'violaciones_fk':len(foreign_errors),
            'tablas':tables,'usuarios':users,'movimientos':transactions,
            'http_login':'200','http_post_login':'303','cookie_secure':True,
            'seed_idempotente':('no se insertarán duplicados' in second_seed.lower()),
            'python':sys.version.split()[0], 'sqlite':sqlite3.sqlite_version
        }
        if not record['seed_idempotente']:
            raise RuntimeError('La segunda ejecución del seed no fue idempotente')
        if report:
            out=Path(report)
            out.parent.mkdir(parents=True,exist_ok=True)
            lines=['# Comprobación de instalación limpia — S4','','Fecha UTC: '+
                   datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                   '', '| Verificación | Resultado |','| --- | --- |']
            for key,value in record.items():
                lines.append(f'| {key} | {value} |')
            lines.extend(['','Esta validación usa una base y un servidor HTTP temporales en localhost.',
                          'No verifica instalación hecha por otro integrante, UI manual, CRNube ni video.'])
            out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        print('INSTALACION LIMPIA S4: OK; SQLite WAL, 5 movimientos, idempotencia, login y cookie Secure')
        return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=None)
    args=parser.parse_args()
    try:
        run(args.report)
    except Exception as exc:
        print('INSTALACION LIMPIA S4: ERROR - '+str(exc),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':
    main()
