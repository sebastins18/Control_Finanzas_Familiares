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

## Integración propuesta V17 / S2 — 23/10/2026 (rama, aún sin merge)
- Se incorporó el módulo ampliado desde ZIP V17 aportado por un integrante; autoría Git individual pendiente de acreditar.
- Ajustes a pruebas de autenticación y conversión manual, cobertura de prefijo `/finanzas`, carga masiva transaccional sintética.
- Protección de credenciales y comprobantes locales en `.gitignore`.
- `v0.2.0` remoto existía antes de estos cambios y no los incluye.
