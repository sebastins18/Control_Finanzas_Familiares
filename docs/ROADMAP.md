# Roadmap posterior a S4

**Referencia:** corte S4 del 6/11/2026, código `8a88aeb`. Plan consolidado con el aporte documental de Diego Fonseca (`dfonseca15`, `4b0bfed`). Son propuestas futuras, no funcionalidades entregadas ni fechas comprometidas por el equipo.

## Próximo mes — horizonte diciembre de 2026

| Trabajo propuesto | Resultado que permitiría verificarlo |
| --- | --- |
| Cerrar las evidencias académicas pendientes | Instalación independiente identificada, acta real, video final sincronizado revisado y publicación autorizada accesible al profesor |
| Completar protección CSRF, defensa contra fuerza bruta y revisión de permisos | Pruebas de rechazo de formularios y accesos indebidos; cookie Secure comprobada bajo HTTPS, cuyo soporte ya existe |
| Revisar recuperación de contraseña por administrador y diseñar recuperación segura | Procedimiento documentado y verificado; no presentar `/olvide-clave` como autoservicio actual |
| Mejorar diseño responsive, accesibilidad y mensajes de error | Recorridos manuales con teclado y navegador real, con incidencias resueltas y evidencia |
| Ensayar restauración de respaldo SQLite y vigilar el proceso en CRNube | Restauración aislada validada y solución de supervisión permitida por la institución; el respaldo consistente ya existe |

## Próximos seis meses — horizonte mayo de 2027

| Trabajo propuesto | Resultado que permitiría verificarlo |
| --- | --- |
| Migrar `http.server` a un servidor WSGI/ASGI adecuado y sesiones persistentes | Instalación reproducible, monitoreo, logging y pruebas de actualización sin pérdida de datos |
| Ampliar gráficos y reportes comparativos | Casos de uso y pruebas con datos ficticios; historial, reporte anual y CSV actuales se conservan |
| Mejorar importación/exportación CSV y filtros | Validación de archivos, errores comprensibles y pruebas de ida y vuelta; no asumir que la importación ya está implementada |
| Evaluar notificaciones de presupuesto | Consentimiento, privacidad y entrega verificable; las alertas visuales actuales de 80/100 % son el punto de partida |
| Automatizar política de respaldo, restauración y gestión de adjuntos | Retención, cuotas, cifrado según riesgo y simulacro de recuperación documentado |
| Profundizar seguridad, privacidad y evolución del esquema | Auditoría por recurso, minimización de datos y CI con pruebas de seguridad/migración |

La comparación experimental WAL/DELETE puede ampliarse como investigación opcional. No es una condición pendiente del cierre técnico de S3, ya documentado en [Issue #3](https://github.com/sebastins18/Control_Finanzas_Familiares/issues/3).

## Posible trabajo final de graduación

Investigar usabilidad y eficacia de un sistema abierto de educación y control financiero familiar, con indicadores de planificación, presupuestos y recomendaciones explicables. Requiere diseño metodológico, consentimiento, protección de información personal y evaluación con usuarios reales. No forma parte del MVP académico entregado ni implica recomendaciones financieras actuales.
