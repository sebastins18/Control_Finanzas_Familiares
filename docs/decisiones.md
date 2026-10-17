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
