# Decisiones técnicas

## D-001 — Solo SQLite

- **Fecha:** 16/10/2026.
- **Decisión:** usar SQLite como único motor principal.
- **Alternativas:** Redis + MongoDB, PostgreSQL, combinación de motores.
- **Justificación:** el problema central es transaccional y local. Un motor único simplifica instalación y permite profundizar en índices, WAL y mediciones.
- **Impacto:** perfil A del enunciado; requiere 2 evidencias de profundidad en los siguientes seguimientos.

## D-002 — Web local sin dependencias externas

- **Decisión:** Python estándar (`http.server`) y `sqlite3` para el prototipo.
- **Alternativas:** Flask, Django, PHP.
- **Justificación:** la instalación se prueba con Python instalado y comandos directos, sin servidor separado ni `pip install`.
- **Límite:** solo demo local; antes de un despliegue real deben implementarse autenticación, sesiones, protección CSRF y operación de producción.

## D-003 — Alcance v1 acotado del esquema v4

- **Decisión:** cinco tablas para la primera implementación: usuarios, categorías, cuentas, movimientos y presupuestos.
- **Alternativas:** crear las tablas completas del diagrama v4 desde la primera semana.
- **Justificación:** el seguimiento 1 pide modelo y conexión, no el producto final. Priorizar registro, dashboard y alertas para una demo verificable.
- **Límite:** el diagrama original incluye divisas, transferencias, metas, sesiones y comprobantes; quedan en backlog.

## D-004 — Montos en centavos enteros

- **Decisión:** persistir `monto_centimos` como `INTEGER`, mostrar CRC en formato monetario.
- **Justificación:** evita errores binarios de `REAL` en importes. Se valida `Decimal` antes de convertir.
- **Límite:** sin cambio de divisas en esta etapa.

## D-005 — Fuente de datos sintética

- **Decisión:** script determinista `scripts/seed.py`, con salarios/gastos totalmente inventados.
- **Justificación:** repetible, protege datos personales y permite volver a ejecutar la demo.

## D-006 — Continuidad del perfil A en S3

- **Fecha:** 30/10/2026.
- **Decisión:** mantener SQLite como único motor y no incorporar un motor secundario para el Seguimiento 3, dando continuidad a D-001.
- **Alternativas técnicas posibles:** migrar a PostgreSQL o incorporar otro motor para una necesidad específica. No hay registro revisado de una evaluación comparativa nueva en S3 ni de una discusión del equipo sobre estas opciones; no se presentan como alternativas históricamente evaluadas.
- **Justificación:** la persistencia implementada usa `sqlite3`, un archivo local y operaciones relacionales transaccionales. Mantener ese alcance permite profundizar y verificar el motor existente sin añadir servicios ni sincronización entre motores.
- **Impacto o limitación:** corresponde al perfil A. El fallo de un motor secundario no aplica; tampoco existe conmutación a otro motor cuando SQLite no está disponible. Las decisiones históricas D-001 a D-005 se conservan como registro de su etapa y no describen por sí solas todo el alcance funcional actual.
- **Evidencia verificable:** [src/db.py](../src/db.py), funciones `db_path`, `connect` e `init_db`; [src/schema.sql](../src/schema.sql); [pruebas S3](seguimientos/pruebas_s3.md), alcance y comportamiento ante fallos; [mediciones S3](seguimientos/mediciones_s3.md), operaciones exclusivamente SQLite.

## D-007 — Profundización en índices, WAL e integridad transaccional

