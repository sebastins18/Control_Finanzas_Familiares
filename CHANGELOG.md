# Registro de cambios

## v1.0.0 — Entrega final

**Fecha de entrega final: viernes 13 de noviembre de 2026.**

Funcionalidades implementadas y documentadas para la entrega final:

- Registro y administración de ingresos y gastos.
- Gestión de cuentas, categorías y presupuestos.
- Perfiles financieros y autenticación de usuarios.
- Metas de ahorro y transferencias.
- Historial de movimientos, filtros y exportación CSV.
- Reportes y movimientos recurrentes.
- Persistencia mediante SQLite como único motor.
- Instalación reproducible y carga de datos sintéticos.
- Pruebas automatizadas, mediciones y respaldos SQLite.

**Resultados históricos documentados de S4 (6/11/2026):** 109/109 pruebas de regresión correctas y 27/27 pruebas E2E satisfactorias. Estos resultados corresponden a la verificación histórica de S4; no se afirma una nueva ejecución para `v1.0.0`.

**Actualización de evidencias — 12/11/2026:** Virtualmin registra **122/122 pruebas correctas**, 0 fallos, errores y omisiones, en **123,43 segundos** (Linux, Python 3.12.3, SQLite 3.45.1). Se sustituyen los reportes de Virtualmin del 11/11/2026; se conservan los registros históricos de S4 y E2E. Mediciones sobre 100.000 movimientos, cinco ejecuciones por escenario y mediana: fecha 0,522/17,074 ms, agrupación 17,540/17,565 ms y actualización por ID 0,017/0,012 ms, con/sin índices. [Reportes, procedencia y SHA-256](docs/seguimientos/evidencia_final_pruebas.md). Cambios documentales pendientes de revisión y publicación; sin nueva ejecución E2E ni cambios funcionales.

**Pendiente de confirmación:** la publicación del Release, el video final y la validación de las evidencias. La publicación de `v1.0.0` sigue pendiente.

## v0.1.0 — Seguimiento 1 (16/10/2026)
- Documentación del problema, usuarios, alcance y decisiones arquitectónicas.
- Prototipo local con servidor web Python y SQLite.
- Modelo MVP de cinco tablas, modo WAL, claves foráneas e índices iniciales.
- Scripts de inicialización, datos sintéticos y verificación de conectividad.
- Backlog en cuatro GitHub Issues y bitácora del seguimiento S1.
- Ajuste del test de conexión a la implementación real del MVP.
- Clarificación de la diferencia entre el DDL operativo y el modelo ampliado propuesto.

> Validación local documentada el 16/10/2026: **10/10 pruebas correctas**, tras corregir incompatibilidad del test de conexión y cierre explícito de conexiones en Windows. El tablero GitHub Projects fue creado con Issues #1–#4 y se vinculó en la bitácora.
>
> Pendiente de cierre: confirmar commits propios de los cuatro integrantes, hacer público el Project y coordinar con el equipo la versión definitiva del tag compartido `v0.1.0`. Los ajustes posteriores están en `main` y no cambian automáticamente el contenido del tag.

## Integración V17 / S2 — 23/10/2026 (PR #5 fusionado)
- Se incorporó el módulo ampliado desde ZIP V17 aportado por un integrante; autoría Git individual pendiente de acreditar.
- Ajustes a pruebas de autenticación y conversión manual, cobertura de prefijo `/finanzas`, carga masiva transaccional sintética.
- Protección de credenciales y comprobantes locales en `.gitignore`.
- La primera referencia de `v0.2.0` se publicó antes de V17; su respaldo histórico quedó como `v0.2.0-original` (`721a4a7`) y el tag de entrega `v0.2.0` fue corregido a `584971e` con `--force-with-lease`.

- PR #5 fusionado en `main` (commit `abf92fb`) con 29/29 pruebas en CRNube y Windows.
- URL de prueba `/finanzas/login` con HTTP 200; base SQLite separada del directorio público.
- Auditoría de rúbrica, evidencias del equipo y tareas pendientes documentadas; Issue #7 mantiene trazabilidad del tag `v0.2.0` preintegración.

