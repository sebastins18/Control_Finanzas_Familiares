# V13: acceso de administrador y cambio de contraseña

Ejecute `python -m src.app` y abra http://127.0.0.1:8000.

**Primer inicio:** usuario `admin`, contraseña `Admin12345!`. No necesita configurar variables de entorno.

En el menú seleccione **Cambiar contraseña**, introduzca la actual, la nueva y su confirmación. Después del cambio deberá iniciar sesión nuevamente con la nueva contraseña. Se almacena un hash con sal, no la contraseña en texto plano.

Si ya usó V12 y existe `data/login_credentials.json`, se mantiene la contraseña configurada previamente; la clave inicial no reemplaza credenciales existentes. Mantenga ese archivo al actualizar la aplicación.

La contraseña inicial es conocida y debe cambiarse inmediatamente. Aplicación para uso local, no para publicación directa en Internet.
