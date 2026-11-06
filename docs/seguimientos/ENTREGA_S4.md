# Matriz verificable de entrega — Seguimiento 4

**Fecha de corte:** viernes 6 de noviembre de 2026 · **Grupo 5** · Universidad Nacional.  
**Código fuente:** https://github.com/sebastins18/Control_Finanzas_Familiares  
**Integración:** [PR #20](https://github.com/sebastins18/Control_Finanzas_Familiares/pull/20), merge `4cbf76ae8c143118b01aec890f35bc20f7a95782`.  
**CI de `main`:** [ejecución 42303414421](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421) finalizada `success` (Linux Python 3.11/3.12 y Windows Python 3.12).

## Estado por requisito

| Requisito | Estado | Evidencia |
| --- | --- | --- |
| Código central S1–S4 consolidado en `main` | **Cumplido** | Todos los PR integrados y sin PR abiertos al corte |
| Bitácora `S4.md` | **Cumplido** | [S4.md](S4.md) |
| README de problema, alcance, instalación, enlaces | **Cumplido con salvedades de demo final** | [README](../../README.md) |
| `portal.yml` | **Preparado, incompleto** | Video, captura auténtica y autores públicos sin datos confirmados |
| Instalación local limpia reproducible | **Comprobada automáticamente** | `scripts/verify_clean_install_s4.py`; salida Windows `INSTALACION LIMPIA S4: OK` |
| Instalar siguiendo instrucciones, por persona distinta | **Pendiente de evidencia independiente** | [ACTA_S4.md](ACTA_S4.md) |
| Suite completa en Windows | **Cumplido** | 109/109 tests, 164.704 s, salida compartida por el equipo el 6/11 |
| CI Linux y Windows en `main` | **Cumplido** | [GitHub Actions](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421) |
| SQLite: índices, consultas, transacciones, errores y backups | **Cumplido en pruebas documentadas** | [S3 mediciones](S3_mediciones.md), [índices](indices_s3.md), tests y scripts S4 |
| Borrador de guion y presentación | **Preparado para revisión** | [Guía de exposición](GUIA_DEMO_FINAL.md) |
| Capturas actuales de S4 | **Pendiente** | Realizar desde aplicación de prueba con datos ficticios |
| Video real de 3–5 minutos y enlace público | **Pendiente** | [Guion para grabación](VIDEO_S4.md) |
| Tag release candidate `v0.9.0` | **Pendiente** | No había sido publicado en la última comprobación; requiere revisión del equipo |
| Tag `v1.0.0` + PDF de Aula Virtual | **Pendiente para día de exposición** | No adelantarlo ni publicar datos personales |
| Despliegue S4 en CRNube | **No ejecutado por instrucción del responsable** | Queda expresamente fuera de esta fase |
| Colaboración de los cuatro y comentarios del docente | **Parcial** | Commits verificables de Sebastián, Diego y Mariano; evidencia de Crystian/acta pendiente |

## Alcance de los resultados

Los casos HTTP 400/401/403/503 provocados por el test runner verifican validaciones y manejo de fallos; no son incidencias de la web pública. Se ejecutaron sobre bases temporales. La salida `109 tests ... OK` corresponde a la terminal Windows aportada; los tres jobs CI son una comprobación independiente de GitHub. No se afirma que un tercero haya realizado la instalación o que el despliegue S4 esté funcionando en el servidor.

## Decisión de entrega

S4 está **técnicamente preparado**, pero **no cerrado académicamente** sin: (1) revisión del grupo y etiqueta de versión, (2) instalación realmente hecha por otro integrante, (3) capturas y video auténticos, (4) acta/participantes, y (5) materiales finales de exposición según la semana asignada.

Los campos no confirmados se dejan vacíos, en lugar de inventar nombres, imágenes, calificaciones o aprobaciones.
