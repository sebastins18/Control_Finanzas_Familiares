# Guion de exposición final — 20 a 25 minutos

La exposición exige demo en vivo de 8–10 minutos; **el video no la reemplaza**. Participan los cuatro integrantes y el profesor puede solicitar un cambio pequeño. Cronometrar y repartir las secciones con el equipo.

| Bloque | Duración | Presentación sugerida |
| --- | --- | --- |
| Problema, usuario, MVP | 2–3 min | Dispersión de ingresos y gastos familiares, límites y alertas |
| Arquitectura y datos | 4–6 min | Python estándar, SQLite como único motor, claves foráneas, WAL, índices, centavos enteros, transacciones y respaldos |
| Demo en vivo | 8–10 min | Registro, login, selección de perfil, crear gasto ficticio, consultar historial, editar y eliminar; presupuesto y alerta, exportar CSV |
| Pruebas y mediciones | 3–4 min | Casos normales/invalidación/fallo, suite, benchmark de 100k, EXPLAIN QUERY PLAN y explicación de la consulta que no mejora |
| Lecciones y roadmap | 3–4 min | Recuperación de errores, organización con PRs, próximos pasos, riesgos de seguridad y límites |

## Demo en vivo, con datos ficticios

1. Abrir en una sesión de prueba; no mostrar contraseña al público.
2. Mostrar el perfil financiero activo y el dashboard con ingreso/gasto por moneda.
3. Crear un gasto **ficticio** con descripción visible y verificar su aparición en el historial.
4. Editarlo y comprobar el saldo; eliminarlo y verificar que desaparece.
5. Mostrar categoría y presupuesto del período; provocar una alerta con una categoría ficticia sin gastos previos.
6. Mostrar historial filtrable, reporte anual y exportación CSV, en la instancia de ensayo preparada; el despliegue S4 confirmado corresponde a `8a88aeb`.
7. Abrir el panel de calidad solo con un usuario administrador de pruebas.
8. Enseñar en GitHub un PR auténtico de Diego y otro de Mariano, los tags y el Project. No atribuir commits inexistentes a Crystian.

## Respuestas para preguntas del profesor

- **¿Por qué SQLite?** Transacciones ACID, claves foráneas, WAL y portabilidad. Perfil A con profundidad.
- **¿Qué dato vive en SQLite?** Usuarios, perfiles, cuentas, categorías, movimientos, presupuestos, tasas, alertas, ahorros y registros recurrentes; los adjuntos se gestionan en archivos privados.
- **¿Qué ocurre al fallar SQLite?** Respuestas HTTP controladas, reversión transaccional, y caché de lectura solo para ciertas páginas; no se prometen reintentos ni cero pérdida.
- **¿Qué midieron?** Tres operaciones repetidas cinco veces, medianas, EXPLAIN QUERY PLAN y comparación con/sin índices sobre bases sintéticas temporales.
- **¿Todo índice es más rápido?** No: la agregación por categoría en la medición anterior fue más lenta con índice, por coste de acceso y agrupación.
- **¿Por qué no datos reales?** Seguridad del MVP todavía no endurecida (CSRF, sesiones persistentes, controles de infraestructura y privacidad).

## Video de 3–5 minutos (grabación local; final sincronizado en preparación)

Existen versiones de trabajo que conservan la voz es-CR-JuanNeural y 19 escenas reales nativas 1080p con desplazamientos y encuadres guiados por la narración. El video final sincronizado sigue en preparación y no está publicado: [inventario local](../../evidencias/s4_final/LEEME.md), [guion y sincronización](../../evidencias/s4_final/MisFinanzas_S4_FINAL_Guion.md), [validación](../../evidencias/s4_final/MisFinanzas_S4_FINAL_Validacion.md). [Repetir la demostración](../../scripts/e2e/PRESENTACION.md). La referencia al MP4 sin audio que sigue corresponde a la primera toma y se conserva como antecedente.

Grabación auténtica del 6/11/2026: [MP4 de 4 min 6,84 s](../../evidencias/s4/video/MisFinanzas_S4.mp4), sin audio, con [guion sincronizado](../../evidencias/s4/GUION_PRESENTACION.md). Registra Chromium real sobre SQLite temporal: login, CRUD, presupuestos, alertas, historial, reporte, validaciones y resultados. El [informe](../../evidencias/s4/reportes/playwright.html) registra 27 aprobadas, 0 fallidas y 0 omitidas. La publicación y los permisos de acceso del profesor siguen pendientes.

Los nombres de archivo `FINAL` y los informes técnicos no equivalen a aceptación editorial. Revisar y escuchar la versión elegida antes de publicarla con autorización.

Propuesta de secuencia: 0:00 problema; 0:30 arquitectura; 1:10 login y CRUD; 2:30 presupuesto y alertas; 3:20 pruebas e índices; 4:15 conclusión. Grabar **pantalla real**, no usar imágenes sintéticas como si fueran funcionamiento comprobado. Tras revisión y autorización, subir a una dirección accesible al profesor, confirmar permisos y agregar el enlace en `README.md` y `portal.yml`.

## Capturas requeridas

- [x] Login y dashboard reales con usuario ficticio, sin datos personales: [capturas](../../evidencias/s4/capturas/).
- [x] Gasto creado, modificado y eliminado desde interfaz.
- [x] Presupuesto y alertas exactas del 80 % y 100 %.
- [ ] GitHub Actions y tabla de mediciones.
- [x] Reporte anual e historial en instancia local aislada: [evidencia](../../evidencias/s4/reportes/RESUMEN.md). La disponibilidad autenticada en el servidor no se comprobó.
- [x] Fecha de grabación local: 6/11/2026; archivos y capturas enlazados en [VIDEO_S4](VIDEO_S4.md).
- [ ] Video final sincronizado revisado, URL pública autorizada y acceso del profesor.
- [ ] Evidencia de instalación hecha por otra persona usando solo README.

**Protección de datos:** no incluir cédulas, contraseñas, tokens, rutas privadas o datos financieros en GitHub público ni en video.

## Material complementario validado para S4

- [Matriz de cumplimiento](ENTREGA_S4.md) y [arquitectura vigente](../arquitectura/ARQUITECTURA_S4.md).
- [Guion breve para grabar el video real](VIDEO_S4.md) y [acta pendiente](ACTA_S4.md).
- [CI del merge de S4](https://github.com/sebastins18/Control_Finanzas_Familiares/actions/runs/42303414421) con tres trabajos aprobados. La evidencia local vigente registra 109/109 regresiones y 27/27 E2E: [resumen](../../evidencias/s4_final/reportes/e2e/reportes/RESUMEN.md). El CI enlazado conserva su commit y fecha históricos.
- El responsable confirmó S4 desplegado en CRNube, commit `8a88aeb`, con respaldo previo consistente. Para esta demostración se utiliza una instancia local aislada; solo se comprobó GET público del login. No se accedió a WebAdmin ni se cambió el servidor. SQLite del despliegue: WAL, 17 tablas, integridad `ok`, FK 0, según el responsable. S3 está cerrado técnicamente en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3). `v0.9.0` no se encontró en la consulta remota de tags al corte.

Los enlaces relativos identifican evidencia local, no publicación acreditada. La [matriz S4](S4.md) recupera la documentación académica de Diego Fonseca (`dfonseca15`, `4b0bfed`) sin sustituir las validaciones humanas pendientes.
