"""Movimientos recurrentes (salario, alquiler...): plantillas por perfil y generación idempotente.

Las plantillas se administran con el mantenimiento genérico de `extension.CONFIG`.
La generación nunca es automática: la persona pulsa «Generar pendientes», en la línea de D-010
(sin escrituras implícitas). Cada ocurrencia se registra en `recurrentes_generados`, cuya clave
primaria (id_recurrente, periodo) garantiza en la propia base que un mes no se genera dos veces.
Si se elimina el movimiento generado, su periodo queda marcado y no se vuelve a crear.
"""
from __future__ import annotations

from datetime import date

from src import db

SCHEMA = '''
CREATE TABLE IF NOT EXISTS movimientos_recurrentes (
    id_recurrente INTEGER PRIMARY KEY,
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil),
    id_cuenta INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
    id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
    tipo TEXT NOT NULL CHECK(tipo IN ('ingreso','gasto')),
    monto_centimos INTEGER NOT NULL CHECK(monto_centimos > 0),
    descripcion TEXT NOT NULL DEFAULT '',
    dia_mes INTEGER NOT NULL CHECK(dia_mes BETWEEN 1 AND 28),
    fecha_inicio TEXT NOT NULL CHECK(length(fecha_inicio) = 10),
    activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
);
CREATE TABLE IF NOT EXISTS recurrentes_generados (
    id_recurrente INTEGER NOT NULL REFERENCES movimientos_recurrentes(id_recurrente) ON DELETE CASCADE,
    periodo TEXT NOT NULL CHECK(length(periodo) = 7),
    id_movimiento INTEGER REFERENCES movimientos(id_movimiento) ON DELETE SET NULL,
    PRIMARY KEY (id_recurrente, periodo)
);
CREATE INDEX IF NOT EXISTS idx_recurrentes_perfil ON movimientos_recurrentes(id_perfil, activo);
'''

# Tope por ejecución para quedar dentro del límite de 8 s de db.connect(); se puede volver a pulsar.
MAX_PER_RUN = 500


def _months(start: date, today: date):
    year, month = start.year, start.month
    while (year, month) <= (today.year, today.month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def pending(c, today: date | None = None) -> list:
    """Ocurrencias vencidas (fecha <= hoy) que aún no se generaron, para el perfil activo."""
    today = today or date.today()
    templates = c.execute('''SELECT * FROM movimientos_recurrentes
        WHERE id_perfil = current_profile_id() AND activo = 1 ORDER BY id_recurrente''').fetchall()
    result = []
    for t in templates:
        start = date.fromisoformat(t['fecha_inicio'])
        done = {r[0] for r in c.execute('SELECT periodo FROM recurrentes_generados WHERE id_recurrente = ?',
                                        (t['id_recurrente'],))}
        for year, month in _months(start, today):
            day = date(year, month, t['dia_mes'])
            period = f'{year:04d}-{month:02d}'
            if start <= day <= today and period not in done:
                result.append((t, period, day))
    return result


def pending_count() -> int:
    with db.connect() as c:
        return len(pending(c))


def generate(today: date | None = None) -> tuple[int, int]:
    """Crea los movimientos pendientes en una sola transacción. Devuelve (creados, restantes)."""
    from src.profiles import require_write
    with db.connect() as c:
        require_write(c, 'movimientos')
        items = pending(c, today)
        created = 0
        for template, period, day in items[:MAX_PER_RUN]:
            claimed = c.execute('INSERT OR IGNORE INTO recurrentes_generados(id_recurrente, periodo) VALUES (?, ?)',
                                (template['id_recurrente'], period)).rowcount
            if claimed != 1:   # otra solicitud lo generó en paralelo
                continue
            try:
                db.validate_category_account(c, template['id_categoria'], template['id_cuenta'], template['tipo'])
            except ValueError:
                raise ValueError(f'La plantilla «{template["descripcion"]}» usa una cuenta o categoría que ya no es válida. '
                                 'Corríjala o desactívela y vuelva a intentarlo.') from None
            movement_id = c.execute('''INSERT INTO movimientos
                (id_perfil, id_cuenta, id_categoria, tipo, monto_centimos, fecha, descripcion, monto_acreditado_centimos)
                VALUES (current_profile_id(), ?, ?, ?, ?, ?, ?, ?)''',
                (template['id_cuenta'], template['id_categoria'], template['tipo'], template['monto_centimos'],
                 day.isoformat(), template['descripcion'], template['monto_centimos'])).lastrowid
            c.execute('UPDATE recurrentes_generados SET id_movimiento = ? WHERE id_recurrente = ? AND periodo = ?',
                      (movement_id, template['id_recurrente'], period))
            created += 1
    return created, max(0, len(items) - MAX_PER_RUN)


def panel_html(can_generate: bool) -> str:
    count = pending_count()
    if not can_generate:
        return ''
    if not count:
        return '<p class="help">No hay movimientos recurrentes pendientes de generar hasta hoy.</p>'
    return (f'<div class="notice-strip"><span><strong>{count}</strong> movimiento{"s" if count != 1 else ""} '
            f'recurrente{"s" if count != 1 else ""} pendiente{"s" if count != 1 else ""} hasta hoy.</span>'
            '<form method="post" action="/recurrentes/generar"><button class="btn btn-primary btn-sm" type="submit">Generar pendientes</button></form></div>')
