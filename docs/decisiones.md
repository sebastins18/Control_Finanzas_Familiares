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

## D-006 — SQLite en modo WAL

- **Fecha:** 30/10/2026.
- **Decisión:** `PRAGMA journal_mode=WAL` al inicializar (`db.init_db`) y `PRAGMA foreign_keys=ON` en cada conexión.
- **Alternativas:** diario `DELETE` (valor por defecto de SQLite).
- **Justificación:** el servidor atiende peticiones en hilos (`ThreadingHTTPServer`); WAL permite lecturas mientras otra conexión escribe.
- **Límites:** no se midió WAL contra `DELETE`, solo está configurado. Crea archivos `-wal` y `-shm` junto a la base: los respaldos deben usar `sqlite3 ... ".backup"` y no copiar solo el `.sqlite3`. No usar WAL sobre sistemas de archivos de red (NFS).

## D-007 — Índices de `movimientos` (medidos en S3)

- **Fecha:** 30/10/2026.
- **Decisión:** conservar `idx_movimientos_fecha_tipo` e `idx_movimientos_categoria_fecha`.
- **Alternativas:** sin índices; índice cubriente `(fecha, tipo, id_categoria, monto_centimos)`.
- **Evidencia (100 000 movimientos, mediana de 5 ejecuciones, `docs/seguimientos/S3_mediciones.md`):** movimientos por rango de fecha 11.344 ms sin índices y 0.288 ms con índices (aprox. 39 veces más rápido); actualización por id sin diferencia, porque usa la clave primaria.
- **Resultado contrario:** el total de gasto por categoría y mes fue **más lento con índices** (17.854 ms) que sin ellos (11.349 ms). El plan con índice usa `idx_movimientos_fecha_tipo` (`SEARCH ... USING INDEX`) y el plan sin índices hace `SCAN movimientos`. No se midió la causa; una hipótesis es que, al seleccionar un mes de unas 8 000 filas, acceder a cada fila por el índice cuesta más que un recorrido secuencial.
- **Pendiente:** probar un índice cubriente para esa consulta. No se implementó ni se midió, por lo que no se afirma que mejore.

## D-008 — Tiempos límite de SQLite

- **Fecha:** 30/10/2026.
- **Decisión:** `busy_timeout` de 3 s y interrupción cooperativa de consultas a los 8 s (`BUSY_TIMEOUT_MS`, `OPERATION_TIMEOUT_SECONDS` en `src/db.py`). Sin reintentos automáticos.
- **Alternativas:** esperas más largas; bucles de reintento.
- **Justificación:** un reintento automático de una escritura puede duplicarla si la primera sí se completó. El mensaje 503 pide comprobar el resultado antes de reenviar.
- **Límite:** el límite de 8 s es cooperativo; no cubre bloqueos del sistema operativo (por ejemplo, un disco de red colgado).

## D-009 — Caché de solo lectura en memoria

- **Fecha:** 30/10/2026.
- **Decisión:** `src/read_cache.py` guarda la última copia de cinco páginas de catálogo (cuentas, categorías, monedas, presupuestos, metas de ahorro). Solo se sirve si SQLite falla en un `GET`, con aviso visible y el encabezado `X-Datos-Desactualizados`.
- **Alternativas:** sin caché; Redis; cola de escrituras pendientes.
- **Justificación:** mantiene consultable el catálogo durante una caída breve sin tocar la integridad de los datos. Es por sesión y por perfil, caduca a los 10 minutos y guarda como máximo 200 páginas.
- **Límites:** vive en un solo proceso (no se comparte entre procesos) y se pierde al reiniciar. No cubre saldos, panel principal ni formularios.

## D-010 — Sin Redis ni cola de escrituras

- **Fecha:** 30/10/2026.
- **Decisión:** no incorporar Redis ni encolar escrituras mientras la base está caída.
- **Alternativas:** Redis como caché compartida; cola de escrituras en disco con identificadores idempotentes.
- **Justificación:** hay un solo proceso y una base local, así que Redis no resuelve un problema real y agrega un servicio que operar y asegurar. Una cola automática puede duplicar gastos o reordenar operaciones, y mostrar "guardado" antes de estarlo.
- **Impacto:** perfil A; no hay motor secundario. El manejo de fallos se documenta sobre SQLite (ver `docs/control_errores.md` y `docs/seguimientos/S3.md`).

## D-011 — Migración de `usuarios` idempotente por columna

- **Fecha:** 30/10/2026.
- **Decisión:** `auth.init` añade cada columna nueva de `usuarios` solo si no existe (antes, la condición era global y fallaba si la columna `username` ya estaba presente sin usuarios poblados).
- **Alternativas:** envolver el arranque en `try/except` y continuar; reconstruir la tabla.
- **Justificación:** un error de migración que impide arrancar es peor que un esquema parcial visible. Comprobar columna a columna es verificable con `PRAGMA table_info` y no altera datos.
- **Límite:** no reemplaza un sistema de versiones de esquema; las migraciones futuras deben seguir el mismo patrón.

## D-012 — Recuperación de contraseña solo por administrador (provisional)

- **Fecha:** 30/10/2026.
- **Decisión:** `/olvide-clave` informa el procedimiento; un administrador restablece la clave en *Seguridad → Mantenimiento de usuarios*. No hay restablecimiento de autoservicio.
- **Alternativas:** restablecer con solo el nombre de usuario (rechazado: cualquiera podría tomar una cuenta); pregunta de seguridad (requiere columna nueva); código de recuperación mostrado en consola o registro (rechazado por el equipo para esta etapa).
- **Justificación:** sin correo electrónico ni verificación adicional, cualquier autoservicio abre una vía de toma de cuentas. Se mantiene la opción segura y se deja para revisión posterior.
- **Límite:** un usuario sin administrador disponible depende del acceso al servidor.

## D-013 — Indicador de carga en el panel de calidad

- **Fecha:** 30/10/2026.
- **Decisión:** mientras corre un trabajo se muestra un indicador con spinner y hora de inicio; el botón cambia a «Iniciando…» al pulsarlo. La actualización automática sigue cada 4 s.
- **Alternativas:** mostrar solo texto de estado; sustituir la recarga por sondeo asíncrono.
- **Justificación:** las suites tardan minutos y sin señal visible el usuario repite la acción. Se conserva la recarga existente para no introducir JavaScript de estado complejo.
- **Límite:** el indicador respeta `prefers-reduced-motion` ralentizando la animación; no se ha verificado en navegador en el servidor Linux.
