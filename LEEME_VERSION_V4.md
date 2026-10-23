# Finanzas Familiares — Integración v4

## Ejecución en Windows 11

1. Descomprime el archivo ZIP.
2. Abre PowerShell en la carpeta `Control_Finanzas_Familiares-main`.
3. Ejecuta `python -m src.app` (Python 3.11 o superior).
4. Visita http://127.0.0.1:8000.
5. Para detener, presiona Ctrl+C.

No requiere instalar paquetes externos. Para probar las funciones, ejecuta `python -m unittest discover -s tests -v`.

## Novedades

- Menú superior agrupado en Operaciones, Planificación, Catálogos y Perfiles.
- Comprobantes de gastos: PDF, PNG, JPEG y WebP (máximo 5 MB). Se guardan en `data/comprobantes` y se asocian a gastos existentes.
- Alertas automáticas al 80 % y 100 % del límite mensual. Se recalculan al visitar el panel o registrar cambios desde la aplicación. Pueden marcarse como leídas desde Alertas.
- Presupuestos en CRC, USD, EUR u otras monedas registradas. Los gastos del panel se registran en CRC y se convierten al presupuesto con el tipo de cambio histórico más reciente no posterior a la fecha del gasto.
- Perfiles locales: selecciona un perfil en el menú. Cada perfil tiene sus cuentas, categorías, presupuestos y movimientos. Los catálogos de monedas y tipos de cambio son compartidos.

## Consideraciones

- Haz una copia de `data/finanzas.sqlite3` y de `data/comprobantes` antes de actualizar. El proyecto nuevo no incluye tus datos anteriores.
- Los archivos adjuntos quedan guardados fuera de SQLite, en el disco local; respáldalos junto con la base de datos.
- Si no existe tipo de cambio histórico para un gasto, el presupuesto muestra un total parcial y un aviso; las alertas pueden subestimar el gasto hasta que se registre el tipo de cambio faltante.
- Los indicadores generales de ingresos y gastos siguen expresándose en CRC; los saldos de las cuentas se muestran en su propia moneda.
- La selección de perfil no tiene contraseña ni controles de acceso. No publicar en Internet ni utilizar información financiera sensible.
- Los datos de tipo de cambio son introducidos manualmente; no se consultan fuentes bancarias automáticamente.
- No hay envío de alertas por correo ni notificaciones externas; aparecen dentro de la aplicación.

## Pruebas

13 pruebas automatizadas cubren funciones originales y pruebas adicionales de perfiles, presupuestos multimoneda, alertas y páginas de mantenimiento. También conviene probar manualmente adjuntos desde el navegador y operaciones de edición/eliminación.
