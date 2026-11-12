# Cambios V7 — control de monedas
- Ingresos y gastos en la moneda propia de la cuenta, sin tipo de cambio.
- Transferencias entre monedas con cotización almacenada y conversión automática.
- Resumen mensual separado por moneda; no suma colones, dólares y euros.
- Presupuestos y alertas usan la moneda real de la cuenta de cada gasto.
- Si falta cotización histórica, se marca el presupuesto como parcial y no se generan alertas basadas en totales incompletos.
- El mantenimiento manual de tipos de cambio ya no se ofrece en la interfaz.
- Consulta de cotizaciones en segundo plano. Requiere conexión para cotizaciones nuevas.
- La cotización externa es de referencia y no equivale necesariamente a compra/venta bancaria.

## Pruebas
`python -m unittest discover -s tests -v`

## Ejecución
`python -m src.app`

Proyecto académico local. No utilizar para operaciones financieras reales sin validación adicional.
