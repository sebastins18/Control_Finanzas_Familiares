# Guion breve para Seguimiento 1 (5 minutos)

**0:00–0:45 — Problema y usuario.** “Somos el Grupo 5. Nuestra propuesta es Control de Finanzas Familiares. Busca centralizar ingresos, gastos y límites mensuales que hoy pueden estar dispersos. El usuario es una familia. El alcance inicial es registro de movimientos, dashboard y presupuestos.”

**0:45–1:30 — Arquitectura.** “Usamos Python web y SQLite como base principal. SQLite guarda usuarios, categorías, cuentas, movimientos y presupuestos. Elegimos un solo motor porque el problema es local y transaccional; cumpliremos la profundidad adicional mediante WAL y una comparación con/sin índices durante S3.”

**1:30–2:15 — Repositorio.** Mostrar README, diagrama, `schema.sql`, estructura de carpetas, issues asignados, colaboración, commits de todos y tag `v0.1.0`. **Mostrar solo lo que exista realmente en GitHub**, no las tareas pendientes.

**2:15–3:20 — Conexión.** Ejecutar `py scripts/init_db.py`, `py scripts/check_connection.py`, `py -m src.app`; abrir `/health` y la página principal. Explicar que `seed.py` genera datos ficticios.

**3:20–4:20 — Mini demo.** Mostrar balance, agregar un gasto y ver cómo cambia el total; mostrar presupuesto y alerta. Es un adelanto del núcleo funcional de S2.

**4:20–5:00 — Próximos pasos.** “Vamos a cerrar el CRUD completo, robustecer validaciones, aumentar el volumen de datos y medir consultas. Las transferencias, multimoneda y metas quedan fuera del MVP de la primera iteración.”

## Preguntas probables

- **¿Por qué SQLite y no MongoDB?** Porque tenemos movimientos y presupuestos con relaciones bien definidas; un SQLite local basta y permite medir índices, EXPLAIN y WAL.
- **¿Es lo mismo que el diseño de la presentación?** Es un subconjunto del modelo v4: unificamos ingresos/gastos en movimientos y diferimos funciones avanzadas.
- **¿Qué pasa si falla SQLite?** La operación devuelve error y no afirma haber guardado los datos; no hay motor secundario.
- **¿Qué van a medir?** Consultas filtradas por fecha y categoría, con y sin índices, al menos tres repeticiones por operación, reportando la mediana.
- **¿Qué es WAL?** Write-Ahead Logging, modo de diario que permite lecturas mientras otro proceso escribe en ciertas condiciones y forma parte de la evidencia SQLite avanzada.