- **Fecha:** 30/10/2026.
- **Decisión:** conservar los índices del esquema, activar WAL al inicializar la base de la aplicación, habilitar claves foráneas en cada conexión de `db.connect()` y agrupar las escrituras en contextos transaccionales con cierre de conexión al finalizar.
- **Alternativas técnicas posibles:** operar sin los índices explícitos, usar otro modo de journal o delegar las relaciones y la atomicidad al código de aplicación. La nueva evidencia compara únicamente conservar o eliminar `idx_movimientos_categoria_fecha`, manteniendo los demás índices. No acredita una evaluación de las otras alternativas ni una discusión histórica nueva por el equipo.
- **Justificación:** los índices `idx_movimientos_fecha_tipo`, `idx_movimientos_categoria_fecha` e `idx_presupuestos_periodo` corresponden a campos de filtros existentes. WAL forma parte de la configuración real de inicialización. Las claves foráneas y las transacciones permiten comprobar referencias válidas y revertir escrituras ante fallos, en lugar de dejar cambios parciales.
- **Impacto o limitación:** los índices implican mantenimiento en las escrituras y espacio adicional; su existencia no demuestra una mejora de rendimiento. La comparación local del índice evaluado registra una reducción de la mediana, sin demostrar una mejora general de estos índices. WAL no elimina los bloqueos de escritura. `src/schema.sql` es el esquema base; `db.init_db()` también inicializa autenticación, extensiones, perfiles y cotizaciones. Tanto el benchmark de tres operaciones como la comparación de índices ejecutan solo el esquema base y no activan WAL, por lo que sus tiempos no validan el rendimiento de la configuración WAL de la aplicación.
- **Evidencia verificable:** [src/schema.sql](../src/schema.sql), declaraciones `REFERENCES` y `CREATE INDEX`; [src/db.py](../src/db.py), `PRAGMA journal_mode = WAL`, `PRAGMA foreign_keys = ON` y contexto `with connection`; [tests/test_connection.py](../tests/test_connection.py), configuración WAL y claves foráneas; [tests/test_error_handling.py](../tests/test_error_handling.py), rollback y cierre; [pruebas S3](seguimientos/pruebas_s3.md) y [mediciones S3](seguimientos/mediciones_s3.md).
- **Evidencia adicional de índices — 30/10/2026:** [scripts/indices_s3.py](../scripts/indices_s3.py) e [indices_s3.md](seguimientos/indices_s3.md) comparan dos copias temporales de 10000 movimientos sintéticos, con consulta, parámetros y configuración equivalentes y diez ejecuciones por escenario. Las medianas fueron **0.2269 ms con `idx_movimientos_categoria_fecha` y 0.4408 ms sin ese índice**, una reducción observada de **48.53 %**. `EXPLAIN QUERY PLAN` muestra `SEARCH movimientos USING INDEX idx_movimientos_categoria_fecha (id_categoria=? AND fecha>? AND fecha<?)` frente a `SEARCH movimientos USING INDEX idx_movimientos_fecha_tipo (fecha>? AND fecha<?)` y `USE TEMP B-TREE FOR LAST TERM OF ORDER BY`. El segundo escenario utiliza otro índice: no es una consulta sin ningún índice. Se comprobaron 273 filas idénticas y no vacías, conteos estables, claves foráneas activas, `foreign_key_check` sin violaciones e `integrity_check=ok` antes y después. Dos calentamientos por escenario y orden alternado no eliminan el sesgo de cachés, que no se vaciaron. Diez muestras en una sola ejecución y una distribución sintética no demuestran significancia estadística ni mejora general; no se midieron costes de escritura, otros índices, respuesta web o Virtualmin. Estas evidencias de optimización y análisis de consultas se distinguen de las pruebas de integridad y manejo transaccional del perfil A.

## D-008 — Fallos controlados de acceso, bloqueo y transacción

