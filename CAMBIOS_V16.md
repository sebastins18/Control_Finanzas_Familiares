# V16: errores controlados de SQLite

- Fallas de SQLite durante consultas y guardados: página amigable y estado HTTP 503.
- Fallas inesperadas: página genérica y estado HTTP 500 sin detalles internos.
- Registro técnico de errores en `logs/errores.log`, con rotación (2 MB y 3 respaldos).
- Al iniciar, si la base no se puede abrir, el proceso termina con mensaje breve y deja detalle en el log; no puede mostrar una página web porque el servidor aún no ha iniciado.
- Las operaciones hechas con `db.connect()` usan transacciones de SQLite y revierten cambios al producirse una excepción.
- Los reintentos son manuales para evitar duplicar operaciones de escritura.
- El sistema sigue siendo un prototipo académico: requiere medidas adicionales de seguridad y despliegue antes de exponerlo a Internet.

Prueba focalizada: `python -m unittest tests.test_sqlite_failure_v16 -v`.
