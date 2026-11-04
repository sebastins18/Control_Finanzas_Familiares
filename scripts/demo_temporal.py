"""Datos de prueba TEMPORALES en un perfil aparte, para ver historial, reporte anual y recurrentes.

    python -m scripts.demo_temporal            # crea el perfil «DEMO · Datos de prueba» (propietario: admin)
    python -m scripts.demo_temporal --borrar   # elimina ese perfil y todo su contenido

No modifica otros perfiles. Antes de cargar, respalda la base junto al archivo SQLite.
Datos ficticios y deterministas (semilla fija). No usar contra la base del servidor.
"""
import argparse
import random
import sqlite3
from contextlib import closing
from datetime import date, datetime

from src import db, profiles, recurrentes, request_ctx

PROFILE_NAME = 'DEMO · Datos de prueba'
OWNER = 'admin'
START = date(2025, 9, 1)

GASTOS = {
    'Alimentación': [('Supermercado', 18000, 65000), ('Feria del agricultor', 8000, 22000), ('Panadería', 2500, 6000), ('Restaurante', 12000, 38000)],
    'Transporte': [('Gasolina', 20000, 35000), ('Uber', 3500, 9000), ('Parqueo', 1500, 4000)],
    'Servicios': [('Recibo de luz', 28000, 42000), ('Recibo de agua', 9000, 15000), ('Plan celular', 15000, 15000)],
    'Entretenimiento': [('Cine', 6000, 14000), ('Salida familiar', 15000, 45000), ('Libros', 8000, 20000)],
    'Salud': [('Farmacia', 5000, 25000), ('Consulta médica', 30000, 45000)],
}
RECURRENTES = [  # descripción, tipo, categoría, monto (CRC), día, activo
    ('Salario mensual', 'ingreso', 'Salario', 850000, 1, 1),
    ('Alquiler del apartamento', 'gasto', 'Vivienda', 280000, 5, 1),
    ('Internet hogar', 'gasto', 'Servicios', 25000, 10, 1),
    ('Gimnasio (pausado)', 'gasto', 'Salud', 22000, 15, 0),
]