- **Fecha:** 30/10/2026.
- **Decisión:** mantener una frontera de errores HTTP que incluya la autenticación, mensajes sin detalles internos para el cliente y registro técnico de excepciones; limitar esperas de SQLite y revertir la transacción cuando falla una operación dentro del contexto de conexión. Mantener también el manejo controlado de errores en CLI.
- **Alternativas técnicas posibles:** propagar excepciones al cliente, reintentar indefinidamente ante bloqueo o confirmar cada escritura parcial de una operación compuesta. No consta que el equipo haya discutido o evaluado esas opciones; se mencionan únicamente para explicar el alcance de la solución implementada.
- **Justificación:** el usuario necesita una respuesta comprensible ante indisponibilidad, conflictos y datos inválidos; las escrituras relacionadas deben conservar atomicidad. `db.connect()` configura `BUSY_TIMEOUT_MS=3000`, un límite de operación de 8 segundos mediante un manejador de progreso y cierre en `finally`. Son valores de configuración, no tiempos de respuesta garantizados ni mediciones observadas.
- **Impacto o limitación:** en los escenarios probados se obtienen HTTP 503 por fallo de conexión, bloqueo real de escritura o permisos de almacenamiento simulados; HTTP 409 por categoría duplicada, borrado con referencias y transferencia abortada; HTTP 400 por formato inválido de cuentas o cotización `NaN`; HTTP 500 por `RuntimeError` simulado en el dashboard. Los tests verifican ausencia de detalles privados en esas respuestas. La interrupción de una consulta costosa se verifica directamente con `SQLITE_INTERRUPT`, sin acreditar su respuesta HTTP. El fallo transaccional probado revierte cambios y cierra la conexión; el fallo CLI termina con código 1 sin traceback ni ruta privada en stderr. No se garantiza recuperación automática para cualquier fallo; ante un POST fallido la aplicación indica comprobar si el cambio se guardó antes de reenviarlo.
- **Evidencia verificable:** [src/app.py](../src/app.py), `controlled_request`; [src/db.py](../src/db.py), `connect` y `cli_errors`; [tests/test_sqlite_failure_v16.py](../tests/test_sqlite_failure_v16.py) y [tests/test_error_handling.py](../tests/test_error_handling.py). [Pruebas S3](seguimientos/pruebas_s3.md) registra el resultado aportado del 30/10/2026: 11 pruebas aprobadas en 6.367 segundos, junto con `tests/test_connection.py`; distingue la evidencia anterior de flujo normal S2 y consigna `ResourceWarning` como observación no bloqueante. No se realizó una nueva ejecución para esta decisión.

## D-009 — Medición local reproducible sobre SQLite temporal

- **Fecha:** 30/10/2026.
- **Decisión:** medir tres operaciones SQLite con cinco ejecuciones por operación y mediana en milisegundos: insertar un gasto incluyendo su commit, consultar movimientos por categoría y rango de fechas consumiendo las filas y calcular `SUM(monto_centimos)` de gastos de un período. Usar `time.perf_counter`, `statistics.median` y una base creada con `tempfile`, inicializada con `src/schema.sql` y al menos 1000 movimientos sintéticos válidos antes de medir.
- **Alternativas técnicas posibles:** medir sobre la base de uso del proyecto, publicar una sola ejecución o usar el promedio; realizar por separado una prueba de respuesta HTTP o del despliegue en Virtualmin. No hay registro de evaluación histórica de estas alternativas en S3; las pruebas web y de despliegue serían experimentos diferentes.
- **Justificación:** la base temporal evita modificar datos existentes; los datos sintéticos con usuario, perfil, cuenta y categoría permiten respetar las relaciones. Publicar las cinco muestras y la mediana permite examinar la variación local sin depender de una sola observación. Las comprobaciones de integridad y de resultados evitan presentar tiempos de consultas vacías o datos inválidos como evidencia funcional.
- **Impacto o limitación:** el reporte existente usa Python 3.15.0 y SQLite 3.53.4 en Windows, con 1000 movimientos iniciales y 1005 finales; sus medianas son 2.401600 ms para inserción confirmada, 1.135100 ms para consulta y 0.266100 ms para suma. Son mediciones locales de SQLite: no miden la respuesta web, red, autenticación, proxy, Virtualmin ni el despliegue. Se reutiliza la conexión y no se reinicia la caché; las consultas se miden después de las cinco inserciones. El esquema base conserva sus índices, pero no hay comparación experimental con índices eliminados ni con otros motores. El benchmark no llama a `db.init_db()` ni activa WAL; no representa toda la configuración de la aplicación. La base temporal se elimina y la evidencia existente se protege contra sobrescritura.
- **Evidencia verificable:** [scripts/benchmark_s3.py](../scripts/benchmark_s3.py), generación, cronometraje y validaciones; [mediciones S3](seguimientos/mediciones_s3.md), cinco tiempos por operación, medianas, versiones, conteos, `foreign_key_check` sin violaciones e `integrity_check=ok`. [Pruebas S3](seguimientos/pruebas_s3.md) documenta pruebas funcionales separadas: los 6.367 segundos de la suite no son una medición de rendimiento de SQLite.
