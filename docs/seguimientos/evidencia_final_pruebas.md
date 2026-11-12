# Evidencia final de pruebas y mediciones — 12/11/2026

Los reportes originales fueron consultados en la terminal de Virtualmin y descargados en Windows. Se incorporan copias fieles, verificadas mediante SHA-256. No se ejecutaron pruebas ni mediciones durante esta actualización documental.

## Procedencia e integridad

| Reporte | Ubicación original en Virtualmin | Copia incorporada |
| --- | --- | --- |
| Regresión | `/home/grupo5/finanzas_private/quality/suite.json` | [suite.json](../../evidencias/s4_final/reportes/virtualmin/suite.json) |
| Rendimiento | `/home/grupo5/finanzas_private/quality/benchmark.md` | [benchmark.md](../../evidencias/s4_final/reportes/virtualmin/benchmark.md) |

Hashes SHA-256 coincidentes entre los archivos de Descargas y las copias incorporadas; no se verificó el servidor directamente en esta revisión:

- `suite.json`: `83b462e8627ed4034adfb454b539d7c2d5b5d6f87b206d4f90c4ed76c7370505`.
- `benchmark.md`: `83bec641f80aea5ba9598d251daefbce07a8af54d84855fc4392ad7852c6123e`.

## Pruebas de regresión del 12/11/2026

| Dato | Resultado verificado en suite.json |
| --- | --- |
| Fecha y hora registradas, sin zona horaria indicada | 12/11/2026, 10:18:51 |
| Entorno | Linux, Python 3.12.3, SQLite 3.45.1 |
| Pruebas correctas | 122/122 |
| Grupos de pruebas | 26 |
| Fallos | 0 |
| Errores | 0 |
| Pruebas omitidas | 0 |
| Duración | 123,43 segundos |

Escenarios S3 incluidos en las 122 pruebas, sin sumarlos nuevamente:

- Caso normal (`test_s3_normal`): 1/1.
- Error de conexión (`test_s3_connection_errors`): 3/3.
- Datos inválidos (`test_s3_invalid_data`): 4/4.

Esta ejecución es distinta de la regresión histórica de S4 del 6/11/2026, registrada en la [matriz de entrega](ENTREGA_S4.md) con 109/109 pruebas y 188.515 segundos. Se reemplazan las copias de Virtualmin del 11/11/2026, conservadas en el historial Git (commit `cb8e7f9`); no se alteran ni se suman los resultados históricos del 6/11/2026.

## Mediciones de rendimiento

El reporte de Virtualmin aportado para el 12/11/2026 utiliza SQLite 3.45.1, Python 3.12.3 y Linux 7.0.0-1014-aws. El archivo no contiene una fecha de generación propia. La base SQLite temporal contiene 100.000 movimientos sintéticos; se realizan cinco ejecuciones por escenario y se reporta la mediana en milisegundos. Las lecturas utilizan una conexión abierta y las actualizaciones se revierten mediante ROLLBACK.

| Operación | Con índices (ms) | Sin índices (ms) |
| --- | ---: | ---: |
| Consulta por fecha (un mes, 100 filas) | 0,522 | 17,074 |
| Total de gastos por categoría en un mes | 17,540 | 17,565 |
| Actualización por ID | 0,017 | 0,012 |

Los resultados corresponden al entorno evaluado y no garantizan el mismo rendimiento en otros equipos. El [reporte original](../../evidencias/s4_final/reportes/virtualmin/benchmark.md) conserva las cinco ejecuciones y los planes EXPLAIN QUERY PLAN. Estas mediciones no sustituyen los registros históricos de S3.

## Pruebas E2E históricas

La [matriz histórica ENTREGA_S4.md](ENTREGA_S4.md), con corte del 6/11/2026, registra 27/27 pruebas E2E satisfactorias, sin fallos ni omisiones. Su reporte original enlazado no está disponible en el checkout actual. No se presenta ese reporte como evidencia publicada ni se afirma una nueva ejecución E2E el 12/11/2026. Las 122 pruebas de regresión no sustituyen esta evidencia de navegador.

## Alcance de esta actualización

Se verificaron el total general, los 26 grupos y los 122 resultados individuales: todos correctos, sin problemas registrados. Las seis medianas se contrastaron con las cinco muestras de cada escenario. La consulta por fecha mejora con índices; la agrupación presenta tiempos próximos y el UPDATE por clave primaria no mejora en esta ejecución. No se infiere una mejora general ni se mide la respuesta HTTP del despliegue.

Se conserva `data/quality/` sin cambios: es la salida del panel local (suite de Windows del 3/11/2026, 85 pruebas), no el archivo documental de Virtualmin. Tampoco se alteran su estado ni su benchmark local.

Los enlaces relativos apuntan a archivos versionados del repositorio y son compatibles con GitHub. Estas nuevas copias requieren revisión, commit y push para estar disponibles allí; el commit `cb8e7f9` contiene la ejecución anterior. El video final continúa pendiente de enlace definitivo.
