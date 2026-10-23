# V12: tipo de cambio manual e inicio de sesión

No se consulta ningún servicio externo de divisas. Para transferencias entre monedas distintas se requiere introducir un tipo de cambio positivo de máximo dos decimales. Para cuentas con la misma moneda no se pide conversión.

## Primer inicio (PowerShell)

```powershell
$env:FINANZAS_ADMIN_PASSWORD="CambieEstaClaveSegura123"
python -m src.app
```

Abra http://127.0.0.1:8000/login. Usuario: `admin`. Contraseña: la configurada en la variable de entorno. En el primer inicio se almacena únicamente el hash de la contraseña en `data/login_credentials.json`. En los siguientes inicios basta `python -m src.app` y se mantiene la contraseña original. Para restablecer la contraseña, detenga el servidor, elimine únicamente `data/login_credentials.json` y configure una contraseña nueva antes de reiniciar. No elimine `data/finanzas.sqlite3`.

Las sesiones se mantienen en memoria y caducan después de ocho horas sin actividad. Se incluye el botón Cerrar sesión. Este inicio de sesión protege el acceso a la aplicación, pero los perfiles familiares existentes siguen siendo seleccionables después de ingresar y no constituyen cuentas independientes. Solo se recomienda su uso local.
