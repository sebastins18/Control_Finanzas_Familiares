# Matriz verificable de entrega — Seguimiento 4

**Versión final: `v1.0.0` — viernes 13 de noviembre de 2026.**

**Corte histórico:** 6/11/2026, Costa Rica · Grupo 5 · Universidad Nacional.
**Código del corte histórico:** `main`, `8a88aeb`. Los reportes del 12/11/2026 están incorporados en `af707b5`; esta revisión integral se realiza en `main`, sin commit.
**Referencia completa:** [S4](S4.md), [README](../../README.md) y [aporte de Diego](S4_APORTE_RESPALDO_DIEGO.md).

**Pruebas finales — Virtualmin, 12/11/2026:** **122/122 exitosas**, 0 fallos, 0 errores y 0 omisiones, en **123,43 segundos**. Las mediciones de rendimiento se realizaron por separado con 100.000 movimientos y cinco ejecuciones por escenario, reportando la mediana. Los [reportes y su trazabilidad](evidencia_final_pruebas.md) están incorporados en el repositorio. El video final continúa sin enlace definitivo.

| Requisito | Situación real | Evidencia y alcance |
| --- | --- | --- |
| Integración S1–S4 | Código integrado en main | `8a88aeb`; se conservan código, seguridad, respaldo, CI y pruebas |
| Explicación, arquitectura e instalación | Documentación consolidada | README, [arquitectura](../arquitectura/ARQUITECTURA_S4.md), [instalación](../INSTALACION_S4.md) |
| Despliegue S4 | Realizado el 6/11/2026 sobre `8a88aeb` | Responsable confirma respaldo SQLite consistente anterior; WAL, 17 tablas, integridad `ok`, FK 0 |
| Instalación limpia automática | Comprobada localmente | Resultados — `../../evidencias/s4_final/reportes/complementarias/comprobaciones_adicionales.json` (archivo histórico no incluido en este checkout); no equivale a validación independiente |
| Instalación por otro integrante usando solo README | Pendiente de evidencia humana | [Ficha de registro](S4.md#validación-independiente-por-otro-integrante), [acta](ACTA_S4.md) |
| Pruebas automatizadas finales | **122/122 exitosas**, 0 fallos, 0 errores y 0 omisiones; **123,43 segundos** | Virtualmin, **12/11/2026**; [suite original](../../evidencias/s4_final/reportes/virtualmin/suite.json) |
| Regresión histórica del 6/11/2026 | 109/109 correctas | Consola — `../../evidencias/s4_final/reportes/complementarias/regresion.txt` (archivo histórico no incluido en este checkout), 188.515 s; 103/105 son antecedentes |
| E2E histórica del 6/11/2026 | 27/27, 0 fallidas, 0 omitidas | Resumen local — `../../evidencias/s4_final/reportes/e2e/reportes/RESUMEN.md` (archivo histórico no incluido en este checkout) |
| Capturas funcionales | Existen localmente | [Capturas 1080p](../../evidencias/s4_final/capturas/) y serie original — `../../evidencias/s4/capturas/` (archivo histórico no incluido en este checkout); no se presupone publicación |
| Video auténtico | Grabación local existente | Original 720p y versiones de trabajo 1080p conservadas; [inventario](VIDEO_S4.md) |
| Video final sincronizado y acceso del profesor | En preparación; sin publicación acreditada | Revisión editorial y enlace público autorizado pendientes; nombres `FINAL` no prueban aceptación |
| CI | Ejecución histórica S4 correcta | [Run 42303414421](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421), `4cbf76a`, tres jobs; no se atribuye al HEAD actual una corrida nueva |
| SQLite y profundidad S3 | S3 cerrado técnicamente | [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3); volumen 100.000, índices/EQP, transacciones y errores; WAL/DELETE opcional |
| Licencia y roadmap | Documentados | [MIT](../../LICENSE), [plan futuro](../ROADMAP.md) |
| `portal.yml` | Conserva los 15 campos académicos | [Ficha](../../portal.yml); video/captura vacíos por URL autorizada pendiente, cuatro autores públicos registrados |
| Versión final `v1.0.0` | Viernes 13 de noviembre de 2026 | [Registro de cambios](../../CHANGELOG.md) y [trazabilidad](evidencia_final_pruebas.md) |
| Aportes individuales y comentarios docentes | Parcialmente documentados | Crédito de Diego Fonseca, `dfonseca15`, `4b0bfed`; [equipo](EVIDENCIA_EQUIPO.md) y acta por completar |

## Procedencia y decisión de entrega

El despliegue y el respaldo previo fueron confirmados por el responsable. La comprobación automática pública se limitó al GET del login; no certifica el commit remoto ni operaciones autenticadas. Las pruebas, cargas y grabaciones utilizaron SQLite temporal y datos ficticios. Los errores HTTP inducidos son casos esperados, no caídas públicas.

Los reportes actuales de Virtualmin están versionados en las rutas enlazadas e incorporados en `af707b5`. Los reportes originales históricos de regresión, E2E y comprobaciones no están disponibles en este checkout; sus rutas se conservan como referencia histórica sin hipervínculo y no como evidencia accesible para el profesor. ZIP y manifiestos anteriores conservan su fecha y alcance; no incluyen automáticamente esta revisión documental.

S4 está desplegado y cuenta con pruebas, capturas y video auténtico locales. **El cierre académico sigue pendiente** de la instalación independiente, preparación y revisión final del video sincronizado, publicación autorizada y acceso del profesor, revisión del candidato, acta y materiales de exposición. No se declara aprobación docente ni se realizan commit, push, merge o tags.
