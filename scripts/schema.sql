PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
  id_usuario INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  correo TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sesiones (
  id_sesion INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expira_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS monedas (
  id_moneda INTEGER PRIMARY KEY,
  codigo_iso TEXT NOT NULL UNIQUE CHECK(length(codigo_iso) = 3),
  nombre TEXT NOT NULL,
  simbolo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tipos_cambio (
  id_tipo_cambio INTEGER PRIMARY KEY,
  id_moneda_origen INTEGER NOT NULL REFERENCES monedas(id_moneda),
  id_moneda_destino INTEGER NOT NULL REFERENCES monedas(id_moneda),
  fecha TEXT NOT NULL,
  valor_escalado INTEGER NOT NULL CHECK(valor_escalado > 0),
  UNIQUE(id_moneda_origen, id_moneda_destino, fecha),
  CHECK(id_moneda_origen <> id_moneda_destino)
);
CREATE TABLE IF NOT EXISTS categorias (
  id_categoria INTEGER PRIMARY KEY,
  id_usuario INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  nombre TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK(tipo IN ('ingreso','gasto'))
);
CREATE TABLE IF NOT EXISTS cuentas (
  id_cuenta INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda),
  nombre TEXT NOT NULL,
  descripcion TEXT,
  saldo_inicial_centavos INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS presupuestos (
  id_presupuesto INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
  id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda),
  anio INTEGER NOT NULL CHECK(anio BETWEEN 2000 AND 2200),
  mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
  monto_limite_centavos INTEGER NOT NULL CHECK(monto_limite_centavos >= 0),
  UNIQUE(id_usuario,id_categoria,id_moneda,anio,mes)
);
CREATE TABLE IF NOT EXISTS ingresos (
  id_ingreso INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
  id_cuenta_destino INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
  id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
  id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda),
  id_tipo_cambio INTEGER REFERENCES tipos_cambio(id_tipo_cambio),
  monto_centavos INTEGER NOT NULL CHECK(monto_centavos > 0),
  monto_acreditado_centavos INTEGER NOT NULL CHECK(monto_acreditado_centavos > 0),
  fecha TEXT NOT NULL,
  descripcion TEXT
);
CREATE TABLE IF NOT EXISTS gastos (
  id_gasto INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
  id_cuenta_origen INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
  id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
  id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda),
  id_tipo_cambio INTEGER REFERENCES tipos_cambio(id_tipo_cambio),
  monto_centavos INTEGER NOT NULL CHECK(monto_centavos > 0),
  monto_debitado_centavos INTEGER NOT NULL CHECK(monto_debitado_centavos > 0),
  fecha TEXT NOT NULL,
  descripcion TEXT
);
CREATE TABLE IF NOT EXISTS transferencias (
  id_transferencia INTEGER PRIMARY KEY,
  id_cuenta_origen INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
  id_cuenta_destino INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
  id_moneda_origen INTEGER NOT NULL REFERENCES monedas(id_moneda),
  id_moneda_destino INTEGER NOT NULL REFERENCES monedas(id_moneda),
  id_tipo_cambio INTEGER REFERENCES tipos_cambio(id_tipo_cambio),
  monto_origen_centavos INTEGER NOT NULL CHECK(monto_origen_centavos > 0),
  monto_destino_centavos INTEGER NOT NULL CHECK(monto_destino_centavos > 0),
  fecha TEXT NOT NULL,
  CHECK(id_cuenta_origen <> id_cuenta_destino)
);
CREATE TABLE IF NOT EXISTS alertas (
  id_alerta INTEGER PRIMARY KEY,
  id_presupuesto INTEGER NOT NULL REFERENCES presupuestos(id_presupuesto) ON DELETE CASCADE,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
  umbral_porcentaje INTEGER NOT NULL CHECK(umbral_porcentaje BETWEEN 1 AND 100),
  fecha TEXT NOT NULL,
  leida INTEGER NOT NULL DEFAULT 0 CHECK(leida IN (0,1))
);
CREATE TABLE IF NOT EXISTS metas_ahorro (
  id_meta INTEGER PRIMARY KEY,
  id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
  id_moneda INTEGER NOT NULL REFERENCES monedas(id_moneda),
  nombre TEXT NOT NULL,
  monto_objetivo_centavos INTEGER NOT NULL CHECK(monto_objetivo_centavos > 0),
  fecha_objetivo TEXT
);
CREATE TABLE IF NOT EXISTS movimientos_ahorro (
  id_movimiento_ahorro INTEGER PRIMARY KEY,
  id_meta INTEGER NOT NULL REFERENCES metas_ahorro(id_meta) ON DELETE CASCADE,
  id_cuenta INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
  tipo TEXT NOT NULL CHECK(tipo IN ('aporte','retiro')),
  monto_centavos INTEGER NOT NULL CHECK(monto_centavos > 0),
  fecha TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comprobantes (
  id_comprobante INTEGER PRIMARY KEY,
  id_gasto INTEGER NOT NULL REFERENCES gastos(id_gasto) ON DELETE CASCADE,
  ruta_archivo TEXT NOT NULL,
  tipo_mime TEXT NOT NULL,
  fecha_subida TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gastos_usuario_fecha ON gastos(id_usuario,fecha);
CREATE INDEX IF NOT EXISTS idx_gastos_categoria_fecha ON gastos(id_categoria,fecha);
CREATE INDEX IF NOT EXISTS idx_ingresos_usuario_fecha ON ingresos(id_usuario,fecha);
CREATE VIEW IF NOT EXISTS v_gastos_por_categoria AS
  SELECT id_usuario, id_categoria, substr(fecha,1,7) AS periodo,
         SUM(monto_debitado_centavos) AS total_centavos
  FROM gastos GROUP BY id_usuario,id_categoria,substr(fecha,1,7);
