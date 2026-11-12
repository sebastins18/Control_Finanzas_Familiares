# Versión integrada para pruebas locales

Ejecutar desde la carpeta raíz: `python -m src.app` y visitar http://127.0.0.1:8000.

Incluye mantenimientos de usuarios locales, categorías, cuentas, monedas, tipos de cambio, presupuestos, alertas, metas, transferencias y movimientos de ahorro; registro original de ingresos y gastos; y saldo calculado por cuenta incluyendo los cuatro tipos de movimiento. La moneda de entrada del formulario principal de ingresos/gastos sigue siendo CRC; cuando la cuenta está en otra moneda se exige una tasa CRC → moneda de cuenta. Los saldos se muestran separados por moneda y no se suman monedas diferentes. Los gastos pueden generar saldos negativos, igual que en el prototipo original. Las transferencias requieren fondos suficientes.

**Limitaciones importantes:** sin autenticación ni sesiones, usuario local de demostración (ID 1); usuarios adicionales no tienen selección de perfil. Los comprobantes tienen tabla pero no formulario de carga de archivos. El panel de presupuestos sigue expresado en CRC y no convierte gastos de otras monedas. El mantenimiento de alertas es manual, no genera notificaciones automáticamente. Las conversiones y saldos son una implementación inicial para pruebas académicas; no usar con datos reales ni publicar en Internet. Para preservar la compatibilidad, no se ha migrado la tabla original `movimientos` a dos tablas físicas `ingresos` y `gastos`. No todas las operaciones complejas cuentan con pruebas automatizadas.

Antes de usar una base existente, respaldar `data/finanzas.sqlite3`. Para pruebas desde cero, usar una carpeta nueva sin ese archivo. Las 10 pruebas de regresión originales pasan con esta entrega.
