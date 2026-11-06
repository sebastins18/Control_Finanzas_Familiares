# Registro de cambios

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
- **Datos de demostración:** `scripts/demo_temporal.py` (perfil DEMO separado) queda solo en el tag `v0.4.0`; en `main` se retiró para que el despliegue del servidor no incluya cargadores de datos ficticios.
- **Pruebas:** 103/103 en Python 3.11 y 3.12 (+18: `test_historial_reportes.py`, `test_formularios_v2.py`).
- Detalle de uso: [docs/consultas_reportes_recurrentes.md](docs/consultas_reportes_recurrentes.md).

## S4 — release candidate integrado en main (6/11/2026; tag v0.9.0 pendiente)

- Preparados la guía reproducible de instalación desde cero, `S4.md`, `portal.yml`, roadmap y guion de exposición con riesgos/evidencias pendientes.
- Nueva comprobación de instalación limpia sobre SQLite temporal: init, seed idempotente, conexión, integridad, WAL, login HTTP y cabeceras.
- Nuevo respaldo SQLite coherente con bases activas en WAL mediante `sqlite3.Connection.backup` y verificación de integridad/relaciones; nunca sobrescribe archivos.
- Arranque de SQLite nuevo con prefijo web exige contraseña inicial de administrador de 12+ caracteres (evita `admin123!` en despliegues nuevos); bases ya existentes conservan el hash.
- Cookies de sesión con `Secure` optativo mediante `FINANZAS_COOKIE_SECURE=1` bajo HTTPS; se añaden cabeceras `X-Frame-Options: DENY` y `Referrer-Policy: same-origin`.
- CI ampliado y **confirmado** sobre el merge de S4 `4cbf76a` ([run 42303414421](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421)): Linux Python 3.11/3.12 y Windows Python 3.12, tres trabajos correctos.
- No se declara demo/manual hecha por otro integrante, video publicado ni release `v1.0.0` hasta contar con evidencia auténtica.

- PR #20 fusionado a `main`; terminal del grupo verificó **109/109 tests OK** en Windows y una instalación limpia S4 exitosa.
- Arquitectura actual, matriz de cumplimiento, acta pendiente y guion de video documentados; el despliegue del servidor del profesor se mantiene sin cambios por instrucción del responsable.
- **Pendiente:** tag `v0.9.0` después de aprobación, video de 3–5 min, instalación por otra persona, capturas actuales y documentación final de exposición.
