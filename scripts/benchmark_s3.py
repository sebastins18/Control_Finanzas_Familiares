"""Mediciones del Seguimiento 3: tres operaciones, tres o mas ejecuciones, con y sin indices.

    python -m scripts.benchmark_s3                 # 100000 movimientos
    python -m scripts.benchmark_s3 --count 5000    # prueba rapida

Trabaja siempre en una base temporal (nunca toca data/finanzas.sqlite3) y escribe el
informe en docs/seguimientos/S3_mediciones.md. Solo biblioteca estandar.
"""
import argparse
import logging
import os
import platform
import sqlite3
import statistics
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

REPORT = Path(__file__).resolve().parent.parent / 'docs' / 'seguimientos' / 'S3_mediciones.md'
INDEXES = ('idx_movimientos_fecha_tipo', 'idx_movimientos_categoria_fecha')


def release_app_log_handlers():
    """Cierra el log de la aplicacion para poder borrar el directorio temporal (necesario en Windows)."""
    logger = logging.getLogger('finanzas')
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def operations(count):
    """Un mes completo dentro de la ventana de 365 dias que cubre la carga sintetica."""
    first = (date.today() - timedelta(days=120)).replace(day=1)
    following = (first + timedelta(days=32)).replace(day=1)
    start, end = first.isoformat(), following.isoformat()
    return [
        ('Movimientos por rango de fecha (1 mes, 100 filas)',
         '''SELECT m.*, c.nombre FROM movimientos m JOIN categorias c ON c.id_categoria=m.id_categoria
            WHERE m.id_perfil=1 AND m.fecha>=? AND m.fecha<? ORDER BY m.fecha DESC, m.id_movimiento DESC LIMIT 100''',
         (start, end), False),
        ('Total de gasto por categoria en un mes',
         '''SELECT id_categoria, SUM(monto_centimos) FROM movimientos
            WHERE tipo='gasto' AND fecha>=? AND fecha<? GROUP BY id_categoria''',
         (start, end), False),
        ('Actualizacion de un gasto por id',
         'UPDATE movimientos SET monto_centimos=monto_centimos+1 WHERE id_movimiento=?',
         (max(1, count // 2),), True),
    ]


def build_database(path, count):
    """Esquema real de la aplicacion y carga masiva en una sola transaccion."""
    os.environ['DB_PATH'] = str(path)
    from src import db
    from scripts.seed_bulk_s2 import bulk_load
    db.init_db()
    return bulk_load(count)


def measure(connection, sql, params, is_write, runs):
    timings = []
    for _ in range(runs):
        started = time.perf_counter()
        if is_write:
            connection.execute('BEGIN')
            connection.execute(sql, params)
            connection.execute('ROLLBACK')
        else:
            connection.execute(sql, params).fetchall()
        timings.append((time.perf_counter() - started) * 1000)
    return timings


def plan(connection, sql, params):
    return [row[3] for row in connection.execute('EXPLAIN QUERY PLAN ' + sql, params)]


def run(count, runs):
    if runs < 3:
        raise ValueError('Se requieren al menos 3 ejecuciones por operacion')
    results = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'benchmark.sqlite'
        loaded = build_database(path, count)
        ops = operations(count)
        try:
            for scenario in ('con indices', 'sin indices'):
                if scenario == 'sin indices':
                    admin = sqlite3.connect(str(path), isolation_level=None)
                    try:
                        for name in INDEXES:
                            admin.execute(f'DROP INDEX IF EXISTS {name}')
                    finally:
                        admin.close()
                # Conexion nueva por escenario: sqlite3 cachea EXPLAIN QUERY PLAN y no se
                # invalida al cambiar el esquema, lo que mostraria un plan obsoleto.
                connection = sqlite3.connect(str(path), isolation_level=None)
                try:
                    connection.execute('PRAGMA foreign_keys=ON')
                    for name, sql, params, is_write in ops:
                        timings = measure(connection, sql, params, is_write, runs)
                        results.append(dict(operation=name, scenario=scenario, timings=timings,
                                            median=statistics.median(timings),
                                            plan=plan(connection, sql, params)))
                finally:
                    connection.close()
        finally:
            release_app_log_handlers()
    return loaded, results


def render(count, loaded, runs, results):
    lines = ['# Seguimiento 3: mediciones SQLite', '',
             f'- Movimientos en la base de prueba: {count} (insertados en esta ejecucion: {loaded})',
             f'- Ejecuciones por operacion: {runs}; se reporta la mediana en milisegundos',
             f'- SQLite {sqlite3.sqlite_version}, Python {platform.python_version()}, {platform.system()} {platform.release()}',
             '- Base temporal; las lecturas usan una conexion abierta y los UPDATE se revierten (ROLLBACK)',
             '- Los tiempos dependen del equipo: comparar entre escenarios, no entre maquinas', '',
             '| Operacion | Escenario | Ejecuciones (ms) | Mediana (ms) |', '| --- | --- | --- | --- |']
    for r in results:
        times = ', '.join(f'{t:.3f}' for t in r['timings'])
        lines.append(f"| {r['operation']} | {r['scenario']} | {times} | {r['median']:.3f} |")
    lines += ['', '## EXPLAIN QUERY PLAN', '']
    for r in results:
        lines.append(f"**{r['operation']} ({r['scenario']})**")
        lines += [f'- `{step}`' for step in r['plan']] + ['']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Mediciones S3 de SQLite')
    parser.add_argument('--count', type=int, default=100000)
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--output', type=Path, default=REPORT)
    args = parser.parse_args()
    loaded, results = run(args.count, args.runs)
    report = render(args.count, loaded, args.runs, results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + '\n', encoding='utf-8')
    print(report)


if __name__ == '__main__':
    from src.db import cli_errors
    with cli_errors():
        main()