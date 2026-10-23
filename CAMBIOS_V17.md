# V17 - Control de mensajes y solicitudes
- Las respuestas HTTP de error no se almacenan en caché y los errores del servidor indican un tiempo sugerido antes de reintentar.
- Los formularios POST evitan el doble envío accidental durante la misma carga de página.
- No se agregan ventanas emergentes de error, temporizadores ni reintentos automáticos.
- Las fallas SQLite siguen mostrando una única página de error amigable, con registro técnico en logs/errores.log.
- No se garantiza recuperación automática si la base de datos falla durante el arranque.
