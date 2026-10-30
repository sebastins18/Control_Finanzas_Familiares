"""Carga transaccional reproducible de movimientos ficticios para S2.

python -m scripts.seed_bulk_s2 --count 1000
python -m scripts.seed_bulk_s2 --count 100000
Una segunda ejecución sobre la misma base omite la carga por seguridad.
"""
import argparse
from datetime import date, timedelta
from random import Random

from src import db


def bulk_load(count=1000, seed=5):
    if not 1 <= count <= 100000:
        raise ValueError('La carga debe contener entre 1 y 100000 movimientos')
    db.init_db()
    with db.connect() as connection:
        if connection.execute("SELECT COUNT(*) FROM movimientos WHERE id_perfil=1 AND descripcion LIKE 'SIM-S2-%'").fetchone()[0]:
            return 0
        profile=1
        acc=connection.execute('SELECT id_cuenta FROM cuentas WHERE id_perfil=? ORDER BY id_cuenta LIMIT 1',(profile,)).fetchone()
        categories=connection.execute("SELECT id_categoria FROM categorias WHERE id_perfil=? AND tipo='gasto' ORDER BY id_categoria",(profile,)).fetchall()
        if not acc or not categories:
            raise RuntimeError('Inicializar cuentas y categorías antes de cargar movimientos')
        rng=Random(seed)
        initial=date.today()-timedelta(days=364)
        cat_ids=[cat[0] for cat in categories]
        def records():
            for n in range(count):
                yield (profile, acc[0], cat_ids[rng.randrange(len(cat_ids))],
                       'gasto',rng.randint(200,250000),
                       (initial+timedelta(days=rng.randrange(365))).isoformat(),
                       f'SIM-S2-{n+1:06d}')
        connection.executemany("""INSERT INTO movimientos
            (id_perfil,id_cuenta,id_categoria,tipo,monto_centimos,fecha,descripcion)
            VALUES(?,?,?,?,?,?,?)""",records())
    return count


def main():
    parser=argparse.ArgumentParser(description='Generar movimientos sintéticos reproducibles')
    parser.add_argument('--count',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=5)
    args=parser.parse_args()
    inserted=bulk_load(args.count,args.seed)
    print(f'Carga S2: {inserted} movimientos nuevos en transacción SQLite; {"ya existían" if not inserted else "creados correctamente"}.')

if __name__=='__main__':
    from src.db import cli_errors
    with cli_errors():
        main()
