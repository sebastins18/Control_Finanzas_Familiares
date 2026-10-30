# Usuarios y permisos

Las cuentas se almacenan en la tabla `usuarios` de SQLite. El campo `rol` solo
admite `administrador` o `usuario`, mediante una restriccion CHECK y validacion
en el servidor. No existe una tabla ni un mantenimiento de roles.

Seguridad -> Mantenimiento de usuarios permite crear cuentas y modificar su
nombre completo, estado, contrasena y rol mediante dos opciones fijas. Solo los
administradores pueden administrar usuarios. No se permite desactivar ni quitar
los permisos al ultimo administrador activo.

Campos: `id_usuario`, `nombre`, `username` unico, `rol`, `activo`,
`password_salt` y `password_hash`. Las contrasenas usan PBKDF2-HMAC-SHA256.
La barra superior muestra el nombre completo del usuario conectado.

**Modo temporal actual:** `auth.STANDARD_USER_MODE=True` aplica permisos normales
a todas las sesiones, incluso si la cuenta conserva el rol administrador en
SQLite. Seguridad solo muestra Cambiar contraseña; las rutas de mantenimiento
de usuarios quedan bloqueadas. El encabezado muestra únicamente el nombre
completo. Los roles almacenados se conservan para poder reactivar la
administración posteriormente. Los permisos de propietario e invitado dentro
de cada perfil financiero siguen funcionando.

En el inicio de sesión, **Crear cuenta** abre `/registro`. El formulario solicita
nombre completo, usuario, contraseña y confirmación. Las cuentas registradas por
esta vía siempre tienen rol `usuario`, estado activo y un perfil financiero
inicial. Al finalizar se vuelve al inicio de sesión con una confirmación.

El usuario de acceso debe ser único, incluso al variar mayúsculas o agregar
espacios al principio o al final. La validación del servidor y los triggers de
SQLite impiden crear duplicados, también con solicitudes simultáneas. El nombre
completo sí puede repetirse. El registro no actualiza ni reemplaza una cuenta
existente. La cuenta y su perfil inicial se crean en una sola transacción.

Los datos financieros pertenecen ahora a perfiles independientes de las cuentas
de acceso. Consulta [perfiles financieros e invitados](perfiles_financieros.md)
para las relaciones, selección por sesión y permisos del propietario e invitados.

Una base nueva crea `admin` con contrasena `admin123!`, salvo que se configure
`FINANZAS_INITIAL_ADMIN_PASSWORD`. Inicializar nuevamente no restablece claves.

## Migracion

Al iniciar, `db.init_db()` crea un respaldo SQLite antes de migrar esquemas
anteriores. Los permisos anteriores se convierten segun `es_administrador`:
1 corresponde a `administrador`, y 0 a `usuario`. Conserva identificadores,
nombres, estados, contrasenas y relaciones financieras. Despues elimina
`usuarios.id_rol` y la tabla `roles`. La migracion es idempotente.

Tambien se mantiene la migracion desde el antiguo JSON de credenciales y el
modelo de perfiles. El JSON ya no se utiliza para iniciar sesion ni guardar
cambios. Los documentos anteriores describen versiones historicas.

Base predeterminada: `data/finanzas.sqlite3`, configurable mediante `DB_PATH`.
