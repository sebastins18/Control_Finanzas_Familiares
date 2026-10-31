# Seguimiento 3: mediciones SQLite

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

