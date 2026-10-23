# Modelo de datos — extensión V17 (Seguimiento 2)

**Un motor único: SQLite.** No se incorporó PostgreSQL, Redis ni MongoDB. La aplicación usa `src/schema.sql` para las cinco tablas originales y `src/extension.py` para el esquema ampliado. `scripts/schema.sql` es un boceto conceptual y **no debe ejecutarse como migración**.

| Origen | Tabla | Propósito |
| --- | --- | --- |
| `src/schema.sql` | `usuarios` | Hogares/perfiles locales de demostración |
| `src/schema.sql` | `categorias` | Clasificación de ingresos y gastos |
| `src/schema.sql` | `cuentas` | Cuenta, saldo inicial y divisa (extensión V17) |
| `src/schema.sql` | `movimientos` | Ingresos/gastos con cuenta y categoría |
| `src/schema.sql` | `presupuestos` | Tope por categoría, período y divisa (extensión V17) |
| `src/extension.py` | `monedas` | Catálogo CRC, USD, EUR |
| `src/extension.py` | `tipos_cambio` | Tasas introducidas para conversiones entre divisas |
| `src/extension.py` | `metas_ahorro` | Objetivos por familia y moneda |
| `src/extension.py` | `transferencias` | Origen/destino, importes y tasa opcional |
| `src/extension.py` | `movimientos_ahorro` | Aportes y retiros de metas |
| `src/extension.py` | `alertas` | Umbrales y estado de lectura |
| `src/extension.py` | `comprobantes` | Metadatos de archivos asociados a movimientos |
| `src/extension.py` | `app_config` | Identificador del perfil local seleccionado |

Se conservó la tabla unificada `movimientos`; `ingresos` y `gastos` son valores del campo `tipo`, no dos tablas físicas distintas. El inicio de sesión está implementado por `src/app.py` con un archivo JSON de credenciales local fuera de Git, **no** por la tabla de sesiones del modelo conceptual v4.

## Profundidad SQLite

- WAL: `PRAGMA journal_mode=WAL` habilitado durante `db.init_db()`.
- Integridad: claves foráneas, restricciones CHECK, transacciones y montos en centavos enteros.
- Índices iniciales: `idx_movimientos_fecha_tipo`, `idx_movimientos_categoria_fecha` e `idx_presupuestos_periodo`.
- S2: script reproducible de carga masiva en una transacción (`scripts/seed_bulk_s2.py`).
- **Pendiente S3:** comparar consultas con y sin índices mediante `EXPLAIN QUERY PLAN` y recopilar tiempos de al menos tres operaciones, con tres repeticiones por operación y mediana.

**Limitaciones:** los perfiles locales no proporcionan separación de datos equivalente a seguridad multiusuario, las modificaciones antiguas del esquema se realizan mediante lógica de extensión, y el programa es para uso académico/local. No usar datos financieros reales ni exponer sus archivos en `public_html`.
