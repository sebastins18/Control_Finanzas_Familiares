# Seguimiento 3: medición local con SQLite

- Python: 3.15.0
- SQLite: 3.53.4
- Plataforma: Windows-11-10.0.26200-SP0
- Movimientos antes de medir: 1000; al finalizar: 1005.
- Período inclusivo: 2026-01-01 a 2026-12-31; categoría de gasto: 1.
- Base temporal creada con tempfile y eliminada al finalizar.
- Esquema e índices originales de src/schema.sql; datos sintéticos.
- Cinco repeticiones por operación, time.perf_counter y statistics.median.
- Inserción: incluye INSERT y commit; consultas: incluyen lectura de resultados.
- Orden: inserciones, consulta por categoría, suma; sin reiniciar la caché.
- Preparación y validaciones fuera de los intervalos medidos.
- Medición local; los tiempos dependen del equipo, disco y caché.

| Operación | 1 (ms) | 2 (ms) | 3 (ms) | 4 (ms) | 5 (ms) | Mediana (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Insertar gasto y confirmar transacción | 1.810000 | 1.737800 | 2.412100 | 2.459300 | 2.401600 | 2.401600 |
| Consultar por categoría y rango de fechas (fetchall) | 1.379600 | 1.311200 | 1.135100 | 1.098900 | 1.100800 | 1.135100 |
| SUM(monto_centimos) de gastos del período | 0.326300 | 0.274000 | 0.262700 | 0.266100 | 0.262800 | 0.266100 |

Validaciones satisfactorias: foreign_keys=ON, foreign_key_check sin
violaciones e integrity_check=ok (antes y después de medir).
La consulta devuelve 1005 movimientos y SUM devuelve 605750 céntimos,
coincidente con la suma de las filas recuperadas.

Ejecución desde la raíz del proyecto en PowerShell:
```powershell
py -3 scripts/benchmark_s3.py
```

El script rechaza sobrescribir esta evidencia si ya existe.
