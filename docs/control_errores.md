# Control de errores de SQLite

Las solicitudes GET y POST pasan por `controlled_request` en `src/app.py`,
incluidas las consultas de autenticación y permisos. La página de error se
construye sin consultar SQLite para poder mostrarse aunque la base falle.

| Situación | Respuesta |
| --- | --- |
| Datos duplicados o restricciones de integridad | 409 y explicación de los datos o relaciones que deben revisarse |
| Base ocupada, inaccesible o consulta interrumpida | 503 y mensaje para volver a intentarlo manualmente |
| Formato incorrecto en la solicitud | 400 y aviso de revisión |
| Fallo inesperado | 500, sin traza ni rutas internas en pantalla |

No hay recarga automática ni reenvío automático de formularios. Si falla una
solicitud de modificación, se recomienda comprobar el resultado antes de repetir:
una operación anterior de la misma solicitud podría haber terminado correctamente.

`db.connect()` centraliza la apertura, transacciones y cierre. Una excepción en
una transacción revierte sus cambios; los recursos se cierran al salir. SQLite
espera hasta 3 segundos por bloqueo. Un manejador de progreso interrumpe consultas
al detectar que se excedieron los 8 segundos del contexto, comprobando cada 1000
instrucciones de SQLite. Es un límite cooperativo, no una garantía de tiempo real
para operaciones del sistema operativo o código Python. Las copias de migración
también tienen un límite de espera. No se implementan bucles de reintentos.

Los detalles quedan en `logs/errores.log`, junto a la base indicada por `DB_PATH`,
con rotación. Si ese archivo no puede abrirse, el servidor utiliza su salida de
errores. Los scripts de inicialización, seed, carga masiva, evidencia y conexión
usan `db.cli_errors()`: terminan con código 1 y un mensaje legible. Sus detalles
van a `logs/errores_scripts.log` si el almacenamiento lo permite.

Las pruebas usan SQLite temporal: autenticación sin base, bloqueo real,
restricciones, transacciones revertidas, cierre de conexiones, interrupción de
consultas, errores inesperados y continuidad del servidor después del fallo.
