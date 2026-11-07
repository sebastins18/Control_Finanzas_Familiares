# Matriz verificable de entrega — Seguimiento 4

**Corte:** 6/11/2026, Costa Rica · Grupo 5 · Universidad Nacional.
**Código vigente:** `main`, `8a88aeb`. **Documentación:** consolidación local en `mejora/video-s4-sincronizado`, sin commit.
**Referencia completa:** [S4](S4.md), [README](../../README.md) y [aporte de Diego](S4_APORTE_RESPALDO_DIEGO.md).

| Requisito | Situación real | Evidencia y alcance |
| --- | --- | --- |
| Integración S1–S4 | Código integrado en main | `8a88aeb`; se conservan código, seguridad, respaldo, CI y pruebas |
| Explicación, arquitectura e instalación | Documentación consolidada | README, [arquitectura](../arquitectura/ARQUITECTURA_S4.md), [instalación](../INSTALACION_S4.md) |
| Despliegue S4 | Realizado el 6/11/2026 sobre `8a88aeb` | Responsable confirma respaldo SQLite consistente anterior; WAL, 17 tablas, integridad `ok`, FK 0 |
| Instalación limpia automática | Comprobada localmente | [Resultados](../../evidencias/s4_final/reportes/complementarias/comprobaciones_adicionales.json); no equivale a validación independiente |
| Instalación por otro integrante usando solo README | Pendiente de evidencia humana | [Ficha de registro](S4.md#validación-independiente-por-otro-integrante), [acta](ACTA_S4.md) |
| Regresión vigente | 109/109 correctas | [Consola](../../evidencias/s4_final/reportes/complementarias/regresion.txt), 188.515 s; 103/105 son antecedentes |
| E2E vigente | 27/27, 0 fallidas, 0 omitidas | [Resumen local](../../evidencias/s4_final/reportes/e2e/reportes/RESUMEN.md) |
| Capturas funcionales | Existen localmente | [Capturas 1080p](../../evidencias/s4_final/capturas/) y [serie original](../../evidencias/s4/capturas/); no se presupone publicación |
| Video auténtico | Grabación local existente | Original 720p y versiones de trabajo 1080p conservadas; [inventario](VIDEO_S4.md) |
| Video final sincronizado y acceso del profesor | En preparación; sin publicación acreditada | Revisión editorial y enlace público autorizado pendientes; nombres `FINAL` no prueban aceptación |
| CI | Ejecución histórica S4 correcta | [Run 42303414421](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421), `4cbf76a`, tres jobs; no se atribuye al HEAD actual una corrida nueva |
| SQLite y profundidad S3 | S3 cerrado técnicamente | [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3); volumen 100.000, índices/EQP, transacciones y errores; WAL/DELETE opcional |
| Licencia y roadmap | Documentados | [MIT](../../LICENSE), [plan futuro](../ROADMAP.md) |
| `portal.yml` | Conserva los 15 campos académicos | [Ficha](../../portal.yml); video/captura vacíos por URL autorizada pendiente, autores públicos vacíos |
| `v0.9.0` | No publicado según consulta remota al corte | Verificado con `git ls-remote --heads --tags origin`; publicar requiere autorización |
| `v1.0.0`, exposición y PDF | Pendientes | Fecha asignada y requisitos finales por confirmar; sin datos personales públicos |
| Aportes individuales y comentarios docentes | Parcialmente documentados | Crédito de Diego Fonseca, `dfonseca15`, `4b0bfed`; [equipo](EVIDENCIA_EQUIPO.md) y acta por completar |

## Procedencia y decisión de entrega

El despliegue y el respaldo previo fueron confirmados por el responsable. La comprobación automática pública se limitó al GET del login; no certifica el commit remoto ni operaciones autenticadas. Las pruebas, cargas y grabaciones utilizaron SQLite temporal y datos ficticios. Los errores HTTP inducidos son casos esperados, no caídas públicas.

Los archivos enlazados bajo `evidencias/` existen en este espacio local. No se afirma que estén subidos a GitHub o disponibles para el profesor. ZIP y manifiestos anteriores conservan su fecha y alcance; no incluyen automáticamente esta revisión documental.

S4 está desplegado y cuenta con pruebas, capturas y video auténtico locales. **El cierre académico sigue pendiente** de la instalación independiente, preparación y revisión final del video sincronizado, publicación autorizada y acceso del profesor, revisión del candidato, acta y materiales de exposición. No se declara aprobación docente ni se realizan commit, push, merge o tags.
