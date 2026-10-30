"""Libro de saldos por cuenta; los movimientos nunca modifican el saldo inicial."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, DecimalException, localcontext
import sqlite3
from contextlib import closing
import time
from src import db

QUOTE_SCHEMA='''CREATE TABLE IF NOT EXISTS tipos_cambio (
    id_tipo_cambio INTEGER PRIMARY KEY,
    id_perfil INTEGER NOT NULL DEFAULT 1 REFERENCES perfiles_financieros(id_perfil),
    id_moneda_base INTEGER NOT NULL REFERENCES monedas(id_moneda),
    id_moneda_cotizada INTEGER NOT NULL REFERENCES monedas(id_moneda),
    fecha TEXT NOT NULL,
    cotizacion TEXT NOT NULL CHECK(CAST(cotizacion AS REAL)>0),
    CHECK(id_moneda_base<>id_moneda_cotizada))'''


def init_quotes():
    """Conserva las cotizaciones históricas exactas y sus identificadores."""
    with closing(sqlite3.connect(db.db_path(),timeout=3)) as c:
        columns={r[1] for r in c.execute('PRAGMA table_info(tipos_cambio)')}
        if 'valor' not in columns:
            c.execute('CREATE INDEX IF NOT EXISTS idx_cotizacion_perfil_fecha ON tipos_cambio(id_perfil,fecha)')
            return
        c.execute('PRAGMA foreign_keys=OFF')
        deadline=time.monotonic()+db.OPERATION_TIMEOUT_SECONDS
        c.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
        try:
            c.execute('BEGIN IMMEDIATE')
            c.execute(QUOTE_SCHEMA.replace('tipos_cambio (','tipos_cambio_nueva (',1))
            c.execute('''INSERT INTO tipos_cambio_nueva
                SELECT id_tipo_cambio,id_perfil,id_moneda_origen,id_moneda_destino,fecha,valor FROM tipos_cambio''')
            c.execute('DROP TABLE tipos_cambio')
            c.execute('ALTER TABLE tipos_cambio_nueva RENAME TO tipos_cambio')
            c.execute('CREATE INDEX idx_cotizacion_perfil_fecha ON tipos_cambio(id_perfil,fecha)')
            if c.execute('PRAGMA foreign_key_check').fetchone():
                raise sqlite3.IntegrityError('Referencias inválidas al migrar cotizaciones')
            c.commit()
        except Exception:
            c.set_progress_handler(None,0)
            c.rollback()
            raise


def quote_pair(c,origin,destination):
    rows=c.execute('SELECT id_moneda,codigo_iso FROM monedas WHERE id_moneda IN (?,?)',(origin,destination)).fetchall()
    if len(rows)!=2: raise ValueError('Las monedas seleccionadas no son válidas.')
    ordered=sorted(rows,key=lambda r:(r['codigo_iso']=='CRC',r['codigo_iso']))
    return ordered[0]['id_moneda'],ordered[1]['id_moneda']


def parse_quote(value):
    raw=str(value).strip()
    if len(raw)>32: raise ValueError('La cotización no es válida.')
    try: quote=Decimal(raw)
    except InvalidOperation: raise ValueError('Ingrese una cotización válida.') from None
    if not quote.is_finite() or quote<Decimal('0.01') or quote>Decimal('1000000000') or quote.as_tuple().exponent < -2:
        raise ValueError('La cotización debe ser positiva, admitir como máximo dos decimales y no superar 1000000000.')
    return format(quote,'.2f')


def apply_quote(quote,origin,destination,amount):
    if {origin,destination}!={quote['id_moneda_base'],quote['id_moneda_cotizada']}:
        raise ValueError('La cotización no corresponde a las monedas seleccionadas.')
    try:
        value=Decimal(quote['cotizacion'])
        if not value.is_finite() or value<=0: raise ValueError('La cotización registrada no es válida.')
        with localcontext() as context:
            context.prec=50
            result=Decimal(amount)*value if origin==quote['id_moneda_base'] else Decimal(amount)/value
            return int(result.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    except DecimalException:
        raise ValueError('No fue posible calcular la conversión con esta cotización.') from None


def quote_label(row):
    base,quoted=row['moneda_base'],row['moneda_cotizada']
    value=Decimal(row['cotizacion'])
    symbol='='
    if base=='CRC' or (quoted!='CRC' and base>quoted):
        with localcontext() as context:
            context.prec=50
            shown=(Decimal(1)/value).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
            if shown*value!=1: symbol='≈'
        base,quoted=quoted,base
    else:
        shown=value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        if shown!=value: symbol='≈'
    return f"1 {base} {symbol} {format(shown,'.2f').replace('.',',')} {quoted}"

def account_balance(c, account_id):
    row=c.execute('SELECT saldo_inicial_centimos FROM cuentas WHERE id_cuenta=?',(account_id,)).fetchone()
    if not row: raise ValueError('Cuenta inexistente')
    balance=row[0]
    balance+=c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN COALESCE(monto_acreditado_centimos,monto_centimos) ELSE -COALESCE(monto_acreditado_centimos,monto_centimos) END),0) FROM movimientos WHERE id_cuenta=?",(account_id,)).fetchone()[0]
    balance+=c.execute('SELECT COALESCE(SUM(monto_destino_centimos),0) FROM transferencias WHERE id_cuenta_destino=?',(account_id,)).fetchone()[0]
    balance-=c.execute('SELECT COALESCE(SUM(monto_origen_centimos),0) FROM transferencias WHERE id_cuenta_origen=?',(account_id,)).fetchone()[0]
    balance+=c.execute("SELECT COALESCE(SUM(CASE WHEN tipo='retiro' THEN monto_centimos ELSE -monto_centimos END),0) FROM movimientos_ahorro WHERE id_cuenta=?",(account_id,)).fetchone()[0]
    return balance

def all_balances():
    with db.connect() as c:
        return [(r['nombre'],r['codigo_iso'],account_balance(c,r['id_cuenta'])) for r in c.execute('SELECT a.*,m.codigo_iso FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda WHERE a.id_perfil=current_profile_id() ORDER BY a.nombre')]

def conversion(c, origin, destination, amount, date, rate_id=None):
    if origin==destination: return amount
    if not rate_id:
        raise ValueError('Indique la cotización para esta transferencia')
    r=c.execute('SELECT * FROM tipos_cambio WHERE id_perfil=current_profile_id() AND id_tipo_cambio=?',(rate_id,)).fetchone()
    if not r or r['fecha']>date:
        raise ValueError('El tipo de cambio no corresponde a las monedas o fecha')
    return apply_quote(r,origin,destination,amount)


def historical_conversion(c,origin,destination,amount,day):
    if origin==destination: return amount
    rate=c.execute('''SELECT * FROM tipos_cambio WHERE id_perfil=current_profile_id() AND
        ((id_moneda_base=? AND id_moneda_cotizada=?) OR (id_moneda_base=? AND id_moneda_cotizada=?))
        AND fecha<=? ORDER BY fecha DESC,id_tipo_cambio DESC LIMIT 1''',(origin,destination,destination,origin,day)).fetchone()
    if not rate: raise ValueError('Falta tipo de cambio histórico')
    return apply_quote(rate,origin,destination,amount)

def format_amount(cents,symbol):
    return f'{symbol}{cents/100:,.2f}'
