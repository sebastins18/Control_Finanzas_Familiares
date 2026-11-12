# MisFinanzas S4 — entrega audiovisual corregida

> Registro audiovisual histórico del 6/11/2026: las 109 regresiones y 27 E2E corresponden a aquella grabación. No representa la suite final de Virtualmin del 12/11/2026 (122/122, 0 fallos, errores y omisiones, 123,43 s). El video final de la entrega `v1.0.0` del viernes 13 de noviembre de 2026 aún no tiene enlace definitivo. Los nombres `FINAL` y las comprobaciones técnicas no acreditan aprobación editorial o publicación.


Código evaluado: `8a88aeb`. Rama local de trabajo: `mejora/video-s4-sincronizado`. Windows, Python 3.12, SQLite, Playwright y FFmpeg/FFprobe.

- **27/27 E2E aprobadas; 0 fallidas y 0 omitidas.** HTML — `reportes/e2e/reportes/playwright.html` (archivo histórico no incluido en este checkout) · Markdown — `reportes/e2e/reportes/RESUMEN.md` (archivo histórico no incluido en este checkout).
- **109/109 de regresión**; instalación limpia, carga idempotente de **1.000** y respaldo íntegro correctos. Resultados — `reportes/complementarias/comprobaciones_adicionales.json` (archivo histórico no incluido en este checkout).
- Video nativo **1920 × 1080, 25 fps, 246.84 s**; sin escalado desde 720p.
- Voz Juan Neural reutilizada: mismos paquetes AAC, sin síntesis, cambios de tempo o tono.
- 19 escenas revisadas mediante fotogramas de acción, resultados y subtítulos. No se realizó escucha humana desde este entorno; la conservación de audio y sus tiempos se comprobaron técnicamente y con ASR local.

## Archivos finales

- MP4 narrado — `MisFinanzas_S4_FINAL_Narrado.mp4` (archivo histórico no incluido en este checkout).
- MP4 narrado y subtitulado — `MisFinanzas_S4_FINAL_Narrado_Subtitulado.mp4` (archivo histórico no incluido en este checkout). Los subtítulos están incrustados: no activar además el SRT.
- [SRT](MisFinanzas_S4_FINAL_Subtitulos.srt), [guion y tabla de sincronización](MisFinanzas_S4_FINAL_Guion.md), [validación](MisFinanzas_S4_FINAL_Validacion.md).
- Hoja de contacto de 19 escenas — `MisFinanzas_S4_FINAL_Hoja_Contacto.jpg` (archivo histórico no incluido en este checkout), muestras por escena — `reportes/revision_escenas/` (archivo histórico no incluido en este checkout), [12 capturas principales](capturas/).
- Montaje y fuente de cada corte — `reportes/montaje_edl.json` (archivo histórico no incluido en este checkout), inventario de 19 audios y escena 15 — `reportes/inventario_audio.json` (archivo histórico no incluido en este checkout), FFprobe — `reportes/ffprobe_final.json` (archivo histórico no incluido en este checkout).
- Propuesta de archivos para Git — `PROPUESTA_GIT.md` (archivo histórico no incluido en este checkout) y [guía para repetir](../../scripts/e2e/PRESENTACION.md).

Los originales del usuario siguen en `evidencias/` y la primera toma en `evidencias/s4/`. Las tomas intermedias están en `.venv-e2e/presentacion/` y no se incluyen en commits. La aplicación no cambió su lógica funcional. Toda escritura de prueba se realizó en SQLite temporal local, eliminada al cerrar.

S3 cerrado técnicamente y S4 desplegado en CRNube en `8a88aeb`, según confirmación del responsable. El GET propio al login devolvió 200. No se modificó el servidor. Quedan pendientes instalación independiente, revisión del grupo, publicación del video y evaluación docente. No se hizo push, merge ni publicación de tags.
