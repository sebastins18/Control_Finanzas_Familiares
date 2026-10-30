from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import connect, db_path

if __name__ == '__main__':
    from src.db import cli_errors
    with cli_errors():
        with connect() as connection:
            result = connection.execute('SELECT sqlite_version()').fetchone()[0]
            tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        print(f'SQLite: OK | version={result} | archivo={db_path()}')
        print('Tablas:', ', '.join(tables) if tables else 'SIN TABLAS (ejecute init_db.py)')
