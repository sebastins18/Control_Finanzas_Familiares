# Validación final de MisFinanzas S4

Fecha: 2026-11-06T19:47:34-06:00.

- Dos MP4 decodificados íntegramente con FFmpeg: H.264 y AAC, 1920 × 1080 nativos, 25 fps.
- Duración: 246.84 segundos; diferencia entre pistas menor de 50 ms.
- Los paquetes AAC son idénticos al audio aceptado. Sin regeneración, filtros de tempo, cambios de tono ni remezcla.
- 19 escenas capturadas nuevamente con Playwright sobre SQLite temporal aislada; consultas de contraste en modo de solo lectura.
- Recorrido funcional independiente: 27 aprobadas, 0 fallidas, 0 omitidas; regresión completa: 109/109.
- Instalación automática, carga idempotente de 1.000 movimientos y respaldo consistente: aprobados; integridad ok y FK 0.
- Escena 15: existen MP3 y WAV originales; la transcripción coincide con tabla anual y exportación. La caché del generador explica una posible omisión de la línea de síntesis, pero no se dispone de aquel log para afirmarlo como hecho.
- Hoja de contacto de 19 escenas y muestras de inicio, acción y resultado en reportes/revision_escenas/.
- No se realizó escucha humana del audio desde este entorno. La revisión usa transcripción local, conservación exacta de paquetes, detección de silencio, lectura de subtítulos y fotogramas por escena.

| Escena | Resultado de revisión visual |
|---|---|
| 01 | Revisada: presentación editorial separada del login real; tecnologías y subtítulos legibles. |
| 02 | Revisada: formulario completo, contraseña enmascarada, ingreso y selección del perfil ficticio. |
| 03 | Revisada: saldos, resumen y ausencia inicial de movimientos aparecen mediante scroll. |
| 04 | Revisada: cuentas y CRUD de categoría; cortes cronológicos muestran formularios y registros al mencionarlos. |
| 05 | Revisada: formulario completo CRC 1.000 y movimiento registrado antes de la comprobación narrada. |
| 06 | Revisada: gasto CRC 25, categoría y descripción; resultado registrado visible. |
| 07 | Revisada: gasto previo, campos CRC 35 y descripción modificada, resultado posterior. |
| 08 | Revisada: eliminación visible y ausencia del gasto; permanece el ingreso. |
| 09 | Revisada: presupuesto CRC 100 y estado inicial centrados durante la explicación. |
| 10 | Revisada: Cerca del límite y 80/100 visibles; después se muestra la alerta 80 persistida. |
| 11 | Revisada: formulario +20, Excedido 100/100 y tabla de alertas 80 y 100. |
| 12 | Revisada: tres movimientos y totales 1.000/100 en el mismo encuadre. |
| 13 | Revisada: filtros visibles y resultado único CRC 80; se mantiene mientras se explica el CSV filtrado. |
| 14 | Revisada: reporte anual, navegación por año y botón CSV visibles antes de su explicación. |
| 15 | Revisada y corregida: tabla anual seguida del visor del CSV auténtico; categoría, mes, año y totales 1.000/100 legibles durante la narración. |
| 16 | Revisada: -10 y burbuja nativa de Chromium visibles durante el mensaje de validación. |
| 17 | Revisada: error controlado de monto mayor que cero visible durante la explicación HTTP 400. |
| 18 | Revisada: identidad ficticia, rechazo 403 y login después del cierre de sesión. |
| 19 | Revisada: 27/27, 109/109, 1.000, instalación, respaldo e integridad; pendientes humanos separados. |

La confirmación del responsable de que S3 está cerrado y S4 desplegado se documenta separadamente de estas pruebas locales. Solo se hizo GET del login público; no se accedió a WebAdmin ni se modificó CRNube.
Pendientes humanos: revisión del grupo, instalación independiente, publicación del video y evaluación docente. No se acredita aprobación del profesor.
