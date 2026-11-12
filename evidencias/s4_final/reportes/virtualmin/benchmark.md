# Seguimiento 3: mediciones SQLite

- Movimientos en la base de prueba: 100000 (insertados en esta ejecucion: 100000)
- Ejecuciones por operacion: 5; se reporta la mediana en milisegundos
- SQLite 3.45.1, Python 3.12.3, Linux 7.0.0-1014-aws
- Base temporal; las lecturas usan una conexion abierta y los UPDATE se revierten (ROLLBACK)
- Los tiempos dependen del equipo: comparar entre escenarios, no entre maquinas

| Operacion | Escenario | Ejecuciones (ms) | Mediana (ms) |
| --- | --- | --- | --- |
| Movimientos por rango de fecha (1 mes, 100 filas) | con indices | 2.745, 0.641, 0.531, 0.547, 0.481 | 0.547 |
| Total de gasto por categoria en un mes | con indices | 17.760, 16.732, 16.334, 16.964, 16.433 | 16.732 |
| Actualizacion de un gasto por id | con indices | 0.053, 0.017, 0.012, 0.011, 0.011 | 0.012 |
| Movimientos por rango de fecha (1 mes, 100 filas) | sin indices | 18.309, 16.304, 16.458, 16.363, 16.204 | 16.363 |
| Total de gasto por categoria en un mes | sin indices | 18.017, 17.799, 17.936, 18.417, 18.096 | 18.017 |
| Actualizacion de un gasto por id | sin indices | 0.059, 0.014, 0.011, 0.011, 0.011 | 0.011 |

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