## Evidencia posetiquetado — GitHub Project #1 (23/10/2026)

- Project #1 enlazado al repositorio y configurado público vía GitHub CLI autenticado.
- Campos de seguimiento/prioridad y 11 elementos confirmados con `gh project item-list`.
- El Issue #7 (ajuste del tag) quedó cerrado tras verificar las referencias en GitHub.
- Siguen abiertos los compromisos individuales, demo manual y acta del profesor; detalles en Issues #6, #8, #9 y #11.

## QA posterior a v0.2.0 — 23/10/2026

- Cobertura HTTP S2 incrementada de 29 a 33 casos de prueba en revisión aislada; sin cambios de funcionalidad ni migraciones.
- Incorporado generador de evidencia no destructiva con SQLite temporal, guía de demo paso a paso y GitHub Actions.
- Este registro **no** altera la etiqueta `v0.2.0` ya entregada.

## Sesión 30/10/2026 — Arranque, panel de calidad y documentación

- Corregido el arranque cuando la migración de `usuarios` intentaba añadir de nuevo la columna `username` (`src/auth.py`).
- Indicador de carga y estado «Iniciando…» en el panel de calidad `/admin/calidad`, con iluminación al pasar el cursor en sus botones.
- Página `/olvide-clave` sin cambios funcionales: la recuperación de contraseña sigue siendo solo por administrador (D-012).
- Actualizados `docs/seguimientos/S3.md` (registro de cambios) y `docs/decisiones.md` (D-011 a D-013).
- Salidas temporales de arranque añadidas a `.gitignore`.

## v0.4.0 — 03/11/2026 (rama `changes-3-nov`)

- **Integración:** `origin/main` (S3 de Diego Fonseca) fusionado con la rama de trabajo; versiones paralelas conservadas como `*_diego` y decisiones renumeradas (D-018).
- **Correcciones:** compatibilidad con Python 3.11 (f-string anidada en `extension.page`, fallaba el CI); la prueba S3 de caso normal ya no depende del mes actual.
- **Historial** (`/historial`): búsqueda y filtros por tipo, categoría, cuenta y fechas, paginación, totales por moneda y exportación CSV (D-019).
- **Reporte anual** (`/reportes/anual`): totales mensuales por categoría y moneda, con CSV (D-019).
- **Movimientos recurrentes:** plantillas mensuales y generación explícita e idempotente; tablas nuevas `movimientos_recurrentes` y `recurrentes_generados`, sin cambios en las existentes (D-020).
- **Formularios rediseñados**, brillo que sigue al puntero en paneles y botones, e indicador animado en selectores y pestañas; mismos nombres y valores enviados al servidor (D-021).
- **Datos de demostración — errata aclarada el 6/11:** el árbol inspeccionado de `v0.4.0` y el HEAD actual no contienen `scripts/demo_temporal.py`. La afirmación anterior de que quedaba en ese tag era incorrecta; utilizar `scripts/seed.py` sobre una base nueva de ensayo.
- **Pruebas históricas de v0.4.0:** 103/103 en Python 3.11 y 3.12 (+18: `test_historial_reportes.py`, `test_formularios_v2.py`).
- Detalle de uso: [docs/consultas_reportes_recurrentes.md](docs/consultas_reportes_recurrentes.md).

## S4 — integración técnica, despliegue y evidencia local (6/11/2026)

