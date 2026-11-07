"""Reejecuta la suite existente y la instalación limpia sin usar la DB del proyecto."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4/reportes')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='misfinanzas_support_') as folder:
        env = dict(os.environ,DB_PATH=str(Path(folder)/'guard.sqlite3'),APP_BASE_PATH='',
                   FINANZAS_INITIAL_ADMIN_PASSWORD=secrets.token_urlsafe(30),FINANZAS_COOKIE_SECURE='0',
                   PYTHONIOENCODING='utf-8')
        for title, cmd, name in [
            ('Suite de regresión existente',['-m','unittest','discover','-s','tests','-v'],'regresion'),
            ('Instalación limpia automática',['-m','scripts.verify_clean_install_s4','--report',str(out/'instalacion_limpia.md')],'instalacion')]:
            start = time.monotonic()
            result = subprocess.run([sys.executable,*cmd],cwd=ROOT,env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=600)
            log = result.stdout+'\n'+result.stderr
            log = log.replace(str(ROOT),'<repositorio>').replace(folder,'<temporal>')
            log = re.sub(r'[A-Za-z]:\\Users\\[^\s\n]+', '<ruta-temporal>', log)
            (out/f'{name}.txt').write_text(log,encoding='utf-8')
            item = dict(prueba=title,estado='APROBADA' if result.returncode==0 else 'FALLIDA',
                        segundos=round(time.monotonic()-start,3),exit_code=result.returncode)
            match = re.search(r'Ran (\d+) tests?',log)
            if match:
                item['tests']=int(match[1])
            results.append(item)
            print(json.dumps(item,ensure_ascii=False),flush=True)
        bulk_env = dict(env,DB_PATH=str(Path(folder)/'bulk.sqlite3'))
        counts = []
        for _ in range(2):
            result = subprocess.run([sys.executable,'-m','scripts.seed_bulk_s2','--count','1000'],cwd=ROOT,env=bulk_env,
                                    capture_output=True,encoding='utf-8',errors='replace',timeout=60)
            if result.returncode:
                raise RuntimeError('Falló la carga sintética local')
            with closing(sqlite3.connect(bulk_env['DB_PATH'])) as cx:
                counts.append(cx.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0])
                integrity = cx.execute('PRAGMA integrity_check').fetchone()[0]
                fk = cx.execute('PRAGMA foreign_key_check').fetchall()
        item = dict(prueba='Carga local 1000 + repetición idempotente',estado='APROBADA' if counts==[1000,1000] and integrity=='ok' and not fk else 'FALLIDA',
                    conteos=counts,integridad=integrity,errores_fk=len(fk))
        results.append(item)
        print(json.dumps(item,ensure_ascii=False),flush=True)
        backup_file = Path(folder)/'respaldo.sqlite3'
        backup_run = subprocess.run([sys.executable,'-m','scripts.backup_sqlite_s4',str(backup_file)],
                                    cwd=ROOT,env=bulk_env,capture_output=True,encoding='utf-8',timeout=60)
        if backup_run.returncode:
            raise RuntimeError('Falló el respaldo local aislado')
        with closing(sqlite3.connect(backup_file.as_uri()+'?mode=ro',uri=True)) as cx:
            backup_count = cx.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]
            backup_integrity = cx.execute('PRAGMA integrity_check').fetchone()[0]
            backup_fk = cx.execute('PRAGMA foreign_key_check').fetchall()
        item = dict(prueba='Respaldo coherente de SQLite local',
                    estado='APROBADA' if backup_count==1000 and backup_integrity=='ok' and not backup_fk else 'FALLIDA',
                    movimientos=backup_count,integridad=backup_integrity,errores_fk=len(backup_fk))
        results.append(item)
        print(json.dumps(item,ensure_ascii=False),flush=True)
    report = dict(fecha=datetime.now(timezone(timedelta(hours=-6))).isoformat(timespec='seconds'),pruebas=results)
    (out/'comprobaciones_adicionales.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return int(any(r['estado']=='FALLIDA' for r in results))


if __name__=='__main__':
    raise SystemExit(main())
