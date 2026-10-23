"""Libro de saldos por cuenta; los movimientos nunca modifican el saldo inicial."""
from decimal import Decimal, ROUND_HALF_UP
from src import db

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
        return [(r['nombre'],r['codigo_iso'],account_balance(c,r['id_cuenta'])) for r in c.execute('SELECT a.*,m.codigo_iso FROM cuentas a JOIN monedas m ON m.id_moneda=a.id_moneda WHERE a.id_usuario=1 ORDER BY a.nombre')]

def conversion(c, origin, destination, amount, date, rate_id=None):
    if origin==destination: return amount
    if not rate_id:
        raise ValueError("Indique el tipo de cambio manual para esta transferencia")
    r=c.execute('SELECT * FROM tipos_cambio WHERE id_tipo_cambio=?',(rate_id,)).fetchone()
    if not r or (r['id_moneda_origen'],r['id_moneda_destino'])!=(origin,destination) or r['fecha']>date:
        raise ValueError('El tipo de cambio no corresponde a las monedas o fecha')
    return int((Decimal(amount)*Decimal(r['valor'])).quantize(Decimal('1'),rounding=ROUND_HALF_UP))


def historical_conversion(c,origin,destination,amount,day):
    if origin==destination: return amount
    rate=c.execute('SELECT valor FROM tipos_cambio WHERE id_moneda_origen=? AND id_moneda_destino=? AND fecha<=? ORDER BY fecha DESC,id_tipo_cambio DESC LIMIT 1',(origin,destination,day)).fetchone()
    if not rate: raise ValueError('Falta tipo de cambio histórico')
    return int((Decimal(amount)*Decimal(rate[0])).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def format_amount(cents,symbol):
    return f'{symbol}{cents/100:,.2f}'