- Base técnica actual `main`, `8a88aeb`; se mantienen los cambios de código, seguridad, respaldo SQLite, CI y pruebas de los PR #20, #21 y #22.
- Instalación limpia aislada con init, seed idempotente, conexión, integridad, WAL, login HTTP y cookies. Respaldo coherente con WAL mediante `sqlite3.Connection.backup`, validación de integridad/FK y destino sin sobrescritura.
- Para una base nueva con prefijo web o con `FINANZAS_REQUIRE_STRONG_ADMIN_PASSWORD=1`, se exige clave inicial privada de 12+ caracteres y se rechaza la credencial pública de demostración. Bases existentes conservan sus hashes.
- Cookie Secure configurable mediante `FINANZAS_COOKIE_SECURE=1` bajo HTTPS; cabeceras `X-Frame-Options: DENY` y `Referrer-Policy: same-origin`.
- CI histórico verificado sobre `4cbf76a`: [run 42303414421](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421), Linux Python 3.11/3.12 y Windows 3.12, tres trabajos correctos. No se declara una nueva corrida sobre la revisión documental.
- **S4 desplegado en CRNube el 6/11/2026 sobre `8a88aeb`**, con respaldo SQLite consistente anterior a la actualización, según el responsable. SQLite del despliegue: **WAL, 17 tablas, integridad `ok`, cero errores FK**. El GET público del login es una comprobación separada y limitada.
- Evidencia local vigente: **109/109 pruebas de regresión correctas**, 188.515 s, y **27/27 E2E satisfactorias**, 0 fallidas/omitidas. [Consola](evidencias/s4_final/reportes/complementarias/regresion.txt), [resumen E2E](evidencias/s4_final/reportes/e2e/reportes/RESUMEN.md), instalación automática y carga/respaldo de ensayo de 1.000 registros.
- Existen capturas y video auténticos locales. Se conservan la primera grabación y las versiones de trabajo 1080p, voz, guion y subtítulos. **El video final sincronizado sigue en preparación; no se afirma su publicación.** Los nombres `FINAL` no equivalen a aceptación editorial.
- **S3 cerrado técnicamente** en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3), estado `closed`, razón `completed`. Volumen de 100.000 e índices/EQP sustentan profundidad; la comparación WAL/DELETE es opcional. No se atribuye aprobación docente.
- `v0.9.0` y `v1.0.0` **no aparecen en la consulta real de tags remotos al corte** (`git ls-remote --heads --tags origin`). No se crean ni publican versiones en esta tarea.
- Pendientes académicos: instalación por otro integrante siguiendo solo README, revisión final del video y publicación autorizada con acceso del profesor, acta/comentarios, fecha de exposición, PDF y revisión del candidato.

## Consolidación documental del aporte de Diego — 6/11/2026

- Se recupera y acredita la documentación detallada de **Diego Fonseca (`dfonseca15`)**, commit [`4b0bfed`](https://github.com/sebastins18/Control_Finanzas_Familiares/commit/4b0bfed6ae37e527daf72fc3b6aa8727e990e199): propósito, usuarios, arquitectura, instalación, lectura SQLite, matriz académica S4, ficha independiente, verificaciones y roadmap.
- Comparación actual: `origin/respaldo-documentacion-s4...origin/main` = **0 / 9**. El commit original ya está integrado en la ascendencia de main; la consolidación es editorial, sin otro merge ni sustitución automática de archivos históricos.
- Se actualizan README, esta bitácora, S4 y documentos de entrega conservando la base técnica y todos los materiales locales de QA/video. [Registro de atribución y diferencias](docs/seguimientos/S4_APORTE_RESPALDO_DIEGO.md).
- **103 y 105 pruebas quedan únicamente como antecedentes históricos**: 103 en la etapa v0.4.0/registro de calidad anterior; 105 aportadas sobre `94412a1`, sin consola original adjunta. Ninguna reemplaza las 109 vigentes ni se suma a ellas.
- `portal.yml` mantiene exactamente los 15 campos académicos y sus valores; se actualizan solo comentarios. Video y captura conservan cadenas vacías por falta de URL pública autorizada; autores públicos permanecen vacíos.
- Los enlaces relativos de evidencia son locales y no acreditan publicación en GitHub. ZIP/manifiestos anteriores conservan su corte de ejecución. La documentación no convierte instalación automática en validación humana ni cierre técnico en aprobación académica.
- Sin cambios de código, bases, credenciales, CI o tests; sin commit, push, merge, tags, publicaciones ni acceso a WebAdmin.
