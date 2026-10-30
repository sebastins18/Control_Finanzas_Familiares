"""Persistencia SQLite: sin servicios externos, datos sintéticos y operaciones parametrizadas."""
from __future__ import annotations

import os
import sqlite3
import time
import sys
import traceback
from contextlib import contextmanager, closing
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / 'src' / 'schema.sql'
DEFAULT_DB = ROOT / 'data' / 'finanzas.sqlite3'
BUSY_TIMEOUT_MS = 3000
OPERATION_TIMEOUT_SECONDS = 8


@contextmanager
def cli_errors():
    """Evita trazas sin controlar al ejecutar herramientas desde la terminal."""
    try:
        yield
    except Exception:
        try:
            logs = db_path().parent / 'logs'
            logs.mkdir(parents=True, exist_ok=True)
            from logging.handlers import RotatingFileHandler
            import logging
            handler = RotatingFileHandler(logs / 'errores_scripts.log', maxBytes=2_000_000,
                                          backupCount=3, encoding='utf-8')
            try:
                handler.emit(logging.LogRecord('finanzas.scripts', logging.ERROR, __file__, 0,
                    traceback.format_exc(), (), None))
            finally:
                handler.close()
        except OSError:
            pass
        print('No se pudo completar la operación. Revise los datos, el acceso a SQLite y el registro de errores antes de intentarlo nuevamente.', file=sys.stderr)
        raise SystemExit(1) from None


def db_path() -> Path:
    configured = os.environ.get('DB_PATH')
    path = Path(configured).expanduser() if configured else DEFAULT_DB
    return path.resolve()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Contexto transaccional que también cierra la conexión al finalizar."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_MS / 1000)
    try:
        from src.request_ctx import user_id, profile_id
        connection.create_function('current_user_id', 0, user_id)
        connection.create_function('current_profile_id', 0, profile_id)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute(f'PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}')
        deadline = time.monotonic() + OPERATION_TIMEOUT_SECONDS
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        with connection:
            yield connection
    finally:
        connection.set_progress_handler(None, 0)
        connection.close()


def init_db() -> None:
    path = db_path()
    if path.exists():
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source:
            columns = {r[1] for r in source.execute('PRAGMA table_info(usuarios)')}
            financial_columns={r[1] for r in source.execute('PRAGMA table_info(cuentas)')}
            rate_columns={r[1] for r in source.execute('PRAGMA table_info(tipos_cambio)')}
            if columns and ('username' not in columns or 'id_rol' in columns or 'id_usuario' in financial_columns or 'valor' in rate_columns):
                backup = path.with_name(path.stem + '.antes-usuarios-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
                with closing(sqlite3.connect(backup)) as destination:
                    deadline = time.monotonic() + OPERATION_TIMEOUT_SECONDS
                    def backup_progress(status, remaining, total):
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Tiempo de respaldo agotado')
                    source.backup(destination, pages=128, progress=backup_progress, sleep=0.05)
    with connect() as connection:
        connection.execute('PRAGMA journal_mode = WAL')
        connection.executescript(SCHEMA.read_text(encoding='utf-8'))
        from src import auth
        auth.init(connection)
    from src import extension, profiles
    extension.init()
    profiles.init()
    from src.finance import init_quotes
    init_quotes()


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
            db.execute('SELECT * FROM categorias WHERE id_perfil=current_profile_id() ORDER BY tipo, nombre').fetchall(),
            db.execute('SELECT * FROM cuentas WHERE id_perfil=current_profile_id() ORDER BY nombre').fetchall(),
        )


