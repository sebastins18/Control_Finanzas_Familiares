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
6. Mostrar historial filtrable, reporte anual y exportación CSV, si el estado desplegado coincide con \`main\`.
7. Abrir el panel de calidad solo con un usuario administrador de pruebas.
8. Enseñar en GitHub un PR auténtico de Diego y otro de Mariano, los tags y el Project. No atribuir commits inexistentes a Crystian.

## Respuestas para preguntas del profesor

- **¿Por qué SQLite?** Transacciones ACID, claves foráneas, WAL y portabilidad. Perfil A con profundidad.
- **¿Qué dato vive en SQLite?** Usuarios, perfiles, cuentas, categorías, movimientos, presupuestos, tasas, alertas, ahorros y registros recurrentes; los adjuntos se gestionan en archivos privados.
- **¿Qué ocurre al fallar SQLite?** Respuestas HTTP controladas, reversión transaccional, y caché de lectura solo para ciertas páginas; no se prometen reintentos ni cero pérdida.
- **¿Qué midieron?** Tres operaciones repetidas cinco veces, medianas, EXPLAIN QUERY PLAN y comparación con/sin índices sobre bases sintéticas temporales.
- **¿Todo índice es más rápido?** No: la agregación por categoría en la medición anterior fue más lenta con índice, por coste de acceso y agrupación.
- **¿Por qué no datos reales?** Seguridad del MVP todavía no endurecida (CSRF, sesiones persistentes, controles de infraestructura y privacidad).

## Video de 3–5 minutos (pendiente de grabación)

Propuesta de secuencia: 0:00 problema; 0:30 arquitectura; 1:10 login y CRUD; 2:30 presupuesto y alertas; 3:20 pruebas e índices; 4:15 conclusión. Grabar **pantalla real**, no usar imágenes sintéticas como si fueran funcionamiento comprobado. Subir a una dirección accesible al profesor, confirmar permisos, agregar el enlace en \`README.md\` y \`portal.yml\`.

## Capturas requeridas

- [ ] Login y dashboard reales sin usuarios ni datos personales.
- [ ] Gasto creado, modificado y eliminado desde interfaz.
- [ ] Presupuesto y alerta de ejemplo.
- [ ] GitHub Actions y tabla de mediciones.
- [ ] Reporte anual e historial (si funcionan en el servidor al momento de exponer).
- [ ] URL final del video, fecha de grabación y evidencia de instalación hecha por otra persona.

**Protección de datos:** no incluir cédulas, contraseñas, tokens, rutas privadas o datos financieros en GitHub público ni en video.
