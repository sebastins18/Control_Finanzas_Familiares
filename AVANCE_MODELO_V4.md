# Ampliación del prototipo hacia el modelo relacional v4

Esta entrega es una **implementación parcial** y compatible con el MVP existente. No incluye sesiones ni autenticación. Se conserva un usuario local de demostración (ID 1).

## Mantenimientos incorporados

- Categorías: alta, consulta, edición y eliminación.
- Cuentas: alta, consulta, edición y eliminación; moneda y saldo inicial.
- Monedas: alta, consulta, edición y eliminación.
- Tipos de cambio: alta, consulta, edición y eliminación; origen, destino, fecha y tasa.
- Metas de ahorro: alta, consulta, edición y eliminación.
- Transferencias: alta, consulta, edición y eliminación; validación básica de monedas y tipo de cambio.
- Movimientos de ahorro: alta, consulta, edición y eliminación; evita retiros mayores que los aportes netos de una meta.
- Se conservan movimientos de ingresos/gastos, presupuestos y panel del MVP.

## Pendiente para cubrir integralmente el diagrama

- Integrar las monedas y conversiones en ingresos, gastos, presupuestos y panel; actualmente el panel original sigue en CRC.
- Contabilizar transferencias y aportes/retiros de ahorro en los saldos de las cuentas; el mantenimiento registra operaciones, pero el saldo no se recalcula todavía.
- Gestión segura de comprobantes PDF e imágenes (se agregó tabla, no carga de archivos).
- CRUD de usuarios y de presupuestos con eliminación y consulta de todos los períodos.
- Alertas persistidas y marcadas como leídas; las alertas actuales se calculan visualmente.
- Reglas avanzadas de consistencia, aislamiento por usuario, validación de saldos y pruebas completas de los nuevos flujos.

## Ejecución

Desde la raíz del proyecto, ejecutar `python -m src.app` y abrir `http://127.0.0.1:8000/`.

**Precaución:** para probar el nuevo esquema con datos existentes, hacer una copia de `data/finanzas.sqlite3` antes de iniciar. La aplicación crea tablas nuevas y agrega columnas de forma incremental. No exponerla a Internet ni registrar información financiera real: no tiene autenticación ni controles de seguridad suficientes.
