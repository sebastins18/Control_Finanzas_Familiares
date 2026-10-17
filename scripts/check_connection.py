from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import connect, db_path

if __name__ == '__main__':
    try:
        with connect() as db:
            result = db.execute('SELECT sqlite_version()').fetchone()[0]
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        print(f'SQLite: OK | version={result} | archivo={db_path()}')
        print('Tablas:', ', '.join(tables) if tables else 'SIN TABLAS (ejecute init_db.py)')
    except Exception as error:
        print(f'SQLite: ERROR | {error}')
        raise SystemExit(1)
