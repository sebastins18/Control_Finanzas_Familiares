# Guion de grabación auténtica del MVP — 3–5 minutos

**Este documento no es un video ni certifica que haya sido grabado.** La grabación debe hacerse sobre la aplicación funcionando de verdad, preferiblemente con una base de datos ficticia aislada.

| Tiempo orientativo | Pantalla o acción real | Narración sugerida |
| --- | --- | --- |
| 0:00–0:25 | Título del proyecto y aplicación | Problema: ingresos y gastos familiares dispersos |
| 0:25–0:55 | Arquitectura simple del repositorio | Python, un solo motor SQLite, transacciones y WAL |
| 0:55–1:35 | Login + panel financiero sin datos personales | Perfiles, cuentas y saldos |
| 1:35–2:30 | Crear, consultar, editar y eliminar un gasto ficticio | Persistencia SQLite, validaciones y CRUD |
| 2:30–3:10 | Presupuesto y alerta real de límite | Estado de umbrales del 80 % y 100 % |
| 3:10–3:45 | Historial filtrable y exportación CSV | Búsqueda, reportes y movimientos recurrentes |
| 3:45–4:20 | Pruebas GitHub Actions / S3 | CI 3 entornos, índices y EXPLAIN QUERY PLAN |
| 4:20–4:40 | Conclusiones y limitaciones | MVP académico y mejoras futuras |

## Verificación antes de publicar

- [ ] Grabar pantalla real, no generar interfaz ficticia como si estuviera implementada.
- [ ] Eliminar contraseñas, tokens, cédulas y datos bancarios de pantalla/audio.
- [ ] Usar movimientos sintéticos y eliminar los creados para la demostración si aplica.
- [ ] Comprobar que el video dura entre tres y cinco minutos.
- [ ] Confirmar el permiso de uso del enlace para el profesor.
- [ ] Colocar URL final en `portal.yml`, README y [ACTA_S4.md](ACTA_S4.md).
- [ ] Capturas auténticas del flujo en `docs/img/` con consentimiento del equipo.

## Para la exposición oral

Video de 3–5 minutos **no sustituye** la demo en vivo de 8–10 minutos descrita en [GUIA_DEMO_FINAL.md](GUIA_DEMO_FINAL.md).
