from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import init_db, db_path, connect

if __name__ == '__main__':
    from src.db import cli_errors
    with cli_errors():
        init_db()
        with connect() as db:
            mode = db.execute('PRAGMA journal_mode').fetchone()[0]
        print(f'Base inicializada: {db_path()} | journal_mode={mode}')