def months(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def backup():
    path = db.db_path()
    target = path.with_name(path.stem + '.antes-demo-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.sqlite3')
    with closing(sqlite3.connect(path)) as source, closing(sqlite3.connect(target)) as dest:
        source.backup(dest)
    return target


def find_profile(c):
    return c.execute('''SELECT p.id_perfil, u.id_usuario FROM perfiles_financieros p JOIN usuarios u ON u.id_usuario = p.id_propietario
        WHERE p.nombre = ? AND u.username = ?''', (PROFILE_NAME, OWNER)).fetchone()


def remove():
    with db.connect() as c:
        row = find_profile(c)
        if not row:
            print('No existe el perfil de demostración; no hay nada que borrar.')
            return
        pid = row[0]
        c.execute('DELETE FROM recurrentes_generados WHERE id_recurrente IN (SELECT id_recurrente FROM movimientos_recurrentes WHERE id_perfil=?)', (pid,))
        c.execute('DELETE FROM movimientos_recurrentes WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM comprobantes WHERE id_movimiento IN (SELECT id_movimiento FROM movimientos WHERE id_perfil=?)', (pid,))
        c.execute('DELETE FROM alertas WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM presupuestos WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM movimientos_ahorro WHERE id_meta IN (SELECT id_meta FROM metas_ahorro WHERE id_perfil=?)', (pid,))
        c.execute('DELETE FROM metas_ahorro WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM transferencias WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM tipos_cambio WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM movimientos WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM categorias WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM cuentas WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM integrantes_perfil WHERE id_perfil=?', (pid,))
        c.execute('DELETE FROM perfiles_financieros WHERE id_perfil=?', (pid,))
    print(f'Perfil de demostración {pid} eliminado con todo su contenido.')


def create():
    today = date.today()
    rnd = random.Random(2026)
    with db.connect() as c:
        if find_profile(c):
            raise SystemExit('El perfil de demostración ya existe. Bórrelo primero con --borrar.')
        owner = c.execute('SELECT id_usuario FROM usuarios WHERE username=?', (OWNER,)).fetchone()
        if not owner:
            raise SystemExit(f'No existe el usuario {OWNER}.')
        uid = owner[0]
        pid = c.execute('INSERT INTO perfiles_financieros(nombre,id_propietario) VALUES(?,?)', (PROFILE_NAME, uid)).lastrowid
        profiles.seed(c, pid)
        crc, usd = (c.execute('SELECT id_moneda FROM monedas WHERE codigo_iso=?', (code,)).fetchone()[0] for code in ('CRC', 'USD'))
        c.execute("UPDATE cuentas SET saldo_inicial_centimos=150000000 WHERE id_perfil=? AND nombre='Cuenta principal'", (pid,))
        c.execute("UPDATE cuentas SET saldo_inicial_centimos=8000000 WHERE id_perfil=? AND nombre='Efectivo'", (pid,))
        usd_account = c.execute("INSERT INTO cuentas(id_perfil,nombre,saldo_inicial_centimos,id_moneda) VALUES(?, 'Ahorros en dólares', 300000, ?)", (pid, usd)).lastrowid
        cat = {r['nombre']: r['id_categoria'] for r in c.execute('SELECT id_categoria,nombre FROM categorias WHERE id_perfil=?', (pid,))}
        acc = {r['nombre']: r['id_cuenta'] for r in c.execute('SELECT id_cuenta,nombre FROM cuentas WHERE id_perfil=?', (pid,))}

        def add(day, kind, category, cents, description, account):
            c.execute('''INSERT INTO movimientos(id_perfil,id_cuenta,id_categoria,tipo,monto_centimos,fecha,descripcion,monto_acreditado_centimos)
                VALUES(?,?,?,?,?,?,?,?)''', (pid, account, cat[category], kind, cents, day.isoformat(), description, cents))

        count = 0
        for y, m in months(START, today):
            last_day = today.day if (y, m) == (today.year, today.month) else 28
            for _ in range(rnd.randint(14, 22) if last_day == 28 else max(2, last_day * 2 // 3)):
                category = rnd.choice(list(GASTOS))
                name, low, high = rnd.choice(GASTOS[category])
                account = acc['Efectivo'] if name in ('Panadería', 'Feria del agricultor', 'Parqueo') else acc['Cuenta principal']
                add(date(y, m, rnd.randint(1, last_day)), 'gasto', category, rnd.randrange(low, high + 1, 50) * 100, name, account)
                count += 1
            if rnd.random() < 0.35:
                add(date(y, m, min(20, last_day)), 'ingreso', 'Otros ingresos', rnd.randrange(40000, 150001, 1000) * 100, 'Trabajo independiente', acc['Cuenta principal'])
                count += 1
            if last_day >= 12:
                add(date(y, m, 12), 'gasto', 'Entretenimiento', 1599, 'Suscripción de streaming', usd_account)
                count += 1
        add(date(today.year, today.month, 1), 'gasto', 'Alimentación', 6000000, 'Compra grande 50% descuento', acc['Cuenta principal'])
        count += 1

        for description, kind, category, amount, day, active in RECURRENTES:
            c.execute('''INSERT INTO movimientos_recurrentes(id_perfil,id_cuenta,id_categoria,tipo,monto_centimos,descripcion,dia_mes,fecha_inicio,activo)
                VALUES(?,?,?,?,?,?,?,?,?)''', (pid, acc['Cuenta principal'], cat[category], kind, amount * 100, description, day, START.isoformat(), active))
        for category, limit in (('Alimentación', 180000), ('Transporte', 60000), ('Entretenimiento', 40000)):
            c.execute('INSERT INTO presupuestos(id_perfil,id_categoria,anio,mes,monto_limite_centimos,id_moneda) VALUES(?,?,?,?,?,?)',
                      (pid, cat[category], today.year, today.month, limit * 100, crc))

    # Recurrentes generados hasta el mes pasado; los del mes en curso quedan pendientes para probar el botón.
    request_ctx.set_user_id(uid)
    request_ctx.set_profile({'id_perfil': pid, 'es_propietario': 1})
    first_of_month = date(today.year, today.month, 1)
    previous = date.fromordinal(first_of_month.toordinal() - 1)
    created, _ = recurrentes.generate(today=previous)
    with db.connect() as c:
        pending = len(recurrentes.pending(c))
    print(f'Perfil «{PROFILE_NAME}» (id {pid}) creado para {OWNER}: {count} movimientos sueltos, '
          f'{created} recurrentes generados, {pending} recurrentes pendientes y 3 presupuestos del mes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--borrar', action='store_true', help='Elimina el perfil de demostración y su contenido')
    args = parser.parse_args()
    with db.cli_errors():
        print('Respaldo previo:', backup())
        remove() if args.borrar else create()


if __name__ == '__main__':
    main()
