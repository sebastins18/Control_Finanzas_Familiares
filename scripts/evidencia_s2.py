"""Genera evidencia S2 con una base SQLite temporal, sin tocar DB real."""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from src import db
from scripts.seed_bulk_s2 import bulk_load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('evidencia_s2_local.md'))
    ap.add_argument('--count', type=int, default=1000)
    args = ap.parse_args()
    if not 1 <= args.count <= 100000:
        ap.error('--count debe estar entre 1 y 100000')
    with tempfile.TemporaryDirectory(prefix='finanzas_s2_') as temp:
        path = str(Path(temp) / 'test.sqlite3')
        env = dict(os.environ, DB_PATH=path)
        env.pop('APP_BASE_PATH', None)
        env.pop('FINANZAS_INITIAL_ADMIN_PASSWORD', None)
        run = subprocess.run(
            [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
            env=env, capture_output=True, text=True, timeout=180
        )
        output = run.stdout + '\n' + run.stderr
        m = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
        if run.returncode or not m or not re.search(r'^OK$', output, re.M):
            print(output[-5000:])
            return 1
        with patch.dict(os.environ, {'DB_PATH': path, 'APP_BASE_PATH': ''}):
            db.init_db()
            inserted = bulk_load(args.count)
            repeat = bulk_load(args.count)
            with db.connect() as con:
                journal = con.execute('PRAGMA journal_mode').fetchone()[0]
                integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
                bad_fk = len(con.execute('PRAGMA foreign_key_check').fetchall())
                rows = con.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]
                tables = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
                version = sqlite3.sqlite_version
    if (journal, integrity, bad_fk, inserted, repeat, rows) != ('wal', 'ok', 0, args.count, 0, args.count):
        print('Falló la comprobación SQLite')
        return 2
    markdown = (
        '# Evidencia S2 — ejecución automatizada y aislada\n\n'
        f'- **UTC:** {datetime.now(timezone.utc).isoformat(timespec="seconds")}\n'
        f'- **Python:** {sys.version.split()[0]}; **SQLite:** {version}\n'
        f'- **Pruebas:** {m.group(1)}/{m.group(1)} OK; duración {m.group(2)} segundos.\n'
        '- **Ámbito:** servidor HTTP temporal y SQLite temporal en localhost; '
        'NO equivale a una demo manual de CRNube.\n'
        f'- **Base:** {tables} tablas; journal_mode={journal}; integrity_check={integrity}; '
        f'violaciones de FK: {bad_fk}.\n'
        f'- **Carga:** {inserted} movimientos ficticios en una transacción, {rows} filas '
        f'verificadas y {repeat} nuevos registros al repetir (idempotencia).\n'
        '- **Cobertura HTTP:** login, CRUD completo, alertas al 80 %/100 %, '
        'errores 400 y rechazo de escrituras sin sesión.\n\n'
        '**Limitación:** no acredita aportes individuales, demo manual, acceso público ni '
        'aprobación del profesor. El benchmark de S3 se hará por separado.\n'
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding='utf-8')
    print(f'OK: {m.group(1)} tests, {inserted} registros, {integrity}. Archivo: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
