-- Control de Finanzas Familiares | Modelo MVP v1 (subconjunto deliberado del diagrama v4).
-- Para este MVP se trabaja en CRC y con un único perfil de demostración local.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'gasto')),
    UNIQUE(id_usuario, nombre, tipo)
);

CREATE TABLE IF NOT EXISTS cuentas (
    id_cuenta INTEGER PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    nombre TEXT NOT NULL,
    saldo_inicial_centimos INTEGER NOT NULL DEFAULT 0,
    UNIQUE(id_usuario, nombre)
);

CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento INTEGER PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_cuenta INTEGER NOT NULL REFERENCES cuentas(id_cuenta),
    id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
    tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'gasto')),
    monto_centimos INTEGER NOT NULL CHECK(monto_centimos > 0),
    fecha TEXT NOT NULL CHECK(length(fecha) = 10),
    descripcion TEXT NOT NULL DEFAULT '',
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS presupuestos (
    id_presupuesto INTEGER PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
    anio INTEGER NOT NULL CHECK(anio BETWEEN 2000 AND 2100),
    mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
    monto_limite_centimos INTEGER NOT NULL CHECK(monto_limite_centimos > 0),
    UNIQUE(id_usuario, id_categoria, anio, mes)
);

CREATE INDEX IF NOT EXISTS idx_movimientos_fecha_tipo ON movimientos(fecha, tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_categoria_fecha ON movimientos(id_categoria, fecha);
CREATE INDEX IF NOT EXISTS idx_presupuestos_periodo ON presupuestos(anio, mes);
