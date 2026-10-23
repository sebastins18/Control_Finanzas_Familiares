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
