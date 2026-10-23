> **Aviso de versión:** lo siguiente describe el estado S1. El módulo V17 agrega tablas y cambia la arquitectura operativa. Consultar [`docs/arquitectura/modelo-v17.md`](arquitectura/modelo-v17.md) para el modelo integrado.

# Modelo de datos SQLite — MVP implementado (S1)

La **fuente de verdad** del modelo implementado es `src/schema.sql`. `src/db.py` trabaja exclusivamente con estas cinco tablas:

| Tabla | Propósito |
| --- | --- |
| `usuarios` | Hogar ficticio de demostración, identificado como usuario 1 |
| `categorias` | Clasificación de ingresos y gastos |
| `cuentas` | Cuentas de la familia y saldo inicial |
| `movimientos` | Ingresos o gastos, monto, cuenta, categoría y fecha |
| `presupuestos` | Límite mensual por categoría |

## Relaciones y restricciones

- `categorias.id_usuario` y `cuentas.id_usuario` → `usuarios.id_usuario`.
- `movimientos` → `usuarios`, `cuentas` y `categorias`.
- `presupuestos` → `usuarios` y `categorias`.
- `tipo` de categorías y movimientos: `ingreso` o `gasto`.
- Los montos en `movimientos` y los límites en `presupuestos` se guardan como **enteros de centavos**, con validación de valores positivos.
- Índices principales: `idx_movimientos_fecha_tipo`, `idx_movimientos_categoria_fecha` e `idx_presupuestos_periodo`.
- `PRAGMA foreign_keys=ON` en cada conexión y modo WAL al inicializar.

## Modelo ampliado: solo propuesta

El diagrama v4 de la presentación propone **monedas, tipos de cambio, ingresos y gastos separados, transferencias, metas de ahorro, alertas, sesiones y comprobantes**, pero esas tablas NO forman parte de la base que utiliza el MVP S1.

El archivo `scripts/schema.sql` conserva ese diseño ampliado para discusión futura: **no utilizarlo con la aplicación actual**, porque la estructura no coincide con `src/db.py`.

Véase el [diagrama real de cinco tablas](arquitectura/modelo_er.md) y [arquitectura](arquitectura/README.md).
