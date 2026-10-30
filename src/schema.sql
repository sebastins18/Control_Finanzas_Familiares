-- Esquema base actual. src/auth.py migra usuarios de versiones anteriores.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL DEFAULT 'usuario' CHECK(rol IN ('administrador','usuario')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS perfiles_financieros (
    id_perfil INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL CHECK(length(trim(nombre)) BETWEEN 1 AND 100),
    id_propietario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS integrantes_perfil (
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil) ON DELETE CASCADE,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    PRIMARY KEY(id_perfil,id_usuario)
);

CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INTEGER PRIMARY KEY,
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil),
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'gasto')),
    UNIQUE(id_perfil, nombre, tipo)
);

CREATE TABLE IF NOT EXISTS cuentas (
    id_cuenta INTEGER PRIMARY KEY,
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil),
    nombre TEXT NOT NULL,
    saldo_inicial_centimos INTEGER NOT NULL DEFAULT 0,
    UNIQUE(id_perfil, nombre)
);

CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento INTEGER PRIMARY KEY,
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil),
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
    id_perfil INTEGER NOT NULL REFERENCES perfiles_financieros(id_perfil),
    id_categoria INTEGER NOT NULL REFERENCES categorias(id_categoria),
    anio INTEGER NOT NULL CHECK(anio BETWEEN 2000 AND 2100),
    mes INTEGER NOT NULL CHECK(mes BETWEEN 1 AND 12),
    monto_limite_centimos INTEGER NOT NULL CHECK(monto_limite_centimos > 0),
    UNIQUE(id_perfil, id_categoria, anio, mes)
);

CREATE INDEX IF NOT EXISTS idx_movimientos_fecha_tipo ON movimientos(fecha, tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_categoria_fecha ON movimientos(id_categoria, fecha);
CREATE INDEX IF NOT EXISTS idx_presupuestos_periodo ON presupuestos(anio, mes);
