# Evidencia final de pruebas y mediciones — 11/11/2026

Los reportes originales fueron consultados en la terminal de Virtualmin y descargados en Windows. Se incorporan copias fieles, verificadas mediante SHA-256. No se ejecutaron pruebas ni mediciones durante esta actualización documental.

## Procedencia e integridad

| Reporte | Ubicación original en Virtualmin | Copia incorporada |
| --- | --- | --- |
| Regresión | `/home/grupo5/finanzas_private/quality/suite.json` | [suite.json](../../evidencias/s4_final/reportes/virtualmin/suite.json) |
| Rendimiento | `/home/grupo5/finanzas_private/quality/benchmark.md` | [benchmark.md](../../evidencias/s4_final/reportes/virtualmin/benchmark.md) |

Hashes SHA-256 coincidentes entre los originales descargados, las copias y los valores proporcionados:

- `suite.json`: `ac788f90db8907ac841c3652d179022b890f9712b450ace9ab0f65c7d526b84d`.
- `benchmark.md`: `8294e909a7b6d09caf854559c87d01d3f86431f01f8b0cf22a6e9f98271f8427`.

## Pruebas de regresión del 11/11/2026

| Dato | Resultado verificado en suite.json |
| --- | --- |
| Fecha y hora registradas, sin zona horaria indicada | 11/11/2026, 12:16:21 |
| Entorno | Linux, Python 3.12.3, SQLite 3.45.1 |
| Pruebas correctas | 109/109 |
| Grupos de pruebas | 24 |
| Fallos | 0 |
| Errores | 0 |
| Pruebas omitidas | 0 |
| Duración | 113,33 segundos |

Escenarios S3 incluidos en las 109 pruebas, sin sumarlos nuevamente:

- Caso normal (`test_s3_normal`): 1/1.
- Error de conexión (`test_s3_connection_errors`): 3/3.
- Datos inválidos (`test_s3_invalid_data`): 4/4.

Esta ejecución es distinta de la regresión histórica de S4 del 6/11/2026, registrada en la [matriz de entrega](ENTREGA_S4.md) con 109/109 pruebas y 188.515 segundos. No se sustituyen ni se suman los resultados de ambas ejecuciones.

## Mediciones de rendimiento

El reporte de Virtualmin aportado para el 11/11/2026 utiliza SQLite 3.45.1, Python 3.12.3 y Linux 7.0.0-1014-aws. El archivo no contiene una fecha de generación propia. La base SQLite temporal contiene 100.000 movimientos sintéticos; se realizan cinco ejecuciones por escenario y se reporta la mediana en milisegundos. Las lecturas utilizan una conexión abierta y las actualizaciones se revierten mediante ROLLBACK.

| Operación | Con índices (ms) | Sin índices (ms) |
| --- | ---: | ---: |
| Consulta por fecha (un mes, 100 filas) | 0,547 | 16,363 |
| Total de gastos por categoría en un mes | 16,732 | 18,017 |
| Actualización por ID | 0,012 | 0,011 |

Los resultados corresponden al entorno evaluado y no garantizan el mismo rendimiento en otros equipos. El [reporte original](../../evidencias/s4_final/reportes/virtualmin/benchmark.md) conserva las cinco ejecuciones y los planes EXPLAIN QUERY PLAN. Estas mediciones no sustituyen los registros históricos de S3.

## Pruebas E2E históricas

La [matriz histórica ENTREGA_S4.md](ENTREGA_S4.md), con corte del 6/11/2026, registra 27/27 pruebas E2E satisfactorias, sin fallos ni omisiones. Su reporte original enlazado no está disponible en el checkout actual. No se presenta ese reporte como evidencia publicada ni se afirma una nueva ejecución E2E el 11/11/2026. Las 109 pruebas de regresión no sustituyen esta evidencia de navegador.
