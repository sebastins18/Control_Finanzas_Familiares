# Video auténtico S4 — estado, guion y preparación final

**Corte:** 6/11/2026, Costa Rica. Existe grabación real de la aplicación. **El video final sincronizado sigue en preparación y no se declara publicado.** La situación vigente se registra aquí, aunque algunos archivos locales lleven `FINAL` en el nombre o describan comprobaciones técnicas ya realizadas.

## Material local conservado

| Material | Archivo real y alcance |
| --- | --- |
| Primera grabación completa | [MP4 720p, 4 min 6,84 s, sin audio](../../evidencias/s4/video/MisFinanzas_S4.mp4); [guion de esa toma](../../evidencias/s4/GUION_PRESENTACION.md) |
| Trabajo posterior en 1080p | [Inventario local](../../evidencias/s4_final/LEEME.md), 19 escenas, voz es-CR-JuanNeural existente, encuadres y desplazamientos guiados por la narración |
| Guion y subtítulos de trabajo | [Guion](../../evidencias/s4_final/MisFinanzas_S4_FINAL_Guion.md), [SRT](../../evidencias/s4_final/MisFinanzas_S4_FINAL_Subtitulos.srt) |
| Revisiones técnicas existentes | [Validación audiovisual local](../../evidencias/s4_final/MisFinanzas_S4_FINAL_Validacion.md); son registros técnicos, no aprobación editorial o docente |
| Capturas reales | [Serie 1080p](../../evidencias/s4_final/capturas/) y [serie original](../../evidencias/s4/capturas/) |
| Pruebas actuales | [27 E2E correctas](../../evidencias/s4_final/reportes/e2e/reportes/RESUMEN.md) y [109 regresiones correctas](../../evidencias/s4_final/reportes/complementarias/regresion.txt) |
| Reproducibilidad | [QA](../../scripts/e2e/README.md), [presentación](../../scripts/e2e/PRESENTACION.md) |

Las grabaciones muestran Chromium y SQLite temporal con datos ficticios, código `8a88aeb`; no simulan una interfaz implementada. S4 fue desplegado en CRNube el 6/11/2026 con respaldo previo, WAL, 17 tablas, integridad `ok` y FK 0, según el responsable. Esta producción local no administra el servidor: su GET público no demuestra operaciones autenticadas.

Los archivos y ZIP anteriores se conservan como evidencia de sus ejecuciones. No se reetiquetan ni se reescriben sus resultados históricos. Su presencia local no garantiza que estén publicados en GitHub o disponibles para el profesor.

## Guion orientativo de 3–5 minutos

La siguiente tabla conserva la propuesta de contenido. Para sincronizar cada toma deben usarse su guion y tiempos reales, sin tratar estos rangos orientativos como una edición final aceptada.

| Tiempo orientativo | Pantalla o acción real | Contenido |
| --- | --- | --- |
| 0:00–0:25 | Proyecto y aplicación | Problema y destinatarios |
| 0:25–0:55 | Arquitectura | Python estándar, SQLite, transacciones y WAL |
| 0:55–1:35 | Login y panel ficticio | Perfil, cuentas y saldos |
| 1:35–2:30 | Crear, consultar, editar y eliminar gasto | Persistencia, validación y CRUD |
| 2:30–3:10 | Presupuesto | Estados y alertas del 80 % y 100 % |
| 3:10–3:45 | Historial, reporte y CSV | Filtros, exportación y recurrentes |
| 3:45–4:20 | Pruebas y mediciones | 109 regresiones, 27 E2E; CI histórico e índices/EQP correctamente fechados |
| 4:20–4:40 | Conclusiones | Límites, roadmap y próximos pasos |

## Cierre editorial y publicación pendientes

- [x] Hay grabación de pantalla auténtica y capturas locales con datos sintéticos.
- [x] La primera toma completa documenta 246,84 s; hay comprobaciones técnicas de las versiones posteriores.
- [ ] Finalizar y revisar la sincronización de voz, acciones y subtítulos en la versión elegida, escuchando y viendo el video completo.
- [ ] Confirmar con el grupo la versión final y revisar que no muestre secretos ni datos personales.
- [ ] Publicar únicamente con autorización y comprobar acceso del profesor desde una sesión apropiada.
- [ ] Agregar la URL real aprobada a `portal.yml`, README y [acta](ACTA_S4.md); actualmente no existe un enlace público acreditado.

`demo_video` permanece vacío por la URL pendiente, no por ausencia de grabación. `captura` permanece vacío por publicación autorizada pendiente, no por ausencia de capturas. No es necesario moverlas a `docs/img/`: se enlaza su ubicación auténtica.

El video de 3–5 minutos no sustituye la demo en vivo de 8–10 minutos de la [guía de exposición](GUIA_DEMO_FINAL.md), la instalación por otro integrante ni la aprobación docente. S3 está cerrado técnicamente en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3). No se publican tags ni video con esta revisión documental.
