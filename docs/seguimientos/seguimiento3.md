# Seguimiento 3 — Evidencia consolidada

Este archivo reemplaza los `.txt` de resultados generados durante la sesión de trabajo. Resume cada ejecución; la salida cruda (con el registro HTTP de los tests) no se conservó. Bitácora y estado de la rúbrica: `docs/seguimientos/S3.md`. Decisiones: `docs/decisiones.md` (D-006 a D-010).

## 1. Resultados de las pruebas (un archivo por proceso)

Cada archivo se ejecutó por separado con `py -m unittest tests.<nombre>`. La columna «Ejecutado» es la fecha de modificación del resultado original: los archivos antiguos no se volvieron a ejecutar tras cada cambio posterior.

### Pruebas del seguimiento 3 y manejo de fallos

| Archivo | Tests | Resultado | Duración (s) | Ejecutado |
| --- | --- | --- | --- | --- |
| `test_error_handling.py` | 8 | OK | 7.198 | 30/10/2026 15:58 |
| `test_read_cache.py` | 3 | OK | 2.664 | 30/10/2026 15:58 |
| `test_s3_benchmark_smoke.py` | 2 | OK | 0.295 | 30/10/2026 15:58 |
| `test_s3_connection_errors.py` | 3 | OK | 2.642 | 30/10/2026 15:58 |
| `test_s3_invalid_data.py` | 4 | OK | 3.598 | 30/10/2026 15:58 |
| `test_s3_normal.py` | 1 | OK | 1.022 | 30/10/2026 15:58 |
| `test_sqlite_failure_v16.py` | 1 | OK | 0.540 | 30/10/2026 15:58 |

### Resto de la suite (regresión)

| Archivo | Tests | Resultado | Duración (s) | Ejecutado |
| --- | --- | --- | --- | --- |
| `test_auth_sqlite.py` | 4 | OK | 3.854 | 30/10/2026 15:18 |
| `test_basepath_v17.py` | 1 | OK | 0.876 | 30/10/2026 15:42 |
| `test_bulk_seed_s2.py` | 2 | OK | 0.265 | 30/10/2026 15:18 |
| `test_connection.py` | 2 | OK | 0.472 | 30/10/2026 15:18 |
| `test_features_v4.py` | 3 | OK | 0.786 | 30/10/2026 15:18 |
| `test_fx_quotes.py` | 7 | OK | 1.645 | 30/10/2026 15:18 |
| `test_http_crud_s2.py` | 4 | OK | 4.293 | 30/10/2026 15:18 |
| `test_lazy_fx_v8.py` | 3 | OK | 0.733 | 30/10/2026 15:18 |
| `test_multicurrency_v7.py` | 3 | OK | 0.738 | 30/10/2026 15:18 |
| `test_profiles.py` | 10 | OK | 15.503 | 30/10/2026 15:19 |
| `test_registration.py` | 7 | OK | 6.186 | 30/10/2026 15:19 |
| `test_smoke.py` | 8 | OK | 3.242 | 30/10/2026 15:42 |

**Total: 76 tests en 19 archivos; sin resultado OK: ninguno.**

Nota: la suma incluye `test_read_cache` y los 4 archivos `test_s3_*`. La cifra de 63 tests citada en una ejecución anterior era previa a esos archivos.

## 2. Mediciones de SQLite (100 000 movimientos, 5 ejecuciones, mediana)

Salida original de `python -m scripts.benchmark_s3 --count 100000 --runs 5`. El mismo informe está en `docs/seguimientos/S3_mediciones.md`.

## Seguimiento 3: mediciones SQLite

- Movimientos en la base de prueba: 100000 (insertados en esta ejecucion: 100000)
- Ejecuciones por operacion: 5; se reporta la mediana en milisegundos
- SQLite 3.42.0, Python 3.12.0, Windows 11
- Base temporal; las lecturas usan una conexion abierta y los UPDATE se revierten (ROLLBACK)
- Los tiempos dependen del equipo: comparar entre escenarios, no entre maquinas

| Operacion | Escenario | Ejecuciones (ms) | Mediana (ms) |
| --- | --- | --- | --- |
| Movimientos por rango de fecha (1 mes, 100 filas) | con indices | 2.199, 0.333, 0.288, 0.268, 0.265 | 0.288 |
| Total de gasto por categoria en un mes | con indices | 18.899, 17.472, 17.854, 18.303, 17.007 | 17.854 |
| Actualizacion de un gasto por id | con indices | 0.040, 0.014, 0.011, 0.010, 0.010 | 0.011 |
| Movimientos por rango de fecha (1 mes, 100 filas) | sin indices | 12.548, 11.318, 11.049, 11.394, 11.344 | 11.344 |
| Total de gasto por categoria en un mes | sin indices | 11.478, 11.301, 11.311, 11.400, 11.349 | 11.349 |
| Actualizacion de un gasto por id | sin indices | 0.042, 0.017, 0.012, 0.011, 0.010 | 0.012 |

### EXPLAIN QUERY PLAN

**Movimientos por rango de fecha (1 mes, 100 filas) (con indices)**
- `SEARCH m USING INDEX idx_movimientos_fecha_tipo (fecha>? AND fecha<?)`
- `SEARCH c USING INTEGER PRIMARY KEY (rowid=?)`
- `USE TEMP B-TREE FOR RIGHT PART OF ORDER BY`

**Total de gasto por categoria en un mes (con indices)**
- `SEARCH movimientos USING INDEX idx_movimientos_fecha_tipo (fecha>? AND fecha<?)`
- `USE TEMP B-TREE FOR GROUP BY`

**Actualizacion de un gasto por id (con indices)**
- `SEARCH movimientos USING INTEGER PRIMARY KEY (rowid=?)`

**Movimientos por rango de fecha (1 mes, 100 filas) (sin indices)**
- `SCAN m`
- `SEARCH c USING INTEGER PRIMARY KEY (rowid=?)`
- `USE TEMP B-TREE FOR ORDER BY`

**Total de gasto por categoria en un mes (sin indices)**
- `SCAN movimientos`
- `USE TEMP B-TREE FOR GROUP BY`

**Actualizacion de un gasto por id (sin indices)**
- `SEARCH movimientos USING INTEGER PRIMARY KEY (rowid=?)`


## 3. Pendiente (no hecho)

- Medir WAL frente a `DELETE` (segunda evidencia de profundidad que pide D-001).
- Probar un índice cubriente para el total por categoría, que fue más lento con índices.
- Ruta `/calidad` solo para administradores que muestre estos resultados (solo lectura).
- Ejecutar la suite y el benchmark en el servidor Linux (todo se midió en Windows).
- Crear el tag `v0.3.0` (lo decide el equipo).
