"""Respaldo SQLite en línea usando sqlite3.Connection.backup.

Uso: python -m scripts.backup_sqlite_s4 /ruta/privada/backup.sqlite3
"""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile

from src.db import db_path


def backup(destination):
    origin = db_path()
    target = Path(destination).expanduser().resolve()
    if not origin.is_file():
        raise ValueError('La base origen no existe')
    if target == origin:
        raise ValueError('El destino no puede ser la base origen')
    if target.exists():
        raise FileExistsError('Ya existe el destino; no se sobrescribe')
    if not target.parent.is_dir():
        raise ValueError('El directorio destino no existe')
    # No copiar el fichero directamente: en WAL los -wal/-shm pueden tener cambios.
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.finanzas_backup_', suffix='.sqlite3',
                                         dir=target.parent, delete=False) as temp:
            tmp_name = temp.name
        with closing(sqlite3.connect(origin.as_uri()+'?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(tmp_name)) as dest:
                source.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('El respaldo no superó integrity_check')
                if dest.execute('PRAGMA foreign_key_check').fetchall():
                    raise ValueError('El respaldo tiene referencias inválidas')
                dest.commit()
        os.chmod(tmp_name, 0o600)
        if target.exists():
            raise FileExistsError('El destino apareció durante el respaldo')
        os.replace(tmp_name, target)
        tmp_name = None
        print('Respaldo SQLite creado y verificado: integridad y claves foráneas OK')
        return target
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    try:
        backup(args.destination)
    except (ValueError,FileExistsError,OSError,sqlite3.Error) as exc:
        parser.exit(1,'No fue posible generar el respaldo: '+str(exc)+'\n')


if __name__=='__main__':
    main()