def validate_category_account(db: sqlite3.Connection, category_id: int, account_id: int, kind: str) -> None:
    category = db.execute(
        'SELECT 1 FROM categorias WHERE id_categoria = ? AND id_perfil=current_profile_id() AND tipo = ?',
        (category_id, kind),
    ).fetchone()
    account = db.execute(
        'SELECT 1 FROM cuentas WHERE id_cuenta = ? AND id_perfil=current_profile_id()',
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
        from src.profiles import require_write
        require_write(db,'movimientos',editing=movement_id is not None)
        validate_category_account(db, category_id, account_id, kind)
        from src.finance import account_balance
        credited = amount_cents
        old=db.execute('SELECT * FROM movimientos WHERE id_movimiento=? AND id_perfil=current_profile_id()',(movement_id,)).fetchone() if movement_id else None
        available=account_balance(db,account_id)
        if old and old['id_cuenta']==account_id:
            available-= (1 if old['tipo']=='ingreso' else -1)*(old['monto_acreditado_centimos'] if old['monto_acreditado_centimos'] is not None else old['monto_centimos'])
        args = (account_id, category_id, kind, amount_cents, valid_date, description,credited)
        if movement_id is None:
            db.execute(
                '''INSERT INTO movimientos
                (id_perfil, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion,monto_acreditado_centimos)
                VALUES (current_profile_id(), ?, ?, ?, ?, ?, ?, ?)''', args,
            )
        else:
            cursor = db.execute(
                '''UPDATE movimientos SET id_cuenta=?, id_categoria=?, tipo=?,
                   monto_centimos=?, fecha=?, descripcion=?,monto_acreditado_centimos=?
                   WHERE id_movimiento=? AND id_perfil=current_profile_id()''', (*args, movement_id),
            )
            if cursor.rowcount != 1:
                raise ValueError('No se encontró el movimiento.')


def remove_movement(movement_id: int) -> None:
    with connect() as db:
        from src.profiles import require_write
        require_write(db,'movimientos',editing=True)
        db.execute('DELETE FROM movimientos WHERE id_movimiento=? AND id_perfil=current_profile_id()', (movement_id,))


def get_movement(movement_id: int) -> sqlite3.Row | None:
    with connect() as db:
        return db.execute(
            'SELECT * FROM movimientos WHERE id_movimiento=? AND id_perfil=current_profile_id()',
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
    moneda=int(form.get('id_moneda') or 0)
    if not (2020 <= year <= 2100 and 1 <= month <= 12):
        raise ValueError('Período fuera de rango.')
    with connect() as db:
        from src.profiles import require_write
        require_write(db,'presupuestos')
        allowed = db.execute(
            "SELECT 1 FROM categorias WHERE id_categoria=? AND id_perfil=current_profile_id() AND tipo='gasto'",
            (category_id,),
        ).fetchone()
        if not allowed:
            raise ValueError('Solo se permiten presupuestos para categorías de gastos.')
        db.execute(
            '''INSERT INTO presupuestos (id_perfil, id_categoria, anio, mes, monto_limite_centimos,id_moneda)
            VALUES (current_profile_id(), ?, ?, ?, ?, ?)
            ON CONFLICT (id_perfil, id_categoria, anio, mes)
            DO UPDATE SET monto_limite_centimos=excluded.monto_limite_centimos,id_moneda=excluded.id_moneda''',
            (category_id, year, month, amount_cents,moneda or db.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]),
        )


def dashboard(year: int, month: int) -> dict:
    start, end = f'{year:04d}-{month:02d}-01', (f'{year+1:04d}-01-01' if month == 12 else f'{year:04d}-{month+1:02d}-01')
    with connect() as db:
        tx = db.execute('''SELECT m.*, c.nombre AS categoria, a.nombre AS cuenta
            FROM movimientos m JOIN categorias c ON c.id_categoria=m.id_categoria
            JOIN cuentas a ON a.id_cuenta=m.id_cuenta
            WHERE m.id_perfil=current_profile_id() AND m.fecha>=? AND m.fecha<?
            ORDER BY m.fecha DESC, m.id_movimiento DESC LIMIT 100''', (start, end)).fetchall()
        sums = db.execute('''SELECT m.tipo, mo.codigo_iso, COALESCE(SUM(m.monto_centimos),0) AS total
            FROM movimientos m JOIN cuentas a ON a.id_cuenta=m.id_cuenta
            JOIN monedas mo ON mo.id_moneda=a.id_moneda
            WHERE m.id_perfil=current_profile_id() AND m.fecha>=? AND m.fecha<?
            GROUP BY m.tipo,mo.codigo_iso''', (start,end)).fetchall()
        totals_by_currency = {}
        for r in sums:
            totals_by_currency.setdefault(r['codigo_iso'], {'ingreso':0,'gasto':0})[r['tipo']] = r['total']
        values = {'ingreso': totals_by_currency.get('CRC',{}).get('ingreso',0),
                  'gasto': totals_by_currency.get('CRC',{}).get('gasto',0)}
        raw_budgets=db.execute("""SELECT p.*,c.nombre AS categoria,mo.simbolo FROM presupuestos p
            JOIN categorias c ON c.id_categoria=p.id_categoria JOIN monedas mo ON mo.id_moneda=p.id_moneda
            WHERE p.id_perfil=current_profile_id() AND p.anio=? AND p.mes=? ORDER BY c.nombre""",(year,month)).fetchall()
        from src.finance import historical_conversion
        crc=db.execute("SELECT id_moneda FROM monedas WHERE codigo_iso='CRC'").fetchone()[0]
        budget_rows=[]
        for b in raw_budgets:
            moves=db.execute("SELECT m.monto_centimos,m.fecha,a.id_moneda FROM movimientos m JOIN cuentas a ON a.id_cuenta=m.id_cuenta WHERE m.id_perfil=current_profile_id() AND m.id_categoria=? AND m.tipo='gasto' AND m.fecha>=? AND m.fecha<?",(b['id_categoria'],start,end)).fetchall()
            spent=0
            missing=0
            for m in moves:
                try: spent+=historical_conversion(db,m['id_moneda'],b['id_moneda'],m['monto_centimos'],m['fecha'])
                except ValueError: missing+=1
            budget_rows.append(dict(categoria=b['categoria'],limite=b['monto_limite_centimos'],gastado=spent,simbolo=b['simbolo'],missing=missing))
        categories = db.execute('SELECT * FROM categorias WHERE id_perfil=current_profile_id() ORDER BY tipo, nombre').fetchall()
        accounts = db.execute('SELECT * FROM cuentas WHERE id_perfil=current_profile_id() ORDER BY nombre').fetchall()
    return dict(
        movements=tx, income=values.get('ingreso',0), expense=values.get('gasto',0),
        budgets=budget_rows, categories=categories, accounts=accounts, totals_by_currency=totals_by_currency,
        year=year, month=month,
    )
