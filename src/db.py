"""Persistencia SQLite: sin servicios externos, datos sintéticos y operaciones parametrizadas."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / 'src' / 'schema.sql'
DEFAULT_DB = ROOT / 'data' / 'finanzas.sqlite3'


def db_path() -> Path:
    configured = os.environ.get('DB_PATH')
    path = Path(configured).expanduser() if configured else DEFAULT_DB
    return path.resolve()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Contexto transaccional que también cierra la conexión al finalizar."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA busy_timeout = 5000')
        with connection:
            yield connection
    finally:
        connection.close()


def init_db() -> None:
    with connect() as connection:
        connection.execute('PRAGMA journal_mode = WAL')
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        connection.execute(
            'INSERT OR IGNORE INTO usuarios (id_usuario, nombre) VALUES (1, ?)',
            ('Familia de demostración',),
        )
        for nombre, tipo in [
            ('Salario', 'ingreso'), ('Otros ingresos', 'ingreso'),
            ('Alimentación', 'gasto'), ('Transporte', 'gasto'),
            ('Vivienda', 'gasto'), ('Servicios', 'gasto'),
            ('Entretenimiento', 'gasto'), ('Salud', 'gasto'),
        ]:
            connection.execute(
                'INSERT OR IGNORE INTO categorias (id_usuario, nombre, tipo) VALUES (1, ?, ?)',
                (nombre, tipo),
            )
        connection.execute(
            "INSERT OR IGNORE INTO cuentas (id_usuario, nombre) VALUES (1, 'Cuenta principal')"
        )
        connection.execute(
            "INSERT OR IGNORE INTO cuentas (id_usuario, nombre) VALUES (1, 'Efectivo')"
        )


def parse_money(value: str) -> int:
    """Conserva centavos como entero para evitar inexactitudes de coma flotante."""
    try:
        amount = Decimal(str(value).strip())
        if not amount.is_finite() or amount <= 0:
            raise ValueError('El monto debe ser mayor que cero.')
        if amount.as_tuple().exponent < -2:
            raise ValueError('El monto admite máximo dos decimales.')
        cents = int(amount * 100)
        if cents > 999_999_999_999:
            raise ValueError('El monto supera el máximo permitido.')
        return cents
    except (InvalidOperation, TypeError):
        raise ValueError('Ingrese un monto válido.') from None


def validate_date(value: str) -> str:
    try:
        date.fromisoformat(value)
        if len(value) != 10:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ValueError('Indique una fecha válida (AAAA-MM-DD).') from None


def choices() -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    with connect() as db:
        return (
            db.execute('SELECT * FROM categorias WHERE id_usuario=1 ORDER BY tipo, nombre').fetchall(),
            db.execute('SELECT * FROM cuentas WHERE id_usuario=1 ORDER BY nombre').fetchall(),
        )


def validate_category_account(db: sqlite3.Connection, category_id: int, account_id: int, kind: str) -> None:
    category = db.execute(
        'SELECT 1 FROM categorias WHERE id_categoria = ? AND id_usuario=1 AND tipo = ?',
        (category_id, kind),
    ).fetchone()
    account = db.execute(
        'SELECT 1 FROM cuentas WHERE id_cuenta = ? AND id_usuario=1',
        (account_id,),
    ).fetchone()
    if not category or not account:
        raise ValueError('La categoría o cuenta seleccionada no es válida para el tipo de movimiento.')


def save_movement(form: dict, movement_id: int | None = None) -> None:
    kind = str(form.get('tipo', '')).strip()
    if kind not in ('ingreso', 'gasto'):
        raise ValueError('El tipo debe ser ingreso o gasto.')
    amount_cents = parse_money(form.get('monto', ''))
    valid_date = validate_date(form.get('fecha', ''))
    try:
        category_id = int(form.get('id_categoria', ''))
        account_id = int(form.get('id_cuenta', ''))
    except (ValueError, TypeError):
        raise ValueError('Seleccione una cuenta y categoría válidas.') from None
    description = str(form.get('descripcion', '')).strip()[:160]
    with connect() as db:
        validate_category_account(db, category_id, account_id, kind)
        args = (account_id, category_id, kind, amount_cents, valid_date, description)
        if movement_id is None:
            db.execute(
                '''INSERT INTO movimientos
                (id_usuario, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion)
                VALUES (1, ?, ?, ?, ?, ?, ?)''', args,
            )
        else:
            cursor = db.execute(
                '''UPDATE movimientos SET id_cuenta=?, id_categoria=?, tipo=?,
                   monto_centimos=?, fecha=?, descripcion=?
                   WHERE id_movimiento=? AND id_usuario=1''', (*args, movement_id),
            )
            if cursor.rowcount != 1:
                raise ValueError('No se encontró el movimiento.')


def remove_movement(movement_id: int) -> None:
    with connect() as db:
        db.execute('DELETE FROM movimientos WHERE id_movimiento=? AND id_usuario=1', (movement_id,))


def get_movement(movement_id: int) -> sqlite3.Row | None:
    with connect() as db:
        return db.execute(
            'SELECT * FROM movimientos WHERE id_movimiento=? AND id_usuario=1',
            (movement_id,),
        ).fetchone()


def save_budget(form: dict) -> None:
    try:
        category_id = int(form.get('id_categoria', ''))
        year = int(form.get('anio', ''))
        month = int(form.get('mes', ''))
    except (ValueError, TypeError):
        raise ValueError('Indique categoría y período correctos.') from None
    amount_cents = parse_money(form.get('monto_limite', ''))
    if not (2020 <= year <= 2100 and 1 <= month <= 12):
        raise ValueError('Período fuera de rango.')
    with connect() as db:
        allowed = db.execute(
            "SELECT 1 FROM categorias WHERE id_categoria=? AND id_usuario=1 AND tipo='gasto'",
            (category_id,),
        ).fetchone()
        if not allowed:
            raise ValueError('Solo se permiten presupuestos para categorías de gastos.')
        db.execute(
            '''INSERT INTO presupuestos (id_usuario, id_categoria, anio, mes, monto_limite_centimos)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT (id_usuario, id_categoria, anio, mes)
            DO UPDATE SET monto_limite_centimos=excluded.monto_limite_centimos''',
            (category_id, year, month, amount_cents),
        )


def dashboard(year: int, month: int) -> dict:
    start, end = f'{year:04d}-{month:02d}-01', (f'{year+1:04d}-01-01' if month == 12 else f'{year:04d}-{month+1:02d}-01')
    with connect() as db:
        tx = db.execute('''SELECT m.*, c.nombre AS categoria, a.nombre AS cuenta
            FROM movimientos m JOIN categorias c ON c.id_categoria=m.id_categoria
            JOIN cuentas a ON a.id_cuenta=m.id_cuenta
            WHERE m.id_usuario=1 AND m.fecha>=? AND m.fecha<?
            ORDER BY m.fecha DESC, m.id_movimiento DESC LIMIT 100''', (start, end)).fetchall()
        sums = db.execute('''SELECT tipo, COALESCE(SUM(monto_centimos),0) AS total
            FROM movimientos WHERE id_usuario=1 AND fecha>=? AND fecha<? GROUP BY tipo''', (start, end)).fetchall()
        values = {r['tipo']:r['total'] for r in sums}
        budget_rows = db.execute('''SELECT p.id_categoria, c.nombre AS categoria,
            p.monto_limite_centimos AS limite,
            COALESCE(SUM(m.monto_centimos),0) AS gastado
            FROM presupuestos p JOIN categorias c ON c.id_categoria=p.id_categoria
            LEFT JOIN movimientos m ON m.id_categoria=p.id_categoria
              AND m.tipo='gasto' AND m.fecha>=? AND m.fecha<? AND m.id_usuario=1
            WHERE p.id_usuario=1 AND p.anio=? AND p.mes=?
            GROUP BY p.id_presupuesto ORDER BY c.nombre''', (start, end, year, month)).fetchall()
        categories = db.execute('SELECT * FROM categorias WHERE id_usuario=1 ORDER BY tipo, nombre').fetchall()
        accounts = db.execute('SELECT * FROM cuentas WHERE id_usuario=1 ORDER BY nombre').fetchall()
    return dict(
        movements=tx, income=values.get('ingreso',0), expense=values.get('gasto',0),
        budgets=budget_rows, categories=categories, accounts=accounts,
        year=year, month=month,
    )
