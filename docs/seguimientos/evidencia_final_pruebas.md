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

Los enlaces relativos apuntan a archivos versionados del repositorio y son compatibles con GitHub. Las copias actuales están incorporadas en `af707b5`; el commit `cb8e7f9` contiene la ejecución anterior. Esta revisión documental adicional se entrega como diff, sin commit ni push. El video final continúa pendiente de enlace definitivo.

## Informe de revisión integral — 12/11/2026

**Entrega académica:** `v1.0.0`, viernes 13 de noviembre de 2026. **Base revisada:** `main`, `af707b5`. Esta revisión modifica solo documentación; no genera commit, push, tags, pruebas nuevas ni cambios en Virtualmin.

### Alcance y archivos revisados

Se buscaron cifras, fechas, versiones, estados y referencias en los archivos versionados del repositorio, incluidos los scripts de generación audiovisual. Se comprobaron las referencias de 59 Markdown, la ficha del portal, el SRT histórico y el JSON final. Los archivos locales de `data/quality/` se inspeccionaron como antecedentes, sin modificarlos.

El inventario abarca README y CHANGELOG; documentación de instalación, arquitectura, modelos, decisiones, usuarios, perfiles, reportes y errores; PLAN_GITHUB y ROADMAP; todos los seguimientos S1–S4, sus matrices, actas, aportes y guías; documentación de evidencias y video; documentación de `scripts/e2e/`, `data/` y los registros de versiones V4–V17 de la raíz. La lista exacta de documentos se obtiene con `git ls-files '*.md' '*.yml' '*.srt'`; el JSON final se revisó por separado.

Archivos corregidos (23 Markdown):

- Raíz: `README.md`, `CHANGELOG.md`.
- Documentación general: `docs/INSTALACION_S4.md`, `docs/PLAN_GITHUB.md`, `docs/arquitectura/ARQUITECTURA_S4.md`, `docs/img/README.md`.
- En `docs/seguimientos/`: `S1.md`, `S2.md`, `S3.md`, `S3_diego.md`, `S3_mediciones.md`, `mediciones_s3.md`, `pruebas_s3.md`, `S4.md`, `S4_APORTE_RESPALDO_DIEGO.md`, `ENTREGA_S4.md`, `GUIA_DEMO_FINAL.md`, `VIDEO_S4.md`, `evidencia_final_pruebas.md`.
- Material audiovisual: `evidencias/s4_final/LEEME.md`, `evidencias/s4_final/MisFinanzas_S4_FINAL_Guion.md`, `evidencias/s4_final/MisFinanzas_S4_FINAL_Validacion.md`, `scripts/e2e/PRESENTACION.md`.

### Inconsistencias encontradas y correcciones

- README, S4, matriz y evidencia describían los reportes del 12/11 como archivos sin commit. Se identificó su incorporación en `af707b5`, conservando `af10724` como base de la actualización anterior y `cb8e7f9` como referencia del 11/11.
- La versión final se confundía con un estado de publicación pendiente o una fecha por confirmar. Se estableció `v1.0.0` para el viernes 13/11/2026, diferenciando esa fecha de la consulta de etiquetas. `v0.9.0` se conserva como candidato histórico.
- Se aclaró el carácter histórico de las 109 regresiones en arquitectura, S3, CHANGELOG y materiales audiovisuales. No se cambiaron sus cifras ni las palabras del audio o del SRT. Los benchmarks Windows de S3 conservan sus resultados y se distinguen del benchmark final de Linux.
- La guía de exposición interpretaba la agregación de una medición anterior como resultado aplicable a la entrega. Ahora presenta las medianas finales: mejora por fecha, valores próximos en agrupación y ausencia de mejora en el UPDATE por clave primaria, sin inferir una mejora general.
- La matriz decía que `autores_publicos` estaba vacío, aunque `portal.yml` registra cuatro integrantes. Se corrigió la descripción sin modificar la ficha ni sus 15 campos.
- Las comparaciones de ramas de 0/9 commits se identifican como históricas del 6/11; no se presentan como una medición del HEAD actual.
- Se detectaron 53 hipervínculos a destinos ausentes. Se conservaron sus rutas y rótulos como texto, indicando que el material histórico no está incluido; no se crearon archivos sustitutos ni se inventaron enlaces públicos.

### Verificaciones y resultados

- Suite JSON: `exito=true`, 122 pruebas y 26 grupos; suma de grupos y 122 resultados individuales correctos; cero fallos, errores, omisiones y problemas registrados. Fecha `2026-11-12T10:18:51`, sin zona indicada; 123,43 segundos, Linux, Python 3.12.3 y SQLite 3.45.1.
- Benchmark: 100.000 movimientos, tres operaciones en dos escenarios, cinco muestras por escenario y seis medianas recalculadas correctamente. No se confunde con una prueba HTTP ni con el total de pruebas de la suite.
- SHA-256: ambos reportes coinciden con Descargas y con los hashes de este documento. Los reportes y `data/quality/` permanecen sin cambios en esta revisión.
- Enlaces: 231 referencias locales activas y seis anclas Markdown comprobadas, sin destinos ausentes ni archivos sin versionar. Las evidencias finales tienen rutas relativas compatibles con GitHub. Las referencias a materiales ausentes se conservan como texto para trazabilidad.
- `git diff --check` sin errores; solo 23 Markdown modificados. `git diff --exit-code -- evidencias/s4_final/reportes/virtualmin data/quality portal.yml` sin diferencias. El 13/11/2026 corresponde a viernes.
- Etiquetas: `git tag --list` no incluye `v1.0.0` ni `v0.9.0`. La consulta de solo lectura `git ls-remote --tags origin refs/tags/v1.0.0 refs/tags/v0.9.0`, completada el 12/11/2026 con código 0, no devolvió referencias. No se acredita un Release publicado a partir de esta consulta de tags.
- No se ejecutó nuevamente la suite ni el benchmark: se validaron las evidencias aportadas. Tampoco se revalidaron por HTTP los enlaces externos históricos de CI, Issues o despliegue; conservan el alcance y fecha de sus registros.

### Asuntos que requieren confirmación

- Enlace definitivo del video final y permisos reales de acceso del profesor; el audio histórico menciona 109 pruebas y no representa la ejecución final de 122.
- Recuperación o publicación de los reportes históricos E2E, consola, instalación, carga y respaldo si se requieren como archivos descargables. La documentación no sustituye esos originales ausentes.
- Instalación independiente por otro integrante, identidad y resultados reales; acta, participación, comentarios docentes y materiales/PDF de exposición.
- Los generadores audiovisuales `scripts/e2e/build_presentation_summary.py`, `package_evidence.py`, `finalize_s4.py`, `review_presentation.py` y el SRT conservan referencias a 109 porque pertenecen a la producción histórica. No se modificaron ni se ejecutaron. Su salida no debe presentarse como evidencia nueva de Virtualmin.
- La aceptación académica y la existencia de un Release requieren evidencia propia; la fecha establecida de versión no demuestra ninguno de esos hechos.
