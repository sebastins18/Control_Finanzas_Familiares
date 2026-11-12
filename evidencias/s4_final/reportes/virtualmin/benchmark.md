# Seguimiento 3: mediciones SQLite

- Movimientos en la base de prueba: 100000 (insertados en esta ejecucion: 100000)
- Ejecuciones por operacion: 5; se reporta la mediana en milisegundos
- SQLite 3.45.1, Python 3.12.3, Linux 7.0.0-1014-aws
- Base temporal; las lecturas usan una conexion abierta y los UPDATE se revierten (ROLLBACK)
- Los tiempos dependen del equipo: comparar entre escenarios, no entre maquinas

| Operacion | Escenario | Ejecuciones (ms) | Mediana (ms) |
| --- | --- | --- | --- |
| Movimientos por rango de fecha (1 mes, 100 filas) | con indices | 2.289, 0.522, 0.539, 0.460, 0.501 | 0.522 |
| Total de gasto por categoria en un mes | con indices | 17.668, 17.540, 17.995, 16.723, 16.620 | 17.540 |
| Actualizacion de un gasto por id | con indices | 0.055, 0.028, 0.017, 0.016, 0.015 | 0.017 |
| Movimientos por rango de fecha (1 mes, 100 filas) | sin indices | 18.186, 16.587, 17.829, 17.074, 16.921 | 17.074 |
| Total de gasto por categoria en un mes | sin indices | 17.924, 17.565, 17.372, 17.970, 17.458 | 17.565 |
| Actualizacion de un gasto por id | sin indices | 0.064, 0.014, 0.011, 0.012, 0.011 | 0.012 |

## EXPLAIN QUERY PLAN

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

