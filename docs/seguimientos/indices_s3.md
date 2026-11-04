# Seguimiento 3 — Evaluación local del índice SQLite

- Python: 3.15.0; SQLite: 3.53.4.
- Plataforma: Windows-11-10.0.26200-SP0.
- Movimientos: 10000; diez categorías de gasto; filas recuperadas: 273.
- Solo SQLite temporal creado con tempfile; no se abre la base real del proyecto.
- Esquema leído de src/schema.sql; datos sintéticos deterministas con claves foráneas válidas.
- Dos copias temporales mediante SQLite backup; solo se elimina el índice evaluado en una copia.
- Los demás índices explícitos se conservan y se comprueba su igualdad.
- Configuración común verificada: {'journal_mode': 'delete', 'synchronous': 2, 'cache_size': -2048, 'temp_store': 2, 'automatic_index': 0}.
- No se activa WAL ni se ejecuta ANALYZE; se usa el esquema base, no db.init_db().

## Consulta idéntica en ambos escenarios

```sql
SELECT id_movimiento, fecha, monto_centimos, descripcion
FROM movimientos
WHERE id_perfil = ? AND id_categoria = ? AND fecha BETWEEN ? AND ?
ORDER BY fecha, id_movimiento
```

Parámetros: `(1, 3, '2026-04-01', '2026-06-30')`.

## EXPLAIN QUERY PLAN

### Con índice

```text
(4, 0, 49, 'SEARCH movimientos USING INDEX idx_movimientos_categoria_fecha (id_categoria=? AND fecha>? AND fecha<?)')
```

### Sin índice

```text
(4, 0, 165, 'SEARCH movimientos USING INDEX idx_movimientos_fecha_tipo (fecha>? AND fecha<?)')
(32, 0, 0, 'USE TEMP B-TREE FOR LAST TERM OF ORDER BY')
```

## Tiempos reales

Diez ejecuciones por escenario con time.perf_counter y statistics.median, en milisegundos.
Se mide execute + fetchall, incluida preparación SQL; cached_statements=0 en ambas conexiones.
Preparación, planes y validaciones quedan fuera del intervalo cronometrado.

| Repetición | Con índice (ms) | Sin índice (ms) |
| --- | ---: | ---: |
| 1 | 0.221200 | 0.557900 |
| 2 | 0.258500 | 0.449700 |
| 3 | 0.296300 | 0.475100 |
| 4 | 0.246900 | 0.474200 |
| 5 | 0.251000 | 0.443600 |
| 6 | 0.228000 | 0.434400 |
| 7 | 0.221000 | 0.431400 |
| 8 | 0.224700 | 0.438000 |
| 9 | 0.221100 | 0.426100 |
| 10 | 0.225800 | 0.429800 |
| Mediana | 0.226900 | 0.440800 |

La mediana con índice fue menor en esta ejecución local (48.53 % respecto de la mediana sin índice). Esto muestra una reducción observada en esta muestra, sin demostrar significancia estadística ni una mejora general para otras cargas.

## Condiciones, validaciones y limitaciones

- Mismos datos por copia de base, consulta, parámetros, configuración y número de lecturas.
- Dos lecturas explícitas de calentamiento por escenario, además de la lectura de validación previa.
- Orden alternado por ronda: con/sin, sin/con; sin escrituras durante las mediciones.
- Cachés de SQLite y del sistema operativo no se vacían. No es una comparación en frío;
  el calentamiento y la alternancia reducen algunos sesgos, pero no los eliminan.
- Diez muestras, una única ejecución local, un tamaño y una distribución sintética no representan
  toda carga real ni permiten asegurar significancia estadística. Influyen equipo, disco y otros procesos.
- La estructura física cambia al eliminar el índice; las dos bases son equivalentes en datos, no en tamaño.
- Los planes reflejan la elección del optimizador; no se fuerza un índice ni se eliminan los demás.
- Se verifican resultados idénticos y no vacíos en cada lectura medida, conteos estables,
  foreign_keys=ON, foreign_key_check sin violaciones e integrity_check=ok antes y después.
- No mide inserciones, coste de mantener índices, respuesta web ni Virtualmin; tampoco compara otros motores.
- No se extrapola el resultado a los otros índices del esquema. Las bases temporales se eliminan al finalizar.

## Ejecución desde PowerShell

```powershell
py -3 scripts/indices_s3.py
```

La evidencia se crea exclusivamente si no existe; el script rechaza sobrescribirla.
