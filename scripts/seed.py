"""Datos totalmente inventados. Ejecución idempotente sobre una base limpia o existente."""
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import connect, init_db, parse_money

if __name__ == '__main__':
    init_db()
    today = date.today()
    examples = [
        ('ingreso', 'Salario', 'Cuenta principal', '850000', 'Ingreso de ejemplo'),
        ('gasto', 'Alimentación', 'Cuenta principal', '92000', 'Supermercado'),
        ('gasto', 'Transporte', 'Efectivo', '22000', 'Transporte semanal'),
        ('gasto', 'Servicios', 'Cuenta principal', '35000', 'Servicios de hogar'),
        ('gasto', 'Entretenimiento', 'Cuenta principal', '18000', 'Salida familiar'),
    ]
    with connect() as db:
        count = db.execute('SELECT COUNT(*) FROM movimientos').fetchone()[0]
        if count:
            print('La base ya tiene movimientos; no se insertarán duplicados.')
        else:
            for kind, cat, acc, amount, desc in examples:
                cat_id = db.execute('SELECT id_categoria FROM categorias WHERE tipo=? AND nombre=?', (kind, cat)).fetchone()[0]
                acc_id = db.execute('SELECT id_cuenta FROM cuentas WHERE nombre=?', (acc,)).fetchone()[0]
                db.execute('''INSERT INTO movimientos
                    (id_usuario, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion)
                    VALUES(1, ?, ?, ?, ?, ?, ?)''', (acc_id, cat_id, kind, parse_money(amount), today.isoformat(), desc))
            print(f'Datos sintéticos cargados: {len(examples)} movimientos.')
        presets = [('Alimentación', '120000'), ('Transporte', '45000'), ('Servicios', '50000'), ('Entretenimiento', '20000')]
        for cat, amount in presets:
            cat_id = db.execute("SELECT id_categoria FROM categorias WHERE tipo='gasto' AND nombre=?", (cat,)).fetchone()[0]
            db.execute('''INSERT OR IGNORE INTO presupuestos(id_usuario,id_categoria,anio,mes,monto_limite_centimos)
                         VALUES(1,?,?,?,?)''', (cat_id, today.year, today.month, parse_money(amount)))
        print(f'Presupuestos de ejemplo preparados para {today.year}-{today.month:02d}.')
